"""The worker heartbeat must survive a busy database and not depend on job length."""

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app import jobs
from app.db import Counter, Session


def test_beat_records_current_time(client):
    assert jobs.beat() is True
    with Session() as db:
        assert db.get(Counter, "worker_heartbeat").value > 0


def test_beat_retries_when_database_is_busy_then_gives_up_quietly(client, monkeypatch):
    calls = []

    class Busy:
        def __enter__(self):
            calls.append(1)
            raise OperationalError("UPDATE counters", {}, Exception("database is locked"))

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(jobs, "Session", lambda: Busy())
    monkeypatch.setattr(jobs.time, "sleep", lambda seconds: None)
    assert jobs.beat(attempts=3) is False
    assert len(calls) == 3


def test_live_places_are_enriched_first_and_waiting_jobs_are_raised(client):
    from app.db import IdentifiedSpot, Job

    with Session() as db:
        for ident, status, data in [
            ("live", "approved", {}),
            ("draft", "identified", {}),
            ("merged", "merged", {}),
            ("done", "approved", {"web_search_results": [{"url": "https://example.org"}]}),
        ]:
            db.add(IdentifiedSpot(id=ident, user_id="u1", identity_key=ident, name=ident, status=status, data=data))
        db.commit()
        jobs.enqueue(db, "spot_enrich", {"spot_id": "live"}, "spot-enrich:live", priority=25)
        jobs.queue_enrichment(db, "u1")
        jobs.queue_enrichment(db, "u1")  # repeat-safe
        rows = {j.payload["spot_id"]: j.priority for j in db.scalars(select(Job).where(Job.kind == "spot_enrich"))}
    assert rows == {"live": jobs.LIVE_ENRICH_PRIORITY, "draft": 25}


def test_beat_recovers_after_one_busy_attempt(client, monkeypatch):
    real = jobs.Session
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] == 1:
            raise OperationalError("UPDATE counters", {}, Exception("database is locked"))
        return real()

    monkeypatch.setattr(jobs, "Session", flaky)
    monkeypatch.setattr(jobs.time, "sleep", lambda seconds: None)
    assert jobs.beat() is True
