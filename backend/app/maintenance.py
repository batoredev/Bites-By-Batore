"""Private evidence monitoring and review packets. A fetch never verifies a fact."""

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from sqlalchemy import select
from .config import ROOT, settings
from .db import IdentifiedSpot, Venue, Claim, Audit, Job, Counter, now
from .providers import Unavailable, DeferredCollection
from .spots import INACTIVE, merge_list, spot_dict
from .inventory import parse_document
from .web_evidence import read_official_html
from .spot_identity import name_key, names_match


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def after(hours):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def page_urls(row):
    urls = [s.get("url", "") for s in row.data.get("sources", [])]
    urls += row.data.get("menu_links", [])
    urls += row.data.get("website_candidates", [])
    return sorted(
        {
            u
            for u in urls
            if urlparse(u).scheme == "https"
            and not any(
                (urlparse(u).hostname or "").endswith(h)
                for h in (
                    "instagram.com",
                    "facebook.com",
                    "youtube.com",
                    "google.com",
                    "goo.gl",
                    "openstreetmap.org",
                )
            )
        }
    )


def expected_fields(row, url, doc):
    """Extract only narrow configured first-party assertions, with literal evidence checks."""
    values = {k: doc[k] for k in ("offerings", "menu_links", "maps_links", "hours_candidates", "vibes") if doc.get(k)}
    seeds = json.loads((ROOT / "resources/coimbatore-spot-seeds.json").read_text(encoding="utf-8"))["spots"]
    text = " ".join(doc["text"].casefold().split())
    gaps = []
    for seed in seeds:
        if seed["url"] != url or not any(
            names_match(seed["name"], alias) for alias in [row.name, *row.data.get("aliases", [])]
        ):
            continue
        for fact in seed.get("facts", []):
            if fact.get("requires") and all(" ".join(s.casefold().split()) in text for s in fact["requires"]):
                values[fact["field"]] = fact["value"]
            else:
                gaps.append(fact["field"])
    return values, sorted(set(gaps))


def alert(row, kind, url, detail):
    data = deepcopy(row.data)
    item = {
        "id": digest([kind, url, detail]),
        "kind": kind,
        "url": url,
        "detail": detail,
        "at": now(),
        "state": "open",
    }
    alerts = data.get("maintenance_alerts", [])
    if not any(a["id"] == item["id"] and a["state"] == "open" for a in alerts):
        alerts.append(item)
    data["maintenance_alerts"] = alerts
    row.data = data


def hold_published(db, row, reason):
    venue = db.get(Venue, row.venue_id) if row.venue_id else None
    if venue and not venue.is_demo and venue.status == "published":
        venue.status, venue.updated_at = "review", now()
        venue.revision += 1
        venue.details = {k: v for k, v in venue.details.items() if k != "location_approval"}
        row.status = "awaiting_approval"
        db.add(
            Audit(
                actor=row.user_id,
                action="maintenance.venue_held",
                target=venue.id,
                detail={"reason": reason, "spot_id": row.id},
            )
        )


def refresh_spot(db, spot_id, user_id):
    row = db.get(IdentifiedSpot, spot_id)
    if not row or row.user_id != user_id or row.status in INACTIVE:
        return {"removed_or_inactive": True}
    pages = deepcopy(row.data.get("page_checks", {}))
    due = [u for u in page_urls(row) if pages.get(u, {}).get("next_check_at", "") <= now()]
    for url in due[:2]:
        previous = pages.get(url, {})
        checked = now()
        try:
            doc = parse_document(read_official_html(db, url, allow_unverified_host=True), url)
            # A fetched page still needs venue association; configured sources can be shared directories.
            trusted_target = any(
                s.get("url") == url and s.get("type") in {"official", "official_menu"}
                for s in row.data.get("sources", [])
            )
            tokens = [
                t
                for t in name_key(row.name).split()
                if len(t) > 3 and t not in {"coimbatore", "restaurant", "cafe"}
            ]
            if not trusted_target and (
                not tokens or not any(t in name_key(doc["text"]).split() for t in tokens)
            ):
                raise Unavailable("Fetched page no longer supports this candidate name; branch review needed")
            values, gaps = expected_fields(row, url, doc)
            payload_hash = digest(values)
            changed = bool(previous.get("values_hash")) and previous["values_hash"] != payload_hash
            entry = {
                "checked_at": checked,
                "last_success_at": checked,
                "next_check_at": after(24),
                "state": "changed" if changed else "checked_unverified",
                "failures": 0,
                "values_hash": payload_hash,
                "observed_fields": values,
                "missing_expected_fields": gaps,
                "verified": False,
            }
            if changed:
                fields = sorted(
                    k
                    for k in set(values) | set(previous.get("observed_fields", {}))
                    if values.get(k) != previous.get("observed_fields", {}).get(k)
                )
                entry["previous_values"] = previous.get("observed_fields", {})
                alert(
                    row,
                    "source_changed",
                    url,
                    {"fields": fields, "before": previous["values_hash"], "after": payload_hash},
                )
                if set(fields) & {
                    "hours",
                    "address",
                    "coordinates",
                    "offerings",
                    "menu_links",
                    "maps_links",
                    "closed",
                }:
                    hold_published(db, row, "A supporting page changed; reconfirm current facts and location")
            if gaps:
                alert(row, "expected_evidence_missing", url, {"fields": gaps})
                hold_published(db, row, "Previously expected source evidence is missing")
            pages[url] = entry
            # Store observations separately; never overwrite accepted facts or silently erase old prices.
            sources = merge_list(
                "sources",
                row.data.get("sources", [])
                + [
                    {
                        "url": url,
                        "type": "monitored_page",
                        "collected_at": checked,
                        "basis": "Page fetched; observed fields and branch remain unverified",
                    }
                ],
            )
            row.data = {**row.data, "sources": sources}
        except DeferredCollection:
            row.data = {**row.data, "page_checks": pages}
            db.commit()
            raise
        except Unavailable as exc:
            failures = previous.get("failures", 0) + 1
            pages[url] = {
                **previous,
                "checked_at": checked,
                "next_check_at": after(min(24, 2**failures)),
                "state": "unavailable",
                "failures": failures,
                "error": str(exc),
                "verified": False,
            }
            if failures >= 3:
                alert(row, "source_unavailable", url, {"reason": str(exc)})
        row.data, row.updated_at = {**row.data, "page_checks": pages}, checked
        db.commit()
    remaining = sum(pages.get(u, {}).get("next_check_at", "") <= now() for u in page_urls(row))
    return {"spot_id": row.id, "checked": min(2, len(due)), "remaining": remaining, "published": False}


def expire_critical_facts(db):
    held = []
    for venue in db.scalars(select(Venue).where(Venue.status == "published", Venue.is_demo.is_(False))):
        fields = set(
            db.scalars(
                select(Claim.field).where(
                    Claim.venue_id == venue.id, Claim.status == "accepted", Claim.expires_at > now()
                )
            )
        )
        missing = {"hours", "closed", "price_per_person"} - fields
        if missing:
            venue.status, venue.updated_at = "review", now()
            venue.revision += 1
            venue.details = {k: v for k, v in venue.details.items() if k != "location_approval"}
            related = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.venue_id == venue.id)))
            for row in related:
                row.status = "awaiting_approval"
                alert(row, "critical_facts_expired", "", {"fields": sorted(missing)})
            for owner in {row.user_id for row in related} or {"worker"}:
                db.add(
                    Audit(
                        actor=owner,
                        action="maintenance.expired",
                        target=venue.id,
                        detail={"fields": sorted(missing), "performed_by": "worker"},
                    )
                )
            held.append(venue.id)
    db.commit()
    return held


def approval_packet(db, row):
    payload = spot_dict(row)
    venue = db.get(Venue, row.venue_id) if row.venue_id else None
    claims = list(db.scalars(select(Claim).where(Claim.venue_id == row.venue_id))) if venue else []
    current = {c.field for c in claims if c.status == "accepted" and c.expires_at > now()}
    blockers = []
    if row.status in INACTIVE:
        blockers.append("Resolve held/merged record before approval")
    if not row.data.get("maps_identity", {}).get("confirmed_by"):
        blockers.append("Independently confirm exact Maps name, address and branch")
    if not venue:
        blockers.append("Prepare a pending venue with checked address and coordinates")
    elif not venue.details.get("branch_confirmed") or not venue.details.get("maps_identity", {}).get(
        "confirmed_by"
    ):
        blockers.append("Confirm exact branch and Maps identity on the prepared venue")
    blockers += [
        "Accept current " + k + " evidence" for k in sorted({"hours", "closed", "price_per_person"} - current)
    ]
    opened = [a for a in row.data.get("maintenance_alerts", []) if a["state"] == "open"]
    if opened:
        blockers.append("Review unresolved source-change/freshness alerts")
    checks = row.data.get("page_checks", {})
    return {
        "id": row.id,
        "name": row.name,
        "area": row.area,
        "category": row.category,
        "status": row.status,
        "venue_id": row.venue_id,
        "maps_url": payload["map_search_url"],
        "sources": row.data.get("sources", []),
        "page_checks": checks,
        "alerts": opened,
        "missing": payload["missing"],
        "conflicts": row.data.get("conflicts", []),
        "possible_duplicates": row.data.get("possible_duplicates", []),
        "blockers": blockers,
        "ready_for_final_approval": not blockers,
        "location_approved": bool(
            venue and venue.status == "published" and venue.details.get("location_approval")
        ),
        "fact_evidence": [
            {
                "id": c.id,
                "field": c.field,
                "value": c.value,
                "source_url": c.source_url,
                "status": c.status,
                "expires_at": c.expires_at,
            }
            for c in claims
        ],
        "rule": "Page checks and draft claims are unverified. Only the operator can approve a location.",
    }


def maintenance_report(db, user_id):
    from .evaluation import source_rows

    rows = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id)))
    active = [r for r in rows if r.status not in INACTIVE]
    packets = [approval_packet(db, r) for r in active]
    grid = {}
    for row in active:
        key = (row.area or "Unknown area", row.category)
        cell = grid.setdefault(key, {"area": key[0], "category": key[1], "drafts": 0, "approved": 0})
        cell["drafts"] += 1
        cell["approved"] += int(next(p for p in packets if p["id"] == row.id)["location_approved"])
    sources = source_rows(db, user_id)
    review_samples = []
    seen = set()
    for source in sorted(sources, key=lambda s: s.created_at, reverse=True):
        if source.canonical_url in seen:
            continue
        seen.add(source.canonical_url)
        langs = sorted(
            {
                l
                for role in ("caption", "comments", "video")
                for l in source.analysis.get(role, {}).get("languages", [])
            }
        )
        review_samples.append(
            {
                "id": source.id,
                "url": source.canonical_url,
                "languages": langs,
                "labels": list(source.analysis.get("evaluation_labels", {})),
                "raw_available": bool(source.content.get("caption") or source.content.get("comments")),
                "watch": source.analysis.get("source_watch", {}),
            }
        )
    jobs = [
        j
        for j in db.scalars(select(Job))
        if j.payload.get("user_id") == user_id
        or j.payload.get("spot_id") in {r.id for r in rows}
        or j.payload.get("source_id") in {s.id for s in sources}
        or j.payload.get("case_id") in {s.case_id for s in sources}
    ]
    failed = [{"id": j.id, "kind": j.kind, "error": j.error} for j in jobs if j.state == "failed"]
    pages = [p for r in active for p in r.data.get("page_checks", {}).values()]
    return {
        "at": now(),
        "draft_count": len(active),
        "approved_count": sum(p["location_approved"] for p in packets),
        "ready_for_approval": sum(p["ready_for_final_approval"] for p in packets),
        "open_alerts": sum(len(p["alerts"]) for p in packets),
        "pages_monitored": len(pages),
        "pages_overdue": sum(p.get("next_check_at", "") <= now() for p in pages),
        "unavailable_pages": sum(p["state"] == "unavailable" for p in pages),
        "grid": sorted(grid.values(), key=lambda c: (c["area"], c["category"])),
        "packets": packets,
        "evaluation_queue": review_samples,
        "failed_jobs": failed,
        "coverage": "Observed inventory only; city-wide venue total and completeness are not established",
        "cadence": {
            "page_hours": 24,
            "reel_days": settings().source_watch_days,
            "reel_checks_per_day": settings().source_watch_daily_limit,
            "note": "Scheduled targets, not guaranteed deadlines; quotas, outages and queued work can delay checks",
        },
    }


def schedule_maintenance(db, user_id):
    from .jobs import enqueue
    from .evaluation import source_rows

    queued = []
    existing = list(db.scalars(select(Job).where(Job.state.in_(["queued", "running"]))))
    for row in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id)):
        if row.status in INACTIVE:
            continue
        search_due = row.data.get("web_search_next_at", "")
        if (
            not search_due
            and "web_search_results" in row.data
            and not any(r.get("status") == "pending" for r in row.data["web_search_results"])
        ):
            # Adopt older completed searches into the recurring cycle without discarding evidence.
            search_due = after(24 * 7)
            row.data = {**row.data, "web_search_next_at": search_due}
            db.commit()
        if (
            search_due
            and search_due <= now()
            and not any(j.kind == "spot_enrich" and j.payload.get("spot_id") == row.id for j in existing)
        ):
            queued.append(
                enqueue(
                    db,
                    "spot_enrich",
                    {"spot_id": row.id, "user_id": user_id},
                    f"spot-enrich-refresh:{row.id}:{now()}",
                    priority=25,
                ).id
            )
        pages = row.data.get("page_checks", {})
        if any(pages.get(u, {}).get("next_check_at", "") <= now() for u in page_urls(row)) and not any(
            j.kind == "spot_refresh" and j.payload.get("spot_id") == row.id for j in existing
        ):
            queued.append(
                enqueue(
                    db,
                    "spot_refresh",
                    {"spot_id": row.id, "user_id": user_id},
                    f"spot-refresh:{row.id}:{now()}",
                    priority=85,
                ).id
            )
    day = datetime.now(timezone.utc).date().isoformat()
    daily_key = f"source-watch-enqueued:{user_id}:{day}"
    count = db.get(Counter, daily_key)
    remaining = max(0, settings().source_watch_daily_limit - (count.value if count else 0))
    seen = set()
    for source in sorted(
        source_rows(db, user_id),
        key=lambda s: s.analysis.get("source_watch", {}).get("checked_at", s.created_at),
    ):
        if source.platform != "instagram" or source.canonical_url in seen:
            continue
        seen.add(source.canonical_url)
        watch = source.analysis.get("source_watch", {})
        if watch.get("next_check_at", after(-1)) > now() or not remaining:
            continue
        if any(j.kind == "source_watch" and j.payload.get("source_id") == source.id for j in existing):
            continue
        from .db import Investigation

        case = db.get(Investigation, source.case_id)
        if not case or case.state in {"queued", "running", "cancelled"}:
            continue
        from .providers import increment_bounded

        if not increment_bounded(db, daily_key, settings().source_watch_daily_limit):
            break
        queued.append(
            enqueue(
                db,
                "source_watch",
                {"source_id": source.id, "user_id": user_id},
                f"source-watch:{source.id}:{day}",
                priority=98,
            ).id
        )
        remaining -= 1
    return queued


def watch_source(db, source_id, user_id):
    from .evaluation import owned_source
    from .browser_sources import browser_instagram

    source = owned_source(db, user_id, source_id)
    result = browser_instagram(db, source.canonical_url)
    checked = now()
    previous = source.analysis.get("source_watch", {})
    status = result.get("browser", {}).get("status", "unavailable")
    watch = {
        **previous,
        "checked_at": checked,
        "access": status,
        "next_check_at": after(24 * settings().source_watch_days if status == "public_content" else 24),
    }
    if status == "public_content":
        # Counts and bounded comments vary independently of caption facts. Track these separately.
        caption_hash = digest(result.get("caption", ""))
        old_hash = previous.get("caption_hash") or (
            digest(source.content["caption"]) if source.content.get("caption") else None
        )
        changed = bool(old_hash) and old_hash != caption_hash and bool(result.get("caption"))
        watch.update(
            caption_hash=caption_hash,
            observed_caption=str(result.get("caption", ""))[:12000],
            collected_comments=len(result.get("comment_texts", [])),
            caption_changed=changed,
            coverage=result.get("browser", {}).get("comment_expansion", {}),
        )
        if changed:
            for row in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id)):
                if source.id in row.data.get("source_ids", []) and row.status not in INACTIVE:
                    alert(
                        row,
                        "reel_caption_changed",
                        source.canonical_url,
                        {"before": old_hash, "after": caption_hash},
                    )
                    hold_published(db, row, "Supporting reel caption changed; review associated claims")
            from .db import Investigation
            from .research import start_case

            original = db.get(Investigation, source.case_id)
            followup = db.scalar(
                select(Investigation).where(
                    Investigation.user_id == user_id,
                    Investigation.context["maintenance_source_id"].as_string() == source.id,
                    Investigation.context["maintenance_watch_hash"].as_string() == caption_hash,
                )
            )
            if not followup:
                followup = start_case(
                    db,
                    user_id,
                    original.query,
                    context={
                        "url": source.canonical_url,
                        "maintenance_source_id": source.id,
                        "maintenance_watch_hash": caption_hash,
                        "refresh_reason": "Supporting reel caption changed",
                    },
                    seed_sources=[{"platform": "instagram", "url": source.canonical_url}],
                )
            watch["reinvestigation_case_id"] = followup.id
        # Do not silently attach older predictions to a changed input. Recollection remains a review lead.
        watch["action"] = (
            "Reinvestigation queued; changed caption remains unverified"
            if changed
            else "Caption monitored; no factual verification"
        )
    source.analysis = {**source.analysis, "source_watch": watch}
    db.commit()
    return watch
