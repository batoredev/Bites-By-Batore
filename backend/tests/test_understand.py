"""The planner AI's frozen test and its scorer (week 1 item 1.6)."""

import pytest

from app.categories import CATEGORIES
from app.understand import evaluate
from app.understand.baseline import keyword_reading
from app.understand.reading import MOODS, NOVELTY, TIMES, TRANSPORT, expected


def test_frozen_test_is_large_valid_and_has_no_duplicates():
    cases = evaluate.load()
    assert len(cases) >= 100
    texts = [c["text"].casefold() for c in cases]
    assert len(texts) == len(set(texts))
    for c in cases:
        e = c["expect"]
        assert set(e["categories"]) <= set(CATEGORIES), c["text"]
        assert e["time_of_day"] in (None, *TIMES)
        assert e["mood"] in (None, *MOODS)
        assert e["novelty"] in (None, *NOVELTY)
        assert e["transport"] in (None, *TRANSPORT)
        assert e["budget_unit"] in (None, "person", "group")
        assert e["budget_unit"] is None or e["budget"] is not None, c["text"]


def test_frozen_test_covers_every_field_and_category():
    cases = evaluate.load()
    for field in ("party_size", "budget", "budget_unit", "duration_minutes", "vegetarian", "children",
                  "wheelchair", "novelty", "mood", "max_stops", "area", "transport", "avoid",
                  "time_of_day", "surprise", "out_of_scope"):
        assert any(c["expect"][field] not in (None, False, []) for c in cases), field
    named = {cat for c in cases for cat in c["expect"]["categories"]}
    assert named == set(CATEGORIES), set(CATEGORIES) - named


def test_unknown_fields_in_a_label_are_refused():
    with pytest.raises(ValueError):
        expected({"party": 4})


def test_scorer_counts_mentioned_and_silent_fields_separately():
    cases = [{"line": 1, "text": "x", "expect": expected({"party_size": 4})}]
    perfect = evaluate.score(lambda t: {"party_size": 4}, cases)
    inventing = evaluate.score(lambda t: {"party_size": 4, "budget": 900}, cases)
    assert perfect["exact_requests"] == 1.0 and perfect["fields"]["party_size"]["when_mentioned"] == 1.0
    assert inventing["fields"]["budget"]["stayed_empty"] == 0.0 and inventing["exact_requests"] == 0.0


def test_all_exams_are_valid_and_never_appear_in_training_data():
    from app.understand import generate

    texts = set()
    for path in (evaluate.FROZEN, evaluate.FROZEN_B, evaluate.FROZEN_C):
        cases = evaluate.load(path)
        for c in cases:
            assert set(c["expect"]["categories"]) <= set(CATEGORIES), c["text"]
        texts |= {c["text"].casefold().strip() for c in cases}
    sample = generate.dataset(3000, seed=99)
    assert all(len(ex["words"]) == len(ex["tags"]) for ex in sample)
    # The training script drops exact collisions; check they stay rare and short.
    collisions = [ex["text"] for ex in sample if ex["text"].casefold().strip() in texts]
    assert all(len(t.split()) <= 3 for t in collisions)


def test_normalize_keeps_area_names_and_never_doubles_words():
    from app.understand.lexicon import normalize

    assert normalize("pure veg dinner in RS Puram") == ["pure", "veg", "dinner", "in", "rs", "puram"]
    assert normalize("rs 500 each") == ["rupees", "500", "each"]
    assert normalize("go karting") == ["go", "karting"]
    assert normalize("gokarting and biriyani") == ["go", "karting", "and", "biryani"]


def test_value_parsers_read_numbers_in_every_form():
    from app.understand import values

    assert values.people(["4", "of", "us"]) == 4
    assert values.people(["naalu", "peru"]) == 4
    assert values.people(["both", "of", "us"]) == 2
    assert values.people(["just", "me"]) == 1
    assert values.rupees(["under", "2k"]) == 2000
    assert values.rupees(["rupees", "1,200", "per", "person"]) == 1200
    assert values.minutes(["one", "and", "a", "half", "hours"]) == 90
    assert values.minutes(["45", "minutes"]) == 45
    assert values.minutes(["an", "hours"]) == 60
    assert values.stops(["just", "one", "place"]) == 1


@pytest.fixture(scope="module")
def model():
    from app.understand.model import CURRENT, Understander

    return Understander.load(CURRENT)


def test_shipped_model_meets_the_release_bar_on_the_blind_exams(model):
    for path in (evaluate.FROZEN_B, evaluate.FROZEN_C):
        result = evaluate.score(model.read, evaluate.load(path))
        assert result["mentioned_accuracy"] >= 0.95, (path.name, result["mentioned_accuracy"])
        assert all(v == 1.0 for v in result["critical"].values()), (path.name, result["critical"])


def test_model_reads_a_full_request(model):
    r = model.read("cheap biryani then bowling near Peelamedu, 4 of us, 2 hours, 800 per head, pure veg")
    assert set(r["categories"]) == {"food", "bowling"} and r["interests"] == ["biryani"]
    assert (r["party_size"], r["duration_minutes"], r["area"]) == (4, 120, "Peelamedu")
    assert (r["budget"], r["budget_unit"], r["vegetarian"]) == (800, "person", True)


def test_model_never_reads_an_age_as_a_group_size(model):
    assert model.read("zoo with my nephew who is 8")["party_size"] is None
    assert model.read("something for a 5 year old")["party_size"] is None


def test_reading_fills_only_what_was_said_and_explains_it():
    from datetime import datetime

    from app.understand.apply import IST, form_and_chips
    from app.understand.reading import Reading

    r = {**Reading().as_dict(), "categories": ["food"], "interests": ["biryani"], "party_size": 4, "budget": 800,
         "budget_unit": "person", "vegetarian": True, "time_of_day": "evening", "duration_minutes": 90}
    now = datetime(2026, 11, 27, 20, 0, tzinfo=IST)
    form, chips, notices = form_and_chips(r, now=now)
    assert form["party_size"] == 4 and form["budget"] == 800 and form["budget_unit"] == "person"
    assert form["vegetarian"] is True and "children" not in form and "wheelchair" not in form
    assert form["departure"] == "2026-11-28T19:00:00+05:30"  # evening already passed today
    labels = [c["label"] for c in chips]
    assert "4 people" in labels and "₹800 per person" in labels and "1 h 30 min" in labels and "biryani" in labels
    assert notices == []
    form, _, notices = form_and_chips({**r, "party_size": 40, "out_of_scope": True})
    assert "party_size" not in form and any("20 people" in n for n in notices)
    assert any("inside Coimbatore" in n for n in notices)


def test_planner_query_opens_detail_only_requests_and_adds_canonical_dishes():
    from app.understand.apply import planner_query
    from app.understand.reading import Reading

    empty = Reading().as_dict()
    assert planner_query("kids day out", {**empty, "children": True}).endswith("something different")
    assert planner_query("briyani", {**empty, "interests": ["biryani"]}) == "briyani biryani"
    assert planner_query("zxqv", empty) == "zxqv"


def test_understand_endpoint_and_planning_use_the_model(client, auth, request_data):
    body = client.post("/api/understand", headers=auth, json={"text": "biryani for 4, 800 per head"}).json()
    assert body["reader"] == "understand-v1"
    assert body["form"]["party_size"] == 4 and body["form"]["budget_unit"] == "person"
    assert {"fields": ["party_size"], "label": "4 people"} in body["chips"]

    away = client.post("/api/plans", headers=auth, json={**request_data, "query": "plan a trip to Ooty"}).json()
    assert away["options"] == [] and "inside Coimbatore" in away["message"]

    kids = client.post("/api/plans", headers=auth,
                       json={**request_data, "query": "something fun with my son", "children": True}).json()
    assert "no supported match" not in kids.get("message", "")
    assert kids["understood_by"] == "understand-v1"


def test_planning_still_works_when_the_model_file_is_missing(client, auth, request_data, monkeypatch):
    from app.understand import model

    monkeypatch.setattr(model, "CURRENT", model.MODEL_DIR / "missing.json")
    monkeypatch.setattr(model, "_loaded", None)
    body = client.post("/api/plans", headers=auth, json=request_data).json()
    assert body["understood_by"] == "keyword"


def test_keyword_baseline_reads_categories_but_nothing_else():
    reading = keyword_reading("biryani then a movie for 4")
    assert set(reading["categories"]) == {"food", "cinema"} and reading["interests"] == ["biryani"]
    assert "party_size" not in reading
