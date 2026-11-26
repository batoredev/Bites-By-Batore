"""Release snapshot: the only data that leaves the laptop for the customer app.

Week 1 items 1.8 and 1.9 in docs/EXECUTION_PLAN.md. A release is a versioned,
checksummed JSON file holding the places that pass the publish rule, with only the facts
the planner needs, each labelled checked or estimated. Raw reels, comments, drafts,
review notes and model observations never go in it.

The publish rule (PUBLISH_RULE, a DRAFT until the owner approves it) decides each live
place. A place goes to customers only when every check passes; otherwise it is held with
the reasons, and stays on the laptop for more evidence or the owner's answer.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from .config import ROOT
from .db import Claim, IdentifiedSpot, Venue

RELEASE_DIR = ROOT / "data" / "releases"
LIVE_SHEET = ROOT / "data" / "city-collection" / "spotcheck-live-200.csv"
CITY_CENTRE = (11.0168, 76.9558)
CITY_RADIUS_KM = 40
FRESH_DAYS = 180
SNAPSHOT_FORMAT = 1

PUBLISH_RULE = {
    "version": "draft-1",
    "approved_by_owner": False,
    "checks": [
        "The place is live on the laptop (approved, published, not demo).",
        "It has a map point inside Coimbatore (within 40 km of the centre).",
        "It is not marked closed, and the owner has not answered 'no' or 'closed' for it.",
        "Either the owner said yes to it (Live places check or Place manager), or at least two "
        "independent kinds of source back it (Overture, OpenStreetMap, Instagram, the official "
        "site, other web pages).",
        "At least one source was seen within the last 180 days.",
        "Every price and opening time goes out labelled 'checked' or 'approx.'.",
    ],
}

# Kinds of source that count as independent of each other. Web search results and pages we
# monitor are one kind: both are "some web page mentions it".
SOURCE_GROUPS = {
    "overture": "overture",
    "openstreetmap": "openstreetmap",
    "instagram": "instagram",
    "official": "official",
    "monitored_page": "web",
    "web_candidate": "web",
}
OWNER_NO = {"no", "closed"}


def km(a, b) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def _when(value) -> datetime | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def owner_verdicts(sheet: Path = LIVE_SHEET) -> dict[str, str]:
    """spot_id -> yes/no/closed from the Live places check (the only sheet keyed by place ID)."""
    if not sheet.exists():
        return {}
    with sheet.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows or "spot_id" not in rows[0]:
        return {}
    id_col = rows[0].index("spot_id")
    verdicts = {}
    for row in rows[1:]:
        if len(row) > id_col and len(row) > 5 and row[5].strip():
            verdicts[row[id_col]] = row[5].strip().lower()
    return verdicts


def _owner_confirmed(venue_details: dict) -> bool:
    by = str(venue_details.get("maps_identity", {}).get("confirmed_by") or "")
    return bool(by) and not by.startswith("agent:")


def publish_decision(venue, spot_data: dict, verdict: str | None, at: datetime) -> dict:
    """Apply the publish rule to one place. Pure: no database access."""
    details = venue.details or {}
    reasons = []
    if venue.status != "published" or venue.is_demo:
        reasons.append("not a live place")
    if venue.lat is None or venue.lng is None or km((venue.lat, venue.lng), CITY_CENTRE) > CITY_RADIUS_KM:
        reasons.append("no map point inside Coimbatore")
    if str(details.get("closed")).lower() == "true":
        reasons.append("marked closed")
    if verdict in OWNER_NO:
        reasons.append(f"owner answered '{verdict}'")
    sources = spot_data.get("sources", []) or []
    groups = sorted({SOURCE_GROUPS.get(s.get("type"), s.get("type") or "unknown") for s in sources})
    owner_yes = verdict == "yes" or _owner_confirmed(details)
    if not owner_yes and len(groups) < 2:
        reasons.append("only one kind of source and no owner OK")
    seen = [_when(s.get("collected_at")) for s in sources] + [_when(spot_data.get("web_search_completed_at"))]
    latest = max((s for s in seen if s), default=None)
    if not owner_yes and (latest is None or at - latest > timedelta(days=FRESH_DAYS)):
        reasons.append(f"no source seen in the last {FRESH_DAYS} days")
    return {
        "publish": not reasons,
        "reasons": reasons,
        "source_groups": groups,
        "owner_ok": owner_yes,
        "last_seen": latest.isoformat() if latest else None,
    }


def _basis(claims: list, field: str) -> str:
    """'checked' only when a non-estimate accepted claim backs the field."""
    for claim in claims:
        if claim.field == field and claim.status == "accepted" and claim.source_type != "test_estimate":
            return "checked"
    return "approx."


def _place(venue, spot_data: dict, claims: list, decision: dict) -> dict:
    d = venue.details or {}
    public_sources = [
        {"type": s.get("type"), "url": s.get("url")}
        for s in spot_data.get("sources", []) or []
        if str(s.get("url", "")).startswith("https://")
    ]
    return {
        "id": venue.id,
        "name": venue.name,
        "category": venue.category,
        "area": venue.area,
        "address": venue.address,
        "lat": venue.lat,
        "lng": venue.lng,
        "tags": venue.tags or [],
        "hours": d.get("hours"),
        "hours_basis": _basis(claims, "hours"),
        "price_per_person": d.get("price_per_person"),
        "price_basis": _basis(claims, "price_per_person"),
        "fee_per_group": d.get("fee_per_group"),
        "visit_minutes": d.get("visit_minutes"),
        "wait_minutes": d.get("wait_minutes"),
        "max_group": d.get("max_group"),
        "min_age": d.get("min_age"),
        "child_friendly": d.get("child_friendly"),
        "vegetarian": d.get("vegetarian"),
        "sessions": d.get("sessions"),
        "sources": public_sources,
        "source_groups": decision["source_groups"],
        "owner_ok": decision["owner_ok"],
        "last_seen": decision["last_seen"],
        "claims": [
            {
                "field": c.field,
                "value": c.value,
                "source_type": c.source_type,
                "observed_at": c.observed_at,
                "expires_at": c.expires_at,
            }
            for c in sorted(claims, key=lambda c: (c.field, c.id))
            if c.status == "accepted"
        ],
    }


def checksum(places: list[dict]) -> str:
    canonical = json.dumps(places, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_snapshot(db, owner_id: str, at: datetime | None = None, sheet: Path = LIVE_SHEET) -> dict:
    at = at or datetime.now(timezone.utc)
    verdicts = owner_verdicts(sheet)
    venues = list(
        db.scalars(
            select(Venue).where(Venue.is_demo.is_(False), Venue.status == "published").order_by(Venue.id)
        )
    )
    spots = {s.id: s for s in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == owner_id))}
    claims_by_venue: dict[str, list] = {}
    if venues:
        for claim in db.scalars(select(Claim).where(Claim.venue_id.in_([v.id for v in venues]))):
            claims_by_venue.setdefault(claim.venue_id, []).append(claim)
    places, held = [], {}
    held_by_category: dict[str, int] = {}
    published_by_category: dict[str, int] = {}
    for venue in venues:
        spot = spots.get((venue.details or {}).get("identified_spot_id"))
        spot_data = spot.data if spot else {}
        decision = publish_decision(venue, spot_data, verdicts.get(spot.id) if spot else None, at)
        if not spot:
            decision["publish"] = False
            decision["reasons"].append("no linked research record")
        if decision["publish"]:
            places.append(_place(venue, spot_data, claims_by_venue.get(venue.id, []), decision))
            published_by_category[venue.category] = published_by_category.get(venue.category, 0) + 1
        else:
            for reason in decision["reasons"]:
                held[reason] = held.get(reason, 0) + 1
            held_by_category[venue.category] = held_by_category.get(venue.category, 0) + 1
    return {
        "format": SNAPSHOT_FORMAT,
        "version": at.strftime("%Y%m%d-%H%M%S"),
        "created_at": at.isoformat(timespec="seconds"),
        "city": "Coimbatore",
        "rule": PUBLISH_RULE,
        "counts": {
            "live_on_laptop": len(venues),
            "published": len(places),
            "held": len(venues) - len(places),
            "published_by_category": dict(sorted(published_by_category.items())),
            "held_by_category": dict(sorted(held_by_category.items())),
            "held_reasons": dict(sorted(held.items(), key=lambda kv: -kv[1])),
        },
        "checksum": checksum(places),
        "places": places,
    }


def write_snapshot(snapshot: dict, directory: Path = RELEASE_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"release-{snapshot['version']}.json"
    if path.exists():
        raise FileExistsError(f"{path.name} already exists; releases are never overwritten")
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return path


def verify_snapshot(path: Path) -> dict:
    """What production runs before importing: format, checksum and basic shape."""
    snapshot = json.loads(Path(path).read_text(encoding="utf-8"))
    problems = []
    if snapshot.get("format") != SNAPSHOT_FORMAT:
        problems.append("unknown format")
    places = snapshot.get("places", [])
    if checksum(places) != snapshot.get("checksum"):
        problems.append("checksum mismatch")
    ids = [p.get("id") for p in places]
    if len(ids) != len(set(ids)):
        problems.append("duplicate place ids")
    if any(p.get("lat") is None or p.get("lng") is None for p in places):
        problems.append("a place has no map point")
    if any(p.get("price_basis") not in {"checked", "approx."} or p.get("hours_basis") not in {"checked", "approx."}
           for p in places):
        problems.append("a price or opening time is not labelled")
    return {"ok": not problems, "problems": problems, "version": snapshot.get("version"), "places": len(ids)}
