from datetime import datetime, timedelta, timezone
from sqlalchemy import select
import pytest
from app.db import Session, Venue, Job
from app.config import settings
from app.providers import route_matrix, gemini_analysis, opening_windows, Unavailable, increment_bounded
from app.evidence import ingest_claim
from app.schemas import ClaimInput
from app.jobs import run_once


def test_route_matrix_partial_failure_is_not_zero_distance(client, monkeypatch):
    from app import providers

    monkeypatch.setattr(settings(), "google_maps_api_key", "test-placeholder")
    monkeypatch.setattr(
        providers,
        "call",
        lambda *a, **k: [
            {
                "originIndex": 0,
                "destinationIndex": 1,
                "condition": "ROUTE_EXISTS",
                "duration": "600s",
                "distanceMeters": 2500,
            },
            {"originIndex": 1, "destinationIndex": 0, "condition": "ROUTE_NOT_FOUND", "status": {"code": 5}},
        ],
    )
    with Session() as db:
        matrix = route_matrix(
            db, [(11, 77), (11.01, 77.01)], "drive", datetime.now(timezone.utc) + timedelta(hours=1)
        )
    assert matrix[(0, 1)]["minutes"] >= 10
    assert (1, 0) not in matrix


def test_gemini_text_only_cannot_claim_video_was_seen(client, monkeypatch):
    from app import providers

    monkeypatch.setattr(settings(), "gemini_api_key", "test-placeholder")
    monkeypatch.setattr(
        providers,
        "call",
        lambda *a, **k: {
            "candidates": [
                {"content": {"parts": [{"text": '{"venue_candidates":[],"video":{"analyzed":true}}'}]}}
            ]
        },
    )
    with Session() as db:
        result = gemini_analysis(db, {"caption": "A cafe"})
    assert result["video"]["analyzed"] is False


def test_invalid_model_output_not_published(client, monkeypatch):
    from app import providers

    monkeypatch.setattr(settings(), "gemini_api_key", "test-placeholder")
    monkeypatch.setattr(
        providers, "call", lambda *a, **k: {"candidates": [{"content": {"parts": [{"text": "not-json"}]}}]}
    )
    with Session() as db, pytest.raises(Unavailable):
        gemini_analysis(db, {"caption": "A cafe"})


def test_current_open_windows_require_dates():
    assert opening_windows({"currentOpeningHours": {"openNow": True}}) == []
    data = {
        "currentOpeningHours": {
            "periods": [
                {
                    "open": {"date": {"year": 2026, "month": 11, "day": 4}, "hour": 10},
                    "close": {"date": {"year": 2026, "month": 11, "day": 4}, "hour": 20},
                }
            ]
        }
    }
    assert len(opening_windows(data)) == 1
    assert "10:00" in opening_windows(data)[0][0]


def test_shared_call_counter_has_atomic_limit(client):
    with Session() as db:
        assert increment_bounded(db, "test-limit", 2)
        assert increment_bounded(db, "test-limit", 2)
        assert not increment_bounded(db, "test-limit", 2)


def test_untrusted_source_cannot_self_assign_authority(client):
    now = datetime.now(timezone.utc)
    with Session() as db:
        c = ingest_claim(
            db,
            ClaimInput(
                venue_id="demo-sushi",
                field="price_per_person",
                value={"value": 490},
                source_url="https://claim.example/menu",
                source_type="official",
                source_group="fake-official",
                observed_at=now,
                expires_at=now + timedelta(hours=3),
            ),
            "visitor",
            trusted=False,
        )
        assert c.status == "review" and c.source_type == "visitor"
        assert db.get(Venue, "demo-sushi").details["price_per_person"] == 480


def test_media_replaces_pending_text_analysis(client, auth):
    sub = client.post("/api/submissions", headers=auth, json={"caption": "Uploaded video"}).json()
    # Minimal signature fixture checks routing/retention, not actual video decoding.
    response = client.post(
        f"/api/submissions/{sub['id']}/media",
        headers=auth,
        files={"file": ("test.mp4", b"\x00\x00\x00\x20ftypisom" + b"\0" * 30, "video/mp4")},
    )
    assert response.status_code == 200
    with Session() as db:
        jobs = list(db.scalars(select(Job)))
        assert sum(j.state == "queued" for j in jobs) == 1
        assert sum(j.state == "cancelled" for j in jobs) == 1
    assert run_once()
    from app.db import Submission

    with Session() as db:
        assert "media" not in db.get(Submission, sub["id"]).content


def test_supported_negation_and_unknown_specific_request(client, auth, request_data):
    request_data.update(query="no sushi, something different")
    rows = client.post("/api/plans", headers=auth, json=request_data).json()["options"]
    assert rows
    assert all(s["venue_id"] != "demo-sushi" for p in rows for s in p["result"]["stops"])
    request_data["query"] = "pizza"
    response = client.post("/api/plans", headers=auth, json=request_data).json()
    assert response["options"] == [] and "no supported match" in response["message"]


def test_operations_validation_and_publication_gates(client, auth):
    assert (
        client.put(
            "/api/admin/venues/demo-sushi/operations", headers=auth, json={"visit_minutes": -5}
        ).status_code
        == 422
    )
    row = client.post(
        "/api/admin/venues",
        headers=auth,
        json={
            "name": "New demo",
            "category": "food",
            "area": "RS Puram",
            "address": "Test-only venue address",
            "lat": 11.01,
            "lng": 76.95,
        },
    ).json()
    assert (
        client.post(
            f"/api/admin/venues/{row['id']}/publish",
            headers=auth,
            json={"decision": "approve", "reason": "Needs essential evidence first"},
        ).status_code
        == 422
    )


@pytest.mark.parametrize("exhausted", ["provider", "instagram-browser"])
def test_blocked_browser_reserves_neither_allowance(client, monkeypatch, exhausted):
    from app.providers import reserve_browser_call, DeferredCollection
    from app.db import Counter

    monkeypatch.setattr(settings(), "max_provider_calls_per_day", 10)
    monkeypatch.setattr(settings(), "browser_daily_limit", 10)
    day = datetime.now(timezone.utc).date().isoformat()
    with Session() as db:
        for name in ["provider", "instagram-browser"]:
            db.add(Counter(key=f"{name}:{day}", value=10 if name == exhausted else 2))
        db.commit()
        with pytest.raises(DeferredCollection):
            reserve_browser_call(db)
        db.expire_all()
        assert db.get(Counter, f"{exhausted}:{day}").value == 10
        other = "provider" if exhausted == "instagram-browser" else "instagram-browser"
        assert db.get(Counter, f"{other}:{day}").value == 2


def test_successful_browser_reserves_both_allowances_once(client, monkeypatch):
    from app.providers import reserve_browser_call
    from app.db import Counter

    monkeypatch.setattr(settings(), "max_provider_calls_per_day", 10)
    monkeypatch.setattr(settings(), "browser_daily_limit", 10)
    day = datetime.now(timezone.utc).date().isoformat()
    with Session() as db:
        reserve_browser_call(db)
        assert db.get(Counter, f"provider:{day}").value == 1
        assert db.get(Counter, f"instagram-browser:{day}").value == 1
