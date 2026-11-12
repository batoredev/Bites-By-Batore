"""Category rules, the stricter name gate and the agent-approved test inventory."""

import pytest
from sqlalchemy import select

from app import test_inventory
from app.categories import CATEGORIES, FOOD, classify
from app.config import settings
from app.db import Claim, IdentifiedSpot, Session, Venue
from app.geocode import coordinates_from_links
from app.spot_identity import quality_issues

OWNER = "owner"


@pytest.mark.parametrize(
    "name,context,expected",
    [
        ("Black Door Cafe", "", "cafe"),
        ("Sree Selvis Mess", "", "street_food"),
        ("MilkStories Ice Cream", "", "dessert"),
        ("Bottoms Up Pub", "", "nightlife"),
        ("Juice Bar", "", "dessert"),
        ("APA Cinemas", "", "cinema"),
        ("KART Attack Sports Centre", "", "adventure"),
        ("Black Thunder", "", "amusement"),
        ("Turf 360", "", "sports"),
        ("Gass Forest Museum", "", "attraction"),
        ("Clay Station", "wheel pottery", "workshop"),
        ("Semmozhi Poonga", "", "park"),
        ("Parking Lot Grill", "", "food"),
        ("Unknown Name", "", "food"),
    ],
)
def test_classifier_uses_name_then_context(name, context, expected):
    assert classify(name, context) == expected
    assert expected in CATEGORIES


def test_food_group_covers_only_eating_categories():
    assert FOOD == {"food", "street_food", "cafe", "dessert"}


@pytest.mark.parametrize(
    "name",
    [
        "a local food spot in Coimbatore",
        "Pet Friendly Cafe in Coimbatore",
        "Diwali celebration",
        "Avinashi Road Cafe",
        "Ram Nagar branch",
        "Mutton Biryani Restaurant",
        "Coimbatore Corporation Bus Stand",
        "Noyyal River",
        "1RK Rent",
    ],
)
def test_descriptions_and_landmarks_are_not_venue_names(name):
    assert quality_issues(name)


@pytest.mark.parametrize(
    "name",
    [
        "Adisil Unavagam",
        "Cafe Coffee Day",
        "A. R. Bakes",
        "Aarafa Biryani",
        "Gokulam Park Coimbatore",
        "Biggies Burger Saibaba Colony",
        "Hotel Thafta Rawther",
        "Brookefields Cinemas",
    ],
)
def test_real_names_pass_the_gate(name):
    assert not quality_issues(name)


def test_hours_parser_needs_most_of_the_week():
    assert test_inventory.parse_hours(["24/7"])["6"] == [[0, 1440]]
    assert test_inventory.parse_hours(["Mo-Su 10:00-22:00"])["0"] == [[600, 1320]]
    assert test_inventory.parse_hours(["Mo-Fr 09:00-18:00; Sa 10:00-14:00"])["5"] == [[600, 840]]
    week = test_inventory.parse_hours([f"{d} 11:00:00-23:00:00" for d in ["Mo", "Tu", "We", "Th", "Fr"]])
    assert week["4"] == [[660, 1380]] and "6" not in week
    assert test_inventory.parse_hours(["Mo 11:00-23:00", "11am – 11pm (Today)"]) == {}


def spot(db, name, category="food", data=None, status="identified"):
    row = IdentifiedSpot(
        user_id=OWNER, identity_key="k:" + name + str(data), name=name, category=category, data=data or {}
    )
    row.status = status
    db.add(row)
    db.flush()
    return row


@pytest.fixture
def local(client, monkeypatch):
    monkeypatch.setenv("APP_MODE", "local")
    settings.cache_clear()
    yield client
    settings.cache_clear()


def test_publish_marks_estimates_dedupes_and_reverts(local):
    here = {"lat": 11.01, "lng": 76.96}
    with Session() as db:
        spot(db, "Zircon Cafe", "cafe", {"coordinates": here, "sources": [{"url": "https://example.org/a"}]})
        spot(db, "Zircon Café", "cafe", {"coordinates": {"lat": 11.0101, "lng": 76.9601}})
        spot(db, "Zircon Cafe", "cafe", {"coordinates": {"lat": 11.05, "lng": 76.99}})
        spot(
            db,
            "Opal Park",
            "park",
            {
                "coordinates": {"lat": 11.02, "lng": 76.97},
                "hours_candidates": [{"value": "Mo-Su 06:00-19:00"}],
                "offerings": [{"name": "Adult entry", "price_inr": 15}],
            },
        )
        spot(db, "No Point Mess", "street_food", {})
        spot(db, "a local food spot", "food", {"coordinates": here})
        spot(db, "Held Place", "food", {"coordinates": here}, status="quarantined")
        result = test_inventory.publish(db, OWNER)
        db.commit()
        assert result["published"] == 3
        assert result["skipped"] == {
            "no coordinates": 1,
            "outside 40 km": 0,
            "name needs review": 1,
            "duplicate nearby": 1,
        }
        live = select(Venue).where(Venue.is_demo.is_(False))
        venues = {v.name + "@" + str(v.lat): v for v in db.scalars(live)}
        park = next(v for v in venues.values() if v.name == "Opal Park")
        assert park.status == "published" and not park.is_demo
        assert park.details["price_per_person"] == 20 or park.details["price_per_person"] == 15
        assert park.details["test_inventory"]["hours_basis"] == "collected opening-hours text"
        assert park.details["hours"]["0"] == [[360, 1140]]
        cafe = next(v for v in venues.values() if v.category == "cafe")
        assert cafe.details["test_inventory"]["price_basis"] == "estimate"
        assert cafe.details["location_approval"]["by"] == test_inventory.AGENT
        claims = list(db.scalars(select(Claim).where(Claim.venue_id == cafe.id)))
        assert {c.field for c in claims} == {"price_per_person", "hours", "closed"}
        assert all(c.status == "accepted" and "not verified" in c.reason for c in claims)
        # Repeat is a no-op: published drafts are no longer eligible.
        assert test_inventory.publish(db, OWNER)["published"] == 0
        assert test_inventory.revert(db, OWNER) == {"removed_venues": 3, "restored_drafts": 3}
        db.commit()
        assert not list(db.scalars(live))
        assert not list(db.scalars(select(Claim).where(Claim.source_group == "test-inventory")))
        assert all(
            r.status in {"identified", "quarantined"} and not r.venue_id
            for r in db.scalars(select(IdentifiedSpot))
        )


def test_retune_holds_descriptions_and_fixes_categories(local):
    with Session() as db:
        spot(db, "group activities", "food")
        workshop = spot(db, "Clay Corner", "food", {"offerings": [{"name": "wheel pottery"}]})
        directory = spot(db, "Sri Ram Bakery", "food", {"directory_refs": ["node/1"]})
        cinema = spot(db, "Cinema Paradiso Restaurant", "cinema", {"directory_refs": ["node/2"]})
        result = test_inventory.retune_drafts(db, OWNER)
        assert result["held"] == 1
        assert workshop.category == "workshop" and directory.category == "dessert"
        # A directory tag outranks a name keyword.
        assert cinema.category == "cinema"


def test_link_coordinates_require_agreement(local):
    with Session() as db:
        agree = spot(
            db,
            "Quartz Kitchen",
            data={
                "maps_links": [
                    "https://www.google.com/maps/dir/?api=1&destination=11.0227840000,76.9957300000",
                    "https://www.google.com/maps/dir/?api=1&destination=11.02276820,76.99572990",
                    "https://maps.app.goo.gl/abc",
                ]
            },
        )
        differ = spot(
            db,
            "Garnet Kitchen",
            data={
                "maps_links": [
                    "https://www.google.com/maps/dir/?api=1&destination=11.00566950,76.95017860",
                    "https://www.google.com/maps/dir/?api=1&destination=11.04370590,77.04250070",
                ]
            },
        )
        assert coordinates_from_links(db, OWNER) == {"set": 1, "links_disagree": 1, "outside_40_km": 0}
        assert agree.data["coordinates"]["lat"] == pytest.approx(11.022784)
        assert "coordinates" not in differ.data


def test_local_planner_uses_test_inventory_without_a_map_provider(local, request_data):
    token = local.post("/api/auth/local").json()["access_token"]
    auth = {"Authorization": "Bearer " + token}
    owner = local.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        for index, (name, category) in enumerate(
            [("Zircon Cafe", "cafe"), ("Opal Park", "park"), ("Topaz Mess", "street_food")]
        ):
            row = spot(db, name, category, {"coordinates": {"lat": 11.01 + index / 500, "lng": 76.95}})
            row.user_id = owner
        test_inventory.publish(db, owner)
        db.commit()
    body = {
        **request_data,
        "query": "Something different",
        "categories": ["cafe", "park", "street_food"],
        "departure": "2026-11-14T17:00:00+05:30",
    }
    response = local.post("/api/plans", headers=auth, json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["options"], result
    assert any("Test inventory" in w for w in result["options"][0]["result"]["warnings"])
    listed = local.get("/api/venues", headers=auth).json()
    assert len(listed) == 3 and {v["freshness"] for v in listed} == {"test estimate"}


def test_reference_with_extra_feature_points_no_longer_fails_matching():
    import base64

    import cv2
    import numpy as np

    from app.visual_places import MAX_POINTS, compare, signature

    rng = np.random.default_rng(7)
    image = (rng.random((600, 800)) * 255).astype(np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    current = signature(encoded.tobytes())
    assert len(current["points"]) <= MAX_POINTS
    # A reference stored before the bound: 501 points, 16,032 descriptor bytes.
    raw = base64.b64decode(current["descriptors"])
    legacy = {
        **current,
        "points": [*current["points"], current["points"][0]][: len(current["points"]) + 1],
        "descriptors": base64.b64encode(raw + raw[:32]).decode(),
    }
    assert len(legacy["points"]) * 32 == len(base64.b64decode(legacy["descriptors"]))
    assert compare(current, legacy)["matched"] is True
    with pytest.raises(ValueError):
        compare(current, {**current, "descriptors": base64.b64encode(raw[:-32]).decode()})


def test_damaged_reference_is_skipped_not_fatal(local):
    from app.visual_places import match_frames

    with Session() as db:
        spot(
            db,
            "Zircon Cafe",
            "cafe",
            {
                "visual_references": [
                    {
                        "url": "https://x.example/a.jpg",
                        "page_url": "https://x.example",
                        "signature": {"points": [[1, 1]] * 30, "descriptors": "AAAA"},
                    }
                ]
            },
        )
        frame = {
            "seconds": 1,
            "signature": {"points": [[1, 1]] * 30, "descriptors": "AAAA", "width": 1, "height": 1},
        }
        result = match_frames(db, OWNER, [frame])
        assert result["unusable_reference_count"] == 1 and result["matches"] == []


def test_collector_keeps_smaller_streams_in_quality_order():
    from app.browser_sources import extract_public_data, public_video_references

    cdn = "https://scontent.cdninstagram.com/v/"
    manifest = (
        '<MPD><Period><AdaptationSet contentType="video">'
        f'<Representation mimeType="video/mp4" width="360" bandwidth="300000"><BaseURL>{cdn}low.mp4</BaseURL></Representation>'
        f'<Representation mimeType="video/mp4" width="720" bandwidth="900000"><BaseURL>{cdn}mid.mp4</BaseURL></Representation>'
        "</AdaptationSet></Period></MPD>"
    )
    assert public_video_references(manifest) == [cdn + "mid.mp4", cdn + "low.mp4"]
    item = {
        "code": "ABC123xyz",
        "media_type": 2,
        "video_versions": [
            {"url": cdn + "small.mp4", "width": 480, "height": 854},
            {"url": cdn + "big.mp4", "width": 1080, "height": 1920},
        ],
        "video_dash_manifest": manifest,
    }
    data = extract_public_data([item], "ABC123xyz", "")
    assert data["media_url"] == cdn + "big.mp4"
    assert data["media_alternatives"] == [cdn + "small.mp4", cdn + "mid.mp4", cdn + "low.mp4"]


@pytest.mark.parametrize(
    "caption,creator,names,kept",
    [
        (
            "Movie night at Broadway Cinemas then coffee at Terminal 2",
            "",
            ["Broadway Cinemas", "Terminal 2"],
            2,
        ),
        ("Dinner date 📍 @warehousecoimbatore #coimbatore", "abhii.pradeep", ["Warehouse Coimbatore"], 1),
        (
            "31 likes - cookinforbae19 on November 3: Dinner and a movie",
            "cookinforbae19",
            ["new cafe in Coimbatore"],
            0,
        ),
        (
            "Find the location 📍 Gandhipuram #justsaappaadu - @just_saappaadu",
            "just_saappaadu",
            ["just saappaadu"],
            0,
        ),
        ("Send this to a friend - @thefairytalefoodie on October 24", "", ["@thefairytalefoodie"], 0),
        (
            "Rain karting! 📍 Apex Karting Arena, Coimbatore #apexkartingarena",
            "apexkartingcbe",
            ["Apex Karting Arena"],
            1,
        ),
    ],
)
def test_caption_names_must_be_written_in_the_caption(caption, creator, names, kept):
    from app.analysts import ground_candidates

    result = ground_candidates({"venue_candidates": [{"name": n} for n in names]}, caption, creator)
    assert len(result["venue_candidates"]) == kept
    assert len(result.get("ungrounded_candidates", [])) == len(names) - kept


def test_caption_specialist_can_use_a_separate_text_model(monkeypatch):
    from app import local_models

    cfg = settings()
    monkeypatch.setattr(cfg, "ollama_text_model", "")
    assert local_models.model_for("caption") == cfg.ollama_model
    monkeypatch.setattr(cfg, "ollama_text_model", "fixture-text:4b")
    assert local_models.model_for("caption") == "fixture-text:4b"
    assert local_models.model_for("video") == cfg.ollama_model
    assert local_models.model_for("comments") == cfg.ollama_model


def test_location_tag_is_read_from_the_reel_record():
    from app.browser_sources import extract_public_data

    item = {
        "code": "ABC123xyz",
        "media_type": 2,
        "location": {"pk": 325274813, "lat": 11.085072, "lng": 76.945472, "name": "Zircon  Cafe"},
    }
    tag = extract_public_data([item], "ABC123xyz", "")["location_tag"]
    assert tag == {"name": "Zircon Cafe", "lat": 11.085072, "lng": 76.945472, "id": "325274813"}
    assert "location_tag" not in extract_public_data([{**item, "location": None}], "ABC123xyz", "")


def test_location_tag_gives_a_draft_its_coordinates(local):
    from types import SimpleNamespace

    from app.spots import identify_from_source

    def reel(code, analysis, tag):
        return SimpleNamespace(
            id="s-" + code,
            platform="instagram",
            canonical_url=f"https://www.instagram.com/reel/{code}/",
            created_at="2026-11-12T00:00:00+00:00",
            content={"location_tag": tag},
            analysis=analysis,
        )

    case = SimpleNamespace(id="case-1", user_id=OWNER)
    with Session() as db:
        named = reel(
            "AAA",
            {
                "caption": {
                    "venue_candidates": [{"name": "Zircon Cafe", "address_clues": [], "dish_or_activity": ""}]
                }
            },
            {"name": "Zircon Cafe", "lat": 11.02, "lng": 76.96},
        )
        identify_from_source(db, case, named)
        only_tag = reel("BBB", {}, {"name": "Opal Bowling Arena", "lat": 11.03, "lng": 76.97})
        identify_from_source(db, case, only_tag)
        area_tag = reel("CCC", {}, {"name": "Thudiyalur,Coimbatore", "lat": 11.08, "lng": 76.94})
        identify_from_source(db, case, area_tag)
        rows = {r.name: r for r in db.scalars(select(IdentifiedSpot))}
        assert set(rows) == {"Zircon Cafe", "Opal Bowling Arena"}
        assert rows["Zircon Cafe"].data["coordinates"]["lat"] == 11.02
        assert rows["Opal Bowling Arena"].category == "bowling"
        assert "Instagram location tag" in rows["Opal Bowling Arena"].data["coordinates"]["basis"]


def test_maintenance_alert_keeps_test_venue_published(local):
    from app.maintenance import hold_published

    with Session() as db:
        row = spot(db, "Zircon Cafe", "cafe", {"coordinates": {"lat": 11.01, "lng": 76.96}})
        test_inventory.publish(db, OWNER)
        hold_published(db, row, "A supporting page changed")
        db.commit()
        venue = db.get(Venue, row.venue_id)
        assert venue.status == "published" and venue.details["location_approval"]
        assert row.status == "approved"


def test_unpublished_listing_explains_why_each_place_is_missing(local):
    token = local.post("/api/auth/local").json()["access_token"]
    auth = {"Authorization": "Bearer " + token}
    owner = local.get("/api/me", headers=auth).json()["id"]
    here = {"lat": 11.01, "lng": 76.96}
    with Session() as db:
        rows = [
            spot(db, "Zircon Cafe", "cafe", {"coordinates": here}),
            spot(
                db,
                "No Point Mess",
                "street_food",
                {"sources": [{"type": "instagram", "url": "https://i.example/r"}]},
            ),
            spot(
                db,
                "Held Place",
                "food",
                {"quality_issues": ["Possible duplicate branch; review this proposal"]},
                status="quarantined",
            ),
        ]
        for row in rows:
            row.user_id = owner
        test_inventory.publish(db, owner)
        db.commit()
    body = local.get("/api/admin/spots/unpublished", headers=auth).json()
    assert body["published"] == 1 and body["unpublished"] == 2
    by_name = {p["name"]: p for p in body["places"]}
    assert "Zircon Cafe" not in by_name
    assert by_name["No Point Mess"]["reason_kind"] == "no_coordinates"
    assert by_name["No Point Mess"]["source"] == "instagram"
    assert by_name["Held Place"]["reason_kind"] == "duplicate"


def test_planner_returns_as_many_distinct_plans_as_requested(local, request_data):
    token = local.post("/api/auth/local").json()["access_token"]
    auth = {"Authorization": "Bearer " + token}
    owner = local.get("/api/me", headers=auth).json()["id"]
    kinds = ["cafe", "park", "street_food", "dessert", "food", "cafe", "park", "dessert"]
    with Session() as db:
        for index, category in enumerate(kinds):
            row = spot(
                db,
                f"Quartz Place {index}",
                category,
                {"coordinates": {"lat": 11.01 + index / 400, "lng": 76.95}},
            )
            row.user_id = owner
        test_inventory.publish(db, owner)
        db.commit()
    body = {
        **request_data,
        "query": "Something different",
        "categories": ["cafe", "park", "street_food", "dessert", "food"],
        "departure": "2026-11-14T17:00:00+05:30",
    }
    three = local.post("/api/plans", headers=auth, json=body).json()
    assert len(three["options"]) == 3 and three["total_options"] > 3
    many = local.post("/api/plans", headers=auth, json={**body, "max_options": 60}).json()
    assert len(many["options"]) == min(60, many["total_options"]) > 3
    sets = [tuple(sorted(s["venue_id"] for s in o["result"]["stops"])) for o in many["options"]]
    assert len(sets) == len(set(sets))
    scores = [o["result"]["score"] for o in many["options"]]
    assert scores == sorted(scores, reverse=True)
