"""Agent-approved TEST inventory so the itinerary planner can be exercised.

The owner asked (12 November 2026) to skip per-location approval for the data
collected so far. Everything published here is marked ``test_inventory`` and
records which values are estimates. Nothing is presented as verified, and
``revert`` removes it again.
"""

import math
import re
import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from .categories import ESTIMATES, FOOD, classify, match
from .db import Audit, Claim, IdentifiedSpot, Venue, now
from .spot_identity import infer_area, name_key, possible_match, quality_issues

AGENT = "agent:test-inventory"
CENTRE = (11.0168, 76.9558)
SHOW_TIMES = ["10:30", "14:00", "18:15", "21:30"]
DAYS = ["mo", "tu", "we", "th", "fr", "sa", "su"]
VEG = re.compile(
    r"\b(pure veg|veg|vegetarian|bhavan|bhawan|annapoorna|saravana|sangeetha|a2b|adyar ananda)\b"
)


def _minutes(text):
    hour, minute = int(text[:2]), int(text[3:5])
    return hour * 60 + minute if 0 <= hour <= 24 and 0 <= minute < 60 else None


def parse_hours(values):
    """Parse simple OSM/JSON-LD style strings. Returns {} unless at least five days are covered."""
    week = {}
    for raw in values:
        text = str(raw).strip().lower().replace("–", "-").replace("—", "-")
        if "today" in text or "tomorrow" in text or "opens" in text:
            continue
        if text == "24/7":
            return {str(i): [[0, 1440]] for i in range(7)}
        for part in re.split(r"[;|]", text):
            part = part.strip()
            spans = re.findall(r"(\d{2}:\d{2})(?::\d{2})?\s*-\s*(\d{2}:\d{2})(?::\d{2})?", part)
            if not spans:
                continue
            head = part[: part.find(spans[0][0])].strip(" ,:")
            days = set()
            if not head:
                days = set(range(7))
            for a, b in re.findall(r"\b(mo|tu|we|th|fr|sa|su)\s*-\s*(mo|tu|we|th|fr|sa|su)\b", head):
                i, j = DAYS.index(a), DAYS.index(b)
                days |= set(range(i, j + 1)) if i <= j else set(range(i, 7)) | set(range(0, j + 1))
            days |= {DAYS.index(d) for d in re.findall(r"\b(mo|tu|we|th|fr|sa|su)\b", head)}
            windows = []
            for start, end in spans:
                a, b = _minutes(start), _minutes(end)
                if a is None or b is None or a == b:
                    continue
                windows.append([a, b])
            for day in days:
                # First source seen for a day wins; later conflicting pages are ignored.
                if windows and str(day) not in week:
                    week[str(day)] = windows
    return week if len(week) >= 5 else {}


def _point(data):
    point = data.get("coordinates") or {}
    try:
        lat, lng = float(point["lat"]), float(point["lng"])
    except (KeyError, TypeError, ValueError):
        return None
    return (lat, lng) if math.isfinite(lat + lng) else None


def _km(a, b):
    from .planner import km

    return km(a, b)


def retune_category(row):
    """Directory tags decide food vs activity; names only refine the kind."""
    named = match(row.name)
    if row.data.get("directory_refs"):
        if row.category in FOOD:
            return named if named in {"street_food", "dessert", "nightlife"} else row.category
        if row.category in {"adventure", "park"} and named in {"amusement", "attraction"}:
            return named
        return row.category
    context = " ".join(str(o.get("name", "")) for o in row.data.get("offerings", []) if isinstance(o, dict))
    return classify(row.name, context)


def _source_evidence(db, owner):
    """Per reel: names the caption gave, and the sign and speech text the video gave."""
    from .db import Investigation, ResearchSource

    def squash(value):
        return name_key(value).replace(" ", "")

    evidence = {}
    query = (
        select(ResearchSource)
        .join(Investigation, ResearchSource.case_id == Investigation.id)
        .where(Investigation.user_id == owner, ResearchSource.platform == "instagram")
    )
    for source in db.scalars(query):
        caption, video = source.analysis.get("caption", {}), source.analysis.get("video", {})
        tag = (source.content.get("location_tag") or {}).get("name", "")
        evidence[source.id] = {
            "names": [c.get("name", "") for c in caption.get("venue_candidates", [])]
            + ([tag] if tag else []),
            "text": squash(
                " ".join(
                    [
                        *(str(o.get("verbatim_text") or "") for o in video.get("observations", [])),
                        str(source.content.get("transcript") or ""),
                        str(source.content.get("caption") or ""),
                    ]
                )
            ),
            "analysed": video.get("status") == "observations_only",
        }
    return evidence


def _name_has_support(row, evidence):
    """False only when every source is an analysed reel and none backs the name."""
    ids = row.data.get("source_ids", [])
    if not ids or row.data.get("directory_refs") or row.data.get("location_tag"):
        return True
    if any(
        s.get("type") not in {"instagram", "web_candidate", "monitored_page"}
        for s in row.data.get("sources", [])
    ):
        return True
    names = [row.name, *row.data.get("aliases", [])]
    for ident in ids:
        found = evidence.get(ident)
        if not found or not found["analysed"]:
            return True  # Not enough stored evidence to judge; leave it alone.
        for name in names:
            key = name_key(name).replace(" ", "")
            if any(possible_match(name, other) for other in found["names"] if other):
                return True
            if key and key in found["text"]:
                return True
    return False


def retune_drafts(db, owner):
    """Re-run the name gate and the category rules over existing unprepared drafts."""
    from .learned import category_for, load

    held, moved = [], {}
    learned, evidence = load(db, owner), _source_evidence(db, owner)
    for row in db.scalars(
        select(IdentifiedSpot).where(
            IdentifiedSpot.user_id == owner,
            IdentifiedSpot.status == "identified",
        )
    ):
        if row.venue_id:
            continue
        issues = [] if row.data.get("operator_named") else quality_issues(row.name, row.area, row.data)
        if not issues and not row.data.get("operator_named"):
            if name_key(row.name) in learned["rejected"]:
                issues = ["You rejected this same name on another record"]
            elif not _name_has_support(row, evidence):
                issues = ["Name came only from video analysis, with no sign, speech or caption to back it"]
        if issues:
            row.data = {**row.data, "quality_issues": issues, "previous_status": row.status}
            row.status, row.updated_at = "quarantined", now()
            held.append(row.name)
            db.add(Audit(actor=AGENT, action="spot.held", target=row.id, detail={"reasons": issues}))
            continue
        category = (
            row.data.get("operator_category") or category_for(learned, row.name) or retune_category(row)
        )
        if category != row.category:
            moved[f"{row.category}->{category}"] = moved.get(f"{row.category}->{category}", 0) + 1
            db.add(
                Audit(
                    actor=AGENT,
                    action="spot.recategorised",
                    target=row.id,
                    detail={"from": row.category, "to": category},
                )
            )
            row.category, row.updated_at = category, now()
    db.flush()
    return {"held": len(held), "held_examples": held[:40], "recategorised": moved}


def _price(row):
    prices = [
        o["price_inr"]
        for o in row.data.get("offerings", [])
        if isinstance(o, dict) and type(o.get("price_inr")) in (int, float) and 0 < o["price_inr"] <= 5000
    ]
    estimate = ESTIMATES[row.category][0]
    if not prices:
        return estimate, "estimate"
    typical = statistics.median(prices)
    if row.category in FOOD:
        # One priced dish is not a meal; never go below the category floor.
        typical = max(typical * 1.5, estimate * 0.5)
    return int(round(min(typical, 3000) / 10) * 10) or estimate, "collected item prices"


def _tags(row):
    words = [row.category.replace("_", " ")]
    words += [str(c).replace("_", " ") for c in row.data.get("cuisine_candidates", [])]
    words += [str(v.get("tag", "")) for v in row.data.get("vibes", []) if isinstance(v, dict)]
    for offering in row.data.get("offerings", []):
        text = name_key(offering.get("name", "")) if isinstance(offering, dict) else ""
        if 2 < len(text) <= 30:
            words.append(text)
    kind = match(row.name)
    if kind:
        words.append(kind.replace("_", " "))
    return list(dict.fromkeys(name_key(w) for w in words if name_key(w)))[:20]


def publish(db, owner):
    stamp = now()
    expires = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
    rows = list(
        db.scalars(
            select(IdentifiedSpot)
            .where(
                IdentifiedSpot.user_id == owner,
                IdentifiedSpot.status == "identified",
            )
            .order_by(IdentifiedSpot.created_at, IdentifiedSpot.id)
        )
    )
    skipped = {"no coordinates": 0, "outside 40 km": 0, "name needs review": 0, "duplicate nearby": 0}
    published, estimated = [], {"price": 0, "hours": 0}
    # Venues published earlier count too, so a repeat run cannot add their duplicates.
    chosen = [(v.name, (v.lat, v.lng)) for v in db.scalars(select(Venue).where(Venue.is_demo.is_(False)))]
    # Prefer the record with the most evidence when two describe the same point.
    rows.sort(key=lambda r: -len(r.data.get("sources", [])))
    for row in rows:
        if row.venue_id:
            continue
        point = _point(row.data)
        if not point:
            skipped["no coordinates"] += 1
            continue
        if _km(point, CENTRE) > 40:
            skipped["outside 40 km"] += 1
            continue
        if not row.data.get("operator_named") and quality_issues(row.name, row.area, row.data):
            skipped["name needs review"] += 1
            continue
        # Same or near-identical name within 250 m is one place; farther apart is a branch.
        if any(possible_match(row.name, other) and _km(point, there) <= 0.25 for other, there in chosen):
            skipped["duplicate nearby"] += 1
            continue
        chosen.append((row.name, point))
        price, price_basis = _price(row)
        hours = parse_hours([h.get("value", "") for h in row.data.get("hours_candidates", [])])
        hours_basis = "collected opening-hours text" if hours else "estimate"
        _, visit, opens, closes = ESTIMATES[row.category]
        if not hours:
            hours = {str(i): [[opens, closes]] for i in range(7)}
        estimated["price"] += price_basis == "estimate"
        estimated["hours"] += hours_basis == "estimate"
        source = next(
            (s["url"] for s in row.data.get("sources", []) if str(s.get("url", "")).startswith("https://")),
            "https://www.openstreetmap.org/copyright",
        )
        address = row.data.get("address") or ", ".join(x for x in [row.area, "Coimbatore"] if x)
        area = row.area or infer_area([address, *row.data.get("address_clues", [])]) or "Coimbatore"
        vegetarian = bool(
            VEG.search(name_key(row.name))
            or {"vegetarian", "pure_veg"} & {str(c).lower() for c in row.data.get("cuisine_candidates", [])}
        )
        details = {
            "visit_minutes": visit,
            "wait_minutes": 10,
            "fee_per_group": 0,
            "max_group": 20 if row.category in {"park", "amusement", "attraction"} else 8,
            "child_friendly": row.category != "nightlife",
            "min_age": 21 if row.category == "nightlife" else 0,
            "branch_confirmed": True,
            "description": "Test inventory entry. Price and hours may be estimates; check before visiting.",
            "identified_spot_id": row.id,
            "price_per_person": price,
            "hours": hours,
            "closed": False,
            # The planner needs show times for a cinema; these are placeholders.
            **({"sessions": SHOW_TIMES} if row.category == "cinema" else {}),
            **({"vegetarian": True} if vegetarian and row.category in FOOD else {}),
            "test_inventory": {
                "by": AGENT,
                "at": stamp,
                "price_basis": price_basis,
                "hours_basis": hours_basis,
                "status_basis": "assumed open",
                **({"sessions_basis": "estimate"} if row.category == "cinema" else {}),
                "note": "Approved by the agent for planner testing at the owner's request; not verified",
            },
            "maps_identity": {
                "confirmed_by": AGENT,
                "confirmed_at": stamp,
                "name": row.name,
                "maps_url": f"https://www.google.com/maps/search/?api=1&query={point[0]},{point[1]}",
                "basis": "Collected coordinates; no operator Maps review",
            },
            "location_approval": {"by": AGENT, "at": stamp, "reason": "Owner-requested test inventory"},
        }
        venue = Venue(
            name=row.name,
            category=row.category,
            area=area,
            address=address,
            lat=point[0],
            lng=point[1],
            tags=_tags(row),
            details=details,
            status="published",
            is_demo=False,
        )
        db.add(venue)
        db.flush()
        facts = [
            ("price_per_person", price, price_basis),
            ("hours", hours, hours_basis),
            ("closed", False, "assumed open"),
        ]
        if details.get("vegetarian"):
            facts.append(("vegetarian", True, "name or directory cuisine tag"))
        for field, value, basis in facts:
            db.add(
                Claim(
                    venue_id=venue.id,
                    field=field,
                    value={"value": value},
                    source_url=source,
                    source_type="test_estimate" if basis in {"estimate", "assumed open"} else "collected",
                    source_group="test-inventory",
                    observed_at=stamp,
                    expires_at=expires,
                    status="accepted",
                    reason=f"Test inventory ({basis}); not verified",
                )
            )
        row.data = {**row.data, "previous_status": row.status, "test_inventory": True}
        row.venue_id, row.status, row.updated_at = venue.id, "approved", stamp
        db.add(
            Audit(
                actor=AGENT,
                action="venue.test_published",
                target=venue.id,
                detail={"spot": row.id, "price_basis": price_basis, "hours_basis": hours_basis},
            )
        )
        published.append(row.category)
    db.flush()
    by_category = {c: published.count(c) for c in sorted(set(published))}
    return {
        "published": len(published),
        "by_category": by_category,
        "estimated_price": estimated["price"],
        "estimated_hours": estimated["hours"],
        "skipped": skipped,
    }


def revert(db, owner):
    """Remove the test inventory and return its drafts to review."""
    venues = [
        v
        for v in db.scalars(select(Venue).where(Venue.is_demo.is_(False)))
        if v.details.get("test_inventory")
    ]
    ids = [v.id for v in venues]
    restored = 0
    for row in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == owner)):
        if row.venue_id in ids:
            data = {k: v for k, v in row.data.items() if k != "test_inventory"}
            row.status, row.venue_id = data.pop("previous_status", "identified"), ""
            row.data, row.updated_at = data, now()
            restored += 1
    if ids:
        db.execute(delete(Claim).where(Claim.venue_id.in_(ids)))
        db.execute(delete(Venue).where(Venue.id.in_(ids)))
        db.add(Audit(actor=AGENT, action="venue.test_reverted", target=owner, detail={"venues": len(ids)}))
    db.flush()
    return {"removed_venues": len(ids), "restored_drafts": restored}
