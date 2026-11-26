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


def test_keyword_baseline_reads_categories_but_nothing_else():
    reading = keyword_reading("biryani then a movie for 4")
    assert set(reading["categories"]) == {"food", "cinema"} and reading["interests"] == ["biryani"]
    assert "party_size" not in reading
