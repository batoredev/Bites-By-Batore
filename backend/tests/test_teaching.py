"""Owner scope rules, duplicate decisions, Overture import, and Claude teaching with undo."""

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app import learned, overture, scope, teacher, test_inventory
from app.config import settings
from app.db import Audit, IdentifiedSpot, Session, Venue
from app.spots import upsert_spot


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


@pytest.mark.parametrize(
    "name,excluded",
    [
        ("Sri Marudhamalai Temple", True),
        ("Glaze Gourmet Caterers", True),
        ("Kovai Food Fest", True),
        ("Amma Home Bakers", True),
        ("PSG College Canteen", True),
        ("Kumaraguru College Cricket Ground", True),
        ("Brookefields Mall", True),
        ("INOX Brookefields Mall", False),
        ("Turf 360", False),
        ("Zircon Cafe", False),
        ("Gokulam Park", False),
    ],
)
def test_owner_scope_rules(name, excluded):
    assert bool(scope.out_of_scope(name)) is excluded


def test_carts_and_adults_flags():
    assert scope.unnamed_cart("pani puri cart near the bus stand", ["Generic description"])
    assert not scope.unnamed_cart("Bismi Pani Puri Stall", [])
    assert scope.adults_only("nightlife") and scope.adults_only("food", "Bottoms Up Pub")
    assert not scope.adults_only("cafe", "Zircon Cafe")


def test_new_finds_follow_scope_and_confirmed_names(local):
    with Session() as db:
        temple = upsert_spot(
            db, local.owner, "Eachanari Vinayagar Temple", "park", "", {"source_ids": ["s1"]}
        )
        cart = upsert_spot(db, local.owner, "a pani puri cart", "street_food", "", {"source_ids": ["s2"]})
        generic = upsert_spot(db, local.owner, "a local restaurant", "food", "", {"source_ids": ["s3"]})
        assert temple.status == "quarantined" and temple.data["scope_hold"] == "out_of_scope"
        assert cart.status == "quarantined" and cart.data["scope_hold"] == "street_cart"
        assert generic is None
        # Once the owner confirms an unusual name, later finds of it pass the name check.
        real = spot(db, local.owner, "Hidden Cafe", "cafe", {"operator_named": True})
        db.commit()
        assert "hidden cafe" in learned.load(db, local.owner)["real"]
        again = upsert_spot(db, local.owner, "Hidden Cafe", "cafe", "Peelamedu", {"source_ids": ["s4"]})
        assert again is not None and again.id != real.id


def test_place_manager_shows_cart_out_of_scope_and_adults(local):
    with Session() as db:
        upsert_spot(db, local.owner, "a pani puri cart", "street_food", "", {"source_ids": ["s2"]})
        upsert_spot(db, local.owner, "Sri Ganesh Temple", "park", "", {"source_ids": ["s1"]})
        spot(db, local.owner, "Bottoms Up Pub", "nightlife")
        db.commit()
    places = {
        p["name"]: p
        for p in local.client.get("/api/admin/spots/unpublished", headers=local.auth).json()["places"]
    }
    assert places["a pani puri cart"]["reason_kind"] == "street_cart"
    assert places["Sri Ganesh Temple"]["reason_kind"] == "out_of_scope"
    assert places["Bottoms Up Pub"]["adults_only"] is True


def test_keep_apart_and_chains_stop_duplicate_pairs(local):
    from app.duplicate_agent import run_scan

    c, auth = local.client, local.auth
    with Session() as db:
        a = spot(db, local.owner, "Annapoorna", "food", {"coordinates": {"lat": 11.010, "lng": 76.950}})
        b = spot(db, local.owner, "Annapoorna", "food", {"coordinates": {"lat": 11.030, "lng": 76.970}})
        held = spot(
            db,
            local.owner,
            "Opal Bakes",
            "dessert",
            {"duplicate_review_candidates": [], "quality_issues": ["Possible duplicate branch; review"]},
            "quarantined",
        )
        other = spot(db, local.owner, "Opal Bakes", "dessert", {})
        held.data = {**held.data, "duplicate_review_candidates": [other.id]}
        db.commit()
        ids = a.id, b.id, held.id, other.id
    chain = c.post(
        f"/api/admin/spots/{ids[0]}/distinct", headers=auth, json={"other_id": ids[1], "chain": True}
    )
    assert chain.status_code == 200
    apart = c.post(f"/api/admin/spots/{ids[2]}/distinct", headers=auth, json={"other_id": ids[3]}).json()
    assert apart["released"] == 1
    with Session() as db:
        rules = learned.load(db, local.owner)
        assert "annapoorna" in rules["chains"] and ids[1] in rules["distinct"][ids[0]]
        assert db.get(IdentifiedSpot, ids[2]).status == "identified"
        third = spot(db, local.owner, "Annapoorna", "food", {"coordinates": {"lat": 11.050, "lng": 76.990}})
        db.commit()
        result = run_scan(db, local.owner)
        db.commit()
        assert result["automatic_merged"] == 0
        assert db.get(IdentifiedSpot, third.id).status == "identified"


def test_same_place_merges_and_keeps_the_planner_entry(local):
    c, auth = local.client, local.auth
    with Session() as db:
        a = spot(db, local.owner, "Yukiira", "food", {"coordinates": {"lat": 11.01, "lng": 76.96}})
        b = spot(db, local.owner, "UKIRA", "food", {"source_ids": ["s9"]})
        test_inventory.publish(db, local.owner)
        db.commit()
        survivor, gone = a.id, b.id
    assert (
        c.post(f"/api/admin/spots/{gone}/same-as", headers=auth, json={"target_id": survivor}).status_code
        == 200
    )
    with Session() as db:
        test_inventory.publish(db, local.owner)
        db.commit()
        row = db.get(IdentifiedSpot, survivor)
        assert "UKIRA" in row.data["aliases"] and db.get(IdentifiedSpot, gone).status == "merged"
        assert row.status == "approved" and db.get(Venue, row.venue_id)


def test_teacher_tags_decisions_and_undo_restores_everything(local):
    with Session() as db:
        junk = spot(db, local.owner, "Rainy Day Vibes", "food", {"source_ids": ["s1"]})
        twin = spot(db, local.owner, "rainy day vibes", "food", area="Peelamedu")
        wrong = spot(db, local.owner, "Quartz Pottery Studio", "food")
        held = spot(
            db, local.owner, "Old School Bites", "food", {"quality_issues": ["Generic"]}, "quarantined"
        )
        pub = spot(db, local.owner, "Opal Mess", "street_food", {"coordinates": {"lat": 11.01, "lng": 76.96}})
        test_inventory.publish(db, local.owner)
        db.commit()
        ids = junk.id, twin.id, wrong.id, held.id, pub.id
        decisions = [
            {"id": ids[0], "action": "reject", "kind": "not_a_venue", "note": "mood phrase"},
            {"id": ids[2], "action": "category", "category": "workshop"},
            {"id": ids[3], "action": "real"},
            {"id": ids[4], "action": "cart"},
            {"id": "missing", "action": "real"},
            {"id": ids[2], "action": "explode"},
        ]
        result = teacher.apply(db, local.owner, decisions)
        assert result["applied"] == 4 and len(result["failed"]) == 2
        assert db.get(IdentifiedSpot, ids[1]).status == "quarantined"  # same name held
        assert db.get(IdentifiedSpot, ids[2]).data["operator_edits"][-1]["by"] == learned.TEACHER_ACTOR
        assert all(db.get(IdentifiedSpot, i).data.get("taught_by") for i in (ids[0], ids[2], ids[3], ids[4]))
        assert db.get(IdentifiedSpot, ids[4]).data["scope_hold"] == "street_cart"
        assert not db.get(IdentifiedSpot, ids[4]).venue_id
        assert teacher.report(db, local.owner)["decisions"] == 4
        undone = teacher.undo(db, local.owner)
        assert undone["decisions_undone"] == 4
        assert db.get(IdentifiedSpot, ids[0]).status == "identified"
        assert db.get(IdentifiedSpot, ids[1]).status == "identified"
        assert db.get(IdentifiedSpot, ids[2]).category == "food"
        assert db.get(IdentifiedSpot, ids[3]).status == "quarantined"
        restored = db.get(IdentifiedSpot, ids[4])
        assert restored.status == "approved" and db.get(Venue, restored.venue_id)
        assert "rainy day vibes" not in learned.load(db, local.owner)["rejected"]
        logs = db.scalars(select(Audit).where(Audit.action.like("%teach.%")))
        assert all(log.action.startswith("undone.") or log.action == "teach.undo_all" for log in logs)


def feature(name, kind, lat=11.02, lng=76.96, confidence=0.8, **extra):
    return {
        "id": "ov-" + name,
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": {
            "names": {"primary": name},
            "taxonomy": {"primary": kind},
            "confidence": confidence,
            "addresses": [{"freeform": "12 Main Road", "locality": "RS Puram", "postcode": "641002"}],
            "sources": [{"dataset": "meta", "license": "CDLA-Permissive-2.0"}],
            **extra,
        },
    }


def test_overture_import_enriches_creates_and_respects_scope(local, tmp_path):
    rows = [
        feature("Zircon Cafe", "cafe", websites=["https://zircon.example"]),
        feature("Beryl Biryani", "indian_restaurant"),
        feature("Opal Gym", "gym"),
        feature("Topaz Bowling", "bowling_alley", confidence=0.4),
        feature("Sri Ganesh Temple", "park"),
        feature("Far Away Cafe", "cafe", lat=13.08, lng=80.27),
        feature("Garnet Ice Cream", "restaurant", confidence=0.65),
    ]
    path = tmp_path / "places.geojsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    with Session() as db:
        known = spot(db, local.owner, "Zircon Cafe", "cafe", {"source_ids": ["s1"]})
        db.commit()
        result = overture.import_file(db, local.owner, str(path))
        assert result["considered"] == 4
        assert result["gave_coordinates"] == 1 and result["created"] == 2 and result["created_held"] == 1
        row = db.get(IdentifiedSpot, known.id)
        assert row.data["coordinates"]["lat"] == 11.02 and row.area == "RS Puram"
        assert "https://zircon.example" in row.data["website_candidates"]
        names = {r.name: r for r in db.scalars(select(IdentifiedSpot))}
        assert names["Garnet Ice Cream"].category == "dessert"
        assert names["Sri Ganesh Temple"].data["scope_hold"] == "out_of_scope"
        assert "Opal Gym" not in names and "Topaz Bowling" not in names
        published = test_inventory.publish(db, local.owner)
        assert published["skipped"]["low-confidence Overture only"] == 1  # Garnet at 0.65
        again = overture.import_file(db, local.owner, str(path))
        assert again.get("created", 0) == 0


def test_retune_keeps_overture_types(local, tmp_path):
    path = tmp_path / "places.geojsonl"
    path.write_text(
        "\n".join(
            json.dumps(r) for r in [feature("KG Complex", "movie_theater"), feature("Hari Bhavan", "bakery")]
        ),
        encoding="utf-8",
    )
    with Session() as db:
        overture.import_file(db, local.owner, str(path))
        test_inventory.retune_drafts(db, local.owner)
        names = {r.name: r.category for r in db.scalars(select(IdentifiedSpot))}
        assert names == {"KG Complex": "cinema", "Hari Bhavan": "dessert"}
