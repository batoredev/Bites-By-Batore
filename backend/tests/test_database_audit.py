import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.db import make_engine, migrate, SCHEMA_VERSION
from app.database_audit import audit_database, schema_sql


@pytest.fixture
def database(tmp_path):
    e = make_engine("sqlite:///" + str(tmp_path / "isolated.db"))
    yield e
    e.dispose()


def test_migration_is_idempotent_and_structural_audit_is_clean(database):
    migrate(database)
    migrate(database)
    result = audit_database(database)
    assert result["healthy"] and result["integrity"] == ["ok"]
    assert result["schema_version"] == SCHEMA_VERSION
    assert result["table_counts"]["schema_migrations"] == SCHEMA_VERSION - 4


def test_simultaneous_startup_serializes_migrations(database):
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: migrate(database), range(2)))
    assert audit_database(database)["healthy"]


def test_forward_database_is_not_downgraded(database):
    migrate(database)
    with database.begin() as c:
        c.execute(text("UPDATE counters SET value=999 WHERE key='schema_version'"))
    with pytest.raises(RuntimeError, match="newer"):
        migrate(database)
    assert audit_database(database)["schema_version"] == 999


def test_upgrade_preserves_rows_and_enforces_source_identity(database):
    migrate(database)
    with database.begin() as c:
        c.execute(text("DROP INDEX uq_source_case_url"))
        c.execute(text("DROP TABLE schema_migrations"))
        c.execute(text("UPDATE counters SET value=5 WHERE key='schema_version'"))
        c.execute(
            text(
                "INSERT INTO research_sources VALUES ('a','case','https://fixture.example/one','web','','{}','{}','lead','2026-11-07')"
            )
        )
    migrate(database)
    with database.connect() as c:
        assert c.execute(text("SELECT count(*) FROM research_sources")).scalar() == 1
    with pytest.raises(IntegrityError):
        with database.begin() as c:
            c.execute(
                text(
                    "INSERT INTO research_sources VALUES ('b','case','https://fixture.example/one','web','','{}','{}','lead','2026-11-07')"
                )
            )


def test_existing_duplicate_blocks_upgrade_without_deleting_evidence(database):
    migrate(database)
    with database.begin() as c:
        c.execute(text("DROP INDEX uq_source_case_url"))
        c.execute(text("UPDATE counters SET value=5 WHERE key='schema_version'"))
        for identifier in ["a", "b"]:
            c.execute(
                text(
                    "INSERT INTO research_sources VALUES (:id,'case','https://fixture.example/one','web','','{}','{}','lead','2026-11-07')"
                ),
                {"id": identifier},
            )
    with pytest.raises(IntegrityError):
        migrate(database)
    result = audit_database(database)
    assert result["schema_version"] == 5 and result["table_counts"]["research_sources"] == 2
    assert result["duplicate_groups"]["research_sources"] == 1
    assert result["orphan_relationships"]["research_sources.case_id->investigations.id"] == 2
    assert not result["healthy"]


def test_generated_sql_is_executable_empty_schema_and_postgres_has_rls(tmp_path):
    path = tmp_path / "from-sql.db"
    con = sqlite3.connect(path)
    con.executescript(schema_sql("sqlite"))
    con.close()
    e = make_engine("sqlite:///" + str(path))
    assert audit_database(e)["healthy"]
    e.dispose()
    sql = schema_sql("postgresql")
    assert "ENABLE ROW LEVEL SECURITY" in sql and "uq_source_case_url" in sql
    assert "INSERT INTO research_sources" not in sql


def test_live_startup_uses_current_schema_version(client, monkeypatch):
    import asyncio
    from app.main import app, lifespan
    from app.config import settings
    from app.db import Session, Counter

    cfg = settings()
    monkeypatch.setattr(cfg, "app_mode", "live")
    monkeypatch.setattr(cfg, "supabase_url", "https://fixture.example")
    monkeypatch.setattr(cfg, "supabase_publishable_key", "fixture-placeholder")
    monkeypatch.setattr(cfg, "database_url", "postgresql://fixture-only")

    # Existing engine stays the isolated test SQLite database; no external calls.
    async def start():
        async with lifespan(app):
            pass

    asyncio.run(start())
    with Session() as db:
        db.get(Counter, "schema_version").value = SCHEMA_VERSION - 1
        db.commit()
    with pytest.raises(RuntimeError, match="migration"):
        asyncio.run(start())


def test_schema6_visit_rows_upgrade_without_losing_history(database):
    migrate(database)
    with database.begin() as c:
        c.execute(text("ALTER TABLE visits DROP COLUMN experience"))
        c.execute(text("UPDATE counters SET value=6 WHERE key='schema_version'"))
        c.execute(
            text(
                "INSERT INTO visits (id,user_id,venue_id,rating,dimensions,note,occasion,visited_on,created_at) VALUES ('old','owner','venue',4,'{}','preserve this note','friends','2026-11-06','2026-11-06')"
            )
        )
    migrate(database)
    with database.connect() as c:
        row = c.execute(text("SELECT note,experience FROM visits WHERE id='old'")).one()
        assert row[0] == "preserve this note" and row[1] == "{}"
