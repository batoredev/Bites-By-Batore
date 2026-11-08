"""Dedicated reconciliation on isolated invented fixtures; no human approvals."""

import hashlib
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from app import jobs, research
from app.db import Audit, IdentifiedSpot, Job, Session
from app.duplicate_agent import request_scan, run_scan, status
from app.spot_identity import same_branch
from app.spots import reconcile_spots, upsert_spot


def row(db, name="Zircon Cafe", owner="owner", status="identified", **data):
    r = IdentifiedSpot(
        user_id=owner,
        name=name,
        category="cafe",
        area="RS Puram",
        identity_key=hashlib.sha256(
            (owner + name + str(len(list(db.scalars(select(IdentifiedSpot.id)))))).encode()
        ).hexdigest(),
        status=status,
        data=data,
    )
    db.add(r)
    db.flush()
    return r


def test_three_proven_duplicates_merge_to_one_and_replay_is_noop(client):
    with Session() as db:
        a = row(
            db,
            maps_identity={"place_key": "fixture-place"},
            sources=[{"url": "https://fixture.example/a", "collected_at": "2026-11-01"}],
        )
        row(db, maps_identity={"place_key": "fixture-place"})
        row(
            db,
            maps_identity={"place_key": "fixture-place"},
            status="quarantined",
            duplicate_review_candidates=[a.id],
            quality_issues=["Possible duplicate branch"],
        )
        db.commit()
        report = run_scan(db, "owner")
        db.commit()
        assert report["automatic_merged"] == 2
        rows = list(db.scalars(select(IdentifiedSpot)))
        assert sum(r.status == "identified" for r in rows) == 1 and len(rows) == 3
        assert sum(r.status == "merged" for r in rows) == 2
        assert len(list(db.scalars(select(Audit).where(Audit.action == "spot.merged")))) == 2
        survivor = next(r for r in rows if r.status == "identified")
        assert survivor.data["sources"][0]["collected_at"] == "2026-11-01"
        assert not survivor.data["maps_identity"].get("confirmed_by") and not survivor.venue_id
        assert run_scan(db, "owner")["automatic_merged"] == 0


def test_transitive_bridge_does_not_merge_different_branches(client):
    with Session() as db:
        point = {"lat": 11.01, "lng": 76.95}
        row(db, address="No.14 Fixture Road", coordinates=point)
        row(db, coordinates=point)
        row(db, address="No.25 Fixture Road", coordinates=point)
        db.commit()
        report = run_scan(db, "owner")
        assert report["automatic_merged"] == 0 and report["pending_count"] >= 2
        assert all(r.status == "identified" for r in db.scalars(select(IdentifiedSpot)))


def test_same_source_caption_sign_variant_merges_without_factual_approval(client):
    with Session() as db:
        case = research.start_case(
            db,
            "owner",
            "Coimbatore cafes",
            seed_sources=[
                {
                    "platform": "instagram",
                    "url": "https://www.instagram.com/reel/fixture/",
                    "caption": "@zirconcafe.coimbatore RS Puram",
                }
            ],
        )
        source = research.case_sources(db, case)[0]
        source.analysis = {
            "caption": {
                "status": "observations_only",
                "venue_candidates": [{"name": "zirconcafe.coimbatore"}],
            },
            "video": {
                "status": "observations_only",
                "venue_candidates": [{"name": "zirconcafe"}],
                "observations": [
                    {"basis": "visual", "verbatim_text": "zirconcafe", "text": "Sign reads zirconcafe"}
                ],
            },
        }
        a = row(db, name="zirconcafe.coimbatore", source_ids=[source.id])
        b = row(db, name="zirconcafe", source_ids=[source.id])
        db.commit()
        report = run_scan(db, "owner")
        db.commit()
        assert report["automatic_merged"] == 1 and a.status == "merged" and b.status == "identified"
        assert not b.data.get("maps_identity") and not b.venue_id


def test_shared_reel_with_two_venues_stays_for_review(client):
    with Session() as db:
        case = research.start_case(
            db,
            "owner",
            "cafes",
            seed_sources=[
                {
                    "platform": "instagram",
                    "url": "https://www.instagram.com/reel/twofixture/",
                    "caption": "Two places",
                }
            ],
        )
        source = research.case_sources(db, case)[0]
        source.analysis = {
            "caption": {
                "status": "observations_only",
                "venue_candidates": [{"name": "zirconcafe.coimbatore"}],
            },
            "video": {
                "status": "observations_only",
                "venue_candidates": [{"name": "zirconcafe"}, {"name": "Another Cafe"}],
                "observations": [{"basis": "visual", "verbatim_text": "zirconcafe"}],
            },
        }
        row(db, name="zirconcafe.coimbatore", source_ids=[source.id])
        row(db, name="zirconcafe", source_ids=[source.id])
        db.commit()
        report = run_scan(db, "owner")
        assert report["automatic_merged"] == 0 and report["pending_count"] == 1


@pytest.mark.parametrize(
    "caption_name,sign_name,partial",
    [
        ("laffinage.coimbatore", "l'affinage", "l'affin"),
        ("G Chat Corner", "G-Chaat Corner", None),
        ("Cosmos Cinemas", "Cosmo Cinemas", None),
    ],
)
def test_scoped_transliteration_and_partial_ocr_keep_complete_sign_name(
    client, caption_name, sign_name, partial
):
    with Session() as db:
        case = research.start_case(
            db,
            "owner",
            "cafes",
            seed_sources=[
                {
                    "platform": "instagram",
                    "url": "https://www.instagram.com/reel/aliasfixture/",
                    "caption": caption_name,
                }
            ],
        )
        src = research.case_sources(db, case)[0]
        video_names = [sign_name] + ([partial, "Viral Underbaked Dessert"] if partial else [])
        src.analysis = {
            "caption": {"status": "observations_only", "venue_candidates": [{"name": caption_name}]},
            "video": {
                "status": "observations_only",
                "venue_candidates": [{"name": n} for n in video_names],
                "observations": [{"basis": "visual", "verbatim_text": sign_name}],
            },
        }
        if partial:
            row(db, name=partial, source_ids=[src.id])
        row(db, name=caption_name, source_ids=[src.id])
        sign = row(db, name=sign_name, source_ids=[src.id])
        db.commit()
        report = run_scan(db, "owner")
        db.commit()
        assert report["automatic_merged"] == (2 if partial else 1)
        assert sign.status == "identified"


def test_generic_shared_search_page_is_not_branch_proof(client):
    with Session() as db:
        a = row(
            db,
            name="Zircon Cafe",
            strict_identity=True,
            coordinates={"lat": 11.01, "lng": 76.95},
            sources=[{"type": "web_candidate", "url": "https://directory.example/chain/menu"}],
        )
        b = row(
            db,
            name="Zircon Cafe",
            strict_identity=True,
            sources=[{"type": "web_candidate", "url": "https://directory.example/chain/menu"}],
        )
        db.commit()
        assert not same_branch(a, b.name, b.area, b.data)
        assert run_scan(db, "owner")["automatic_merged"] == 0


def test_conflicting_legacy_hash_cannot_override_maps_or_far_coordinates(client):
    with Session() as db:
        a = upsert_spot(
            db,
            "owner",
            "Zircon Cafe",
            area="RS Puram",
            data={"maps_identity": {"place_key": "first"}, "coordinates": {"lat": 11.01, "lng": 76.95}},
        )
        db.commit()
        b = upsert_spot(
            db,
            "owner",
            "Zircon Cafe",
            area="RS Puram",
            data={"maps_identity": {"place_key": "second"}, "coordinates": {"lat": 11.03, "lng": 76.95}},
        )
        db.commit()
        assert a.id != b.id and a.data["maps_identity"]["place_key"] == "first"
        assert (
            upsert_spot(
                db,
                "owner",
                "Zircon Cafe",
                area="RS Puram",
                data={"maps_identity": {"place_key": "second"}, "coordinates": {"lat": 11.03, "lng": 76.95}},
            ).id
            == b.id
        )


def test_explicit_manual_merge_allows_held_source_and_serializes_reciprocal_requests(client, auth):
    owner = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        a = row(db, owner=owner, status="quarantined", quality_issues=["Possible duplicate branch"])
        b = row(db, owner=owner)
        db.commit()
        aid, bid = a.id, b.id
    response = client.post(
        f"/api/admin/spots/{aid}/merge",
        headers=auth,
        json={"target_id": bid, "same_branch_checked": True, "reason": "Checked exact fixture branch"},
    )
    assert response.status_code == 200
    with Session() as db:
        assert db.get(IdentifiedSpot, aid).data["previous_status"] == "quarantined"
    with Session() as db:
        c = row(db, owner=owner)
        d = row(db, owner=owner)
        db.commit()
        cid, did = c.id, d.id

    def merge(pair):
        x, y = pair
        return client.post(
            f"/api/admin/spots/{x}/merge",
            headers=auth,
            json={"target_id": y, "same_branch_checked": True, "reason": "Checked exact fixture branch"},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(merge, [(cid, did), (did, cid)])) == [200, 409]


def test_private_agent_jobs_and_decisions_export_erase_and_rescan_changes(client, auth):
    owner = client.get("/api/me", headers=auth).json()["id"]
    with Session() as db:
        row(db, owner=owner)
        row(db, owner="other")
        db.commit()
        job = request_scan(db, owner)
        own_id = job.id
        assert request_scan(db, owner).id == own_id
        other_id = request_scan(db, "other").id
    assert jobs.run_once(include_kinds=["spot_deduplicate"])
    with Session() as db:
        assert db.get(Job, own_id).state == "done"
        assert request_scan(db, owner).id == own_id
        original = db.scalar(select(IdentifiedSpot).where(IdentifiedSpot.user_id == owner))
        original.area = "Peelamedu"
        db.commit()
        assert request_scan(db, owner).id != own_id
    exported = client.get("/api/me/export", headers=auth).json()
    assert all(j["payload"]["user_id"] == owner for j in exported["duplicate_agent_runs"])
    assert client.delete("/api/me/data", headers=auth).status_code == 200
    with Session() as db:
        assert db.get(Job, own_id) is None and db.get(Job, other_id) is not None
        assert status(db, owner)["pending_count"] == 0


def test_terminal_scan_failure_can_retry_without_inventory_change(client):
    with Session() as db:
        row(db)
        db.commit()
        first = request_scan(db, "owner")
        first.state = "failed"
        first.completed_at = "2000-01-01T00:00:00+00:00"
        db.commit()
        retried = request_scan(db, "owner")
        assert retried.id != first.id and retried.state == "queued"
        assert request_scan(db, "owner").id == retried.id


def test_legacy_cleanup_cannot_bypass_concrete_street_conflicts(client):
    with Session() as db:
        shared = [{"type": "instagram", "url": "https://www.instagram.com/reel/chainfixture/"}]
        a = row(db, address_clues=["Bharathi Road"], sources=shared)
        b = row(db, address_clues=["Mettupalayam Road"], sources=shared)
        db.commit()
        assert reconcile_spots(db, "owner")["merged"] == 0
        assert a.status != "merged" and b.status != "merged"
