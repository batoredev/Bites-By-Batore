"""Discovery-only early exits. A known location is not a verified new reel."""

import re
from sqlalchemy import select, or_
from .config import settings
from .db import IdentifiedSpot, ResearchSource, Investigation, now
from .providers import renew_job
from .spot_identity import name_key, names_match, quality_issues, branch_clues, area_key, infer_area
from .performance import span

POLICY_VERSION = "known-location-discovery-v1"
INACTIVE = {"merged", "quarantined", "rejected"}


def allowed(case, source):
    return (
        settings().known_spot_skip_enabled
        and settings().app_mode != "demo"
        and source.platform == "instagram"
        and not any(
            case.context.get(k) for k in ("force_full_analysis", "maintenance_source_id", "refresh_reason")
        )
        and not source.analysis.get("evaluation_labels")
    )


def compilation_size(source):
    text = " ".join(str(source.content.get(k, "")) for k in ("caption", "title", "search_preview"))
    counts = re.findall(r"\b(?:top|best|these|all)\s*(\d{1,2})\b", text, re.I)
    if counts:
        return max(int(n) for n in counts)
    return (
        2
        if re.search(
            r"\b(?:food trail|cafe hopping|multiple (?:places|cafes|spots)|roundup|round up)\b", text, re.I
        )
        else 1
    )


def active_spots(db, user_id):
    return list(
        db.scalars(
            select(IdentifiedSpot).where(
                IdentifiedSpot.user_id == user_id, IdentifiedSpot.status.not_in(INACTIVE)
            )
        )
    )


def strong_branch(row, candidate):
    name = candidate.get("name", "")
    data = {"address_clues": candidate.get("address_clues", [])}
    if quality_issues(name, data=data) or not any(
        names_match(a, name) for a in [row.name, *row.data.get("aliases", [])]
    ):
        return False
    area = infer_area(data["address_clues"])
    if row.area and area and area_key(row.area) != area_key(area):
        return False
    # Area/name alone is insufficient to discard a new branch's video.
    old = [row.data.get("address", ""), *row.data.get("address_clues", [])]
    fresh = data["address_clues"]
    exact_address = any(len(name_key(a)) >= 20 and name_key(a) == name_key(b) for a in old for b in fresh)
    tokens = branch_clues(data)
    old_tokens = branch_clues(row.data)
    if any(tokens[k] and old_tokens[k] and tokens[k] != old_tokens[k] for k in tokens):
        return False
    return exact_address and bool(tokens["numbers"] or tokens["postal"])


def decision(db, case, source, *, candidates=None, stage="before_collection"):
    if not allowed(case, source):
        return None
    rows = active_spots(db, case.user_id)
    if not rows:
        return None
    # Never borrow labels or cached identities from another owner's evaluation origin.
    origin = source.content.get("content_fingerprint")
    same_origin = ResearchSource.canonical_url == source.canonical_url
    if origin:
        same_origin = or_(same_origin, ResearchSource.content["content_fingerprint"].as_string() == origin)
    related = list(
        db.scalars(
            select(ResearchSource)
            .join(Investigation, ResearchSource.case_id == Investigation.id)
            .where(Investigation.user_id == case.user_id, same_origin)
        )
    )
    if any(s.analysis.get("evaluation_labels") for s in related):
        return None
    if candidates is None:
        # The exact post already completed a location pass. Retain its reference,
        # without fetching it again or claiming a new freshness check.
        for previous in sorted(related, key=lambda s: s.created_at, reverse=True):
            checks = previous.analysis.get("inventory_checks", [])
            if (
                previous.id == source.id
                or previous.canonical_url != source.canonical_url
                or not previous.content.get("streamed")
                or not checks
                or any(c.get("decision") != "saved" for c in checks)
            ):
                continue
            if (
                source.content.get("caption")
                and previous.content.get("caption")
                and source.content["caption"] != previous.content["caption"]
            ):
                continue
            ids = {c.get("spot_id") for c in checks}
            resolved = set()
            all_resolved = True
            for ident in ids:
                row = db.get(IdentifiedSpot, ident) if ident else None
                seen = set()
                while row and row.status == "merged" and row.id not in seen:
                    seen.add(row.id)
                    row = db.get(IdentifiedSpot, row.data.get("merged_into"))
                if row and row.user_id == case.user_id and row.status not in INACTIVE:
                    resolved.add(row.id)
                else:
                    all_resolved = False
            if not all_resolved or len(resolved) == 0:
                continue
            ids = resolved
            matches = [r for r in rows if r.id in ids or previous.id in r.data.get("source_ids", [])]
            names = {name_key(c.get("name", "")) for c in checks}
            if matches and ids.issubset({r.id for r in matches}) and len(names) >= compilation_size(source):
                return receipt(
                    matches,
                    stage,
                    "Exact previously processed reel; all recorded candidates remain in private inventory",
                )
        return None
    unique = {(name_key(c.get("name", "")), tuple(c.get("address_clues", []))): c for c in candidates}
    if len({key[0] for key in unique}) < compilation_size(source) or not unique:
        return None
    matches = []
    for candidate in unique.values():
        found = [
            r
            for r in rows
            if strong_branch(r, candidate)
            and (
                r.created_at < source.created_at
                or any(ident != source.id for ident in r.data.get("source_ids", []))
                or any(s.get("url") != source.canonical_url for s in r.data.get("sources", []))
            )
        ]
        if len(found) != 1:
            return None
        matches.append(found[0])
    return receipt(
        matches,
        stage,
        "Every extracted candidate matches one existing named branch with exact address evidence",
    )


def receipt(rows, stage, basis):
    return {
        "policy": POLICY_VERSION,
        "at": now(),
        "stage": stage,
        "basis": basis,
        "spot_ids": sorted({r.id for r in rows}),
        "coverage_complete": False,
        "note": "Remaining reel evidence intentionally skipped for discovery. No new fact verification, freshness renewal, creator judgement or publication.",
    }


def apply(db, case, source, result):
    from .spots import merge_list, lock_inventory

    renew_job(db)
    with span("known_spot_early_exit"):
        lock_inventory(db)
        rows = [db.get(IdentifiedSpot, ident, populate_existing=True) for ident in result["spot_ids"]]
        if any(not r or r.user_id != case.user_id or r.status in INACTIVE for r in rows):
            return False
        for row in rows:
            data = dict(row.data)
            data["source_ids"] = list(dict.fromkeys([*data.get("source_ids", []), source.id]))
            data["case_ids"] = list(dict.fromkeys([*data.get("case_ids", []), case.id]))
            # Separate from analysed source observations: no new fact timestamp.
            data["discovery_references"] = merge_list(
                "discovery_references",
                [
                    *data.get("discovery_references", []),
                    {
                        "source_id": source.id,
                        "url": source.canonical_url,
                        "policy": POLICY_VERSION,
                        "analysis_skipped": True,
                    },
                ],
            )
            row.data = data
        analysis = dict(source.analysis)
        analysis["discovery_skip"] = result
        analysis["inventory_checks"] = [
            {
                "name": r.name,
                "spot_id": r.id,
                "decision": "saved",
                "basis": "Existing private record; reel analysis skipped",
            }
            for r in rows
        ]
        for role in ("caption", "comments", "video"):
            if analysis.get(role, {}).get("status") != "observations_only":
                analysis[role] = {
                    "status": "skipped_known_location",
                    "reason": result["basis"],
                    "video_analyzed": False,
                }
        source.analysis = analysis
        source.content = {
            k: v
            for k, v in source.content.items()
            if k not in {"media", "media_url", "audio_url", "video_url"}
        }
        source.content = {
            **source.content,
            "streamed": True,
            "analysis_pending": False,
            "processing_outcome": "skipped_known_location",
        }
        if source.state == "lead":
            source.state = "known_spot_reference"
        db.commit()
        return True


def try_skip(db, case, source, **kwargs):
    found = decision(db, case, source, **kwargs)
    return bool(found and apply(db, case, source, found))
