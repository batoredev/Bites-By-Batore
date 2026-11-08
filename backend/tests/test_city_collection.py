"""Isolated invented directory fixtures; no real facts or approvals are created."""

import json
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from app import city_collection as c, jobs, research
from app.db import Session, IdentifiedSpot, Venue, Claim, Counter, Job
from app.providers import Unavailable
from app.spots import upsert_spot
from app.maintenance import page_urls


def element(ident=1, lat=11.01, lon=76.95, **tags):
    return {
        "id": ident,
        "type": "node",
        "lat": lat,
        "lon": lon,
        "tags": {"name": "Zircon Cafe", "amenity": "cafe", **tags},
    }


def load(db, *items, owner="owner"):
    return c.import_directory(db, owner, {"elements": list(items)}, "2026-11-08T00:00:00+00:00")


def test_directory_replay_preserves_license_unknowns_and_no_publication(client):
    with Session() as db:
        before = (len(list(db.scalars(select(Venue)))), len(list(db.scalars(select(Claim)))))
        data = element(
            opening_hours="Mo-Sa 10:00-20:00",
            cuisine="indian;coffee",
            outdoor_seating="yes",
            website="https://fixture.example/menu",
        )
        assert load(db, data)["created"] == 1
        assert load(db, data)["created"] == 0
        row = db.scalar(select(IdentifiedSpot))
        assert row.status == "identified" and not row.venue_id
        assert len(row.data["sources"]) == 1
        assert row.data["source_licenses"][0]["attribution"] == c.ATTRIBUTION
        assert row.data["hours_candidates"][0]["value"] == "Mo-Sa 10:00-20:00"
        assert not row.data.get("hours") and not row.data.get("offerings")
        assert not row.data.get("maps_identity")
        assert page_urls(row) == ["https://fixture.example/menu"]
        assert (len(list(db.scalars(select(Venue)))), len(list(db.scalars(select(Claim))))) == before


def test_owner_isolation_and_distinct_physical_branches(client):
    with Session() as db:
        load(db, element(), element(2, lat=11.03))
        load(db, element(), owner="other")
        rows = list(db.scalars(select(IdentifiedSpot)))
        assert len(rows) == 3
        assert all(r.status == "identified" for r in rows)
        assert c.coverage(db, "other")["active_drafts"] == 1


def test_nearby_node_way_duplicate_but_address_conflicts_stay_separate(client):
    with Session() as db:
        node = element(**{"addr:street": "Fixture Road", "addr:housenumber": "14"})
        way = {
            **element(2, **{"addr:street": "Fixture Road", "addr:housenumber": "14"}),
            "type": "way",
            "center": {"lat": 11.01001, "lon": 76.95},
        }
        different = element(3, **{"addr:street": "Fixture Road", "addr:housenumber": "22"})
        result = load(db, node, way, different)
        assert result["created"] == 2 and result["updated"] == 1
        rows = list(db.scalars(select(IdentifiedSpot)))
        assert len(rows[0].data["directory_refs"]) == 2
        assert len(rows) == 2


def test_area_only_match_with_existing_reel_is_held_not_auto_merged(client):
    with Session() as db:
        existing = upsert_spot(
            db,
            "owner",
            "Zircon Cafe",
            "cafe",
            "RS Puram",
            {"sources": [{"url": "https://www.instagram.com/reel/fixture/"}]},
        )
        db.commit()
        result = load(db, element(**{"addr:suburb": "RS Puram"}))
        assert result["created"] == 1 and result["held"] == 1
        assert not existing.data.get("directory_refs")
        held = db.scalar(select(IdentifiedSpot).where(IdentifiedSpot.status == "quarantined"))
        assert held.data["duplicate_review_candidates"] == [existing.id]


def test_rejected_and_merged_originals_are_not_reactivated(client):
    with Session() as db:
        load(db, element(), element(2, lat=11.03))
        rows = list(db.scalars(select(IdentifiedSpot)))
        rows[0].status = "merged"
        rows[0].data = {**rows[0].data, "merged_into": rows[1].id}
        rows[1].status = "rejected"
        db.commit()
        assert load(db, element())["created"] == 0
        assert rows[0].status == "merged" and rows[1].status == "rejected"
        assert "node/1" in rows[1].data["directory_refs"]


@pytest.mark.parametrize(
    "bad", [element(lat=float("nan")), element(lat=12), element(ident=True), element(amenity="hospital")]
)
def test_unsupported_and_invalid_candidates_never_enter_inventory(client, bad):
    with Session() as db:
        assert load(db, bad)["outside_or_unsupported"] == 1
        assert not list(db.scalars(select(IdentifiedSpot)))


def test_partial_directory_fails_before_any_insertion(client):
    with Session() as db:
        with pytest.raises(Unavailable):
            c.import_directory(db, "owner", {"remark": "timeout", "elements": [element()]})
        assert not list(db.scalars(select(IdentifiedSpot)))


def test_directory_cache_reuse_makes_no_network_request(client, monkeypatch, tmp_path):
    from app.db import now

    folder = tmp_path / "data" / "city-collection"
    folder.mkdir(parents=True)
    boundary = {
        "id": 99,
        "type": "relation",
        "tags": {"boundary": "administrative", "name": "Coimbatore", "admin_level": "5"},
    }
    (folder / "osm-coimbatore-candidates.json").write_text(
        json.dumps({"elements": [element(), boundary]}), encoding="utf-8"
    )
    (folder / "osm-fetch.json").write_text(json.dumps({"at": now(), "query": c.QUERY}), encoding="utf-8")
    monkeypatch.setattr(c, "ROOT", tmp_path)
    import httpx

    def forbidden(*a, **k):
        pytest.fail("A fresh directory cache must not make a network request")

    monkeypatch.setattr(httpx, "Client", forbidden)
    with Session() as db:
        assert c.collect_directory(db, "owner")["created"] == 1


def test_missing_boundary_cannot_silently_use_broad_radius():
    with pytest.raises(Unavailable, match="boundary missing"):
        c.area_scope({"elements": [element()]})


def test_scope_reconciliation_holds_outside_leads_keeps_originals_and_owners(client):
    with Session() as db:
        load(db, element(), element(2, lat=11.03))
        load(db, element(2, lat=11.03), owner="other")
        scope = {"name": "fixture Coimbatore boundary"}
        held = c.reconcile_scope(db, "owner", {"elements": [element()]}, scope)
        assert len(held) == 1
        row = db.get(IdentifiedSpot, held[0])
        assert row.status == "quarantined" and row.data["sources"]
        assert row.data["directory_scope_review"]["scope"] == scope
        assert c.reconcile_scope(db, "owner", {"elements": [element()]}, scope) == []
        assert c.coverage(db, "other")["active_drafts"] == 1


def test_start_is_durable_idempotent_and_grid_is_not_completeness(client):
    with Session() as db:
        db.add(Counter(key="research_paused", value=1))
        db.commit()
        first = c.start_collection(db, "owner")
        assert c.start_collection(db, "owner")["directory_job_id"] == first["directory_job_id"]
        assert db.get(Counter, "research_paused").value == 0
        assert len(list(db.scalars(select(Job).where(Job.kind == "city_directory")))) == 1
        report = c.coverage(db, "owner")
        assert report["discovery_queries"] == 168 and report["queries_scheduled"] == 0
        assert report["city_complete"] is False


def test_private_coverage_export_and_erasure_include_directory_jobs_and_licence(client, auth):
    owner = client.get("/api/me", headers=auth).json()["id"]
    assert client.post("/api/admin/city-collection/start", headers=auth).status_code == 409
    with Session() as db:
        load(db, element(), owner=owner)
        load(db, element(2), owner="other")
        own_job = c.start_collection(db, owner)["directory_job_id"]
        other_job = c.start_collection(db, "other")["directory_job_id"]
    result = client.get("/api/admin/city-collection", headers=auth).json()
    assert result["active_drafts"] == 1
    exported = client.get("/api/me/export", headers=auth).json()
    assert len(exported["identified_spots"]) == 1
    assert exported["identified_spots"][0]["data"]["source_licenses"][0]["url"] == c.LICENSE_URL
    assert client.delete("/api/me/data", headers=auth).status_code == 200
    with Session() as db:
        assert db.get(Job, own_job) is None and db.get(Job, other_job) is not None
        assert c.coverage(db, owner)["active_drafts"] == 0
        assert c.coverage(db, "other")["active_drafts"] == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://fixture.example",
        "https://127.0.0.1/menu",
        "https://localhost/menu",
        "https://10.0.0.1/menu",
        "https://user:password@fixture.example",
    ],
)
def test_unsafe_website_hints_are_not_saved(url):
    assert c.public_link(url) is None


def test_caption_draft_commits_before_location_lookup_wait(client, monkeypatch):
    def analyze(db, case, task, only_source):
        assert task.role == "caption"
        only_source.analysis = {
            "caption": {
                "status": "observations_only",
                "venue_candidates": [{"name": "Zircon Cafe", "address_clues": ["RS Puram Coimbatore"]}],
            }
        }

    def location(db, *args):
        assert db.scalar(select(IdentifiedSpot)).name == "Zircon Cafe"
        raise Unavailable("fixture external allowance exhausted")

    monkeypatch.setattr(research, "analysis_stage", analyze)
    monkeypatch.setattr(research, "location_stage", location)
    with Session() as db:
        case = research.start_case(
            db,
            "owner",
            "cafes",
            seed_sources=[
                {
                    "platform": "instagram",
                    "url": "https://www.instagram.com/reel/fixture/",
                    "caption": "Zircon Cafe Coimbatore",
                }
            ],
        )
        src = research.case_sources(db, case)[0]
        job = SimpleNamespace(
            kind="source_quality_upgrade", payload={"user_id": "owner", "source_id": src.id}
        )
        with pytest.raises(Unavailable):
            jobs.execute_job(db, job)
        db.rollback()
        assert db.scalar(select(IdentifiedSpot)).name == "Zircon Cafe"
        case.state = "cancelled"
        db.commit()
        assert jobs.execute_job(db, job) == {"removed": True}
