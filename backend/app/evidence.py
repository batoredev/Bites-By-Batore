from datetime import datetime, timezone
from urllib.parse import urlparse
from sqlalchemy import select
from .db import Claim, Venue, Audit, now
from .categories import FOOD


def validate_value(field, value):
    if field == "offerings":
        from .schemas import MenuOffering
        from .menu import item_key
        from pydantic import ValidationError

        if not isinstance(value, list) or len(value) > 200:
            return False
        try:
            rows = [MenuOffering.model_validate(row) for row in value]
            return len({item_key(r.name) for r in rows}) == len(rows)
        except (ValidationError, TypeError):
            return False
    if field == "dining_format":
        from .menu import DINING_FORMATS

        return isinstance(value, str) and value in DINING_FORMATS
    if field == "amenities":
        return isinstance(value, dict) and all(
            k in {"parking", "washroom", "indoor_seating", "outdoor_seating"}
            and (v is None or type(v) is bool)
            for k, v in value.items()
        )
    if field in {"packages", "dated_sessions"}:
        from .schemas import ActivityPackage, DatedSession
        from pydantic import ValidationError

        model = ActivityPackage if field == "packages" else DatedSession
        if not isinstance(value, list) or len(value) > (10 if field == "packages" else 60):
            return False
        try:
            for row in value:
                model.model_validate(row)
            return True
        except ValidationError:
            return False
    if field == "price_per_person":
        return type(value) in (int, float) and 0 <= value <= 100000
    if field in {"closed", "vegetarian", "wheelchair"}:
        return isinstance(value, bool)
    if field == "hours":
        return isinstance(value, dict) and all(
            k in [str(i) for i in range(7)]
            and isinstance(windows, list)
            and all(
                isinstance(w, list)
                and len(w) == 2
                and all(type(n) is int and 0 <= n <= 1440 for n in w)
                and w[0] != w[1]
                for w in windows
            )
            for k, windows in value.items()
        )
    return isinstance(value, str) and 1 <= len(value) <= 500


def apply_claim(db, claim, actor):
    venue = db.get(Venue, claim.venue_id)
    newer = db.scalar(
        select(Claim).where(
            Claim.venue_id == claim.venue_id,
            Claim.field == claim.field,
            Claim.status == "accepted",
            Claim.observed_at > claim.observed_at,
        )
    )
    if newer:
        claim.status, claim.reason = "superseded", "A newer accepted observation exists"
        return
    for old in db.scalars(
        select(Claim).where(
            Claim.venue_id == claim.venue_id, Claim.field == claim.field, Claim.status == "accepted"
        )
    ):
        if old.id != claim.id:
            old.status = "superseded"
    claim.status = "accepted"
    if claim.field == "address":
        venue.address = claim.value["value"]
    else:
        venue.details = {**venue.details, claim.field: claim.value["value"]}
    venue.revision += 1
    venue.updated_at = now()
    db.add(
        Audit(
            actor=actor,
            action="claim.applied",
            target=claim.id,
            detail={"venue": venue.id, "field": claim.field},
        )
    )
    db.flush()
    # Fact acceptance never grants location approval. Only an explicit operator
    # publish action may make a venue available to itinerary recommendations.


def ingest_claim(db, data, actor, trusted=False):
    venue = db.get(Venue, data.venue_id)
    if not venue:
        raise ValueError("Unknown venue")
    value = data.value["value"]
    if data.field in {"offerings", "dining_format"} and venue.category not in FOOD:
        raise ValueError("Menus and dining formats apply to food venues")
    if not validate_value(data.field, value):
        raise ValueError("Invalid value for this fact")
    if data.observed_at > datetime.now(timezone.utc):
        raise ValueError("Observation cannot be in the future")
    if not venue.is_demo and urlparse(data.source_url).scheme != "https":
        raise ValueError("Live evidence requires an HTTPS source link")
    # Public submissions cannot self-assert an official/merchant authority.
    source_type = data.source_type if trusted else "visitor"
    observed = data.observed_at.astimezone(timezone.utc).isoformat()
    expires = data.expires_at.astimezone(timezone.utc).isoformat()
    duplicate = db.scalar(
        select(Claim).where(
            Claim.venue_id == venue.id,
            Claim.field == data.field,
            Claim.source_url == data.source_url,
            Claim.observed_at == observed,
        )
    )
    if duplicate:
        return duplicate
    claim = Claim(
        venue_id=venue.id,
        field=data.field,
        value=data.value,
        source_url=data.source_url,
        source_type=source_type,
        source_group=data.source_group,
        observed_at=observed,
        expires_at=expires,
        status="review",
        reason="Unverified visitor report",
    )
    db.add(claim)
    db.flush()
    old_value = venue.address if data.field == "address" else venue.details.get(data.field)
    unusual = False
    if data.field == "price_per_person" and old_value is not None:
        unusual = value == 0 or abs(value - old_value) / max(old_value, 1) > 0.35
    if data.field in {"closed", "address", "wheelchair", "vegetarian"} and old_value != value:
        unusual = True
    if expires <= now():
        claim.reason = "Evidence already expired"
    elif unusual:
        claim.reason = "Unusual or consequential change requires human review"
    elif trusted and source_type in {"merchant", "official"}:
        claim.reason = "Authenticated authoritative source; ordinary update"
        apply_claim(db, claim, actor)
    else:
        claim.reason = "Independent corroboration or human review required"
    db.add(Audit(actor=actor, action="claim.received", target=claim.id, detail={"status": claim.status}))
    db.commit()
    return claim
