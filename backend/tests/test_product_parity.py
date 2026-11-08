"""Behavioral acceptance checks for the common discovery, diary and planning flows."""

from datetime import date, timedelta
import pytest
from sqlalchemy import select
from app.db import Session, Venue, Claim, DishEntry
from app.menu import item_key
from app.evidence import validate_value
from app.config import settings


def dish(client, auth):
    return client.get("/api/venues/demo-sushi", headers=auth).json()["menu"]["items"][0]


def put_dish(client, auth, status="favourite", **extra):
    item = dish(client, auth)
    return client.put(
        "/api/venues/demo-sushi/dish-diary/" + item["key"],
        headers=auth,
        json={
            "status": status,
            "tried_on": date.today().isoformat() if status != "want_to_try" else None,
            **extra,
        },
    )


def visit_payload():
    return {
        "venue_id": "demo-sushi",
        "rating": 5,
        "dimensions": {"food": 5, "atmosphere": 5},
        "note": "Private source experience",
        "occasion": "friends",
        "visited_on": date.today().isoformat(),
    }


@pytest.mark.parametrize(
    "items",
    [
        [{"name": "Rice", "price_inr": True}],
        [{"name": "Rice", "price_inr": float("nan")}],
        [{"name": "Rice", "price_inr": -1}],
        [{"name": "Rice", "unit": "per_family"}],
        [{"name": "Rice"}, {"name": "RICE"}],
        [{"name": "++"}],
        [{"name": "Rice", "verified": True}],
    ],
)
def test_unreviewable_menu_values_are_rejected(items):
    assert not validate_value("offerings", items)


def test_reviewed_menu_has_unknowns_without_inventing_popularity(client, auth):
    result = client.get("/api/venues/demo-sushi", headers=auth).json()["menu"]
    assert result["status"] == "current" and len(result["items"]) == 2
    assert all(i["source_url"].startswith("demo://") for i in result["items"])
    assert all("community" not in i and "rating" not in i for i in result["items"])
    assert validate_value("amenities", {"parking": None, "washroom": False})
    assert not validate_value("amenities", {"parking": "yes"})


def test_dish_search_uses_fresh_reviewed_evidence_and_filters(client, auth):
    found = client.get("/api/venues?q=miso", headers=auth).json()
    assert [r["id"] for r in found] == ["demo-sushi"]
    assert any(
        v["id"] == "demo-sushi"
        for v in client.get(
            "/api/venues?cuisine=Japanese&max_price=150&vegetarian=true&washroom=true", headers=auth
        ).json()
    )
    assert client.get("/api/venues?q=miso&parking=true", headers=auth).json() == []
    assert client.get("/api/venues?q=miso&max_price=100", headers=auth).json() == []
    with Session() as db:
        claim = db.scalar(select(Claim).where(Claim.venue_id == "demo-sushi", Claim.field == "offerings"))
        claim.expires_at = "2000-01-01T00:00:00+00:00"
        db.commit()
    assert client.get("/api/venues?q=miso", headers=auth).json() == []
    assert client.get("/api/venues/demo-sushi", headers=auth).json()["menu"]["status"] == "expired"


def test_filters_apply_before_pagination_and_never_publish_pending_rows(client, auth):
    with Session() as db:
        template = db.get(Venue, "demo-sushi")
        for i in range(305):
            db.add(
                Venue(
                    id=f"pagination-{i}",
                    name=f"Aa {i:03d}",
                    category="food",
                    area="RS Puram",
                    address="Isolated fixture",
                    lat=11,
                    lng=77,
                    tags=["specialtoken"] if i == 304 else [],
                    details=template.details,
                    status="published",
                    is_demo=True,
                )
            )
        db.add(
            Venue(
                id="hidden",
                name="Hidden specialtoken",
                category="food",
                area="RS Puram",
                address="Isolated fixture",
                lat=11,
                lng=77,
                tags=["specialtoken"],
                details={},
                status="review",
                is_demo=True,
            )
        )
        db.commit()
    assert [v["id"] for v in client.get("/api/venues?q=specialtoken", headers=auth).json()] == [
        "pagination-304"
    ]
    first = client.get("/api/venues?limit=10", headers=auth).json()
    second = client.get("/api/venues?limit=10&offset=10", headers=auth).json()
    assert len(first) == len(second) == 10 and not ({v["id"] for v in first} & {v["id"] for v in second})


def test_whole_word_search_and_unknown_diet_are_not_positive_matches(client, auth):
    with Session() as db:
        v = db.get(Venue, "demo-sushi")
        v.tags = ["steak"]
        c = db.scalar(select(Claim).where(Claim.venue_id == v.id, Claim.field == "offerings"))
        c.value = {"value": [{"name": "Steak plate", "vegetarian": None}]}
        db.commit()
    assert not any(v["id"] == "demo-sushi" for v in client.get("/api/venues?q=tea", headers=auth).json())
    client.put("/api/me", headers=auth, json={"name": "Test", "vegetarian": True})
    item = dish(client, auth)
    assert not item["eligible_pick"] and item["vegetarian"] is None and item["price_inr"] is None


def test_wishlist_is_not_a_visit_and_repeated_experiences_do_not_amplify_taste(client, auth):
    first = put_dish(client, auth, "want_to_try")
    assert first.status_code == 200 and not first.json()["counts_as_venue_visit"]
    assert client.get("/api/visits", headers=auth).json() == []
    assert client.get("/api/me", headers=auth).json()["profile"]["inferred"] == {}
    for _ in range(3):
        saved = put_dish(client, auth)
        assert saved.status_code == 200
    assert len(client.get("/api/dish-diary", headers=auth).json()) == 1
    assert client.get("/api/me", headers=auth).json()["profile"]["inferred"]["japanese"] == 0.4
    put_dish(client, auth, "not_for_me")
    assert client.get("/api/me", headers=auth).json()["profile"]["inferred"]["japanese"] == -0.4


def test_dated_dish_feedback_and_notes_are_private(client, auth):
    saved = put_dish(client, auth, note="Owner-only dish note").json()
    other = {"Authorization": "Bearer " + client.post("/api/auth/demo").json()["access_token"]}
    assert client.get("/api/dish-diary", headers=other).json() == []
    assert client.delete("/api/dish-diary/" + saved["id"], headers=other).status_code == 404
    assert dish(client, other)["diary_status"] is None
    assert saved["note"] == "Owner-only dish note"
    assert put_dish(client, auth, tried_on=(date.today() + timedelta(days=2)).isoformat()).status_code == 422
    assert put_dish(client, auth, tried_on=None).status_code == 422


def test_expired_menu_stops_new_items_but_preserves_editable_private_history(client, auth):
    saved = put_dish(client, auth).json()
    with Session() as db:
        c = db.scalar(select(Claim).where(Claim.venue_id == "demo-sushi", Claim.field == "offerings"))
        c.expires_at = "2000-01-01T00:00:00+00:00"
        db.commit()
    path = "/api/venues/demo-sushi/dish-diary/" + saved["offering_key"]
    assert (
        client.put(
            path,
            headers=auth,
            json={"status": "tried", "tried_on": date.today().isoformat(), "note": "Edited history"},
        ).status_code
        == 200
    )
    missing = "/api/venues/demo-sushi/dish-diary/" + item_key("not on the menu")
    assert client.put(missing, headers=auth, json={"status": "want_to_try"}).status_code == 404
    assert client.delete("/api/dish-diary/" + saved["id"], headers=auth).status_code == 200


def test_edits_deletion_opt_out_and_clear_rebuild_preferences(client, auth):
    visit = client.post("/api/visits", headers=auth, json=visit_payload()).json()
    saved = put_dish(client, auth).json()
    assert client.get("/api/me", headers=auth).json()["profile"]["inferred"]["japanese"] == 0.8
    changed = {**visit_payload(), "dimensions": {"food": 1, "atmosphere": 1}}
    assert client.put("/api/visits/" + visit["id"], headers=auth, json=changed).status_code == 200
    assert client.get("/api/me", headers=auth).json()["profile"]["inferred"].get("japanese", 0) == 0
    client.delete("/api/dish-diary/" + saved["id"], headers=auth)
    assert client.get("/api/me", headers=auth).json()["profile"]["inferred"]["japanese"] == -0.4
    client.put("/api/me", headers=auth, json={"name": "Test", "learn_from_visits": False})
    assert client.get("/api/me", headers=auth).json()["profile"]["inferred"] == {}
    client.put("/api/me", headers=auth, json={"name": "Test", "learn_from_visits": True})
    assert client.get("/api/me", headers=auth).json()["profile"]["inferred"]["japanese"] == -0.4
    client.delete("/api/visits/" + visit["id"], headers=auth)
    assert client.get("/api/me", headers=auth).json()["profile"]["inferred"] == {}
    put_dish(client, auth)
    assert len(client.get("/api/me/export", headers=auth).json()["dish_diary"]) == 1
    client.delete("/api/me/memory", headers=auth)
    assert client.get("/api/dish-diary", headers=auth).json() == []


def test_experience_ownership_duplicate_dates_and_snapshot_learning(client, auth):
    visit = client.post("/api/visits", headers=auth, json=visit_payload()).json()
    other = {"Authorization": "Bearer " + client.post("/api/auth/demo").json()["access_token"]}
    assert client.put("/api/visits/" + visit["id"], headers=other, json=visit_payload()).status_code == 404
    assert client.delete("/api/visits/" + visit["id"], headers=other).status_code == 404
    assert (
        client.put(
            "/api/visits/" + visit["id"], headers=auth, json={**visit_payload(), "venue_id": "demo-coffee"}
        ).status_code
        == 422
    )
    with Session() as db:
        db.get(Venue, "demo-sushi").tags = ["unrelated-new-tag"]
        db.commit()
    client.put("/api/visits/" + visit["id"], headers=auth, json=visit_payload())
    inferred = client.get("/api/me", headers=auth).json()["profile"]["inferred"]
    assert "unrelated new tag" not in inferred and inferred["japanese"] == 0.4


def test_unapproved_locations_cannot_enter_bookmarks_or_dish_diary(client, auth, monkeypatch):
    with Session() as db:
        v = db.get(Venue, "demo-sushi")
        v.is_demo = False
        db.commit()
    monkeypatch.setattr(settings(), "app_mode", "local")
    assert client.get("/api/venues", headers=auth).json() == []
    assert client.post("/api/venues/demo-sushi/save", headers=auth).status_code == 404
    assert (
        client.put(
            "/api/venues/demo-sushi/dish-diary/" + item_key("Avocado maki"),
            headers=auth,
            json={"status": "want_to_try"},
        ).status_code
        == 404
    )


def test_unknown_intent_and_both_intents_are_not_substring_guesses(client, auth):
    result = client.post(
        "/api/discovery/conversation", headers=auth, json={"message": "display something"}
    ).json()
    assert result["key"] == "purpose"
    result = client.post(
        "/api/discovery/conversation",
        headers=auth,
        json={"message": "food and bowling, quiet please", "answers": {"novelty": "different"}},
    ).json()
    assert result["ready"] and result["suggestion"]["outing_type"] == "combined"
    assert result["suggestion"]["mood"] == "quiet" and result["suggestion"]["novelty"] == "new_taste"
    result = client.post(
        "/api/discovery/conversation", headers=auth, json={"message": "not coffee, gaming"}
    ).json()
    assert result["answers"]["purpose"] == "entertainment"


def test_profile_normalization_and_conflicting_preferences(client, auth):
    r = client.put(
        "/api/me",
        headers=auth,
        json={
            "name": "Test",
            "liked_tags": [" Café ", "cafe"],
            "preferred_cuisines": [" Japanese ", "Japanese"],
            "spice_preference": "mild",
        },
    )
    assert r.status_code == 200
    assert r.json()["profile"]["liked_tags"] == ["cafe"] and r.json()["profile"]["preferred_cuisines"] == [
        "japanese"
    ]
    assert (
        client.put(
            "/api/me", headers=auth, json={"liked_tags": ["Coffee"], "avoided_tags": ["coffee"]}
        ).status_code
        == 422
    )


def test_planner_supports_reviewed_dish_names_and_preserves_constraints(client, auth, request_data):
    query = {**request_data, "query": "miso", "novelty": "new_taste", "mood": "quiet", "max_stops": 1}
    result = client.post("/api/plans", headers=auth, json=query)
    assert result.status_code == 200 and result.json()["options"]
    plan = result.json()["options"][0]
    assert plan["result"]["stops"][0]["venue_id"] == "demo-sushi"
    assert (
        plan["request"]["budget"] == query["budget"] and plan["request"]["party_size"] == query["party_size"]
    )
    assert (
        plan["result"]["total_cost"] <= query["budget"]
        and plan["result"]["total_minutes"] <= query["duration_minutes"]
    )
    assert (
        plan["result"]["stops"][0]["cost"] == 480 * query["party_size"]
    )  # menu item price is not substituted for an outing cost


def test_account_erasure_includes_private_dish_history(client, auth):
    saved = put_dish(client, auth).json()
    assert client.delete("/api/me/data", headers=auth).status_code == 200
    with Session() as db:
        assert db.get(DishEntry, saved["id"]) is None


@pytest.mark.parametrize("field,value", [("vegetarian", "yes"), ("available", "true"), ("price_inr", "120")])
def test_menu_fact_types_do_not_coerce_unknown_strings(field, value):
    assert not validate_value("offerings", [{"name": "Rice", field: value}])


def test_saved_places_beyond_browse_page_remain_private_and_persistent(client, auth):
    with Session() as db:
        source = db.get(Venue, "demo-sushi")
        for i in range(301):
            db.add(
                Venue(
                    id=f"saved-page-{i}",
                    name=f"Aaa {i:03d}",
                    category="food",
                    area="RS Puram",
                    address="Test only",
                    lat=11,
                    lng=77,
                    tags=[],
                    details=source.details,
                    status="published",
                    is_demo=True,
                )
            )
        db.commit()
    assert client.post("/api/venues/demo-sushi/save", headers=auth).json()["saved"]
    assert not any(v["id"] == "demo-sushi" for v in client.get("/api/venues", headers=auth).json())
    assert [v["id"] for v in client.get("/api/me/saved-venues", headers=auth).json()] == ["demo-sushi"]
    other = {"Authorization": "Bearer " + client.post("/api/auth/demo").json()["access_token"]}
    assert client.get("/api/me/saved-venues", headers=other).json() == []


def test_spicy_exclusion_uses_reviewed_spice_fact_without_requiring_duplicate_tags(client, auth):
    with Session() as db:
        c = db.scalar(select(Claim).where(Claim.venue_id == "demo-sushi", Claim.field == "offerings"))
        c.value = {"value": [{"name": "Hot curry", "spice": "hot", "tags": []}]}
        db.commit()
    client.put("/api/me", headers=auth, json={"name": "Test", "avoided_tags": ["spicy"]})
    assert not dish(client, auth)["eligible_pick"]


def test_combined_dish_filters_apply_to_the_same_current_item(client, auth):
    with Session() as db:
        c = db.scalar(select(Claim).where(Claim.venue_id == "demo-sushi", Claim.field == "offerings"))
        c.value = {
            "value": [
                {"name": "Veg bowl", "vegetarian": True, "price_inr": 500, "cuisine": "Japanese"},
                {"name": "Chicken bowl", "vegetarian": False, "price_inr": 100, "cuisine": "Japanese"},
            ]
        }
        db.commit()
    assert client.get("/api/venues?cuisine=Japanese&vegetarian=true&max_price=150", headers=auth).json() == []
    assert client.get("/api/venues?q=Chicken%20bowl&vegetarian=true", headers=auth).json() == []


def test_explicit_bookmark_state_is_idempotent(client, auth):
    for _ in range(3):
        assert client.put("/api/venues/demo-sushi/save", headers=auth, json={"saved": True}).json() == {
            "saved": True
        }
    assert len(client.get("/api/me/saved-venues", headers=auth).json()) == 1
    for _ in range(2):
        assert client.put("/api/venues/demo-sushi/save", headers=auth, json={"saved": False}).json() == {
            "saved": False
        }
    assert client.get("/api/me/saved-venues", headers=auth).json() == []
    assert client.put("/api/venues/demo-sushi/save", headers=auth, json={"saved": "true"}).status_code == 422


def test_live_candidate_checks_prioritize_requested_dish_over_nearest_unrelated_places(
    client, auth, request_data
):
    from app.planner import live_candidate_order
    from app.schemas import OutingRequest
    from app.db import Claim
    from types import SimpleNamespace

    request = OutingRequest(**{**request_data, "query": "Miso soup"})
    with Session() as db:
        target = db.get(Venue, "demo-sushi")
        target.lat = 11.08
        near = [
            SimpleNamespace(
                id=f"near-{i}",
                name="Nearby other food",
                tags=["dosa"],
                category="food",
                lat=request.lat,
                lng=request.lng,
            )
            for i in range(12)
        ]
        claims = list(db.scalars(select(Claim).where(Claim.venue_id == target.id)))
        ordered = live_candidate_order(request, [*near, target], claims)
        assert ordered[0].id == target.id
        locked = request.model_copy(update={"lock_ids": ["near-0"]})
        assert live_candidate_order(locked, [*near, target], claims)[0].id == "near-0"


def test_review_samples_deduplicate_sources_and_keep_conflicting_views(client, auth):
    from datetime import datetime, timezone

    observed = datetime.now(timezone.utc) - timedelta(hours=1)

    def signal(url, group, sentiment, days=2):
        return {
            "source_url": url,
            "evidence_group": group,
            "sentiment": sentiment,
            "observed_at": observed.isoformat(),
            "expires_at": (observed + timedelta(days=days)).isoformat(),
        }

    evidence = [
        signal("https://reviews.example/a", "first", "praise"),
        signal("https://reviews.example/b", "second", "complaint"),
        signal("https://reviews.example/a", "second", "praise"),
        signal("https://reviews.example/c", "old", "praise", -1),
    ]
    # The deliberately expired observation must still precede expiry; use a genuinely older timestamp.
    evidence[-1]["observed_at"] = (observed - timedelta(days=10)).isoformat()
    with Session() as db:
        c = db.scalar(select(Claim).where(Claim.venue_id == "demo-sushi", Claim.field == "offerings"))
        c.value = {"value": [{"name": "Reviewed bowl", "review_evidence": evidence}]}
        db.commit()
    support = dish(client, auth)["review_support"]
    assert support["groups"] == 1 and support["counts"]["mixed"] == 1
    assert support["counts"]["praise"] == support["counts"]["complaint"] == 0
    assert len(support["sources"][0]["sources"]) == 2
    assert not validate_value(
        "offerings", [{"name": "Bowl", "review_evidence": [{**evidence[0], "sentiment": "viral"}]}]
    )
    assert not validate_value(
        "offerings",
        [
            {
                "name": "Bowl",
                "review_evidence": [
                    {**evidence[0], "observed_at": (observed + timedelta(days=20)).isoformat()}
                ],
            }
        ],
    )


def test_unaccepted_review_signals_never_influence_public_dish_picks(client, auth):
    from datetime import datetime, timezone

    observed = datetime.now(timezone.utc) - timedelta(hours=1)
    with Session() as db:
        db.add(
            Claim(
                venue_id="demo-sushi",
                field="offerings",
                value={
                    "value": [
                        {
                            "name": "Unreviewed viral bowl",
                            "review_evidence": [
                                {
                                    "source_url": "https://unreviewed.example/",
                                    "evidence_group": "ad",
                                    "sentiment": "praise",
                                    "observed_at": observed.isoformat(),
                                    "expires_at": (observed + timedelta(days=1)).isoformat(),
                                }
                            ],
                        }
                    ]
                },
                source_url="https://unreviewed.example/",
                source_type="social",
                source_group="fixture",
                observed_at=observed.isoformat(),
                expires_at=(observed + timedelta(days=1)).isoformat(),
                status="review",
            )
        )
        db.commit()
    menu = client.get("/api/venues/demo-sushi", headers=auth).json()["menu"]
    assert all(
        i["name"] != "Unreviewed viral bowl" and i["review_support"]["groups"] == 0 for i in menu["items"]
    )
