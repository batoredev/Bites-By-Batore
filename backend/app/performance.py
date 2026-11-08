"""Local execution timings. Never record prompts, source text, credentials or media."""

import time
import math
from contextvars import ContextVar
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timezone

ACTIVE_TRACE = ContextVar("batore_execution_trace", default=None)


class Trace:
    def __init__(self):
        self.started = time.perf_counter()
        self.at = datetime.now(timezone.utc).isoformat()
        self.phases = {}
        self.model = {
            "calls": 0,
            "load_seconds": 0.0,
            "prompt_seconds": 0.0,
            "generation_seconds": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    def record(self, name, seconds, failed=False):
        row = self.phases.setdefault(name, {"calls": 0, "seconds": 0.0, "failures": 0})
        row["calls"] += 1
        row["seconds"] = round(row["seconds"] + max(0, seconds), 6)
        row["failures"] += int(failed)

    def summary(self):
        return {
            "started_at": self.at,
            "execution_seconds": round(time.perf_counter() - self.started, 6),
            "phases": self.phases,
            "model": self.model,
            "note": "Nested phases overlap; do not sum them as wall time. No accuracy is inferred.",
        }


@contextmanager
def span(name):
    start, failed = time.perf_counter(), False
    try:
        yield
    except BaseException:
        failed = True
        raise
    finally:
        trace = ACTIVE_TRACE.get()
        if trace is not None:
            trace.record(name, time.perf_counter() - start, failed)


def model_metrics(response):
    trace = ACTIVE_TRACE.get()
    if trace is None:
        return
    trace.model["calls"] += 1
    for field, key in [
        ("load_duration", "load_seconds"),
        ("prompt_eval_duration", "prompt_seconds"),
        ("eval_duration", "generation_seconds"),
    ]:
        trace.model[key] = round(trace.model[key] + max(0, response.get(field, 0) or 0) / 1e9, 6)
    for field, key in [("prompt_eval_count", "input_tokens"), ("eval_count", "output_tokens")]:
        trace.model[key] += max(0, response.get(field, 0) or 0)


def measured(name):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            with span(name):
                return fn(*args, **kwargs)

        return wrapped

    return decorate


def wait_reason(exc):
    from .providers import DeferredCollection
    from .db import is_database_busy

    if is_database_busy(exc):
        return "database_busy"

    if isinstance(exc, DeferredCollection):
        return exc.reason
    cause = getattr(exc, "__cause__", None)
    if cause is not None:
        return wait_reason(cause)
    return "pending_source_or_stage" if hasattr(exc, "retry_seconds") else "retry_after_error"


def delivery_metrics(job, trace, previous, reason=""):
    started = datetime.fromisoformat(trace.at)
    created, due = datetime.fromisoformat(job.created_at), datetime.fromisoformat(job.due_at)
    attempt = {
        **trace.summary(),
        "state": job.state,
        "wait_reason": reason,
        "age_at_start_seconds": max(0, (started - created).total_seconds()),
        "eligible_queue_wait_seconds": max(0, (started - max(created, due)).total_seconds()),
    }
    attempts = [*previous.get("deliveries", []), attempt]
    return {
        "version": 1,
        "delivery_count": previous.get("delivery_count", 0) + 1,
        "execution_seconds": round(previous.get("execution_seconds", 0) + attempt["execution_seconds"], 6),
        "last": attempt,
        "deliveries": attempts[-20:],
        "deferred_until": job.due_at if reason else None,
        "history_note": "Last 20 deliveries retained; cumulative execution/delivery totals include earlier deliveries.",
    }


def case_metrics(db, case):
    from sqlalchemy import select
    from .db import Job

    rows = list(
        db.scalars(
            select(Job).where(
                Job.kind.in_(["investigation", "source_analysis"]),
                Job.payload["case_id"].as_string() == case.id,
            )
        )
    )
    samples = [j.result["_performance"] for j in rows if j.result.get("_performance")]
    attempts = [a for s in samples for a in s.get("deliveries", [])]
    queued = [j for j in rows if j.state == "queued"]
    return {
        "measured_jobs": len(samples),
        "pending_jobs": len(queued),
        "execution_seconds": round(sum(s.get("execution_seconds", 0) for s in samples), 3),
        "deliveries": sum(s.get("delivery_count", 0) for s in samples),
        "wait_reasons": sorted(
            {s["last"]["wait_reason"] for s in samples if s.get("last", {}).get("wait_reason")}
        ),
        "next_due_at": min((j.due_at for j in queued), default=None),
        "phases": phase_report(attempts),
        "note": "Measured execution excludes future quota waits and does not establish accuracy or a speedup.",
    }


def distribution(values):
    values = sorted(values)
    return {
        "samples": len(values),
        "p50_seconds": values[math.ceil(len(values) * 0.5) - 1] if values else None,
        "p95_seconds": values[math.ceil(len(values) * 0.95) - 1] if values else None,
    }


def phase_report(attempts):
    names = sorted({name for a in attempts for name in a.get("phases", {})})
    return {
        name: {
            "calls": sum(a.get("phases", {}).get(name, {}).get("calls", 0) for a in attempts),
            "seconds": round(sum(a.get("phases", {}).get(name, {}).get("seconds", 0) for a in attempts), 3),
            "failures": sum(a.get("phases", {}).get(name, {}).get("failures", 0) for a in attempts),
        }
        for name in names
    }


def owned_jobs(db, user_id):
    from sqlalchemy import select, or_
    from .db import Investigation, ResearchSource, Job, IdentifiedSpot, Submission

    cases = select(Investigation.id).where(Investigation.user_id == user_id)
    sources = select(ResearchSource.id).where(ResearchSource.case_id.in_(cases))
    spots = select(IdentifiedSpot.id).where(IdentifiedSpot.user_id == user_id)
    submissions = select(Submission.id).where(Submission.user_id == user_id)
    return list(
        db.scalars(
            select(Job).where(
                or_(
                    Job.payload["case_id"].as_string().in_(cases),
                    Job.payload["source_id"].as_string().in_(sources),
                    Job.payload["spot_id"].as_string().in_(spots),
                    Job.payload["submission_id"].as_string().in_(submissions),
                    Job.payload["user_id"].as_string() == user_id,
                )
            )
        )
    )


def metrics_export(db, user_id):
    return [
        {
            "job_id": j.id,
            "kind": j.kind,
            "state": j.state,
            "created_at": j.created_at,
            "due_at": j.due_at,
            "performance": j.result["_performance"],
        }
        for j in owned_jobs(db, user_id)
        if j.result.get("_performance")
    ]


def owner_report(db, user_id):
    from .db import now
    from .config import settings

    rows = owned_jobs(db, user_id)
    samples = [j.result["_performance"] for j in rows if j.result.get("_performance")]
    attempts = [a for s in samples for a in s.get("deliveries", [])]
    queued = [j for j in rows if j.state == "queued"]
    cfg = settings()
    return {
        "at": now(),
        "owner_jobs": len(rows),
        "measured_jobs": len(samples),
        "unmeasured_jobs": len(rows) - len(samples),
        "retained_delivery_samples": len(attempts),
        "total_measured_deliveries": sum(s.get("delivery_count", 0) for s in samples),
        "execution_seconds": round(sum(s.get("execution_seconds", 0) for s in samples), 3),
        "delivery_execution": distribution([a["execution_seconds"] for a in attempts]),
        "eligible_queue_wait": distribution([a["eligible_queue_wait_seconds"] for a in attempts]),
        "phases": phase_report(attempts),
        "queued": len(queued),
        "deferred": sum(j.due_at > now() for j in queued),
        "next_due_at": min((j.due_at for j in queued), default=None),
        "wait_reasons": sorted(
            {s["last"]["wait_reason"] for s in samples if s.get("last", {}).get("wait_reason")}
        ),
        "configuration": {
            "pipeline": cfg.research_pipeline_enabled,
            "reuse": cfg.analysis_reuse_enabled,
            "browser_reuse": cfg.browser_reuse_enabled,
            "keep_alive": cfg.ollama_keep_alive,
            "model": cfg.ollama_model,
            "frame_budget": cfg.media_max_frames,
            "known_spot_skip": cfg.known_spot_skip_enabled,
            "gpu_layers_requested": cfg.ollama_gpu_layers,
        },
        "scope": "Delivery distributions include failures/retries, not per-reel completion. Last 20 deliveries per job; legacy jobs lack timings. Nested phases overlap. No speedup or accuracy claim.",
    }
