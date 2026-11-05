"""Authenticated merchant push updates with replay protection and evidence review."""

import hashlib
import hmac
import time
from typing import Annotated
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update, or_
from .config import settings
from .db import get_db, Job, Venue, now
from .schemas import ClaimInput
from .evidence import ingest_claim, validate_value
from .jobs import enqueue, later

router = APIRouter()


class MerchantEvent(BaseModel):
    event_id: str = Field(min_length=5, max_length=200, pattern=r"^[A-Za-z0-9_.:-]+$")
    facts: list[ClaimInput] = Field(min_length=1, max_length=50)


@router.post("/api/ingest/merchant")
async def merchant_event(
    request: Request,
    data: MerchantEvent,
    x_batore_timestamp: Annotated[str, Header()] = "",
    x_batore_signature: Annotated[str, Header()] = "",
    db=Depends(get_db),
):
    secret = settings().merchant_webhook_secret
    if len(secret) < 32:
        raise HTTPException(503, "Merchant ingestion is not configured")
    try:
        timestamp = int(x_batore_timestamp)
    except ValueError as exc:
        raise HTTPException(401, "Invalid signature timestamp") from exc
    if abs(time.time() - timestamp) > 300:
        raise HTTPException(401, "Expired signature timestamp")
    raw = await request.body()
    expected = hmac.new(secret.encode(), x_batore_timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_batore_signature):
        raise HTTPException(401, "Invalid merchant signature")
    digest = hashlib.sha256(raw).hexdigest()
    key = "merchant:" + data.event_id
    record = db.scalar(select(Job).where(Job.key == key))
    if record:
        if record.payload.get("digest") != digest:
            raise HTTPException(409, "Event ID reused with different content")
        if record.state == "done":
            return {**record.result, "duplicate": True}
    for fact in data.facts:
        v = db.get(Venue, fact.venue_id)
        if not v or v.is_demo != (settings().app_mode == "demo"):
            raise HTTPException(422, "Unknown venue in merchant event")
        if not validate_value(fact.field, fact.value["value"]):
            raise HTTPException(422, "Invalid fact value")
    if not record:
        record = enqueue(db, "merchant_event", {"digest": digest}, key, state="received")
    if record.payload.get("digest") != digest:
        raise HTTPException(409, "Event ID reused with different content")
    won = db.execute(
        update(Job)
        .where(
            Job.id == record.id,
            or_(Job.state == "received", (Job.state == "processing_external") & (Job.lease_until < now())),
        )
        .values(state="processing_external", lease_until=later(120))
    )
    db.commit()
    if not won.rowcount:
        raise HTTPException(
            409, "This merchant event is already processing or completed; retry with the same event ID"
        )
    results = []
    for fact in data.facts:
        try:
            # Authority is established by the shared integration secret, not payload labels.
            claim = ingest_claim(
                db, fact.model_copy(update={"source_type": "merchant"}), "merchant-ingestion", trusted=True
            )
        except ValueError as exc:
            record.state, record.lease_until, record.error = "received", None, str(exc)[:500]
            db.commit()
            raise HTTPException(422, str(exc)) from exc
        results.append({"claim_id": claim.id, "status": claim.status})
        if claim.status == "review":
            enqueue(db, "refresh", {"venue_id": fact.venue_id}, f"correction:{claim.id}", priority=85)
    record.result, record.state, record.completed_at = {"facts": results}, "done", now()
    record.lease_until = None
    db.commit()
    return {**record.result, "duplicate": False}
