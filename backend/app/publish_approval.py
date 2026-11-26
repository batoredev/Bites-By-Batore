"""Operations > Approve places: the owner approves every place before customers can see it.

The owner decided on 26 November 2026 to personally approve every single place. Each
approval is tied to the exact facts shown (release.fact_fingerprint); if a fact changes
later, the place comes back as "changed". Approvals live in venue.details["owner_publish"]
and are read by the release snapshot (release.py). Every decision is written to the audit
trail. There is no bulk approve: one place, one decision.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from . import release
from .auth import admin_user
from .db import Audit, Claim, IdentifiedSpot, Venue, get_db, now

router = APIRouter(prefix="/api/admin/publish")
STATES = ("waiting", "changed", "blocked", "approved", "rejected")


def _uid(user) -> str:
    return str(getattr(user, "id", None) or user)


def _maps(venue) -> tuple[str, str]:
    if venue.lat is not None and venue.lng is not None:
        point = f"{venue.lat},{venue.lng}"
        return (f"https://www.google.com/maps/search/?api=1&query={point}",
                f"https://maps.google.com/maps?q={point}&z=17&output=embed")
    query = quote_plus(f"{venue.name} {venue.area} Coimbatore")
    return (f"https://www.google.com/maps/search/?api=1&query={query}",
            f"https://maps.google.com/maps?q={query}&z=14&output=embed")


def _item(venue, spot_data: dict, claims: list, decision: dict) -> dict:
    place = release._place(venue, spot_data, claims, decision)
    approval = (venue.details or {}).get("owner_publish") or {}
    link, embed = _maps(venue)
    return {
        **{k: place[k] for k in (
            "id", "name", "category", "area", "address", "lat", "lng", "tags", "hours", "hours_basis",
            "price_per_person", "price_basis", "fee_per_group", "visit_minutes", "max_group", "min_age",
            "child_friendly", "vegetarian", "sessions", "sources", "source_groups", "last_seen")},
        "state": decision["state"],
        "blockers": decision["blockers"],
        "hints": decision["hints"],
        "decided_at": approval.get("at"),
        "note": approval.get("note", ""),
        "maps_link": link,
        "embed": embed,
    }


def _load(db, owner_id: str, ids: list[str] | None = None):
    query = select(Venue).where(Venue.is_demo.is_(False), Venue.status == "published")
    if ids is not None:
        query = query.where(Venue.id.in_(ids))
    venues = list(db.scalars(query.order_by(Venue.category, Venue.name, Venue.id)))
    spot_ids = [s for s in ((v.details or {}).get("identified_spot_id") for v in venues) if s]
    spots = (
        {s.id: s for s in db.scalars(select(IdentifiedSpot).where(
            IdentifiedSpot.user_id == owner_id, IdentifiedSpot.id.in_(spot_ids)))}
        if spot_ids else {}
    )
    claims: dict[str, list] = {}
    if venues:
        for claim in db.scalars(select(Claim).where(Claim.venue_id.in_([v.id for v in venues]))):
            claims.setdefault(claim.venue_id, []).append(claim)
    verdicts = release.owner_verdicts()
    at = datetime.now(timezone.utc)
    rows = []
    for venue in venues:
        spot = spots.get((venue.details or {}).get("identified_spot_id"))
        data = spot.data if spot else {}
        decision = release.publish_decision(venue, data, verdicts.get(spot.id) if spot else None, at)
        if not spot:
            decision["blockers"].append("no linked research record")
            if decision["state"] != "rejected":
                decision["state"] = "blocked"
        rows.append((venue, data, claims.get(venue.id, []), decision))
    return rows


@router.get("/places")
def places(
    state: Literal["waiting", "changed", "blocked", "approved", "rejected", "all"] = "waiting",
    category: str = "",
    q: str = Query("", max_length=100),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user=Depends(admin_user),
    db=Depends(get_db),
):
    rows = _load(db, _uid(user))
    counts = {s: 0 for s in STATES}
    for *_, decision in rows:
        counts[decision["state"]] += 1
    in_state = [r for r in rows if state == "all" or r[3]["state"] == state]
    categories: dict[str, int] = {}
    for venue, *_ in in_state:
        categories[venue.category] = categories.get(venue.category, 0) + 1
    needle = q.strip().casefold()
    chosen = [
        r for r in in_state
        if (not category or r[0].category == category)
        and (not needle or needle in r[0].name.casefold() or needle in (r[0].area or "").casefold())
    ]
    return {
        "counts": counts,
        "total_places": len(rows),
        "categories": dict(sorted(categories.items())),
        "matching": len(chosen),
        "items": [_item(*r) for r in chosen[offset:offset + limit]],
        "rule": release.PUBLISH_RULE,
    }


class Decide(BaseModel):
    venue_id: str = Field(min_length=1, max_length=64)
    decision: Literal["approve", "reject", "clear"]
    note: str = Field("", max_length=500)


@router.post("/decide")
def decide(body: Decide, user=Depends(admin_user), db=Depends(get_db)):
    venue = db.get(Venue, body.venue_id)
    if not venue or venue.is_demo or venue.status != "published":
        raise HTTPException(404, "No such live place")
    uid = _uid(user)
    before = (venue.details or {}).get("owner_publish") or {}
    (row,) = _load(db, uid, [venue.id])
    blockers = row[3]["blockers"]
    if body.decision == "approve" and blockers:
        raise HTTPException(409, "This place can't be approved yet: " + "; ".join(blockers))
    details = {k: v for k, v in (venue.details or {}).items() if k != "owner_publish"}
    if body.decision != "clear":
        details["owner_publish"] = {
            "decision": body.decision,
            "by": uid,
            "at": now(),
            "fingerprint": release.fact_fingerprint(venue),
            "note": body.note.strip(),
        }
    venue.details = details
    db.add(Audit(actor=uid, action="publish." + body.decision, target=f"venue:{venue.id}",
                 detail={"name": venue.name, "before": before.get("decision"), "note": body.note.strip()}))
    db.commit()
    (row,) = _load(db, uid, [venue.id])
    return _item(*row)
