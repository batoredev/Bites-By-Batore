"""Owner edits and what the agent learns from them; relevance and video-name checks."""

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app import learned, relevance
from app.analysts import ground_video_candidates
from app.config import settings
from app.db import Claim, IdentifiedSpot, ResearchCorrection, Session, Venue
from app.spots import identify_from_source, upsert_spot


@pytest.fixture
def local(client, monkeypatch):
    monkeypatch.setenv("APP_MODE", "local")
    settings.cache_clear()
    token = client.post("/api/auth/local").json()["access_token"]
    auth = {"Authorization": "Bearer " + token}
    owner = client.get("/api/me", headers=auth).json()["id"]
    yield SimpleNamespace(client=client, auth=auth, owner=owner)
    settings.cache_clear()


def spot(db, owner, name, category="food", data=None, status="identified", area=""):
    row = IdentifiedSpot(
        user_id=owner, identity_key="k:" + name + str(data), name=name, category=category, area=area
    )
    row.data, row.status = data or {}, status
    db.add(row)
    db.flush()
    return row


def reel(code="AAA", caption="", creator="", tag=None, analysis=None):
    return SimpleNamespace(
        id="s-" + code,
        platform="instagram",
        canonical_url=f"https://www.instagram.com/reel/{code}/",
        created_at="2026-11-13T00:00:00+00:00",
        content={"caption": caption, "creator": creator, **({"location_tag": tag} if tag else {})},
        analysis=analysis or {},
        state="collected",
    )


@pytest.mark.parametrize(
    "caption,creator,tag,skipped",
    [
        ("Best biryani in town at Zircon Mess, RS Puram, Coimbatore", "", None, False),
        ("Girl dinner and a movie on Pluto TV, the perfect night in!", "eater", None, True),
        ("Kovai's favourite tea kadai is back with bajji", "", None, False),
        ("Amazing ramen you must try in Chennai this weekend", "chennaifoodspots", None, True),
        ("2 BHK for rent in Saibaba Colony, Coimbatore. Call now", "", None, True),
        (
            "Weekend plan sorted, the food here is unreal",
            "",
            {"name": "Zircon", "lat": 11.02, "lng": 76.96},
            False,
        ),
        (
            "Weekend plan sorted, the food here is unreal",
            "",
            {"name": "Zircon", "lat": 13.08, "lng": 80.27},
            True,
        ),
        ("short", "", None, False),
    ],
)
def test_relevance_needs_a_coimbatore_signal_and_an_in_scope_topic(caption, creator, tag, skipped):
    reason = relevance.assess({"caption": caption, "creator": creator, "location_tag": tag})
    assert bool(reason) is skipped


def test_blocked_creator_and_owner_supplied_sources(local):
    content = {"caption": "Lovely new cafe in Coimbatore, RS Puram", "creator": "Spam_Page"}
    assert relevance.assess(content) == ""
    assert relevance.assess(content, {"spam_page"})
    assert relevance.owner_supplied(SimpleNamespace(context={"url": "https://www.instagram.com/reel/x/"}))
    assert not relevance.owner_supplied(SimpleNamespace(context={"autonomous": True}))


def test_irrelevant_reel_is_skipped_without_analysis(local):
    with Session() as db:
        case = SimpleNamespace(id="c1", user_id=local.owner, context={})
        source = reel(caption="Girl dinner and a movie on Pluto TV, the perfect night in!", creator="eater")
        source.content["media"] = {"base64": "x"}
        db.commit = lambda: None
        assert relevance.try_skip(db, case, source)
        assert source.state == "irrelevant" and "media" not in source.content
        assert source.analysis["video"]["status"] == "skipped_irrelevant"
        assert source.content["processing_outcome"] == "skipped_irrelevant"
        kept = reel(caption="Zircon Cafe, Race Course, Coimbatore has a new menu")
        assert not relevance.try_skip(db, case, kept)
        assert identify_from_source(db, case, source) == []


def test_video_names_need_a_sign_speech_or_caption():
    result = {
        "venue_candidates": [
            {"name": "Zircon Cafe"},
            {"name": "a restaurant with a purple wall"},
            {"name": "Opal Bowling"},
            {"name": "Topaz Mess"},
            {"name": "Genieo"},
        ],
        "observations": [{"verbatim_text": "ZIRCON CAFE", "text": "Sign reads Zircon Cafe"}],
    }
    grounded = ground_video_candidates(
        result, transcript="we are at opal bowling today", caption_candidates=[{"name": "Topaz Mess"}]
    )
    assert [c["name"] for c in grounded["venue_candidates"]] == ["Zircon Cafe", "Opal Bowling", "Topaz Mess"]
    assert {d["name"] for d in grounded["ungrounded_candidates"]} == {
        "a restaurant with a purple wall",
        "Genieo",
    }
    untouched = {"venue_candidates": [], "observations": []}
    assert ground_video_candidates(untouched) is untouched


def test_rename_recategorise_and_release_are_kept_and_reused(local):
    c, auth = local.client, local.auth
    with Session() as db:
        a = spot(db, local.owner, "Chitralaya Art Studio", "food", {"source_ids": ["src-1"]})
        b = spot(db, local.owner, "Quartz Momos", "food")
        d = spot(db, local.owner, "Garnet Momos", "food")
        held = spot(
            db, local.owner, "Family Restaurant", "food", {"quality_issues": ["Generic"]}, "quarantined"
        )
        db.commit()
        ids = (a.id, b.id, d.id, held.id)
    edit = c.post(
        f"/api/admin/spots/{ids[0]}/edit",
        headers=auth,
        json={"name": "Chitralayaa Paint Studio", "category": "workshop", "area": "RS Puram"},
    )
    assert edit.status_code == 200, edit.text
    assert edit.json()["category"] == "workshop"
    for ident in ids[1:3]:
        assert (
            c.post(
                f"/api/admin/spots/{ident}/edit", headers=auth, json={"category": "street_food"}
            ).status_code
            == 200
        )
    assert (
        c.post(f"/api/admin/spots/{ids[3]}/edit", headers=auth, json={"release": True}).json()["status"]
        == "identified"
    )
    assert c.post(f"/api/admin/spots/{ids[1]}/edit", headers=auth, json={}).status_code == 422
    with Session() as db:
        row = db.get(IdentifiedSpot, ids[0])
        assert "Chitralaya Art Studio" in row.data["aliases"] and row.data["operator_named"]
        assert [e["field"] for e in row.data["operator_edits"]] == ["name", "category", "area"]
        correction = db.scalar(select(ResearchCorrection))
        assert (
            correction.scope == "Chitralaya Art Studio" and correction.corrected == "Chitralayaa Paint Studio"
        )
        rules = learned.load(db, local.owner)
        # Same name keeps its category; a word two edits agree on generalises.
        assert learned.category_for(rules, "chitralayaa paint studio") == "workshop"
        assert learned.category_for(rules, "Chitralaya Art Studio") == "workshop"
        assert learned.category_for(rules, "Beryl Momos") == "street_food"
        assert learned.category_for(rules, "Beryl Dosa") is None
        # A later reel using the old spelling attaches to the corrected record.
        again = upsert_spot(db, local.owner, "Chitralaya Art Studio", area="RS Puram", data={})
        assert again is not None and again.id == ids[0]
        # The released generic name is now the owner's call.
        assert db.get(IdentifiedSpot, ids[3]).data["operator_named"]
    summary = c.get("/api/admin/spots/learned", headers=auth).json()
    assert summary["category_by_word"] == {"momos": "street_food"}
    assert summary["renames"] == [{"from": "Chitralaya Art Studio", "to": "Chitralayaa Paint Studio"}]


def test_rejecting_a_name_stops_it_returning_and_restore_undoes_it(local):
    c, auth = local.client, local.auth
    with Session() as db:
        a = spot(db, local.owner, "Rainy Day Bites", "food", {"source_ids": ["src-9"]})
        twin = spot(db, local.owner, "rainy day bites", "food", area="Peelamedu")
        db.commit()
        first, second = a.id, twin.id
    body = c.post(f"/api/admin/spots/{first}/reject", headers=auth, json={"kind": "not_a_venue"}).json()
    assert body["status"] == "rejected" and body["also_held"] == 1
    with Session() as db:
        assert db.get(IdentifiedSpot, second).status == "quarantined"
        assert upsert_spot(db, local.owner, "Rainy Day Bites", area="Gandhipuram", data={}) is None
        assert "rainy day bites" in learned.load(db, local.owner)["rejected"]
    assert (
        c.post(f"/api/admin/spots/{first}/edit", headers=auth, json={"category": "cafe"}).status_code == 409
    )
    assert c.post(f"/api/admin/spots/{first}/restore", headers=auth).json()["status"] == "identified"
    with Session() as db:
        assert "rainy day bites" not in learned.load(db, local.owner)["rejected"]
        assert upsert_spot(db, local.owner, "Rainy Day Bites", area="Gandhipuram", data={}) is not None
    # "Closed" removes the place but teaches nothing about the name.
    assert (
        c.post(f"/api/admin/spots/{first}/reject", headers=auth, json={"kind": "closed"}).status_code == 200
    )
    with Session() as db:
        assert "rainy day bites" not in learned.load(db, local.owner)["rejected"]


def test_rejecting_a_published_test_place_removes_it_from_the_planner(local):
    from app import test_inventory

    c, auth = local.client, local.auth
    with Session() as db:
        row = spot(db, local.owner, "Zircon Cafe", "cafe", {"coordinates": {"lat": 11.01, "lng": 76.96}})
        test_inventory.publish(db, local.owner)
        db.commit()
        ident, venue_id = row.id, row.venue_id
    assert (
        c.post(f"/api/admin/spots/{ident}/edit", headers=auth, json={"category": "dessert"}).status_code
        == 200
    )
    with Session() as db:
        assert db.get(Venue, venue_id).category == "dessert"
    assert (
        c.post(f"/api/admin/spots/{ident}/reject", headers=auth, json={"kind": "closed"}).status_code == 200
    )
    with Session() as db:
        assert db.get(Venue, venue_id) is None
        assert not list(db.scalars(select(Claim).where(Claim.venue_id == venue_id)))
        assert db.get(IdentifiedSpot, ident).venue_id == ""


def test_owner_can_add_known_places_and_publish_them(local):
    c, auth = local.client, local.auth
    link = "https://www.google.com/maps/place/Zircon/@11.0227840,76.9957300,17z"
    one = c.post(
        "/api/admin/spots/add",
        headers=auth,
        json={"names": ["Family Restaurant"], "area": "RS Puram", "maps_url": link, "investigate": False},
    )
    assert one.status_code == 200, one.text
    assert one.json() == {"added": ["Family Restaurant"], "already_listed": [], "investigations_started": 0}
    many = c.post(
        "/api/admin/spots/add",
        headers=auth,
        json={
            "names": ["Opal Bowling Arena", "Family Restaurant", " "],
            "area": "RS Puram",
            "investigate": False,
        },
    ).json()
    assert many["added"] == ["Opal Bowling Arena"] and many["already_listed"] == ["Family Restaurant"]
    bad = c.post(
        "/api/admin/spots/add",
        headers=auth,
        json={"names": ["A", "B Place"], "maps_url": "https://www.google.com/maps/search/zircon"},
    )
    assert bad.status_code == 422
    listed = {p["name"]: p for p in c.get("/api/admin/spots/unpublished", headers=auth).json()["places"]}
    # A generic-looking name the owner typed is trusted, and has its coordinates.
    assert (
        listed["Family Restaurant"]["reason_kind"] == "ready"
        and listed["Family Restaurant"]["source"] == "owner"
    )
    assert listed["Opal Bowling Arena"]["category"] == "bowling"
    assert listed["Opal Bowling Arena"]["reason_kind"] == "no_coordinates"
    result = c.post("/api/admin/spots/publish-ready", headers=auth).json()
    assert result["published"] == 1
    everything = c.get("/api/admin/spots/unpublished?include_published=true", headers=auth).json()
    assert {p["reason_kind"] for p in everything["places"]} == {"published", "no_coordinates"}
    assert everything["published"] == 1 and everything["unpublished"] == 1


def test_vague_plan_requests_do_not_start_research(local, request_data, monkeypatch):
    monkeypatch.setattr(settings(), "autonomous_discovery", True)
    started = []
    monkeypatch.setattr(
        "app.research.start_case", lambda *a, **k: started.append(a) or SimpleNamespace(id="x")
    )
    with Session() as db:
        spot(db, local.owner, "Zircon Cafe", "cafe", {"coordinates": {"lat": 11.01, "lng": 76.96}})
        from app import test_inventory

        test_inventory.publish(db, local.owner)
        db.commit()
    body = {
        **request_data,
        "query": "Something different",
        "categories": ["park"],
        "departure": "2026-11-14T17:00:00+05:30",
    }
    assert local.client.post("/api/plans", headers=local.auth, json=body).json()["options"] == []
    assert started == []
