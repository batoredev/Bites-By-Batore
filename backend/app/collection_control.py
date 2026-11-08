"""Local initial-fill controls: unlimited daily counts, paced I/O and durable retries."""

import math
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .config import settings
from .db import Counter


def bulk_enabled():
    cfg = settings()
    return cfg.app_mode == "local" and cfg.local_bulk_collection


def daily_limits():
    cfg = settings()
    return {
        "external": 0 if bulk_enabled() else cfg.max_provider_calls_per_day,
        "browser": 0 if bulk_enabled() else cfg.browser_daily_limit,
        "investigations": 0 if bulk_enabled() else cfg.research_daily_limit,
    }


def count_request(db, key, maximum, *, commit=True):
    """Zero means unlimited only for request counts; monetary guards use increment_bounded."""
    if maximum < 0:
        raise ValueError("Request allowance cannot be negative")
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    db.execute(insert(Counter).values(key=key, value=0).on_conflict_do_nothing(index_elements=["key"]))
    statement = update(Counter).where(Counter.key == key)
    if maximum:
        statement = statement.where(Counter.value < maximum)
    result = db.execute(statement.values(value=Counter.value + 1))
    if commit:
        db.commit()
    return result.rowcount == 1


def host_key(host):
    return str(host).casefold().strip().rstrip(".")[:253]


def pace(db, host):
    """Reserve a persistent per-source slot without blocking the worker thread."""
    from .providers import DeferredCollection

    host = host_key(host)
    stamp = int(time.time())
    cooldown = db.get(Counter, "source-cooldown:" + host)
    if cooldown and cooldown.value > stamp:
        raise DeferredCollection(
            "Source retry time has not arrived",
            cooldown.value - stamp,
            reason="source_cooldown",
        )
    if not bulk_enabled():
        return
    interval = max(1, math.ceil(settings().public_request_interval_seconds))
    key = "source-next:" + host
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    db.execute(insert(Counter).values(key=key, value=0).on_conflict_do_nothing(index_elements=["key"]))
    result = db.execute(
        update(Counter).where(Counter.key == key, Counter.value <= stamp).values(value=stamp + interval)
    )
    if result.rowcount != 1:
        db.expire_all()
        due = db.get(Counter, key).value
        db.commit()
        raise DeferredCollection("Source request spacing", max(1, due - stamp), reason="source_pacing")
    db.commit()


def backoff(db, host, *, headers=None, default=60):
    """Honor delta/date Retry-After, retain a shared cooldown and exponential failures."""
    from .providers import DeferredCollection

    host = host_key(host)
    key = "source-failures:" + host
    count_request(db, key, 0)
    db.expire_all()
    failures = db.get(Counter, key).value
    seconds = min(3600, default * 2 ** min(6, failures - 1))
    value = (headers or {}).get("retry-after") or (headers or {}).get("Retry-After")
    if value:
        try:
            seconds = max(seconds, math.ceil(float(value)))
        except (ValueError, TypeError, OverflowError):
            try:
                seconds = max(
                    seconds,
                    math.ceil((parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()),
                )
            except (ValueError, TypeError, OverflowError):
                pass
    key = "source-cooldown:" + host
    seconds = min(seconds, 2**31 - 1 - int(time.time()))
    due = int(time.time() + seconds)
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    db.execute(insert(Counter).values(key=key, value=due).on_conflict_do_nothing(index_elements=["key"]))
    db.execute(update(Counter).where(Counter.key == key, Counter.value < due).values(value=due))
    db.commit()
    raise DeferredCollection(
        "Source is unavailable or rate limited; retry scheduled", seconds, reason="source_cooldown"
    )


def success(db, host):
    db.execute(update(Counter).where(Counter.key == "source-failures:" + host_key(host)).values(value=0))
    db.commit()


def fair_kind(db, eligible):
    """Weighted rotation keeps discovery, enrichment and current-page checks moving."""
    cycle = [
        "investigation",
        "spot_enrich",
        "spot_refresh",
        "spot_enrich",
        "spot_inventory",
        "source_watch",
        "city_directory",
    ]
    eligible = set(eligible)
    if not eligible.intersection(cycle):
        return None
    key = "bulk-dispatch"
    count_request(db, key, 0)
    db.expire_all()
    index = db.get(Counter, key).value - 1
    return next(
        cycle[(index + offset) % len(cycle)]
        for offset in range(len(cycle))
        if cycle[(index + offset) % len(cycle)] in eligible
    )


def resume_bulk(db, user_id):
    from .db import Job, IdentifiedSpot, Investigation, now
    from .providers import Unavailable

    if not bulk_enabled():
        raise Unavailable("Enable local initial collection before resuming its queue")
    spots = set(db.scalars(select(IdentifiedSpot.id).where(IdentifiedSpot.user_id == user_id)))
    cases = set(db.scalars(select(Investigation.id).where(Investigation.user_id == user_id)))
    resumed = []
    for job in db.scalars(select(Job).where(Job.state == "queued")):
        owned = (
            job.payload.get("user_id") == user_id
            or job.payload.get("spot_id") in spots
            or job.payload.get("case_id") in cases
        )
        previous = job.result.get("_performance", {}).get("last", {}).get("wait_reason")
        if owned and previous in {"local_daily_limit", "quota_or_collection_cooldown"}:
            # Old records combine quota/cooldown. Re-check through source guards;
            # do not clear any source cooldown, attempt count or request counter.
            job.due_at = now()
            resumed.append(job.id)
    pause = db.get(Counter, "research_paused")
    if pause:
        pause.value = 0
    db.commit()
    return {
        "resumed_jobs": len(resumed),
        "daily_limits": daily_limits(),
        "monthly_budget_inr": settings().monthly_budget_inr,
        "scope": "Local initial collection; source cooldowns, cache and approval gates retained",
    }
