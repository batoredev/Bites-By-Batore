from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from urllib.parse import urlencode

from sqlalchemy import func, select
from .auth import admin_user
from .config import settings
from .db import get_db, IdentifiedSpot, Venue, Audit, now
from .spots import spot_dict, reconcile_spots, INACTIVE
from .spot_identity import maps_reference, quality_issues, name_key, clean_name
from .schemas import VenueInput, VenueOperations

router = APIRouter(prefix="/api/admin/spots")


@router.get("/duplicates")
def duplicate_status(user=Depends(admin_user), db=Depends(get_db)):
    from .duplicate_agent import status

    return status(db, user.id)


@router.post("/duplicates/run")
def duplicate_run(user=Depends(admin_user), db=Depends(get_db)):
    from .duplicate_agent import request_scan

    job = request_scan(db, user.id, force=True)
    return {"job_id": job.id, "state": job.state}


def _unpublished_reason(row, has_point):
    """One plain reason a draft is not in the planner."""
    issues = row.data.get("quality_issues") or []
    if row.status == "merged":
        return "merged", "Merged into another record"
    if row.status == "rejected":
        return "rejected", "Rejected"
    if row.status == "quarantined":
        text = issues[0] if issues else "Held for review"
        kind = "duplicate" if "duplicate" in text.casefold() else "held"
        return kind, text
    if row.status == "awaiting_approval":
        return "awaiting_approval", "Prepared; awaiting approval"
    if not has_point:
        return "no_coordinates", "No map coordinates yet"
    if quality_issues(row.name, row.area, row.data):
        return "held", "Name needs review"
    return "ready", "Ready; not yet published (new, or a duplicate of a nearby published place)"


@router.get("/unpublished")
def unpublished(user=Depends(admin_user), db=Depends(get_db)):
    """Compact list of every draft the planner cannot use, with the reason."""
    rows = []
    for row in db.scalars(
        select(IdentifiedSpot)
        .where(IdentifiedSpot.user_id == user.id, IdentifiedSpot.status != "approved")
        .order_by(IdentifiedSpot.updated_at.desc())
    ):
        data = row.data
        point = data.get("coordinates") or {}
        has_point = "lat" in point and "lng" in point
        kind, reason = _unpublished_reason(row, has_point)
        sources = data.get("sources") or []
        types = {s.get("type") for s in sources}
        first = next((s.get("url") for s in sources if str(s.get("url", "")).startswith("https://")), "")
        rows.append(
            {
                "id": row.id,
                "name": row.name,
                "category": row.category,
                "area": row.area,
                "status": row.status,
                "reason_kind": kind,
                "reason": reason,
                "has_coordinates": has_point,
                "has_price": any(
                    isinstance(o, dict) and o.get("price_inr") is not None for o in data.get("offerings", [])
                ),
                "has_hours": bool(data.get("hours") or data.get("hours_candidates")),
                "source": "instagram"
                if "instagram" in types
                else "directory"
                if "openstreetmap" in types
                else "web",
                "source_count": len(sources),
                "source_url": first,
                "offerings": [
                    str(o.get("name"))[:60]
                    for o in data.get("offerings", [])[:3]
                    if isinstance(o, dict) and o.get("name")
                ],
                "updated_at": row.updated_at,
                "map_search_url": "https://www.google.com/maps/search/?"
                + urlencode({"api": 1, "query": " ".join([row.name, row.area, "Coimbatore"])}),
            }
        )
    published = db.scalar(
        select(func.count())
        .select_from(IdentifiedSpot)
        .where(IdentifiedSpot.user_id == user.id, IdentifiedSpot.status == "approved")
    )
    return {"places": rows, "unpublished": len(rows), "published": published or 0}


@router.get("")
def listing(include_held: bool = False, user=Depends(admin_user), db=Depends(get_db)):
    rows = list(
        db.scalars(
            select(IdentifiedSpot)
            .where(IdentifiedSpot.user_id == user.id)
            .order_by(IdentifiedSpot.updated_at.desc())
        )
    )
    return {
        "spots": [spot_dict(r) for r in rows if include_held or r.status not in INACTIVE],
        "total": len(rows),
        "active": sum(r.status not in INACTIVE for r in rows),
        "held": sum(r.status in INACTIVE for r in rows),
        "publication": "Every location requires your explicit approval before itinerary suggestions",
    }


@router.post("/quality-check")
def quality_check(user=Depends(admin_user), db=Depends(get_db)):
    result = reconcile_spots(db, user.id)
    db.commit()
    return result


class MergeInput(BaseModel):
    target_id: str
    same_branch_checked: bool
    reason: str = Field(min_length=10, max_length=1000)


@router.post("/{spot_id}/merge")
def merge(spot_id: str, data: MergeInput, user=Depends(admin_user), db=Depends(get_db)):
    from .spots import lock_inventory
    from .duplicate_agent import merge_records

    lock_inventory(db)
    source, target = db.get(IdentifiedSpot, spot_id), db.get(IdentifiedSpot, data.target_id)
    if not source or not target or source.user_id != user.id or target.user_id != user.id:
        raise HTTPException(404, "Spot not found")
    if source.id == target.id or not data.same_branch_checked:
        raise HTTPException(422, "Choose a different record and confirm the exact same branch")
    if (
        source.venue_id
        or target.venue_id
        or source.status in {"merged", "rejected"}
        or target.status in INACTIVE
    ):
        raise HTTPException(409, "Merge active drafts before preparing either for approval")
    left, right = source.data.get("maps_identity", {}), target.data.get("maps_identity", {})
    if left.get("place_key") and right.get("place_key") and left["place_key"] != right["place_key"]:
        raise HTTPException(409, "Different confirmed Maps identities require identity correction first")
    try:
        merge_records(db, source, target, user.id, [data.reason])
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    db.commit()
    return {"spot_id": target.id, "published": False}


@router.post("/{spot_id}/maps-candidates")
def maps_candidates(spot_id: str, user=Depends(admin_user), db=Depends(get_db)):
    from .providers import google_search, Unavailable
    from .planner import km

    row = db.get(IdentifiedSpot, spot_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Spot not found")
    try:
        candidates = google_search(db, f"{row.name} {row.area} Coimbatore", 11.0168, 76.9558)
    except Unavailable as exc:
        return {
            "status": "unavailable",
            "reason": str(exc),
            "candidates": [],
            "search_url": spot_dict(row)["map_search_url"],
        }
    candidates = [
        c
        for c in candidates
        if c.get("location")
        and km((c["location"]["latitude"], c["location"]["longitude"]), (11.0168, 76.9558)) <= 40
    ]
    # API content is transient; no API names/addresses copied into our database.
    from .branch_matching import rank_google

    candidates = rank_google(
        {"name": row.name, "address_clues": [row.area, *row.data.get("address_clues", [])]}, candidates
    )
    return JSONResponse(
        {"status": "review_required", "candidates": candidates, "attribution": "Google Maps"},
        headers={"Cache-Control": "no-store"},
    )


@router.post("/sync-investigations")
def sync(user=Depends(admin_user), db=Depends(get_db)):
    from .spots import sync_inventory

    return sync_inventory(db, user.id)


@router.post("/collect")
def collect(user=Depends(admin_user), db=Depends(get_db)):
    from datetime import datetime, timezone
    from .jobs import enqueue

    if settings().app_mode == "demo":
        raise HTTPException(409, "Real inventory collection is disabled in demo")
    job = enqueue(
        db,
        "spot_inventory",
        {"user_id": user.id},
        f"spot-inventory:{user.id}:{datetime.now(timezone.utc).date().isoformat()}",
        priority=95,
    )
    return {"job_id": job.id, "state": job.state}


class Preparation(BaseModel):
    venue: VenueInput
    evidence_url: str = Field(pattern=r"^https://", max_length=2000)
    reason: str = Field(min_length=10, max_length=1000)
    maps_url: str = Field(default="", max_length=2048)
    maps_name_checked: bool = False


@router.post("/{spot_id}/prepare")
def prepare(spot_id: str, data: Preparation, user=Depends(admin_user), db=Depends(get_db)):
    row = db.get(IdentifiedSpot, spot_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Spot not found")
    if row.venue_id:
        return {"venue_id": row.venue_id, "status": row.status}
    if row.status == "merged":
        raise HTTPException(409, "Use the surviving record for this merged location")
    identity = None
    if settings().app_mode != "demo" or data.maps_url:
        if not data.maps_name_checked or not data.venue.details.get("branch_confirmed"):
            raise HTTPException(422, "Check the exact branch and its name against the Google Maps place")
        try:
            identity = maps_reference(data.maps_url)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        issues = quality_issues(data.venue.name, data.venue.area, {"address": data.venue.address})
        # Heuristics may flag real names such as 'Hidden Cafe'. An explicit
        # independent branch/Maps review can resolve them; keep that decision.
        identity["reviewed_warnings"] = issues
        for other in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user.id)):
            if (
                other.id != row.id
                and other.status not in INACTIVE
                and (
                    other.data.get("maps_identity", {}).get("place_key") == identity["place_key"]
                    or (
                        name_key(other.name) == name_key(data.venue.name)
                        and other.data.get("address")
                        and name_key(other.data["address"]) == name_key(data.venue.address)
                    )
                )
            ):
                raise HTTPException(
                    409,
                    {
                        "message": "This branch already exists; review or merge the existing record",
                        "spot_id": other.id,
                    },
                )
    from .planner import km

    if km((data.venue.lat, data.venue.lng), (11.0168, 76.9558)) > 40:
        raise HTTPException(422, "The first inventory covers Coimbatore within 40 km")
    if identity:
        for other in db.scalars(select(Venue).where(Venue.is_demo == (settings().app_mode == "demo"))):
            if other.details.get("maps_identity", {}).get("place_key") == identity["place_key"]:
                raise HTTPException(409, "This exact Maps branch already has a venue record")
    if any(
        k in data.venue.details for k in ("price_per_person", "hours", "closed", "vegetarian", "wheelchair")
    ):
        raise HTTPException(422, "Add essential facts through the evidence review queue")
    try:
        operations = VenueOperations.model_validate(data.venue.details)
    except ValueError as exc:
        raise HTTPException(422, "Invalid planning details") from exc
    venue = Venue(
        **data.venue.model_dump(exclude={"details"}),
        details={
            **operations.model_dump(mode="json"),
            **({"google_place_id": identity.get("place_id", "")} if identity else {}),
            "identified_spot_id": row.id,
            "branch_confirmation_source": data.evidence_url,
            **(
                {
                    "maps_identity": {
                        **identity,
                        "confirmed_by": user.id,
                        "confirmed_at": now(),
                        "name": data.venue.name,
                        "basis": "Operator independently checked name and exact Maps branch",
                    }
                }
                if identity
                else {}
            ),
        },
        status="pending",
        is_demo=settings().app_mode == "demo",
    )
    db.add(venue)
    db.flush()
    if identity:
        row.data = {
            **row.data,
            "aliases": list(dict.fromkeys([row.name, *row.data.get("aliases", [])])),
            "maps_identity": venue.details["maps_identity"],
            "name_status": "operator_maps_confirmed",
            "quality_issues": [],
            "address": data.venue.address,
            "coordinates": {
                "lat": data.venue.lat,
                "lng": data.venue.lng,
                "basis": "Operator branch confirmation",
            },
        }
        row.name, row.area, row.category = clean_name(data.venue.name), data.venue.area, data.venue.category
    row.venue_id, row.status, row.updated_at = venue.id, "awaiting_approval", now()
    db.add(
        Audit(
            actor=user.id,
            action="spot.prepared",
            target=row.id,
            detail={"venue_id": venue.id, "reason": data.reason, "evidence_url": data.evidence_url},
        )
    )
    db.commit()
    return {
        "venue_id": venue.id,
        "status": row.status,
        "message": "Venue prepared. Review essential facts, then explicitly approve this location in Venue desk.",
    }
