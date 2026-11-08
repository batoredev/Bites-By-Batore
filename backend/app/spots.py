"""Private venue inventory drafts. Collection is never publication or approval."""

import hashlib
import json
import re
from collections import Counter as CharacterCounts
from collections import defaultdict
from copy import deepcopy
from difflib import SequenceMatcher
from urllib.parse import urlencode

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from .db import IdentifiedSpot, now
from .spot_identity import (
    branch_clues,
    clean_name,
    infer_area,
    name_key,
    possible_match,
    quality_issues,
    same_branch,
    signature,
    source_urls,
)

INACTIVE = {"merged", "quarantined", "rejected"}


def lock_inventory(db):
    """Serialize identity reads and writes; SQLite and PostgreSQL supported."""
    if db.bind.dialect.name == "sqlite":
        connection = db.connection()
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
    elif db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(672807)"))


def unresolved_duplicate(row, name, area, data):
    """Hold an indistinguishable name proposal; do not assert two branches are one."""
    from .spot_identity import area_key

    if name_key(row.name).replace(" ", "") != name_key(name).replace(" ", ""):
        return False
    if row.area and area and area_key(row.area) != area_key(area):
        return False
    for key in ("branch_key", "address"):
        if row.data.get(key) and data.get(key) and name_key(row.data[key]) != name_key(data[key]):
            return False
    left, right = branch_clues(row.data), branch_clues(data)
    if any(left[k] and right[k] and left[k] != right[k] for k in left):
        return False
    a, b = row.data.get("coordinates", {}), data.get("coordinates", {})
    if all(k in a and k in b for k in ("lat", "lng")):
        from .planner import km

        try:
            if km((float(a["lat"]), float(a["lng"])), (float(b["lat"]), float(b["lng"]))) > 0.15:
                return False
        except (ValueError, TypeError):
            pass
    a, b = row.data.get("maps_identity", {}).get("place_key"), data.get("maps_identity", {}).get("place_key")
    return not (a and b and a != b)


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
            key = (
                name_key(item)
                if isinstance(item, str) and field in {"aliases", "address_clues"}
                else json.dumps(item, sort_keys=True)
            )
        elif field == "sources":
            key = (item.get("url"), item.get("type"))
        elif field == "visual_references":
            key = (item.get("url"), item.get("page_url"))
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
        if key in result and field == "visual_references":
            result[key] = item
        elif key in result and field == "sources":
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
            if key in {"observations", "vibes"}:

                def identity(item):
                    if key == "observations":
                        return (
                            name_key(item.get("text", "")),
                            item.get("source_url"),
                            item.get("basis"),
                            item.get("timestamp_seconds"),
                        )
                    return (item.get("tag"), item.get("source_url"), name_key(item.get("evidence", "")))

                held = {identity(item) for item in merged.get("unassigned_" + key, [])}
                value = [item for item in value if identity(item) not in held]
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
    lock_inventory(db)
    name, data = clean_name(name), deepcopy(data or {})
    if branch_key:
        data["branch_key"] = branch_key
    records = list(
        db.scalars(
            select(IdentifiedSpot)
            .where(IdentifiedSpot.user_id == user_id)
            .execution_options(populate_existing=True)
        )
    )
    matches = [r for r in records if r.status not in INACTIVE and same_branch(r, name, area, data)]
    row = matches[0] if len(matches) == 1 else None
    issues = quality_issues(name, area, data)
    identity_review = row.data.get("maps_identity", {}) if row else {}
    if issues and not (
        identity_review.get("confirmed_by")
        and set(issues).issubset(identity_review.get("reviewed_warnings", []))
    ):
        return None
    # A conflicting address needs a separate identity even when names/areas agree.
    branch = branch_key or data.get("address") or area
    if data.get("strict_identity") and data.get("coordinates"):
        point = data["coordinates"]
        branch += f"|point:{float(point['lat']):.5f},{float(point['lng']):.5f}"
    strong_clues = branch_clues(data)
    if any(strong_clues.values()):
        branch += "|" + json.dumps(strong_clues, sort_keys=True)
    elif not branch and source_urls(data):
        # Same brand in different posts without branch evidence is ambiguous.
        # Preserve separate proposals until a real address or Maps ID links them.
        branch = "unresolved|" + sorted(source_urls(data))[0]
    identity = hashlib.sha256(f"{user_id}|{name_key(name)}|{name_key(branch)}".encode()).hexdigest()
    if row is None:
        row = db.scalar(select(IdentifiedSpot).where(IdentifiedSpot.identity_key == identity))
        visited = set()
        while row and row.status == "merged":
            if row.id in visited:
                return None
            visited.add(row.id)
            row = db.get(IdentifiedSpot, row.data.get("merged_into"))
            if row and row.user_id != user_id:
                return None
        if row and row.status in {"quarantined", "rejected"}:
            return None
    if row is None:
        ambiguous = [
            r for r in records if r.status not in INACTIVE and unresolved_duplicate(r, name, area, data)
        ]
        row = IdentifiedSpot(
            user_id=user_id, identity_key=identity, name=name, category=category, area=area, data={}
        )
        try:
            with db.begin_nested():
                db.add(row)
                db.flush()
        except IntegrityError:
            row = db.scalar(select(IdentifiedSpot).where(IdentifiedSpot.identity_key == identity))
            if row is None:
                raise
        if ambiguous:
            row.status = "quarantined"
            data = {
                **data,
                "duplicate_review_candidates": [r.id for r in ambiguous],
                "quality_issues": [
                    "Possible duplicate branch; review this proposal before adding another active location"
                ],
                "previous_status": "identified",
            }
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


from .performance import measured


@measured("identified_spot_update")
def identify_from_source(db, case, source):
    if source.analysis.get("discovery_skip"):
        return [
            r.id
            for r in db.scalars(
                select(IdentifiedSpot).where(
                    IdentifiedSpot.user_id == case.user_id,
                    IdentifiedSpot.status.not_in(INACTIVE),
                    IdentifiedSpot.id.in_(source.analysis["discovery_skip"].get("spot_ids", [])),
                )
            )
        ]
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
        topic = (candidate.get("name", "") + " " + candidate.get("dish_or_activity", "")).lower()
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
        row = upsert_spot(db, case.user_id, candidate["name"], category, area, data)
        if row and row.status not in INACTIVE:
            output.append(row.id)
            checks.append({"name": candidate["name"], "decision": "saved", "spot_id": row.id})
        else:
            checks.append(
                {
                    "name": candidate["name"],
                    "decision": "held",
                    "reasons": issues
                    or (row.data.get("quality_issues", []) if row else [])
                    or ["Existing rejection or identity review prevents another insert"],
                    **({"spot_id": row.id} if row else {}),
                }
            )
    source.analysis = {**source.analysis, "inventory_checks": unique(checks)}
    db.flush()
    return list(dict.fromkeys(output))


class _ReconciliationIndex:
    """Conservative candidates over the rows locked by this reconciliation.

    Keep normalization local to this transaction. Rows are still compared by the
    canonical branch predicates, and changed merge targets are indexed at once.
    """

    def __init__(self, rows):
        self.rows = rows
        self.order = {row.id: index for index, row in enumerate(rows)}
        self.by_id = {row.id: row for row in rows}
        self.names = {}
        self.letters = {}
        self.aliases = defaultdict(set)
        self.signatures = defaultdict(set)
        self.map_keys = defaultdict(set)
        self.row_names = defaultdict(set)
        self.sources = defaultdict(set)
        for row in rows:
            self.row_names[self.name(row.name)[0]].add(row.id)
            self.update(row)

    def name(self, value):
        value = str(value)
        if value not in self.names:
            sig = signature(value)
            self.names[value] = (name_key(value).replace(" ", ""), sig, sig.replace(" ", ""))
            compact = self.names[value][2]
            if compact not in self.letters:
                self.letters[compact] = CharacterCounts(compact)
        return self.names[value]

    def update(self, row):
        # Keeping an earlier candidate is safe: same_branch rechecks current data.
        for alias in [row.name, *row.data.get("aliases", [])]:
            exact, sig, _ = self.name(alias)
            self.aliases[exact].add(row.id)
            if sig:
                self.signatures[sig].add(row.id)
        place = row.data.get("maps_identity", {}).get("place_key")
        if place:
            self.map_keys[place].add(row.id)
        for url in source_urls(row.data):
            self.sources[url].add(row.id)

    def ordered(self, ids):
        return [self.by_id[ident] for ident in sorted(ids, key=self.order.__getitem__)]

    def branch_candidates(self, row):
        exact, sig, _ = self.name(row.name)
        ids = self.aliases[exact] | self.signatures[sig]
        place = row.data.get("maps_identity", {}).get("place_key")
        if place:
            ids = ids | self.map_keys[place]
        return self.ordered(ids)

    def duplicate_candidates(self, row):
        return self.ordered(self.row_names[self.name(row.name)[0]])

    def source_candidates(self, row):
        ids = set()
        for url in source_urls(row.data):
            ids.update(self.sources[url])
        return self.ordered(ids)

    def possible_names(self, left, right):
        exact_a, sig_a, compact_a = self.name(left)
        exact_b, sig_b, compact_b = self.name(right)
        if not compact_a or not compact_b:
            return False
        if exact_a == exact_b or sig_a == sig_b:
            return True
        # These are upper bounds on the same directional SequenceMatcher ratio
        # used by possible_match; they cannot reject an eligible fuzzy match.
        length = len(compact_a) + len(compact_b)
        if 2 * min(len(compact_a), len(compact_b)) / length < 0.82:
            return False
        left_counts, right_counts = self.letters[compact_a], self.letters[compact_b]
        common = sum(min(amount, right_counts.get(char, 0)) for char, amount in left_counts.items())
        if 2.0 * common / length < 0.82:
            return False
        matcher = SequenceMatcher(None, compact_a, compact_b)
        return matcher.ratio() >= 0.82


def reconcile_spots(db, user_id):
    """Reversible cleanup: retain originals and provenance; never publish or erase."""
    from .db import Audit

    lock_inventory(db)

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
    index = _ReconciliationIndex(rows)
    for row in rows:
        if row.status in INACTIVE or row.venue_id:
            continue
        matches = [
            r
            for r in index.branch_candidates(row)
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
            index.update(target)
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
        if row.status not in INACTIVE and not row.venue_id:
            older = [
                r
                for r in index.duplicate_candidates(row)
                if r.id != row.id
                and (r.created_at, r.id) < (row.created_at, row.id)
                and r.status not in INACTIVE
                and unresolved_duplicate(r, row.name, row.area, row.data)
                and not same_branch(r, row.name, row.area, row.data)
            ]
            if older:
                row.status = "quarantined"
                row.data = {
                    **row.data,
                    "duplicate_review_candidates": [r.id for r in older],
                    "quality_issues": [
                        "Possible duplicate branch; inspect retained evidence before separate activation"
                    ],
                    "previous_status": "identified",
                }
                counts["quarantined"] += 1
        if row.status not in INACTIVE:
            possible = [
                r.id
                for r in rows
                if r.id != row.id and r.status not in INACTIVE and index.possible_names(row.name, r.name)
            ]
            row.data = {
                **row.data,
                "possible_duplicates": possible,
                "name_status": row.data.get("name_status", "unconfirmed_extraction"),
            }
    # Old runs copied every observation into every candidate in a multi-venue
    # reel. Keep ambiguous evidence available without presenting it as this spot's vibe.
    for row in rows:
        if row.status in INACTIVE:
            continue
        aliases = [name_key(a) for a in [row.name, *row.data.get("aliases", [])]]
        ambiguous_urls = set()
        for other in index.source_candidates(row):
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


def sync_inventory(db, user_id):
    """Replay saved extraction into the canonical private inventory; never publish."""
    from .db import Investigation, ResearchSource

    before = {r.id for r in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id))}
    sources = list(
        db.scalars(
            select(ResearchSource)
            .join(Investigation, ResearchSource.case_id == Investigation.id)
            .where(Investigation.user_id == user_id)
            .order_by(ResearchSource.created_at)
        )
    )
    touched = set()
    for source in sources:
        case = db.get(Investigation, source.case_id)
        if case.state == "cancelled":
            continue
        # Existing skip references already point to the canonical row.
        if source.analysis.get("discovery_skip"):
            continue
        touched.update(identify_from_source(db, case, source))
        db.commit()
    cleanup = reconcile_spots(db, user_id)
    db.commit()
    rows = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id)))
    return {
        "source_records_examined": len(sources),
        "identified_spots": len(touched),
        "new_records": sum(r.id not in before for r in rows),
        "active": sum(r.status not in INACTIVE for r in rows),
        "held_or_merged": sum(r.status in INACTIVE for r in rows),
        "cleanup": cleanup,
        "published": 0,
        "review_status": "Saved in local SQL inventory; awaiting your location review",
    }
