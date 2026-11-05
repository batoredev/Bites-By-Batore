import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, or_
from sqlalchemy.exc import IntegrityError
from .config import settings
from .db import Session, Job, Submission, Venue, Audit, Plan, Counter, now, migrate
from .providers import (
    Unavailable,
    gemini_analysis,
    youtube_id,
    youtube_context,
    google_details,
    google_search,
    web_search,
    youtube_discover,
    ACTIVE_JOB,
)
from .resolver import resolve_candidates, source_track_record
from .research import execute_case, PendingSource, purge_expired_sources
from .db import Investigation, ResearchTask


def later(seconds):
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def enqueue(db, kind, payload, key, priority=20, state="queued"):
    existing = db.scalar(select(Job).where(Job.key == key))
    if existing:
        return existing
    job = Job(kind=kind, payload=payload, key=key, priority=priority, state=state)
    try:
        with db.begin_nested():
            db.add(job)
            db.flush()
        db.commit()
        return job
    except IntegrityError:
        return db.scalar(select(Job).where(Job.key == key))


def claim_job(db):
    eligible = or_(Job.state == "queued", (Job.state == "running") & (Job.lease_until < now()))
    ids = list(
        db.scalars(
            select(Job.id)
            .where(eligible, Job.due_at <= now())
            .order_by(Job.priority.desc(), Job.due_at)
            .limit(10)
        )
    )
    for job_id in ids:
        result = db.execute(
            update(Job)
            .where(Job.id == job_id, eligible)
            .values(state="running", lease_until=later(600), attempts=Job.attempts + 1)
        )
        db.commit()
        if result.rowcount:
            db.expire_all()
            return db.get(Job, job_id)
    return None


def analyze_submission(db, submission):
    content = dict(submission.content)
    media = content.pop("media", None)
    if settings().app_mode == "demo":
        # A real demonstration of source-state handling, not a fake AI analysis.
        return {
            "summary": "Content saved for review. Live language/video analysis is disabled in demo mode.",
            "caption": {"supplied": bool(content.get("caption"))},
            "comments": {
                "supplied": bool(content.get("comments")),
                "limitations": ["No sentiment or reliability claim has been inferred"],
            },
            "video": {"analyzed": False, "reason": "Gemini is disabled in demonstration mode"},
            "creator": {"reliability": "unestablished", "reason": "Likes and views do not prove accuracy"},
            "venue_candidates": [],
            "next_checks": [
                "Enable live providers to analyze supplied media",
                "Verify the exact venue branch and current price",
            ],
            "unknowns": ["Location, prices, source reliability and video content remain unverified"],
        }
    video_id = youtube_id(submission.url)
    if video_id and settings().youtube_api_key:
        context = youtube_context(db, video_id)
        content["provider_context"] = context
    if (
        "instagram.com" in submission.url
        and not any(content.get(k) for k in ["caption", "comments", "transcript"])
        and not media
    ):
        raise Unavailable(
            "Instagram link saved. Supply permitted video, caption or comments; arbitrary reel fetching is not configured."
        )
    result = gemini_analysis(
        db, content, media, "https://www.youtube.com/watch?v=" + video_id if video_id and not media else None
    )
    result["place_matching"] = resolve_candidates(db, result)
    result["source_track_record"] = source_track_record(db, submission.url)
    result["analysis_scope"] = {
        "supplied_video": bool(media or video_id),
        "caption_supplied": bool(content.get("caption")),
        "comments_supplied": bool(content.get("comments")),
        "youtube_metadata_checked": bool(content.get("provider_context")),
        "publication": "Observations require factual verification before publication",
    }
    return result


def execute_job(db, job):
    if job.kind == "spot_enrich":
        from .spot_search import enrich_spot
        from .providers import DeferredCollection

        if settings().app_mode == "demo":
            raise Unavailable("Real spot enrichment is disabled in demo")
        try:
            result = enrich_spot(db, job.payload["spot_id"])
        except DeferredCollection as exc:
            raise PendingSource(exc.retry_seconds) from exc
        if result.get("remaining"):
            raise PendingSource(30)
        return result
    if job.kind == "spot_inventory":
        from .inventory import collect_inventory
        from .providers import DeferredCollection

        if settings().app_mode == "demo":
            raise Unavailable("Real inventory collection is disabled in demo")
        try:
            return collect_inventory(db, job.payload["user_id"])
        except DeferredCollection as exc:
            raise PendingSource(exc.retry_seconds) from exc
    if job.kind == "investigation":
        return execute_case(db, job.payload["case_id"], int(job.key.rsplit(":", 1)[1]))
    if job.kind == "analysis":
        sub = db.get(Submission, job.payload["submission_id"])
        if not sub:
            return {"message": "Submission removed by its owner"}
        if settings().app_mode != "demo":
            from .research import start_case

            existing = [
                c
                for c in db.scalars(select(Investigation).where(Investigation.user_id == sub.user_id))
                if c.context.get("submission_id") == sub.id and c.state not in {"failed", "cancelled"}
            ]
            case = (
                existing[0]
                if existing
                else start_case(
                    db, sub.user_id, "Investigate this food or entertainment find", {"submission_id": sub.id}
                )
            )
            sub.status, sub.result = (
                "investigating",
                {
                    "investigation_id": case.id,
                    "summary": "Specialists are collecting and checking the available evidence",
                },
            )
            return {"submission_id": sub.id, "investigation_id": case.id}
        sub.status = "processing"
        db.commit()
        result = analyze_submission(db, sub)
        sub.result, sub.status = result, "review"
        sub.content = {k: v for k, v in sub.content.items() if k != "media"}
        return {"submission_id": sub.id, "message": "Analysis ready for verification"}
    if job.kind == "refresh":
        venue = db.get(Venue, job.payload["venue_id"])
        if not venue:
            return {"message": "Venue no longer exists"}
        if venue.is_demo:
            return {"message": "Demo fixture inspected. No real-world verification performed.", "demo": True}
        place_id = venue.details.get("google_place_id")
        if not place_id:
            raise Unavailable(
                "Venue needs an exact Google place ID or a merchant update before automated checks"
            )
        data = google_details(db, place_id)
        # Do not persist Google place-content into the owned venue database.
        if data.get("businessStatus") != "OPERATIONAL":
            venue.status = "review"
            venue.revision += 1
            db.add(
                Audit(
                    actor="worker",
                    action="venue.review_needed",
                    target=venue.id,
                    detail={"reason": "External operating status differs or is unknown"},
                )
            )
        return {
            "message": "Provider checked. Critical details will be rechecked when planning.",
            "checked_at": now(),
        }
    if job.kind == "discovery":
        if settings().app_mode == "demo":
            return {
                "message": "External discovery is disabled in demo. Fictional venues are kept separate.",
                "sources": [],
            }
        query = job.payload.get("query", "food cafes entertainment Coimbatore")
        if settings().autonomous_discovery:
            from .research import start_case
            from .db import User

            owner = (
                "local-operator"
                if settings().app_mode == "local"
                else settings().admin_user_ids.split(",")[0].strip()
            )
            if not owner or not db.get(User, owner):
                raise Unavailable("Autonomous discovery needs a configured admin account that has signed in")
            if job.payload.get("case_id"):
                return {"investigation_id": job.payload["case_id"]}
            case = start_case(db, owner, query, {"scheduled_job": job.id})
            job.payload = {**job.payload, "case_id": case.id}
            db.commit()
            return {
                "investigation_id": case.id,
                "message": "Discovery delegated to the complete investigation workflow",
            }
        output = {}
        for name, fn in [
            ("web", lambda: web_search(db, query)),
            ("youtube", lambda: youtube_discover(db, query)),
            ("maps", lambda: google_search(db, query, 11.0168, 76.9558)),
        ]:
            try:
                rows = fn()
                if name == "maps":
                    # Retain IDs only. Display fresh details on demand through the provider.
                    rows = [{"google_place_id": x["id"]} for x in rows]
                output[name] = rows
            except Unavailable as exc:
                output[name] = {"unavailable": str(exc)}
        if all(isinstance(v, dict) and "unavailable" in v for v in output.values()):
            raise Unavailable(
                "All discovery sources are unavailable; configure at least one supported source"
            )
        output["message"] = (
            "Discovery leads require exact-branch matching and verified venue facts before publication"
        )
        return output
    raise ValueError("Unsupported job kind")


def run_once():
    with Session() as db:
        job = claim_job(db)
        if not job:
            return False
        active_token = ACTIVE_JOB.set(job.id)
        try:
            job.result = execute_job(db, job)
            job.state, job.completed_at, job.error = "done", now(), ""
        except PendingSource as exc:
            job.state, job.due_at, job.attempts = "queued", later(exc.retry_seconds), max(0, job.attempts - 1)
        except Exception as exc:
            db.rollback()
            job = db.get(Job, job.id)
            if not job:
                return True
            message = (
                str(exc)
                if isinstance(exc, (Unavailable, ValueError))
                else "Unexpected worker error; inspect server logs"
            )
            if not isinstance(exc, (Unavailable, ValueError)):
                import logging

                logging.getLogger(__name__).exception("Job %s failed", job.id)
            job.error = message[:500]
            job.state = "failed" if job.attempts >= settings().max_attempts else "queued"
            job.due_at = later(min(3600, 30 * 2**job.attempts))
            if job.kind == "investigation":
                case = db.get(Investigation, job.payload.get("case_id"))
                if case and case.state != "cancelled":
                    case.state = "failed" if job.state == "failed" else "queued"
                    task = db.scalar(
                        select(ResearchTask)
                        .where(ResearchTask.case_id == case.id, ResearchTask.state != "done")
                        .order_by(ResearchTask.ordinal)
                    )
                    if task:
                        task.state, task.error = case.state, message[:500]
            if job.kind == "analysis":
                sub = db.get(Submission, job.payload["submission_id"])
                if sub:
                    sub.status = "needs_input" if job.state == "failed" else "retrying"
                    sub.result = {"message": message}
                    if job.state == "failed":
                        sub.content = {k: v for k, v in sub.content.items() if k != "media"}
        finally:
            ACTIVE_JOB.reset(active_token)
        job.lease_until = None
        db.commit()
        return True


def schedule():
    cfg = settings()
    bucket = int(time.time() // (max(1, cfg.refresh_interval_hours) * 3600))
    with Session() as db:
        purge_expired_sources(db)
        # Recover a crash between a committed stage result and enqueueing its successor.
        for case in db.scalars(select(Investigation).where(Investigation.state.in_(["queued", "running"]))):
            task = db.scalar(
                select(ResearchTask)
                .where(ResearchTask.case_id == case.id, ResearchTask.state != "done")
                .order_by(ResearchTask.ordinal)
            )
            if task:
                enqueue(
                    db, "investigation", {"case_id": case.id}, f"case:{case.id}:{task.ordinal}", priority=90
                )
        active_venues = set()
        for plan in db.scalars(select(Plan).where(Plan.saved.is_(True))):
            departure = datetime.fromisoformat(plan.request["departure"])
            if datetime.now(timezone.utc) <= departure <= datetime.now(timezone.utc) + timedelta(days=1):
                active_venues.update(s["venue_id"] for s in plan.result["stops"])
        venues = list(
            db.scalars(
                select(Venue).where(Venue.status == "published", Venue.is_demo == (cfg.app_mode == "demo"))
            )
        )
        for venue in venues:
            urgent = venue.id in active_venues
            interval_bucket = int(time.time() // 3600) if urgent else bucket
            enqueue(
                db,
                "refresh",
                {"venue_id": venue.id},
                f"refresh:{venue.id}:{interval_bucket}:{'active' if urgent else 'regular'}",
                priority=80 if urgent else 20,
            )
        if cfg.app_mode == "local" and cfg.autonomous_discovery:
            from .frontier import start_next
            from .db import User

            if db.get(User, "local-operator"):
                paused = db.get(Counter, "research_paused")
                if cfg.inventory_collection_enabled and not (paused and paused.value):
                    enqueue(
                        db,
                        "spot_inventory",
                        {"user_id": "local-operator"},
                        f"spot-inventory:local-operator:{datetime.now(timezone.utc).date().isoformat()}",
                        priority=95,
                    )
                    from .db import IdentifiedSpot

                    for spot in db.scalars(
                        select(IdentifiedSpot).where(IdentifiedSpot.user_id == "local-operator")
                    ):
                        if spot.status in {"merged", "quarantined", "rejected"}:
                            continue
                        if not spot.data.get("web_search_results") and not any(
                            s.get("type") == "official" for s in spot.data.get("sources", [])
                        ):
                            enqueue(
                                db, "spot_enrich", {"spot_id": spot.id}, f"spot-enrich:{spot.id}", priority=25
                            )
                try:
                    start_next(db, "local-operator", scheduled=True)
                except Unavailable:
                    pass
        elif cfg.app_mode == "live":
            enqueue(
                db,
                "discovery",
                {"query": "Coimbatore new restaurants cafes bowling gaming parks"},
                f"discovery:{bucket}",
                priority=50,
            )
        # Ephemeral search previews expire after one day; audit status remains.
        cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        for job in db.scalars(select(Job).where(Job.kind == "discovery", Job.created_at < cutoff)):
            job.result = {"message": "Search preview expired. Run discovery again for fresh results."}
        # Uploaded bytes never remain after terminal jobs; recover abandoned media as well.
        media_cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        for sub in db.scalars(select(Submission).where(Submission.created_at < media_cutoff)):
            if "media" in sub.content:
                sub.content = {k: v for k, v in sub.content.items() if k != "media"}
        db.commit()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if settings().app_mode in {"demo", "local"}:
        migrate()
    scheduled = 0
    while True:
        try:
            with Session() as db:
                heartbeat = db.get(Counter, "worker_heartbeat")
                if heartbeat:
                    heartbeat.value = int(time.time())
                else:
                    db.add(Counter(key="worker_heartbeat", value=int(time.time())))
                db.commit()
            if time.monotonic() - scheduled > 60:
                schedule()
                scheduled = time.monotonic()
            worked = run_once()
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Worker loop failed; retrying after backoff")
            if args.once:
                raise
            time.sleep(10)
            continue
        if args.once:
            break
        if not worked:
            time.sleep(max(1, settings().worker_poll_seconds))


if __name__ == "__main__":
    main()
