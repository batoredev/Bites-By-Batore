import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from app.config import settings


def test_signed_merchant_update_is_replay_safe(client, monkeypatch):
    secret = "test-only-secret-with-more-than-32-characters"
    monkeypatch.setattr(settings(), "merchant_webhook_secret", secret)
    current = datetime.now(timezone.utc)
    payload = {
        "event_id": "test-price-001",
        "facts": [
            {
                "venue_id": "demo-sushi",
                "field": "price_per_person",
                "value": {"value": 490},
                "source_url": "https://merchant.example/menu",
                "source_type": "merchant",
                "source_group": "merchant.example",
                "observed_at": current.isoformat(),
                "expires_at": (current + timedelta(days=1)).isoformat(),
            }
        ],
    }
    raw = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(secret.encode(), timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-Batore-Timestamp": timestamp,
        "X-Batore-Signature": signature,
    }
    response = client.post("/api/ingest/merchant", content=raw, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["duplicate"] is False
    assert response.json()["facts"][0]["status"] == "accepted"
    repeated = client.post("/api/ingest/merchant", content=raw, headers=headers)
    assert repeated.json()["duplicate"] is True
    assert repeated.json()["facts"] == response.json()["facts"]
    bad = {**headers, "X-Batore-Signature": "invalid"}
    assert client.post("/api/ingest/merchant", content=raw, headers=bad).status_code == 401
    old = {**headers, "X-Batore-Timestamp": str(int(time.time()) - 3600)}
    assert client.post("/api/ingest/merchant", content=raw, headers=old).status_code == 401


def test_unconfigured_ingestion_cannot_change_data(client, monkeypatch):
    monkeypatch.setattr(settings(), "merchant_webhook_secret", "")
    current = datetime.now(timezone.utc)
    response = client.post(
        "/api/ingest/merchant",
        json={
            "event_id": "test-closed-001",
            "facts": [
                {
                    "venue_id": "demo-sushi",
                    "field": "closed",
                    "value": {"value": True},
                    "source_url": "https://merchant.example/status",
                    "source_type": "merchant",
                    "source_group": "merchant",
                    "observed_at": current.isoformat(),
                    "expires_at": (current + timedelta(days=1)).isoformat(),
                }
            ],
        },
    )
    assert response.status_code == 503
