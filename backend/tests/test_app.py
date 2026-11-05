from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db import Session, Claim, Venue, Job
from app.jobs import enqueue, run_once, claim_job
from app.providers import safe_social_url, media_payload, Unavailable, youtube_id
from app.config import settings
import pytest


def make_plan(client, auth, request_data):
    response = client.post("/api/plans", headers=auth, json=request_data)
    assert response.status_code == 200, response.text
    return response.json()


def test_explicit_request_budget_and_time(client, auth, request_data):
    result = make_plan(client, auth, request_data)
    assert result["options"]
    for plan in result["options"]:
        r = plan["result"]
        assert r["total_cost"] <= request_data["budget"]
        assert r["total_minutes"] <= request_data["duration_minutes"]
        assert any(s["venue_id"] == "demo-sushi" for s in r["stops"])
        assert (
            r["total_cost"]
            == sum(s["cost"] + s["fees"] + s["travel"]["cost"] for s in r["stops"]) + r["reserve"]
        )
        end = datetime.fromisoformat(r["stops"][-1]["end"])
        start = datetime.fromisoformat(request_data["departure"])
        assert r["total_minutes"] == int((end - start).total_seconds() / 60) + r["time_buffer"]


def test_impossible_budget_not_silently_raised(client, auth, request_data):
    request_data["budget"] = 50
    assert make_plan(client, auth, request_data)["options"] == []


def test_per_person_budget_and_combined(client, auth, request_data):
    request_data.update(budget=1200, budget_unit="person", outing_type="combined")
    rows = make_plan(client, auth, request_data)["options"]
    assert rows
    for p in rows:
        assert p["result"]["budget_cap"] == 2400
        assert len(p["result"]["stops"]) == 2
        assert any(s["category"] in {"food", "cafe"} for s in p["result"]["stops"])
        assert any(s["category"] not in {"food", "cafe"} for s in p["result"]["stops"])


def test_visit_must_finish_before_closing(client, auth, request_data):
    request_data.update(departure="2026-11-05T21:45:00+05:30")
    assert make_plan(client, auth, request_data)["options"] == []


def test_cinema_wait_and_full_screening(client, auth, request_data):
    request_data.update(
        query="movies", categories=["cinema"], departure="2026-11-05T17:00:00+05:30", duration_minutes=240
    )
    rows = make_plan(client, auth, request_data)["options"]
    assert rows
    stop = rows[0]["result"]["stops"][0]
    assert datetime.fromisoformat(stop["start"]).hour == 18
    assert stop["visit_minutes"] == 140
    request_data["duration_minutes"] = 120
    assert make_plan(client, auth, request_data)["options"] == []


def test_mixed_access_and_children_constraints(client, auth, request_data):
    request_data.update(query="", categories=["adventure"], wheelchair=True, children=True)
    assert make_plan(client, auth, request_data)["options"] == []


def test_revision_lock_and_exclusion(client, auth, request_data):
    request_data.update(query="", lock_ids=["demo-coffee"], exclude_ids=["demo-sushi"])
    rows = make_plan(client, auth, request_data)["options"]
    assert rows
    for p in rows:
        ids = [s["venue_id"] for s in p["result"]["stops"]]
        assert "demo-coffee" in ids and "demo-sushi" not in ids


def test_private_plans_and_profile(client, auth, request_data):
    p = make_plan(client, auth, request_data)["options"][0]
    assert client.post(f"/api/plans/{p['id']}/save", headers=auth).json()["saved"]
    another = {"Authorization": "Bearer " + client.post("/api/auth/demo").json()["access_token"]}
    assert client.get(f"/api/plans/{p['id']}", headers=another).status_code == 404
    assert client.post(f"/api/plans/{p['id']}/save", headers=another).status_code == 404
    assert client.get("/api/plans", headers=another).json() == []
    assert len(client.get("/api/plans", headers=auth).json()) == 1
    assert client.get("/api/venues").status_code == 401


def test_saves_do_not_train_taste_visits_do(client, auth):
    client.post("/api/venues/demo-sushi/save", headers=auth)
    assert client.get("/api/visits", headers=auth).json() == []
    response = client.post(
        "/api/visits",
        headers=auth,
        json={
            "venue_id": "demo-sushi",
            "rating": 5,
            "dimensions": {"food": 5, "value": 2},
            "visited_on": "2026-01-01",
            "occasion": "friends",
            "note": "Good sushi",
        },
    )
    assert response.status_code == 200
    profile = client.get("/api/me", headers=auth).json()["profile"]
    assert profile["inferred"]["sushi"] > 0
    assert "budget" not in profile
    assert (
        client.post(
            "/api/visits",
            headers=auth,
            json={"venue_id": "demo-sushi", "rating": 5, "visited_on": "2026-01-01"},
        ).status_code
        == 409
    )
    client.delete("/api/me/memory", headers=auth)
    assert client.get("/api/visits", headers=auth).json() == []
    assert client.get("/api/me", headers=auth).json()["profile"]["inferred"] == {}


def test_stale_critical_fact_excludes_venue(client, auth, request_data):
    existing = make_plan(client, auth, request_data)["options"][0]
    with Session() as db:
        c = db.scalar(
            select(Claim).where(
                Claim.venue_id == "demo-sushi", Claim.field == "hours", Claim.status == "accepted"
            )
        )
        c.expires_at = "2000-01-01T00:00:00+00:00"
        db.commit()
    result = make_plan(client, auth, request_data)
    assert result["options"] == []
    assert result["excluded"]["facts need verification"] >= 1
    assert client.get(f"/api/plans/{existing['id']}", headers=auth).json()["needs_refresh"] is True


def test_review_changes_saved_plan_revision(client, auth, request_data):
    p = make_plan(client, auth, request_data)["options"][0]
    review = client.get("/api/admin/overview", headers=auth).json()["review"][0]
    assert (
        client.post(
            f"/api/admin/claims/{review['id']}/review",
            headers=auth,
            json={"decision": "approve", "reason": "Confirmed fictional test evidence"},
        ).status_code
        == 200
    )
    assert client.get(f"/api/plans/{p['id']}", headers=auth).json()["needs_refresh"] is True


def test_jobs_are_idempotent_and_leases_exclusive(client):
    with Session() as db:
        first = enqueue(db, "refresh", {"venue_id": "demo-sushi"}, "test-refresh")
        second = enqueue(db, "refresh", {"venue_id": "demo-sushi"}, "test-refresh")
        assert first.id == second.id
        claimed = claim_job(db)
        assert claimed.id == first.id
    with Session() as db:
        assert claim_job(db) is None
        job = db.get(Job, first.id)
        job.lease_until = "2000-01-01T00:00:00+00:00"
        db.commit()
    assert run_once()
    with Session() as db:
        job = db.get(Job, first.id)
        assert job.state == "done" and job.attempts == 2
        assert "No real-world verification" in job.result["message"]


def test_demo_source_does_not_invent_video_analysis(client, auth):
    data = {"url": "https://www.instagram.com/reel/example/", "caption": "Sushi near RS Puram"}
    sub = client.post("/api/submissions", headers=auth, json=data).json()
    assert client.post("/api/submissions", headers=auth, json=data).json()["id"] == sub["id"]
    assert run_once()
    result = client.get("/api/submissions", headers=auth).json()[0]
    assert result["result"]["video"]["analyzed"] is False
    assert result["result"]["venue_candidates"] == []


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "https://127.0.0.1",
        "https://instagram.com.evil.test/a",
        "https://user:pw@instagram.com/reel/a",
        "https://instagram.com:444/a",
        "file:///C:/Windows/system.ini",
    ],
)
def test_untrusted_media_urls_rejected(url):
    with pytest.raises(ValueError):
        safe_social_url(url)


def test_media_signature_and_youtube_id():
    assert youtube_id("https://youtu.be/abcdefghijk") == "abcdefghijk"
    assert youtube_id("https://youtube.com/shorts/abcdefghijk") == "abcdefghijk"
    assert youtube_id("https://evil.test/watch?v=abcdefghijk") is None
    with pytest.raises(ValueError):
        media_payload(b"<html>not a video</html>", "video/mp4")


def test_live_mode_does_not_accept_demo_session(client, auth, monkeypatch):
    monkeypatch.setattr(settings(), "app_mode", "live")
    assert client.post("/api/auth/demo").status_code == 404
    # Supabase validation cannot fall back to demo tokens or local identities.
    import app.auth as auth_module

    class Response:
        status_code = 401

    monkeypatch.setattr(auth_module.httpx, "get", lambda *args, **kwargs: Response())
    assert client.get("/api/me", headers=auth).status_code == 401


def test_live_admin_uses_server_allowlist(client, auth, monkeypatch):
    me = client.get("/api/me", headers=auth).json()
    monkeypatch.setattr(settings(), "app_mode", "live")
    import app.auth as auth_module

    class Response:
        status_code = 200

        def json(self):
            return {"id": me["id"], "user_metadata": {"role": "admin"}}

    monkeypatch.setattr(auth_module.httpx, "get", lambda *args, **kwargs: Response())
    monkeypatch.setattr(settings(), "admin_user_ids", "")
    assert client.get("/api/admin/overview", headers=auth).status_code == 403
    # Private live access is gated until data review, even with a valid identity.
    assert client.get("/api/venues", headers=auth).status_code == 403
    from app.db import Counter

    with Session() as db:
        db.add(Counter(key="launch_data_approved", value=1))
        db.commit()
    monkeypatch.setattr(settings(), "release_stage", "test")
    monkeypatch.setattr(settings(), "test_user_ids", me["id"])
    assert client.get("/api/venues", headers=auth).json() == []


def test_invalid_request_and_out_of_coverage(client, auth, request_data):
    request_data["party_size"] = 0
    assert client.post("/api/plans", headers=auth, json=request_data).status_code == 422
    request_data.update(party_size=2, lat=13.08, lng=80.27)
    assert client.post("/api/plans", headers=auth, json=request_data).status_code == 422


def test_failed_refresh_does_not_change_verification(client, monkeypatch):
    from app import jobs

    with Session() as db:
        v = db.get(Venue, "demo-sushi")
        v.is_demo = False
        v.details = {**v.details, "google_place_id": "abc"}
        db.commit()
        before = [
            (c.id, c.observed_at, c.expires_at)
            for c in db.scalars(select(Claim).where(Claim.venue_id == v.id))
        ]
        job = enqueue(db, "refresh", {"venue_id": v.id}, "failure-test")

    def fail(*args):
        raise Unavailable("Simulated provider outage")

    monkeypatch.setattr(jobs, "google_details", fail)
    assert run_once()
    with Session() as db:
        assert [
            (c.id, c.observed_at, c.expires_at)
            for c in db.scalars(select(Claim).where(Claim.venue_id == v.id))
        ] == before
        j = db.get(Job, job.id)
        assert j.state == "queued" and j.completed_at is None


def test_older_claim_cannot_override_newer_fact(client, auth):
    from app.evidence import ingest_claim
    from app.schemas import ClaimInput

    current = datetime.now(timezone.utc)
    with Session() as db:
        data = ClaimInput(
            venue_id="demo-sushi",
            field="price_per_person",
            value={"value": 500},
            source_url="https://merchant.example/menu",
            source_type="merchant",
            source_group="merchant",
            observed_at=current - timedelta(days=1),
            expires_at=current + timedelta(days=1),
        )
        c = ingest_claim(db, data, "test-admin", trusted=True)
        assert c.status == "superseded"
        assert db.get(Venue, "demo-sushi").details["price_per_person"] == 480
