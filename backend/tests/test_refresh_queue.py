"""Published-place refresh jobs must run in bulk mode and must not pile up."""

from sqlalchemy import select

from app import collection_control
from app.db import Job, Session, Venue
from app.jobs import enqueue, schedule


def _venue(db, ident, details):
    db.add(Venue(id=ident, name=ident, category="food", area="RS Puram", address="", lat=11.0, lng=76.9,
                 tags=[], details=details, status="published", is_demo=True))


def test_refresh_gets_a_turn_in_the_bulk_rotation(client):
    with Session() as db:
        assert collection_control.fair_kind(db, ["refresh"]) == "refresh"


def test_schedule_skips_uncheckable_test_places_and_supersedes_stale_refreshes(client):
    with Session() as db:
        _venue(db, "checkable", {"google_place_id": "abc"})
        _venue(db, "test-only", {"test_inventory": {"by": "agent:test-inventory"}})
        db.commit()
        enqueue(db, "refresh", {"venue_id": "checkable"}, "refresh:checkable:1:regular", priority=20)
        enqueue(db, "refresh", {"venue_id": "test-only"}, "refresh:test-only:1:regular", priority=20)
        enqueue(db, "refresh", {"venue_id": "checkable"}, "correction:claim-1", priority=85)
        db.commit()
    schedule()
    schedule()  # repeat-safe
    with Session() as db:
        queued = {j.key for j in db.scalars(select(Job).where(Job.kind == "refresh", Job.state == "queued"))}
        cancelled = {j.key for j in db.scalars(select(Job).where(Job.kind == "refresh", Job.state == "cancelled"))}
    assert "refresh:checkable:1:regular" in cancelled and "refresh:test-only:1:regular" in cancelled
    assert "correction:claim-1" in queued  # owner-correction refreshes are never superseded
    assert sum(k.startswith("refresh:checkable:") for k in queued) == 1
    assert not any(k.startswith("refresh:test-only:") for k in queued)
