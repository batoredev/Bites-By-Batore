"""Dedicated, owner-private duplicate reconciliation. Merging never approves a venue."""

import hashlib
import json
import re
from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import select

from .db import Audit, IdentifiedSpot, Investigation, Job, ResearchSource, now
from .duplicate_identity import assess_pair, identity_conflicts, name_variant_key
from .spot_identity import name_key, signature, source_urls
from .spots import INACTIVE, lock_inventory, merge_data

POLICY = "duplicate-agent-v1"


def inventory_version(db, owner):
    fields = list(
        db.execute(
            select(
                IdentifiedSpot.id,
                IdentifiedSpot.name,
                IdentifiedSpot.area,
                IdentifiedSpot.status,
                IdentifiedSpot.venue_id,
                IdentifiedSpot.updated_at,
            )
            .where(IdentifiedSpot.user_id == owner)
            .order_by(IdentifiedSpot.id)
        )
    )
    return hashlib.sha256(json.dumps([list(r) for r in fields]).encode()).hexdigest()


def request_scan(db, owner, force=False):
    from .jobs import enqueue

    latest = db.scalar(
        select(Job)
        .where(Job.kind == "spot_deduplicate", Job.payload["user_id"].as_string() == owner)
        .order_by(Job.created_at.desc())
    )
    if latest and latest.state in {"queued", "running"}:
        return latest
    version = inventory_version(db, owner)
    if latest and latest.state == "done" and latest.result.get("inventory_version") == version and not force:
        return latest
    if latest and latest.state == "failed" and not force:
        failed_at = latest.completed_at or latest.created_at
        if datetime.fromisoformat(failed_at) + timedelta(minutes=5) > datetime.now(UTC):
            return latest
    key = f"duplicate-agent:{owner}:{version}" + (":" + now() if force else "")
    previous = db.scalar(select(Job).where(Job.key == key))
    if previous and previous.state in {"failed", "cancelled"}:
        key += ":retry:" + latest.id
    return enqueue(db, "spot_deduplicate", {"user_id": owner, "policy": POLICY}, key, priority=88)


def eligible(row):
    if row.venue_id or row.status in {"merged", "rejected"}:
        return False
    if row.status != "quarantined":
        return True
    issues = row.data.get("quality_issues", [])
    return (
        bool(row.data.get("duplicate_review_candidates"))
        and bool(issues)
        and all("duplicate" in str(i).lower() for i in issues)
    )


def side(row):
    return {k: getattr(row, k) for k in ("id", "name", "area", "status", "venue_id")}


def _snapshot(row):
    return SimpleNamespace(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        area=row.area,
        category=row.category,
        status=row.status,
        venue_id=row.venue_id,
        created_at=row.created_at,
        data=deepcopy(row.data),
    )


def _candidate_pairs(rows):
    """Broad lexical/stable-reference/near-point blocks; never a top-N match prune."""
    buckets = defaultdict(set)
    for r in rows:
        aliases = [r.name, *r.data.get("aliases", [])]
        for name in aliases:
            key = name_variant_key(name)
            if key:
                buckets["name:" + key.replace(" ", "")].add(r.id)
            for token in signature(name).split():
                if len(token) >= 3:
                    buckets["token:" + token].add(r.id)
        for ref in r.data.get("directory_refs", []):
            buckets["osm:" + ref].add(r.id)
        place = r.data.get("maps_identity", {}).get("place_key")
        if place:
            buckets["maps:" + place].add(r.id)
        for ident in r.data.get("source_ids", []):
            buckets["source:" + ident].add(r.id)
        for url in source_urls(r.data):
            buckets["url:" + url].add(r.id)  # Candidate retrieval only, never merge proof.
        point = r.data.get("coordinates", {})
        try:
            import math

            lat, lng = float(point["lat"]), float(point["lng"])
            if not math.isfinite(lat + lng):
                continue
            x, y = math.floor(lat / 0.0003), math.floor(lng / 0.0003)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    buckets[f"point:{x + dx}:{y + dy}"].add(r.id)
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
    pairs = set()
    for ids in buckets.values():
        ordered = sorted(ids)
        pairs.update((a, b) for i, a in enumerate(ordered) for b in ordered[i + 1 :])
    return sorted(pairs)


def _alias_key(name):
    tokens = name_variant_key(name).split()
    return "".join(
        re.sub(r"([aeiou])\1+", r"\1", token[:-1] if len(token) > 4 and token.endswith("s") else token)
        for token in tokens
    )


def _source_alias(db, left, right):
    """Caption/sign co-reference; global fuzzy spelling or a shared reel alone cannot merge."""
    keys = [_alias_key(r.name) for r in (left, right)]
    if any(len(k) < 4 for k in keys):
        return None
    short, long = sorted(keys, key=len)
    if keys[0] != keys[1] and not (
        len(short) >= 6 and len(short) * 3 >= len(long) * 2 and long.startswith(short)
    ):
        return None
    shared = set(left.data.get("source_ids", [])) & set(right.data.get("source_ids", []))
    for ident in sorted(shared):
        record = db.execute(
            select(ResearchSource.analysis, ResearchSource.content["caption"].as_string())
            .join(Investigation, ResearchSource.case_id == Investigation.id)
            .where(ResearchSource.id == ident, Investigation.user_id == left.user_id)
        ).first()
        if not record:
            continue
        analysis, caption = record
        if analysis.get("evaluation_labels") or analysis.get("discovery_skip"):
            continue
        if re.search(
            r"\b(vs|versus|comparison|compare|food trail|hopping|multiple|both)\b|\b(?:top|best|these)\s*\d|\b(?:[2-9]|two|three|four|five|several)\s+(?:places|venues|cafes|restaurants|branches|locations|spots)\b",
            caption or "",
            re.IGNORECASE,
        ):
            continue
        roles = [analysis.get(role, {}) for role in ("caption", "video")]
        if any(role.get("status") != "observations_only" for role in roles):
            continue
        caption_keys = {_alias_key(c.get("name", "")) for c in roles[0].get("venue_candidates", [])}
        if len(caption_keys) != 1:
            continue
        anchor = next(iter(caption_keys))
        visual_keys = {
            _alias_key(o["verbatim_text"])
            for o in roles[1].get("observations", [])
            if o.get("basis") == "visual" and o.get("verbatim_text")
        }
        if anchor not in visual_keys:
            continue

        def corresponds(key, anchor=anchor, visual_keys=visual_keys):
            return key == anchor or (
                len(key) >= 6
                and len(key) * 3 >= len(anchor) * 2
                and anchor.startswith(key)
                and key not in visual_keys
            )

        if not all(corresponds(k) for k in keys):
            continue
        compatible = True
        for candidate in roles[1].get("venue_candidates", []):
            name = candidate.get("name", "")
            # Preserve these raw model outputs; a promotional dish title is not
            # an additional business blocking a clearly named caption/sign alias.
            promo = bool(
                re.search(r"^(?:viral|trending)\b.*\b(?:dessert|dish|food|snack)\b", name, re.IGNORECASE)
            ) and not re.search(r"\b(?:cafe|restaurant|bakery|cinema|park|arena)\b", name, re.IGNORECASE)
            if not corresponds(_alias_key(name)) and not promo:
                compatible = False
        if not compatible:
            continue
        return {
            "visual_anchor_key": anchor,
            "visual_name_keys": sorted(
                {
                    name_key(o["verbatim_text"]).replace(" ", "")
                    for o in roles[1].get("observations", [])
                    if o.get("basis") == "visual"
                    and o.get("verbatim_text")
                    and _alias_key(o["verbatim_text"]) == anchor
                }
            ),
            "reasons": [
                "Single recorded caption/sign entity after handle, punctuation or limited transliteration/OCR normalization",
                "Recorded visual lettering and caption agree in source "
                + ident
                + "; Maps/venue approval unchanged",
            ],
        }
    return None


def decision(db, left, right):
    result = assess_pair(left, right)
    if result["decision"] == "merge" or result["conflicts"]:
        return result
    proof = _source_alias(db, left, right)
    return {"decision": "merge", **proof, "conflicts": []} if proof else result


def merge_records(db, source, target, actor, reasons, automatic=False):
    """Caller holds inventory lock and has freshly revalidated identity/lifecycle."""
    if source.user_id != actor or target.user_id != actor or source.id == target.id:
        raise ValueError("Choose two owned, different records")
    if (
        source.venue_id
        or target.venue_id
        or source.status in {"merged", "rejected"}
        or target.status in INACTIVE
    ):
        raise ValueError("Merge unprepared drafts into an active surviving draft")
    conflicts = identity_conflicts(source, target)
    if conflicts and automatic:
        raise ValueError("Correct conflicting branch evidence before merging: " + "; ".join(conflicts))
    left_key = source.data.get("maps_identity", {}).get("place_key")
    right_key = target.data.get("maps_identity", {}).get("place_key")
    if left_key and right_key and left_key != right_key:
        raise ValueError("Correct different explicit Maps identities before merging")
    before = {"target_data": deepcopy(target.data), "source_status": source.status}
    incoming = deepcopy(source.data)
    # Review metadata belongs to the retained original, not a new rejection of the survivor.
    for key in ("duplicate_review_candidates", "duplicate_agent_review", "previous_status", "quality_issues"):
        incoming.pop(key, None)
    target.data = merge_data(
        target.data, {**incoming, "aliases": [source.name, *incoming.get("aliases", [])]}
    )
    for field in ("possible_duplicates", "duplicate_review_candidates"):
        if field in target.data:
            target.data = {
                **target.data,
                field: [x for x in target.data[field] if x not in {source.id, target.id}],
            }
    target.updated_at = now()
    source.status, source.updated_at = "merged", now()
    source.data = {**source.data, "merged_into": target.id, "previous_status": before["source_status"]}
    db.add(
        Audit(
            actor=actor,
            action="spot.merged",
            target=source.id,
            detail={
                "into": target.id,
                "reason": "; ".join(reasons),
                "automatic": automatic,
                "policy": POLICY,
                "before": before,
                "conflicts_reviewed": conflicts if not automatic else [],
            },
        )
    )


def _survivor_key(row, anchors=None, signs=None):
    reviewed = bool(row.data.get("maps_identity", {}).get("confirmed_by"))
    official = any(s.get("type") in {"official", "official_menu"} for s in row.data.get("sources", []))
    handle = bool(re.search(r"[@_.]", row.name))
    partial = bool(anchors) and _alias_key(row.name) not in anchors
    not_sign = bool(signs) and name_key(row.name).replace(" ", "") not in signs
    return (not reviewed, not official, not_sign, partial, handle, row.created_at, row.id)


def run_scan(db, owner):
    from .providers import renew_job

    renew_job(db)
    input_version = inventory_version(db, owner)
    rows = [
        _snapshot(r)
        for r in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == owner))
        if eligible(r)
    ]
    by_id = {r.id: r for r in rows}
    reviews, graph, judgements = {}, defaultdict(set), {}
    pairs = _candidate_pairs(rows)
    for n, (a, b) in enumerate(pairs):
        if n and n % 100 == 0:
            renew_job(db)
        result = decision(db, by_id[a], by_id[b])
        judgements[(a, b)] = result
        if result["decision"] == "merge":
            graph[a].add(b)
            graph[b].add(a)
        elif result["decision"] == "review":
            reviews[(a, b)] = result
    groups, seen = [], set()
    for root in sorted(graph):
        if root in seen:
            continue
        pending, component = [root], set()
        while pending:
            ident = pending.pop()
            if ident in component:
                continue
            component.add(ident)
            pending.extend(graph[ident] - component)
        seen.update(component)
        members = sorted(component)
        complete = True
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                result = judgements.get((a, b)) or decision(db, by_id[a], by_id[b])
                if result["decision"] != "merge":
                    complete = False
        if complete and any(by_id[x].status not in INACTIVE for x in members):
            groups.append(members)
        else:
            for a in members:
                for b in graph[a]:
                    if a < b:
                        reviews[(a, b)] = {
                            "decision": "review",
                            "conflicts": [],
                            "reasons": [
                                "Group contains conflicting or incomplete branch identities; no automatic bridge merge"
                            ],
                        }
    db.rollback()  # No identity writes while planning comparisons.
    merged, stale = [], 0
    for group in groups:
        renew_job(db)
        lock_inventory(db)
        live = list(
            db.scalars(
                select(IdentifiedSpot)
                .where(IdentifiedSpot.user_id == owner, IdentifiedSpot.id.in_(group))
                .execution_options(populate_existing=True)
            )
        )
        if len(live) != len(group) or not all(eligible(r) for r in live):
            db.rollback()
            stale += 1
            continue
        checked = [decision(db, a, b) for i, a in enumerate(live) for b in live[i + 1 :]]
        if not all(d["decision"] == "merge" for d in checked):
            db.rollback()
            stale += 1
            continue
        active = [r for r in live if r.status not in INACTIVE]
        if not active:
            db.rollback()
            continue
        anchors = {d["visual_anchor_key"] for d in checked if d.get("visual_anchor_key")}
        signs = {s for d in checked for s in d.get("visual_name_keys", [])}
        target = min(active, key=lambda r: _survivor_key(r, anchors, signs))
        for source in sorted(live, key=_survivor_key):
            if source.id == target.id:
                continue
            result = decision(db, source, target)
            merge_records(db, source, target, owner, result["reasons"], automatic=True)
            merged.append({"source_id": source.id, "target_id": target.id, "reasons": result["reasons"]})
        db.commit()
    # Report review pairs, not fabricated branch decisions. Originals remain intact.
    candidates = []
    for (a, b), result in reviews.items():
        left, right = db.get(IdentifiedSpot, a), db.get(IdentifiedSpot, b)
        if not left or not right or not eligible(left) or not eligible(right):
            continue
        current = decision(db, left, right)
        if current["decision"] == "separate":
            continue
        key = hashlib.sha256(f"{owner}|{a}|{b}".encode()).hexdigest()
        candidates.append({"key": key, "left": side(left), "right": side(right), **result})
    result = {
        "at": now(),
        "policy": POLICY,
        "scanned_records": len(rows),
        "candidate_pairs": len(pairs),
        "merged": merged,
        "automatic_merged": len(merged),
        "candidates": candidates,
        "pending_count": len(candidates),
        "stale_groups": stale,
        "published": False,
        "inventory_version": input_version,
        "current_inventory_version": inventory_version(db, owner),
    }
    return result


def status(db, owner):
    job = db.scalar(
        select(Job)
        .where(Job.kind == "spot_deduplicate", Job.payload["user_id"].as_string() == owner)
        .order_by(Job.created_at.desc())
    )
    candidates = []
    completed = job
    if job and job.state != "done":
        completed = db.scalar(
            select(Job)
            .where(
                Job.kind == "spot_deduplicate",
                Job.state == "done",
                Job.payload["user_id"].as_string() == owner,
            )
            .order_by(Job.completed_at.desc())
        )
    for saved in completed.result.get("candidates", []) if completed else []:
        left, right = (
            db.get(IdentifiedSpot, saved["left"]["id"]),
            db.get(IdentifiedSpot, saved["right"]["id"]),
        )
        if (
            left
            and right
            and left.user_id == right.user_id == owner
            and eligible(left)
            and eligible(right)
            and assess_pair(left, right)["decision"] != "separate"
        ):
            candidates.append({**saved, "left": side(left), "right": side(right)})
    return {
        "agent": {
            "state": job.state if job else "not_scheduled",
            "job_id": job.id if job else None,
            "last_completed_at": completed.completed_at if completed else None,
        },
        "candidates": candidates,
        "pending_count": len(candidates),
    }
