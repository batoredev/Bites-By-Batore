"""Private venue inventory drafts. Collection is never publication or approval."""

import hashlib
import json
import re
from copy import deepcopy
from urllib.parse import urlencode
from sqlalchemy import select
from .db import IdentifiedSpot, now
from .spot_identity import clean_name, name_key, infer_area, quality_issues, same_branch, possible_match

INACTIVE = {"merged", "quarantined", "rejected"}


def unique(items):
    seen, result = set(), []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def merge_list(field, items):
    """Deduplicate evidence by meaning and source, not changing fetch timestamps."""
    result = {}
    for original in items:
        item = deepcopy(original)
        if not isinstance(item, dict):
            key = name_key(item) if isinstance(item, str) else json.dumps(item, sort_keys=True)
        elif field == "sources":
            key = (item.get("url"), item.get("type"))
        elif field == "offerings":
            key = (
                name_key(item.get("name", "")),
                item.get("source_url"),
                item.get("price_inr"),
                item.get("unit"),
            )
        elif field == "observations":
            key = (
                name_key(item.get("text", "")),
                item.get("source_url"),
                item.get("basis"),
                item.get("timestamp_seconds"),
            )
        elif field == "vibes":
            key = (item.get("tag"), item.get("source_url"), name_key(item.get("evidence", "")))
        else:
            key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key in result and field == "sources":
            previous = result[key]
            dates = sorted(
                d
                for d in [
                    previous.get("first_collected_at"),
                    previous.get("collected_at"),
                    item.get("collected_at"),
                ]
                if d
            )
            previous.update({k: v for k, v in item.items() if v is not None})
            if dates:
                previous["first_collected_at"], previous["collected_at"] = dates[0], dates[-1]
        elif key not in result:
            result[key] = item
    return list(result.values())


def merge_data(existing, incoming):
    merged = deepcopy(existing)
    for key, value in incoming.items():
        if isinstance(value, list):
            merged[key] = merge_list(key, merged.get(key, []) + value)
        elif value and not merged.get(key):
            merged[key] = value
        elif value and value != merged.get(key):
            merged["conflicts"] = unique(
                merged.get("conflicts", []) + [{"field": key, "existing": merged[key], "proposed": value}]
            )
    return merged


def spot_dict(row):
    data = row.data
    missing = [
        label
        for key, label in [
            ("address", "Exact branch address"),
            ("coordinates", "Map coordinate lead"),
            ("menu_links", "Menu / activity price evidence"),
            ("hours", "Current opening hours"),
            ("vibes", "Vibe evidence"),
        ]
        if not data.get(key)
        and not (
            key == "menu_links" and any(x.get("price_inr") is not None for x in data.get("offerings", []))
        )
    ]
    if not data.get("maps_identity", {}).get("confirmed_by"):
        missing.insert(0, "Maps name and exact place confirmation")
    return {
        "id": row.id,
        "name": row.name,
        "category": row.category,
        "area": row.area,
        "status": row.status,
        "venue_id": row.venue_id,
        "data": data,
        "missing": missing,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "map_search_url": data.get("maps_identity", {}).get("maps_url")
        or "https://www.google.com/maps/search/?"
        + urlencode({"api": 1, "query": " ".join([row.name, row.area, "Coimbatore"])}),
    }


def upsert_spot(db, user_id, name, category="food", area="", data=None, branch_key=""):
    from .providers import renew_job

    renew_job(db)
    name, data = clean_name(name), deepcopy(data or {})
    if branch_key:
        data["branch_key"] = branch_key
    if quality_issues(name, area, data):
        return None
    records = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id)))
    matches = [r for r in records if r.status not in INACTIVE and same_branch(r, name, area, data)]
    row = matches[0] if len(matches) == 1 else None
    # A conflicting address needs a separate identity even when names/areas agree.
    branch = branch_key or data.get("address") or area
    identity = hashlib.sha256(f"{user_id}|{name_key(name)}|{name_key(branch)}".encode()).hexdigest()
    if row is None:
        row = db.scalar(select(IdentifiedSpot).where(IdentifiedSpot.identity_key == identity))
        if row and row.status == "merged":
            row = db.get(IdentifiedSpot, row.data.get("merged_into"))
        if row and row.status in {"quarantined", "rejected"}:
            return None
    if row is None:
        row = IdentifiedSpot(
            user_id=user_id, identity_key=identity, name=name, category=category, area=area, data={}
        )
        db.add(row)
        db.flush()
    if not row.area and area:
        row.area = area
    data["aliases"] = unique([name, *data.get("aliases", [])])
    similar = [
        r.id for r in records if r.id != row.id and r.status not in INACTIVE and possible_match(r.name, name)
    ]
    if similar:
        data["possible_duplicates"] = similar
    merged = merge_data(row.data, data)
    merged.setdefault("name_status", "unconfirmed_extraction")
    row.data, row.updated_at = merged, now()
    return row


def identify_from_source(db, case, source):
    if source.platform == "web" and source.content.get("spot_name"):
        candidates = [{"name": source.content["spot_name"], "address_clues": [], "dish_or_activity": ""}]
    else:
        candidates = [
            c
            for role in ("caption", "video")
            for c in source.analysis.get(role, {}).get("venue_candidates", [])
        ]
    output, checks = [], []
    named_candidates = {
        name_key(c.get("name", "")) for c in candidates if not quality_issues(c.get("name", ""))
    }
    for candidate in candidates:
        area = infer_area(candidate.get("address_clues", []))
        issues = quality_issues(
            candidate.get("name", ""), area, {"address_clues": candidate.get("address_clues", [])}
        )
        if issues:
            checks.append({"name": candidate.get("name"), "decision": "held", "reasons": issues})
            continue
        topic = (case.query + " " + candidate.get("dish_or_activity", "")).lower()
        category = next(
            (
                c
                for word, c in [
                    ("kart", "adventure"),
                    ("bowling", "bowling"),
                    ("arcade", "gaming"),
                    ("gaming", "gaming"),
                    ("cinema", "cinema"),
                    ("park", "park"),
                    ("cafe", "cafe"),
                ]
                if word in topic
            ),
            "food",
        )
        observations = [
            {
                "text": o["text"],
                "basis": o["basis"],
                "source_url": source.canonical_url,
                "timestamp_seconds": o.get("timestamp_seconds"),
            }
            for role in ("caption", "video")
            for o in source.analysis.get(role, {}).get("observations", [])
            if len(named_candidates) == 1 or name_key(candidate["name"]) in name_key(o["text"])
        ]
        data = {
            "case_ids": [case.id],
            "source_ids": [source.id],
            "sources": [
                {
                    "url": source.canonical_url,
                    "type": source.platform,
                    "published_at": source.content.get("published_at"),
                    "collected_at": source.content.get("fetched_at", source.created_at),
                    "basis": "Model-extracted candidate; exact branch unconfirmed",
                }
            ],
            "address_clues": candidate.get("address_clues", []),
            "offerings": [
                {
                    "name": candidate["dish_or_activity"],
                    "source_url": source.canonical_url,
                    "price_inr": None,
                    "unit": "unknown",
                    "basis": "Model observation",
                }
            ]
            if candidate.get("dish_or_activity")
            else [],
            "observations": observations,
            "vibes": [
                {
                    "tag": tag,
                    "source_url": o["source_url"],
                    "basis": "Unverified model observation",
                    "evidence": o["text"],
                }
                for o in observations
                for tag in ("quiet", "outdoor", "indoor", "family", "romantic", "lively")
                if re.search(r"\b" + tag + r"\b", o["text"], re.I)
                and not re.search(r"\b(no|not|never|without|unknown|unconfirmed)\b", o["text"], re.I)
            ],
        }
        issues = quality_issues(candidate["name"], area, data)
        if issues:
            checks.append({"name": candidate["name"], "decision": "held", "reasons": issues})
            continue
        row = upsert_spot(db, case.user_id, candidate["name"], category, area, data)
        if row:
            output.append(row.id)
            checks.append({"name": candidate["name"], "decision": "saved", "spot_id": row.id})
    source.analysis = {**source.analysis, "inventory_checks": unique(checks)}
    db.flush()
    return list(dict.fromkeys(output))


def reconcile_spots(db, user_id):
    """Reversible cleanup: retain originals and provenance; never publish or erase."""
    from .db import Audit

    rows = list(
        db.scalars(
            select(IdentifiedSpot)
            .where(IdentifiedSpot.user_id == user_id)
            .order_by(IdentifiedSpot.created_at)
        )
    )
    counts = {"merged": 0, "quarantined": 0, "deduplicated_lists": 0, "unassigned_observations": 0}
    for row in rows:
        if row.status in INACTIVE or row.venue_id:
            continue
        issues = quality_issues(row.name, row.area, row.data)
        if issues:
            row.status = "quarantined"
            row.data = {**row.data, "quality_issues": issues, "previous_status": "identified"}
            counts["quarantined"] += 1
            continue
        data = deepcopy(row.data)
        for key in ("sources", "offerings", "observations", "vibes", "address_clues"):
            if key in data:
                clean = merge_list(key, data[key])
                counts["deduplicated_lists"] += len(data[key]) - len(clean)
                data[key] = clean
        row.data = data
        row.area = row.area or infer_area(data.get("address_clues", []))
    for row in rows:
        if row.status in INACTIVE or row.venue_id:
            continue
        matches = [
            r
            for r in rows
            if r.id != row.id
            and r.status not in INACTIVE
            and not r.venue_id
            and same_branch(r, row.name, row.area, row.data)
        ]
        # One-to-one evidence only; never choose arbitrarily among multiple branches.
        if len(matches) == 1:
            target = matches[0]
            target.data = merge_data(
                target.data, {**row.data, "aliases": [row.name, *row.data.get("aliases", [])]}
            )
            target.area = target.area or row.area
            row.status = "merged"
            row.data = {**row.data, "merged_into": target.id, "previous_status": "identified"}
            db.add(
                Audit(
                    actor=user_id,
                    action="spot.merged",
                    target=row.id,
                    detail={"into": target.id, "reason": "Equivalent names with compatible branch evidence"},
                )
            )
            counts["merged"] += 1
    for row in rows:
        if row.status not in INACTIVE:
            possible = [
                r.id
                for r in rows
                if r.id != row.id and r.status not in INACTIVE and possible_match(row.name, r.name)
            ]
            row.data = {
                **row.data,
                "possible_duplicates": possible,
                "name_status": row.data.get("name_status", "unconfirmed_extraction"),
            }
    # Old runs copied every observation into every candidate in a multi-venue
    # reel. Keep ambiguous evidence available without presenting it as this spot's vibe.
    from .spot_identity import source_urls

    for row in rows:
        if row.status in INACTIVE:
            continue
        aliases = [name_key(a) for a in [row.name, *row.data.get("aliases", [])]]
        ambiguous_urls = set()
        for other in rows:
            if (
                other.id != row.id
                and other.status not in INACTIVE
                and not same_branch(other, row.name, row.area, row.data)
            ):
                ambiguous_urls.update(source_urls(other.data) & source_urls(row.data))
        data = deepcopy(row.data)
        for field, text_key in (("observations", "text"), ("vibes", "evidence")):
            kept, unassigned = [], []
            for item in data.get(field, []):
                if item.get("source_url") in ambiguous_urls and not any(
                    a in name_key(item.get(text_key, "")) for a in aliases
                ):
                    unassigned.append(item)
                else:
                    kept.append(item)
            if unassigned:
                data[field] = kept
                data["unassigned_" + field] = unique(data.get("unassigned_" + field, []) + unassigned)
                counts["unassigned_observations"] += len(unassigned)
        row.data = data
    if any(counts.values()):
        db.add(Audit(actor=user_id, action="spots.quality_cleanup", target=user_id, detail=counts))
    db.flush()
    return counts
