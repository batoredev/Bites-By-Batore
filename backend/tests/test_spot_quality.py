"""Identity/relevance regression cases use isolated SQLite and invented fixtures."""

import pytest
from sqlalchemy import select
from app.db import Session, IdentifiedSpot, Venue
from app.config import settings
from app.spots import upsert_spot, reconcile_spots, identify_from_source
from app.spot_identity import maps_reference, infer_area, name_key
from app import research


def evidence(url="https://www.instagram.com/reel/fixture/", **extra):
    return {"sources": [{"url": url, "type": "instagram", "collected_at": "2026-11-01T00:00:00Z"}], **extra}


def test_dedup_same_reel_different_name_order_and_missing_area(client):
    with Session() as db:
        a = upsert_spot(db, "owner", "Cafe Zircon", data=evidence())
        b = upsert_spot(db, "owner", "Zircon Café", area="RS Puram", data=evidence())
        assert a.id == b.id and b.area == "RS Puram"
        assert len(b.data["aliases"]) == 2
        assert len(list(db.scalars(select(IdentifiedSpot)))) == 1


def test_same_name_different_branch_or_owner_never_merged(client):
    with Session() as db:
        a = upsert_spot(db, "owner", "Zircon Cafe", area="Peelamedu", data=evidence())
        b = upsert_spot(db, "owner", "Zircon Cafe", area="RS Puram", data=evidence())
        c = upsert_spot(db, "other", "Zircon Cafe", area="Peelamedu", data=evidence())
        d = upsert_spot(
            db, "owner", "Zircon Cafe", area="Peelamedu", data=evidence(address="11 Fixture Street")
        )
        e = upsert_spot(
            db, "owner", "Zircon Cafe", area="Peelamedu", data=evidence(address="22 Fixture Street")
        )
        assert len({a.id, b.id, c.id}) == 3
        assert d.id != e.id


def test_explicit_branch_keys_are_preserved(client):
    with Session() as db:
        a = upsert_spot(db, "owner", "Zircon Cafe", branch_key="north", data=evidence())
        b = upsert_spot(db, "owner", "Zircon Cafe", branch_key="south", data=evidence())
        assert a.id != b.id


def test_typo_is_flagged_not_silently_merged(client):
    with Session() as db:
        a = upsert_spot(db, "owner", "Zircona Cafe", data=evidence())
        b = upsert_spot(db, "owner", "Zirconna Cafe", data=evidence())
        assert a.id != b.id and a.id in b.data["possible_duplicates"]


@pytest.mark.parametrize(
    "name,clues",
    [
        ("New Cafe in Coimbatore", ["Coimbatore"]),
        ("Aesthetic Café", ["Coimbatore"]),
        ("RS Puram", ["Coimbatore"]),
        ("go-karting facility", ["Coimbatore"]),
        ("Zircon Cafe", ["Arumbakkam, Chennai"]),
        ("Fixture Textiles", ["Coimbatore"]),
    ],
)
def test_irrelevant_candidates_never_enter_inventory(client, name, clues):
    with Session() as db:
        assert upsert_spot(db, "owner", name, data=evidence(address_clues=clues)) is None
        assert not list(db.scalars(select(IdentifiedSpot)))


def test_refresh_updates_receipt_without_repeating_source_or_item(client):
    with Session() as db:
        a = upsert_spot(
            db,
            "owner",
            "Zircon Cafe",
            data=evidence(
                offerings=[
                    {
                        "name": "Soup",
                        "unit": "item",
                        "price_inr": 100,
                        "source_url": "https://fixture.example/menu",
                    }
                ]
            ),
        )
        newer = evidence(
            offerings=[
                {
                    "name": "soup",
                    "unit": "item",
                    "price_inr": 100,
                    "source_url": "https://fixture.example/menu",
                }
            ]
        )
        newer["sources"][0]["collected_at"] = "2026-11-06T00:00:00Z"
        b = upsert_spot(db, "owner", "Zircon Cafe", data=newer)
        db.commit()
        db.expire_all()
        assert a.id == b.id and len(b.data["sources"]) == len(b.data["offerings"]) == 1
        assert b.data["sources"][0]["first_collected_at"].startswith("2026-11-01")
        assert b.data["sources"][0]["collected_at"].startswith("2026-11-06")


def test_cleanup_retains_originals_and_is_idempotent(client):
    with Session() as db:
        rows = [
            IdentifiedSpot(user_id="owner", identity_key=str(i), name=name, area=area, data=evidence())
            for i, (name, area) in enumerate(
                [("Zircon Cafe", ""), ("Zircon Cafe", "RS Puram"), ("New Cafe in Coimbatore", "")]
            )
        ]
        db.add_all(rows)
        db.commit()
        result = reconcile_spots(db, "owner")
        db.commit()
        assert result["merged"] == result["quarantined"] == 1
        assert len(list(db.scalars(select(IdentifiedSpot)))) == 3
        assert len([r for r in rows if r.status == "identified"]) == 1
        assert not any(reconcile_spots(db, "owner").values())
        # Replaying a merged spelling resolves to its surviving record.
        row = upsert_spot(db, "owner", "Zircon Cafe", data=evidence())
        assert row.status == "identified"


def test_multivenue_observations_not_assigned_to_every_candidate(client):
    with Session() as db:
        case = research.start_case(
            db,
            "owner",
            "Coimbatore cafes",
            seed_sources=[{"platform": "instagram", "url": "https://www.instagram.com/reel/fixture/"}],
        )
        source = research.case_sources(db, case)[0]
        source.analysis = {
            "caption": {
                "venue_candidates": [
                    {"name": "Zircon Cafe", "address_clues": ["Coimbatore"], "dish_or_activity": "tea"},
                    {"name": "Beryl Cafe", "address_clues": ["Coimbatore"], "dish_or_activity": "coffee"},
                    {"name": "New Cafe in Coimbatore", "address_clues": [], "dish_or_activity": "food"},
                ],
                "observations": [
                    {"text": "Zircon Cafe is quiet", "basis": "caption"},
                    {"text": "There are outdoor tables", "basis": "caption"},
                ],
            }
        }
        identify_from_source(db, case, source)
        rows = list(db.scalars(select(IdentifiedSpot)))
        assert len(rows) == 2
        assert next(r for r in rows if r.name == "Beryl Cafe").data["vibes"] == []
        assert any(x["decision"] == "held" for x in source.analysis["inventory_checks"])


def test_area_punctuation_and_accents():
    assert infer_area(["30 Subramaniam Rd, R.S. Puram, Coimbatore"]) == "RS Puram"
    assert name_key("Café_Zircon") == "cafe zircon"
    assert name_key("கோவை") == "கோவை"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.google.com/maps/search/?api=1&query=Zircon",
        "https://www.google.com/maps/dir//11.01,76.96",
        "https://www.google.com.evil.example/maps?cid=123",
        "https://maps.app.goo.gl/fixture",
        "https://www.google.com/search?cid=123",
    ],
)
def test_maps_reference_rejects_generic_or_wrong_host(url):
    with pytest.raises(ValueError):
        maps_reference(url)


def test_maps_identity_accepts_precise_id_and_cid():
    assert (
        maps_reference(
            "https://www.google.com/maps/search/?api=1&query=Zircon&query_place_id=ChIJfixture123"
        )["place_id"]
        == "ChIJfixture123"
    )
    a = maps_reference("https://www.google.com/maps/place/Zircon/data=!4m2!3m1!1s0x123:0x7b")
    assert a["place_key"] == maps_reference("https://www.google.com/maps?cid=123")["place_key"]


def preparation():
    return {
        "venue": {
            "name": "Zircon Cafe",
            "category": "cafe",
            "area": "RS Puram",
            "address": "Fixture address Coimbatore",
            "lat": 11.01,
            "lng": 76.96,
            "details": {"branch_confirmed": True},
        },
        "evidence_url": "https://fixture.example/branch",
        "reason": "Operator independently checked this test branch",
        "maps_url": "https://www.google.com/maps?cid=123",
        "maps_name_checked": True,
    }


def test_maps_confirmation_required_and_duplicate_place_blocked(client, auth, monkeypatch):
    user = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        a = upsert_spot(db, user, "Zircon Cafe")
        b = upsert_spot(db, user, "Beryl Cafe")
        db.commit()
        aid, bid = a.id, b.id
    monkeypatch.setattr(settings(), "app_mode", "local")
    # Local auth uses a different operator; use the dependency's same owner for this isolated request.
    from app.main import app
    from app.auth import admin_user
    from types import SimpleNamespace

    app.dependency_overrides[admin_user] = lambda: SimpleNamespace(id=user)
    try:
        body = preparation()
        body["maps_name_checked"] = False
        assert client.post(f"/api/admin/spots/{aid}/prepare", json=body).status_code == 422
        body["maps_name_checked"] = True
        result = client.post(f"/api/admin/spots/{aid}/prepare", json=body)
        assert result.status_code == 200, result.text
        assert client.post(f"/api/admin/spots/{bid}/prepare", json=body).status_code == 409
        with Session() as db:
            spot = db.get(IdentifiedSpot, aid)
            assert spot.data["maps_identity"]["confirmed_by"] == user
            assert db.get(Venue, spot.venue_id).status == "pending"
    finally:
        app.dependency_overrides.clear()


def test_cleanup_listing_and_manual_merge_are_owner_scoped(client, auth):
    user = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        a = upsert_spot(db, user, "Zircon Cafe")
        b = upsert_spot(db, user, "Zircona Cafe")
        other = upsert_spot(db, "another-owner", "Zircon Cafe")
        db.commit()
        aid, bid, oid = a.id, b.id, other.id
    body = {
        "target_id": oid,
        "same_branch_checked": True,
        "reason": "Checked test branch against independent fixture",
    }
    assert client.post(f"/api/admin/spots/{aid}/merge", json=body, headers=auth).status_code == 404
    body["target_id"] = bid
    assert client.post(f"/api/admin/spots/{aid}/merge", json=body, headers=auth).status_code == 200
    assert len(client.get("/api/admin/spots", headers=auth).json()["spots"]) == 1
    assert len(client.get("/api/admin/spots?include_held=true", headers=auth).json()["spots"]) == 2


def test_missing_maps_provider_is_honest_and_does_not_save_guessed_name(client, auth, monkeypatch):
    user = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        row = upsert_spot(db, user, "Zircon Cafe")
        db.commit()
        sid = row.id
    monkeypatch.setattr(settings(), "google_maps_api_key", "")
    response = client.post(f"/api/admin/spots/{sid}/maps-candidates", headers=auth)
    assert response.status_code == 200 and response.json()["status"] == "unavailable"
    with Session() as db:
        assert "maps_identity" not in db.get(IdentifiedSpot, sid).data
