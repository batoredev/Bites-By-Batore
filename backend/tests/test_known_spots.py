"""Known-place discovery policy, local inventory and concurrency; isolated fixtures."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from app import research
from app.config import settings
from app.db import Session, IdentifiedSpot, Venue, Claim
from app.spots import upsert_spot, identify_from_source, sync_inventory
from app.known_spots import decision, try_skip

ADDRESS = "No. 14, Fixture Road, RS Puram, Coimbatore 641002"


@pytest.fixture
def enabled(client, monkeypatch):
    cfg = settings()
    monkeypatch.setattr(cfg, "app_mode", "local")
    monkeypatch.setattr(cfg, "known_spot_skip_enabled", True)
    monkeypatch.setattr(cfg, "local_search_enabled", False)
    monkeypatch.setattr(cfg, "instagram_browser_enabled", False)
    return client


def source(db, code="fixture", owner="owner", caption="Zircon Cafe Coimbatore"):
    case = research.start_case(
        db,
        owner,
        "Coimbatore cafes",
        seed_sources=[
            {"platform": "instagram", "url": f"https://www.instagram.com/reel/{code}/", "caption": caption}
        ],
    )
    return case, research.case_sources(db, case)[0]


def existing(db, owner="owner", code="older"):
    case, row = source(db, code, owner)
    row.analysis = {
        "caption": {
            "status": "observations_only",
            "venue_candidates": [{"name": "Zircon Cafe", "address_clues": [ADDRESS]}],
        }
    }
    ids = identify_from_source(db, case, row)
    row.content = {**row.content, "streamed": True}
    db.commit()
    return db.get(IdentifiedSpot, ids[0]), row


def test_repeat_permalink_skips_before_network_and_keeps_reference(enabled, monkeypatch):
    with Session() as db:
        spot, previous = existing(db)
        case, current = source(db, "older")
        current.content = {
            **current.content,
            "media": {"base64": "fixture"},
            "media_url": "https://fixture.example/video",
        }
        monkeypatch.setattr(
            research, "stream_source", lambda *args: pytest.fail("Known source reached inference")
        )
        research.collect_stage(db, case, SimpleNamespace())
        assert current.analysis["discovery_skip"]["spot_ids"] == [spot.id]
        assert current.analysis["video"]["status"] == "skipped_known_location"
        assert current.content["streamed"] and "media" not in current.content
        assert current.id in spot.data["source_ids"]
        assert len(spot.data["sources"]) == 1  # No fabricated fresh fact receipt.
        checks = current.analysis["inventory_checks"]
        assert identify_from_source(db, case, current) == [spot.id]
        assert current.analysis["inventory_checks"] == checks
        assert not list(
            db.scalars(select(Claim).join(Venue, Claim.venue_id == Venue.id).where(Venue.is_demo.is_(False)))
        )


def test_caption_identifies_known_branch_and_stops_video_and_comments(enabled, monkeypatch):
    calls = []

    def analyze(db, role, *args, **kwargs):
        calls.append(role)
        assert role == "caption"
        return {
            "status": "observations_only",
            "venue_candidates": [{"name": "Zircon Cafe", "address_clues": [ADDRESS]}],
        }

    monkeypatch.setattr(research, "analyze", analyze)
    with Session() as db:
        spot, _ = existing(db)
        case, current = source(db, "different-reel")
        current.content = {**current.content, "media": {"base64": "unused"}, "comments": "fixture question"}
        research.stream_source(db, case, current)
        assert calls == ["caption"]
        assert current.analysis["discovery_skip"]["stage"] == "after_caption"
        assert current.analysis["comments"]["status"] == "skipped_known_location"
        assert len(list(db.scalars(select(IdentifiedSpot)))) == 1
        assert len(spot.data["discovery_references"]) == 1


@pytest.mark.parametrize("clues", [["RS Puram"], [], ["No. 99, Fixture Road, RS Puram, Coimbatore 641002"]])
def test_name_area_or_other_house_cannot_discard_a_branch(enabled, clues):
    with Session() as db:
        existing(db)
        case, current = source(db, "new-branch")
        assert (
            decision(db, case, current, candidates=[{"name": "Zircon Cafe", "address_clues": clues}]) is None
        )


def test_known_plus_unknown_and_compilation_keep_processing(enabled):
    with Session() as db:
        existing(db)
        case, current = source(db, "multiple")
        known = {"name": "Zircon Cafe", "address_clues": [ADDRESS]}
        assert (
            decision(db, case, current, candidates=[known, {"name": "Beryl Cafe", "address_clues": []}])
            is None
        )
        current.content = {**current.content, "caption": "Top 10 Coimbatore cafes"}
        assert decision(db, case, current, candidates=[known]) is None


@pytest.mark.parametrize(
    "context",
    [
        {"force_full_analysis": True},
        {"maintenance_source_id": "fixture"},
        {"refresh_reason": "Changed caption"},
    ],
)
def test_manual_and_maintenance_refresh_bypass_discovery_skip(enabled, context):
    with Session() as db:
        existing(db)
        case, current = source(db, "older")
        case.context = context
        assert decision(db, case, current) is None


def test_changed_caption_held_candidates_and_gold_labels_block_reuse(enabled):
    with Session() as db:
        _, previous = existing(db)
        case, current = source(db, "older", caption="Different branch and changed evidence")
        assert decision(db, case, current) is None
        current.content = {**current.content, "caption": previous.content["caption"]}
        previous.analysis = {
            **previous.analysis,
            "inventory_checks": [
                *previous.analysis["inventory_checks"],
                {"name": "Unknown cafe", "decision": "held"},
            ],
        }
        db.commit()
        assert decision(db, case, current) is None
        previous.analysis = {**previous.analysis, "evaluation_labels": {"caption": {"split": "holdout"}}}
        assert (
            decision(db, case, current, candidates=[{"name": "Zircon Cafe", "address_clues": [ADDRESS]}])
            is None
        )


def test_other_owner_and_inactive_spots_never_trigger_skip(enabled):
    with Session() as db:
        spot, _ = existing(db, "private-other")
        case, current = source(db, "older")
        assert decision(db, case, current) is None
        spot.user_id = case.user_id
        spot.status = "quarantined"
        db.commit()
        assert (
            decision(db, case, current, candidates=[{"name": "Zircon Cafe", "address_clues": [ADDRESS]}])
            is None
        )


def test_new_caption_location_is_committed_before_video(enabled, monkeypatch):
    calls = []

    def analyze(db, role, *args, **kwargs):
        calls.append(role)
        if role == "video":
            assert db.scalar(select(IdentifiedSpot).where(IdentifiedSpot.name == "Beryl Cafe")) is not None
        return {
            "status": "observations_only",
            "venue_candidates": [{"name": "Beryl Cafe", "address_clues": [ADDRESS]}]
            if role == "caption"
            else [],
        }

    monkeypatch.setattr(research, "analyze", analyze)
    with Session() as db:
        case, current = source(db, "unseen", caption="Beryl Cafe, " + ADDRESS)
        current.content = {
            **current.content,
            "media": {"base64": "unused", "mime": "video/mp4"},
            "comments": "Fixture comment",
        }
        research.stream_source(db, case, current)
        assert calls == ["caption", "video", "comments"]
        assert not current.analysis.get("discovery_skip")
        assert not list(db.scalars(select(Venue).where(Venue.is_demo.is_(False))))


def test_video_callback_stops_unneeded_groups_and_reports_actual_coverage(enabled, monkeypatch):
    from app import local_models, media
    from app.analysts import analyze
    from app.analysis_reuse import mark, valid_result

    frames = [{"seconds": i, "base64": "eA==", "mime": "image/jpeg"} for i in range(8)]
    monkeypatch.setattr(media, "extract_frames", lambda *args: frames)
    monkeypatch.setattr(local_models, "transcribe", lambda *args: {"text": "fixture speech"})
    calls = []

    def chat(*args):
        calls.append(1)
        return json.dumps({"venue_candidates": [{"name": "Zircon Cafe", "address_clues": [ADDRESS]}]})

    monkeypatch.setattr(local_models, "local_chat", chat)
    with Session() as db:
        result = analyze(
            db, "video", {}, {"base64": "unused", "mime": "video/mp4"}, on_pass=lambda partial: True
        )
    assert len(calls) == 1 and result["early_exit"]
    assert result["sampling"] == [0, 1, 2, 3]
    assert not valid_result(mark(result, "key", "digest"), "key")


def test_inventory_backfill_is_repeat_safe_and_does_not_publish(enabled):
    with Session() as db:
        case, current = source(db)
        current.analysis = {
            "caption": {
                "venue_candidates": [
                    {"name": "Zircon Cafe", "address_clues": [ADDRESS]},
                    {"name": "New Cafe in Coimbatore", "address_clues": []},
                ]
            }
        }
        db.commit()
        first = sync_inventory(db, case.user_id)
        second = sync_inventory(db, case.user_id)
        assert first["new_records"] == 1 and second["new_records"] == 0
        assert first["active"] == second["active"] == 1
        assert any(c["decision"] == "held" for c in current.analysis["inventory_checks"])
        assert not list(db.scalars(select(Venue).where(Venue.is_demo.is_(False))))


def test_concurrent_alias_insert_uses_one_canonical_sql_row(enabled):
    barrier = Barrier(2)

    def insert(name):
        with Session() as db:
            barrier.wait(timeout=5)
            row = upsert_spot(
                db,
                "owner",
                name,
                "cafe",
                "RS Puram",
                {
                    "sources": [{"url": "https://www.instagram.com/reel/concurrent/", "type": "instagram"}],
                    "address_clues": [ADDRESS],
                },
            )
            db.commit()
            return row.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        ids = list(executor.map(insert, ["Cafe Zircon", "Zircon Café"]))
    assert len(set(ids)) == 1
    with Session() as db:
        rows = list(db.scalars(select(IdentifiedSpot)))
        assert len(rows) == 1 and len(rows[0].data["aliases"]) == 2


def test_indistinguishable_name_is_held_without_merging_branches(enabled):
    with Session() as db:
        a = upsert_spot(
            db, "owner", "Zircon Cafe", data={"sources": [{"url": "https://www.instagram.com/reel/a/"}]}
        )
        b = upsert_spot(
            db, "owner", "Zircon Cafe", data={"sources": [{"url": "https://www.instagram.com/reel/b/"}]}
        )
        db.commit()
        assert a.id != b.id and b.status == "quarantined"
        assert b.data["duplicate_review_candidates"] == [a.id]
        assert b.data["sources"][0]["url"].endswith("/b/")
        assert len(list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.status == "identified")))) == 1


def test_replaying_multivenue_unassigned_observations_is_idempotent(enabled):
    with Session() as db:
        case, current = source(db)
        current.analysis = {
            "caption": {
                "venue_candidates": [{"name": "Zircon Cafe"}, {"name": "Beryl Cafe"}],
                "observations": [{"text": "Outdoor seating is visible", "basis": "visual"}],
            }
        }
        db.commit()
        sync_inventory(db, case.user_id)
        second = sync_inventory(db, case.user_id)
        assert second["new_records"] == 0 and not any(second["cleanup"].values())


def test_mixed_active_and_held_previous_candidates_cannot_skip(enabled):
    with Session() as db:
        spot, previous = existing(db)
        held = upsert_spot(db, "owner", "Beryl Cafe", data={"sources": [{"url": previous.canonical_url}]})
        held.status = "quarantined"
        previous.analysis = {
            **previous.analysis,
            "inventory_checks": [
                *previous.analysis["inventory_checks"],
                {"name": held.name, "spot_id": held.id, "decision": "saved"},
            ],
        }
        db.commit()
        case, current = source(db, "older")
        assert decision(db, case, current) is None


def test_skipped_sources_remain_in_export_and_erasure(enabled):
    token = enabled.post("/api/auth/local").json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    with Session() as db:
        existing(db, "local-operator")
        case, current = source(db, "older", "local-operator")
        assert try_skip(db, case, current)
    exported = enabled.get("/api/me/export", headers=headers).json()
    assert "discovery_skip" in json.dumps(exported)
    assert enabled.delete("/api/me/data", headers=headers).status_code == 200
    with Session() as db:
        assert not list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == "local-operator")))
