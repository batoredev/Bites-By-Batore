from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Literal

from pydantic import BaseModel, Field
from urllib.parse import urlencode

from sqlalchemy import func, select
from .auth import admin_user
from .config import settings
from .db import get_db, IdentifiedSpot, Venue, Audit, now
from .spots import spot_dict, reconcile_spots, INACTIVE
from .spot_identity import maps_reference, quality_issues, name_key, clean_name
from .schemas import Category, VenueInput, VenueOperations

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
        kind = (row.data.get("rejection") or {}).get("kind", "")
        return "rejected", "Rejected by you" + (": " + kind.replace("_", " ") if kind else "")
    if row.status == "quarantined":
        text = issues[0] if issues else "Held for review"
        kind = "duplicate" if "duplicate" in text.casefold() else "held"
        return kind, text
    if row.status == "awaiting_approval":
        return "awaiting_approval", "Prepared; awaiting approval"
    if not has_point:
        return "no_coordinates", "No map coordinates yet"
    if not row.data.get("operator_named") and quality_issues(row.name, row.area, row.data):
        return "held", "Name needs review"
    return "ready", "Ready; not yet published (new, or a duplicate of a nearby published place)"


@router.get("/unpublished")
def unpublished(include_published: bool = False, user=Depends(admin_user), db=Depends(get_db)):
    """Compact list of every draft the planner cannot use, with the reason."""
    rows = []
    query = select(IdentifiedSpot).where(IdentifiedSpot.user_id == user.id)
    if not include_published:
        query = query.where(IdentifiedSpot.status != "approved")
    for row in db.scalars(query.order_by(IdentifiedSpot.updated_at.desc())):
        data = row.data
        point = data.get("coordinates") or {}
        has_point = "lat" in point and "lng" in point
        kind, reason = _unpublished_reason(row, has_point)
        if row.status == "approved":
            kind, reason = "published", "Published in the planner"
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
                "edited_by_you": bool(data.get("operator_edits") or data.get("operator_named")),
                "source": "owner"
                if "owner" in types
                else "instagram"
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
    return {
        "places": rows,
        "unpublished": sum(r["reason_kind"] != "published" for r in rows),
        "published": published or 0,
    }


class SpotEdit(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    category: Category | None = None
    area: str | None = Field(default=None, max_length=100)
    maps_url: str | None = Field(default=None, max_length=2048)
    release: bool = False


class SpotRejection(BaseModel):
    kind: Literal["not_a_venue", "out_of_scope", "wrong_city", "closed", "other"]
    block_creator: bool = False
    reason: str = Field(default="", max_length=500)


class PlacesAdd(BaseModel):
    names: list[str] = Field(min_length=1, max_length=50)
    category: Category | None = None
    area: str = Field(default="", max_length=100)
    maps_url: str = Field(default="", max_length=2048)
    investigate: bool = True


def _owned(db, spot_id, user):
    row = db.get(IdentifiedSpot, spot_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Place not found")
    return row


def _link_point(maps_url):
    from .geocode import link_points
    from .planner import km

    points = link_points([maps_url])
    if not points:
        raise HTTPException(
            422, "Open the place in Google Maps and paste a link that contains its coordinates"
        )
    lat, lng, link = points[0]
    if km((lat, lng), (11.0168, 76.9558)) > 40:
        raise HTTPException(422, "That point is more than 40 km from Coimbatore")
    return {"lat": lat, "lng": lng, "source_url": link, "basis": "Maps link supplied by the owner"}


def _sync_venue(db, row):
    """Keep a published test venue in step with its corrected place record."""
    venue = db.get(Venue, row.venue_id) if row.venue_id else None
    if not venue:
        return
    venue.name, venue.category = row.name, row.category
    if row.area:
        venue.area = row.area
    point = row.data.get("coordinates") or {}
    if "lat" in point and "lng" in point:
        venue.lat, venue.lng = float(point["lat"]), float(point["lng"])
    venue.revision += 1
    venue.updated_at = now()


@router.post("/publish-ready")
def publish_ready(user=Depends(admin_user), db=Depends(get_db)):
    """Publish every ready place to the labelled test inventory (local testing only)."""
    from . import test_inventory

    if settings().app_mode != "local":
        raise HTTPException(409, "The agent-approved test inventory exists only in local mode")
    result = test_inventory.publish(db, user.id)
    db.commit()
    return result


@router.get("/learned")
def learned_rules(user=Depends(admin_user), db=Depends(get_db)):
    from .learned import summary

    return summary(db, user.id)


@router.post("/add")
def add_places(data: PlacesAdd, user=Depends(admin_user), db=Depends(get_db)):
    """Places the owner knows. The name is trusted; everything else still needs evidence."""
    from .categories import classify
    from .learned import category_for, load
    from .spots import upsert_spot

    point = _link_point(data.maps_url) if data.maps_url else None
    names = list(dict.fromkeys(clean_name(n) for n in data.names if len(clean_name(n)) >= 2))
    if not names:
        raise HTTPException(422, "Enter at least one place name")
    if point and len(names) > 1:
        raise HTTPException(422, "A Maps link belongs to one place; add that place on its own")
    learned = load(db, user.id)
    added, existing, started = [], [], 0
    for name in names:
        before = set(db.scalars(select(IdentifiedSpot.id).where(IdentifiedSpot.user_id == user.id)))
        evidence = {
            "sources": [
                {
                    "type": "owner",
                    "url": data.maps_url,
                    "collected_at": now(),
                    "basis": "Added by the owner from personal knowledge; details unverified",
                }
            ],
            "operator_named": True,
            "name_status": "operator_named",
            **({"coordinates": point, "maps_links": [data.maps_url]} if point else {}),
        }
        category = data.category or category_for(learned, name) or classify(name)
        row = upsert_spot(db, user.id, name, category, data.area, evidence)
        if row is None:
            existing.append(name)
            continue
        if data.category:
            row.category = data.category
            row.data = {**row.data, "operator_category": data.category}
        if row.status == "quarantined":
            row.status = "identified"
            row.data = {**row.data, "quality_issues": []}
        (existing if row.id in before else added).append(row.name)
        db.add(Audit(actor=user.id, action="spot.owner_added", target=row.id, detail={"name": name}))
        db.commit()
        if data.investigate and settings().app_mode == "local" and started < 10:
            from .research import start_case

            start_case(
                db,
                user.id,
                " ".join(x for x in [row.name, row.area, "Coimbatore"] if x),
                {"owner_added_spot": row.id},
            )
            started += 1
    db.commit()
    return {"added": added, "already_listed": existing, "investigations_started": started}


@router.post("/{spot_id}/edit")
def edit_spot(spot_id: str, data: SpotEdit, user=Depends(admin_user), db=Depends(get_db)):
    """Correct a place by hand. Each correction is kept and reused as a rule."""
    from .spots import lock_inventory

    lock_inventory(db)
    row = _owned(db, spot_id, user)
    if row.status in {"merged", "rejected"}:
        raise HTTPException(409, "Restore this place before editing it")
    record, edits = dict(row.data), []
    if data.name and clean_name(data.name) != row.name:
        new = clean_name(data.name)
        area = data.area if data.area is not None else row.area
        clash = next(
            (
                o
                for o in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user.id))
                if o.id != row.id
                and o.status not in INACTIVE
                and name_key(o.name) == name_key(new)
                and name_key(o.area) == name_key(area)
            ),
            None,
        )
        if clash:
            raise HTTPException(
                409, {"message": "A place with this name and area already exists", "spot_id": clash.id}
            )
        edits.append({"field": "name", "from": row.name, "to": new})
        record["aliases"] = list(dict.fromkeys([new, row.name, *record.get("aliases", [])]))
        record["operator_named"], record["name_status"] = True, "operator_named"
        source_id = next(iter(record.get("source_ids", [])), None)
        if source_id and len(row.name) >= 3:
            # The same correction also reaches the model as a reviewed example.
            from .db import ResearchCorrection

            db.add(
                ResearchCorrection(
                    user_id=user.id,
                    source_id=source_id,
                    role="caption",
                    scope=row.name[:120],
                    original=row.name,
                    corrected=new,
                    reason="Owner corrected the venue name on the place record",
                )
            )
        row.name = new
    if data.category and data.category != row.category:
        edits.append({"field": "category", "from": row.category, "to": data.category})
        row.category = data.category
    if data.category:
        record["operator_category"] = data.category
    if data.area is not None and data.area.strip() != row.area:
        edits.append({"field": "area", "from": row.area, "to": data.area.strip()})
        row.area = data.area.strip()
    if data.maps_url:
        record["coordinates"] = _link_point(data.maps_url)
        record["maps_links"] = list(dict.fromkeys([data.maps_url, *record.get("maps_links", [])]))
        edits.append({"field": "coordinates", "from": "", "to": data.maps_url[:200]})
    if data.release and row.status == "quarantined":
        edits.append({"field": "status", "from": "quarantined", "to": "identified"})
        row.status = "identified"
        record["quality_issues"] = []
        record["operator_named"], record["name_status"] = True, "operator_named"
    if not edits and not data.category:
        raise HTTPException(422, "Nothing to change")
    stamp = now()
    history = [*record.get("operator_edits", []), *({**e, "at": stamp} for e in edits)]
    record["operator_edits"] = history[-40:]
    row.data, row.updated_at = record, stamp
    _sync_venue(db, row)
    db.add(Audit(actor=user.id, action="spot.edited", target=row.id, detail={"edits": edits}))
    db.commit()
    return {
        "id": row.id,
        "name": row.name,
        "category": row.category,
        "area": row.area,
        "status": row.status,
    }


@router.post("/{spot_id}/reject")
def reject_spot(spot_id: str, data: SpotRejection, user=Depends(admin_user), db=Depends(get_db)):
    """Remove a place. Rejecting it as not a venue stops the same name being proposed again."""
    from sqlalchemy import delete

    from .db import Claim, ResearchSource
    from .learned import LEARN_FROM_REJECTION
    from .spots import lock_inventory

    lock_inventory(db)
    row = _owned(db, spot_id, user)
    if row.status in {"merged", "rejected"}:
        raise HTTPException(409, "This place is already inactive")
    creators = []
    ids = row.data.get("source_ids", [])
    if data.block_creator and ids:
        found = db.scalars(select(ResearchSource.creator).where(ResearchSource.id.in_(ids)))
        creators = sorted({c.casefold().lstrip("@") for c in found if c})
    if row.venue_id:
        venue = db.get(Venue, row.venue_id)
        if venue and not venue.details.get("test_inventory"):
            raise HTTPException(409, "Pause this verified venue in the Venue desk instead")
        if venue:
            db.execute(delete(Claim).where(Claim.venue_id == venue.id))
            db.delete(venue)
        row.venue_id = ""
    stamp = now()
    row.data = {
        **row.data,
        "previous_status": "identified" if row.status == "approved" else row.status,
        "rejection": {
            "kind": data.kind,
            "reason": data.reason,
            "at": stamp,
            "blocked_creators": creators,
        },
    }
    row.status, row.updated_at = "rejected", stamp
    also_held = 0
    if data.kind in LEARN_FROM_REJECTION:
        for other in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user.id)):
            if (
                other.id != row.id
                and other.status == "identified"
                and not other.venue_id
                and name_key(other.name) == name_key(row.name)
            ):
                other.data = {
                    **other.data,
                    "previous_status": other.status,
                    "quality_issues": ["You rejected this same name on another record"],
                }
                other.status, other.updated_at = "quarantined", stamp
                also_held += 1
    db.add(
        Audit(
            actor=user.id,
            action="spot.rejected",
            target=row.id,
            detail={"kind": data.kind, "blocked_creators": creators, "also_held": also_held},
        )
    )
    db.commit()
    return {"id": row.id, "status": row.status, "blocked_creators": creators, "also_held": also_held}


@router.post("/{spot_id}/restore")
def restore_spot(spot_id: str, user=Depends(admin_user), db=Depends(get_db)):
    """Undo a rejection; its learned rule disappears with it."""
    row = _owned(db, spot_id, user)
    if row.status != "rejected":
        raise HTTPException(409, "Only a rejected place can be restored")
    record = {k: v for k, v in row.data.items() if k != "rejection"}
    row.status = record.pop("previous_status", "identified")
    row.data, row.updated_at = record, now()
    db.add(Audit(actor=user.id, action="spot.restored", target=row.id, detail={}))
    db.commit()
    return {"id": row.id, "status": row.status}


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
