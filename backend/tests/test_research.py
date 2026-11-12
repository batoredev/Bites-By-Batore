"""Behavioral checks for investigation recovery, evidence gates and privacy."""

import base64
import subprocess
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
import pytest
from app.db import Session, Investigation, ResearchTask, ResearchSource, Job, Venue, now
from app.config import settings
from app.jobs import run_once, schedule
from app import research, social
from app.providers import Unavailable
from app.media import extract_frames


def create_case(client, auth, **kwargs):
    response = client.post("/api/investigations", headers=auth, json={"query": "Coimbatore sushi", **kwargs})
    assert response.status_code == 200, response.text
    return response.json()


def drain(limit=25):
    for _ in range(limit):
        if not run_once():
            return
    raise AssertionError("Investigation did not settle within its bounded task count")


def test_demo_research_finishes_honestly_without_providers(client, auth, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Demo attempted an external call")

    monkeypatch.setattr(research, "web_search", forbidden)
    case = create_case(client, auth)
    assert create_case(client, auth)["id"] == case["id"]
    drain()
    result = client.get(f"/api/investigations/{case['id']}", headers=auth).json()
    assert result["state"] == "unavailable"
    assert len(result["tasks"]) == 8
    assert all(t["state"] == "done" for t in result["tasks"])
    assert result["result"]["eligible_venue_ids"] == []


def test_supplied_source_survives_stages_without_fake_analysis(client, auth):
    sub = client.post(
        "/api/submissions",
        headers=auth,
        json={"caption": "Sushi in Coimbatore", "comments": "Loved it\nLoved it"},
    ).json()
    case = create_case(client, auth, submission_id=sub["id"])
    drain()
    result = client.get(f"/api/investigations/{case['id']}", headers=auth).json()
    assert result["state"] == "review"
    assert result["sources"][0]["analysis"]["comments"]["sample"]["repeated_texts"] == 1
    assert result["sources"][0]["analysis"]["video"]["video_analyzed"] is False
    assert "media" not in result["sources"][0]["content"]


def test_investigations_private_export_erase_and_cancel(client, auth):
    case = create_case(client, auth)
    token = client.post("/api/auth/demo").json()["access_token"]
    other = {"Authorization": "Bearer " + token}
    assert client.get(f"/api/investigations/{case['id']}", headers=other).status_code == 404
    assert client.post(f"/api/investigations/{case['id']}/cancel", headers=other).status_code == 404
    assert client.get("/api/investigations", headers=other).json() == []
    assert client.get("/api/me/export", headers=auth).json()["investigations"][0]["id"] == case["id"]
    assert (
        client.post(f"/api/investigations/{case['id']}/cancel", headers=auth).json()["state"] == "cancelled"
    )
    drain()
    assert client.delete("/api/me/data", headers=auth).status_code == 200
    with Session() as db:
        assert db.get(Investigation, case["id"]) is None
        assert not list(db.scalars(select(ResearchTask)))


def test_research_rate_limit_is_separate_from_reads(client, auth, monkeypatch):
    monkeypatch.setattr(settings(), "research_daily_limit", 1)
    create_case(client, auth)
    assert client.post("/api/investigations", headers=auth, json={"query": "bowling"}).status_code == 429
    assert client.get("/api/investigations", headers=auth).status_code == 200


def test_scheduler_repairs_lost_stage_enqueue(client, auth):
    case = create_case(client, auth)
    with Session() as db:
        task = db.scalar(
            select(ResearchTask).where(ResearchTask.case_id == case["id"], ResearchTask.ordinal == 0)
        )
        task.state = "done"
        job = db.scalar(select(Job).where(Job.kind == "investigation"))
        job.state = "done"
        db.commit()
    schedule()
    with Session() as db:
        assert db.scalar(select(Job).where(Job.key == f"case:{case['id']}:1")) is not None


def test_recovered_old_job_cannot_execute_a_different_stage(client, auth, monkeypatch):
    case = create_case(client, auth)
    with Session() as db:
        first = db.scalar(
            select(ResearchTask).where(ResearchTask.case_id == case["id"], ResearchTask.ordinal == 0)
        )
        first.state = "done"
        old_job = db.scalar(select(Job).where(Job.key == f"case:{case['id']}:0"))
        old_job.state = "running"
        old_job.lease_until = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        db.commit()
    monkeypatch.setattr(
        research,
        "collect_stage",
        lambda *args: (_ for _ in ()).throw(AssertionError("Wrong stage executed by old delivery")),
    )
    assert run_once()
    with Session() as db:
        second = db.scalar(
            select(ResearchTask).where(ResearchTask.case_id == case["id"], ResearchTask.ordinal == 1)
        )
        assert second.state == "pending"


def test_failed_task_can_resume_without_repeating_done_steps(client, auth, monkeypatch):
    monkeypatch.setattr(settings(), "max_attempts", 1)
    original = research.discover_stage
    monkeypatch.setattr(
        research, "discover_stage", lambda *a: (_ for _ in ()).throw(Unavailable("Temporary source outage"))
    )
    case = create_case(client, auth)
    assert run_once()
    result = client.get(f"/api/investigations/{case['id']}", headers=auth).json()
    assert result["state"] == "failed"
    monkeypatch.setattr(research, "discover_stage", original)
    assert client.post(f"/api/investigations/{case['id']}/retry", headers=auth).status_code == 200
    drain()
    assert client.get(f"/api/investigations/{case['id']}", headers=auth).json()["state"] == "unavailable"


def test_wrong_branch_stays_unconfirmed_and_new_venue_stays_pending(client, auth):
    case = create_case(client, auth)
    with Session() as db:
        row = db.get(Investigation, case["id"])
        row.state = "review"
        source = ResearchSource(
            case_id=row.id,
            canonical_url="https://www.instagram.com/p/example/",
            platform="instagram",
            analysis={
                "caption": {"venue_candidates": [{"name": "Nori & Rice", "address_clues": ["Coimbatore"]}]}
            },
        )
        db.add(source)
        db.commit()
        research.location_stage(db, row, None)
        matches = source.analysis["location"]["hypotheses"][0]["inventory_matches"]
        assert all(m["status"] != "confirmed" for m in matches)
        sid = source.id
    result = client.post(
        f"/api/admin/research-sources/{sid}/resolve",
        headers=auth,
        json={
            "venue": {
                "name": "A newly confirmed fixture",
                "area": "RS Puram",
                "address": "12 Example Street, RS Puram",
                "lat": 11.01,
                "lng": 76.95,
                "category": "food",
            },
            "reason": "Confirmed the complete address against independent fixture evidence",
            "evidence_url": "https://example.com/fixture-branch",
        },
    )
    assert result.status_code == 200, result.text
    assert result.json()["result"]["eligible_venue_ids"] == []
    with Session() as db:
        venue = db.scalar(select(Venue).where(Venue.name == "A newly confirmed fixture"))
        assert venue.status == "pending"


def test_canonical_posts_and_media_network_boundary():
    assert social.canonical_url("https://instagram.com/reel/abc/?igsh=tracking") == social.canonical_url(
        "https://www.instagram.com/p/abc/"
    )
    for value in [
        "https://127.0.0.1/video.mp4",
        "https://example.com/video.mp4",
        "http://cdninstagram.com/a",
        "https://cdninstagram.com.evil.example/a",
    ]:
        with pytest.raises(Unavailable):
            social.allowed_media_url(value)


def test_async_provider_resumes_saved_run(client, auth, monkeypatch):
    case = create_case(client, auth)
    calls = []
    monkeypatch.setattr(settings(), "app_mode", "live")
    monkeypatch.setattr(settings(), "instagram_provider", "apify")
    monkeypatch.setattr(research, "apify_start", lambda *a: calls.append("start") or "RUN123")
    poll = iter(
        [None, [{"url": "https://www.instagram.com/p/abc/", "platform": "instagram", "caption": "Cafe"}]]
    )
    monkeypatch.setattr(research, "apify_poll", lambda *a: next(poll))
    monkeypatch.setattr(research, "web_search", lambda *a: [])
    monkeypatch.setattr(research, "youtube_discover", lambda *a: [])
    assert run_once()
    with Session() as db:
        job = db.scalar(select(Job).where(Job.kind == "investigation"))
        assert job.state == "queued" and job.attempts == 0
        job.due_at = now()
        db.commit()
    assert run_once()
    assert calls == ["start"]
    with Session() as db:
        assert len(list(db.scalars(select(ResearchSource).where(ResearchSource.case_id == case["id"])))) == 1


def test_real_local_frame_extraction_is_bounded(tmp_path, monkeypatch):
    from imageio_ffmpeg import get_ffmpeg_exe

    video = tmp_path / "test.mp4"
    subprocess.run(
        [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=64x64:d=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        timeout=20,
        check=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    monkeypatch.setattr(settings(), "media_max_frames", 2)
    payload = {"mime": "video/mp4", "base64": base64.b64encode(video.read_bytes()).decode()}
    frames = extract_frames(payload, [0, 1, 2, 3])
    assert len(frames) == 2 and frames[1]["seconds"] == 1
    assert all(base64.b64decode(f["base64"]).startswith(b"\xff\xd8") for f in frames)


def test_conversation_preserves_hard_constraints(client, auth):
    reply = client.post(
        "/api/discovery/conversation", headers=auth, json={"message": "I'm tired and hungry"}
    ).json()
    assert reply["key"] == "novelty"
    reply = client.post(
        "/api/discovery/conversation",
        headers=auth,
        json={"message": "I'm tired and hungry", "answers": {"novelty": "different"}},
    ).json()
    assert reply["ready"] and reply["suggestion"]["categories"] == ["food", "street_food", "cafe", "dessert"]
    assert not {"budget", "duration_minutes", "party_size", "lat", "lng"}.intersection(reply["suggestion"])


def test_extended_planner_packages_and_stop_bounds(client, auth, request_data):
    request_data.update(query="Something different", max_stops=3, duration_minutes=480, budget=10000)
    result = client.post("/api/plans", headers=auth, json=request_data).json()
    assert result["options"]
    assert any(len(p["result"]["stops"]) == 3 for p in result["options"])
    assert all(
        len(p["result"]["stops"]) <= 3 and p["result"]["total_cost"] <= 10000 for p in result["options"]
    )
    with Session() as db:
        v = db.get(Venue, "demo-sushi")
        v.details = {
            **v.details,
            "packages": [
                {
                    "name": "Shared tasting",
                    "unit": "group",
                    "people_per_unit": 2,
                    "price": 600,
                    "duration_minutes": 40,
                    "expires_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                    "source_url": "https://example.com/fixture",
                }
            ],
        }
        db.commit()
    request_data.update(query="sushi", max_stops=1, party_size=3)
    plan = client.post("/api/plans", headers=auth, json=request_data).json()["options"][0]["result"]
    assert plan["stops"][0]["cost"] == 1200 and plan["stops"][0]["visit_minutes"] == 40


def test_launch_gates_and_import_are_not_publication(client, auth):
    report = client.get("/api/admin/quality", headers=auth).json()
    assert "Only fictional demo inventory is being assessed" in report["launch_blockers"]
    response = client.post(
        "/api/admin/launch-review",
        headers=auth,
        json={"approve": True, "reason": "Attempted signoff without actual data verification"},
    )
    assert response.status_code == 409
    first = client.post("/api/admin/launch-leads", headers=auth).json()
    second = client.post("/api/admin/launch-leads", headers=auth).json()
    assert len(first["investigation_ids"]) == 9 and first == second
    with Session() as db:
        assert len(list(db.scalars(select(Venue)))) == 12


def test_budget_reservation_blocks_network_before_exceeding_limit(client, monkeypatch):
    import app.providers as providers

    monkeypatch.setattr(settings(), "app_mode", "live")
    monkeypatch.setattr(settings(), "monthly_budget_inr", 0)
    with Session() as db, pytest.raises(Unavailable, match="Monthly provider"):
        providers.call(db, "GET", "https://api.search.brave.com/res/v1/web/search")


def test_creator_history_deduplicates_origins_and_excludes_changed_facts(client, auth):
    from app.db import SourceAssessment

    with Session() as db:
        for outcome, group in [
            ("supported", "one"),
            ("supported", "one"),
            ("refuted", "two"),
            ("outdated", "three"),
        ]:
            db.add(
                SourceAssessment(
                    source_id="source",
                    creator_identity="instagram:example",
                    evidence_group=group,
                    outcome=outcome,
                    reason="Human fixture outcome",
                    evidence_url="https://example.com",
                    actor="test",
                )
            )
        db.commit()
        result = research.creator_assessment(db, "instagram:example")
        assert result["supported"] == 1 and result["refuted"] == 1 and result["outdated"] == 1
        assert result["observed_support_rate"] == 0.5 and result["status"] == "limited_review_history"


def test_dated_social_extraction_creates_review_claim_not_accepted_fact(client, auth):
    from app.db import Claim

    case = create_case(client, auth)
    with Session() as db:
        c = db.get(Investigation, case["id"])
        source = ResearchSource(
            case_id=c.id,
            platform="instagram",
            creator="example",
            canonical_url="https://www.instagram.com/p/facttest/",
            content={"published_at": now()},
            analysis={
                "human_resolution": {"venue_id": "demo-sushi"},
                "caption": {
                    "venue_candidates": [
                        {
                            "name": "Nori & Rice",
                            "facts": [
                                {
                                    "field": "price_per_person",
                                    "value": {"value": 999},
                                    "basis": "Explicit per-person caption claim",
                                }
                            ],
                        }
                    ]
                },
            },
        )
        db.add(source)
        db.commit()
        research.verification_stage(db, c, None)
        db.commit()
        claims = list(db.scalars(select(Claim).where(Claim.source_url == source.canonical_url)))
        assert len(claims) == 1 and claims[0].status == "review"
        assert db.get(Venue, "demo-sushi").details["price_per_person"] == 480


def test_empty_live_inventory_starts_bounded_research_when_enabled(client, auth, monkeypatch, request_data):
    from app.main import create_plans
    from app.schemas import OutingRequest
    from app.db import User

    user_id = client.get("/api/me", headers=auth).json()["id"]
    monkeypatch.setattr(settings(), "app_mode", "live")
    monkeypatch.setattr(settings(), "autonomous_discovery", True)
    request_data["departure"] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    with Session() as db:
        result = create_plans(OutingRequest(**request_data), db.get(User, user_id), db)
        assert result["options"] == [] and result["investigation_id"]
        repeated = create_plans(OutingRequest(**request_data), db.get(User, user_id), db)
        assert repeated["investigation_id"] == result["investigation_id"]


def test_review_can_conclude_no_evidence_but_cannot_invent_eligibility(client, auth):
    case = create_case(client, auth)
    drain()
    path = f"/api/admin/investigations/{case['id']}/conclude"
    assert (
        client.post(
            path,
            headers=auth,
            json={
                "decision": "use_verified_venues",
                "reason": "No independent branch facts have been obtained",
            },
        ).status_code
        == 409
    )
    response = client.post(
        path,
        headers=auth,
        json={
            "decision": "insufficient_evidence",
            "reason": "Sources were unavailable and no branch could be independently verified",
        },
    )
    assert response.status_code == 200 and response.json()["state"] == "insufficient_evidence"
