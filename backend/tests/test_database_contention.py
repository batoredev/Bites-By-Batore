"""Transient SQLite conflicts must preserve durable work and avoid terminal failures."""

import sqlite3
import pytest
from sqlalchemy.exc import OperationalError
from app import jobs, auth as auth_module
from app.db import Session, Counter, Job, is_database_busy


def busy():
    return OperationalError("private fixture SQL", {}, sqlite3.OperationalError("database is locked"))


def test_lock_detection_distinguishes_unrelated_database_errors():
    assert is_database_busy(busy())
    assert not is_database_busy(OperationalError("fixture", {}, sqlite3.OperationalError("no such table")))
    try:
        raise RuntimeError("wrapped") from busy()
    except RuntimeError as error:
        assert is_database_busy(error)


def test_busy_claim_does_not_execute_or_consume_attempts(client, monkeypatch):
    with Session() as db:
        ident = jobs.enqueue(db, "fixture", {}, "contention-claim").id

    def blocked(*args, **kwargs):
        raise busy()

    monkeypatch.setattr(jobs, "claim_job", blocked)
    monkeypatch.setattr(jobs, "execute_job", lambda *a: pytest.fail("No claim, no remote work"))
    assert jobs.run_once() is False
    with Session() as db:
        row = db.get(Job, ident)
        assert row.state == "queued" and row.attempts == 0


def test_busy_execution_retains_checkpoint_and_retry_allowance(client, monkeypatch):
    with Session() as db:
        ident = jobs.enqueue(db, "fixture", {}, "contention-execution").id

    def execute(db, job):
        db.add(Counter(key="saved-source-checkpoint", value=1))
        db.commit()
        raise busy()

    monkeypatch.setattr(jobs, "execute_job", execute)
    assert jobs.run_once()
    with Session() as db:
        row = db.get(Job, ident)
        assert row.state == "queued" and row.attempts == 0 and row.lease_until is None
        assert row.result["_performance"]["last"]["wait_reason"] == "database_busy"
        assert db.get(Counter, "saved-source-checkpoint").value == 1


def test_busy_completion_write_is_recoverable_and_does_not_erase_saved_source(client, monkeypatch):
    with Session() as db:
        ident = jobs.enqueue(db, "fixture", {}, "contention-completion").id

    def execute(db, job):
        db.add(Counter(key="committed-source", value=1))
        db.commit()
        return {"saved": True}

    monkeypatch.setattr(jobs, "execute_job", execute)
    original = Session.class_.commit
    rejected = []

    def conflict(db):
        if not rejected and any(
            isinstance(row, Job) and row.id == ident and row.state == "done"
            for row in db.identity_map.values()
        ):
            rejected.append(True)
            raise busy()
        return original(db)

    monkeypatch.setattr(Session.class_, "commit", conflict)
    assert jobs.run_once()
    with Session() as db:
        row = db.get(Job, ident)
        assert rejected and row.state == "queued" and row.attempts == 0 and row.lease_until is None
        assert row.result["_performance"]["last"]["wait_reason"] == "database_busy"
        assert db.get(Counter, "committed-source").value == 1


def test_busy_api_returns_retry_hint_without_sql_parameters(client, auth, monkeypatch):
    def blocked(*args, **kwargs):
        raise busy()

    monkeypatch.setattr(auth_module, "increment_bounded", blocked)
    response = client.get("/api/me", headers=auth)
    assert response.status_code == 503 and response.headers["Retry-After"] == "2"
    assert "private fixture SQL" not in response.text
    assert "retry" in response.json()["detail"].lower()
