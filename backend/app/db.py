from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import JSON, Boolean, Float, Integer, String, Text, Index, create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import ROOT, settings


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return str(uuid4())


def is_database_busy(error):
    """Recognize SQLite lock contention through wrapped exceptions, without SQL text."""
    import sqlite3

    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        original = getattr(error, "orig", error)
        if isinstance(original, sqlite3.OperationalError):
            code = getattr(original, "sqlite_errorcode", 0) & 255
            if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) or str(original).lower() in {
                "database is locked",
                "database table is locked",
                "database schema is locked",
            }:
                return True
        error = getattr(error, "__cause__", None) or getattr(error, "__context__", None)
    return False


class Base(DeclarativeBase):
    pass


SCHEMA_VERSION = 7


class SchemaMigration(Base):
    __tablename__ = "schema_migrations"
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String)
    applied_at: Mapped[str] = mapped_column(String, default=now)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String, default="Explorer")
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String, default=now)


class SessionToken(Base):
    __tablename__ = "demo_sessions"
    token_hash: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    expires_at: Mapped[str] = mapped_column(String)


class Venue(Base):
    __tablename__ = "venues"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, index=True)
    area: Mapped[str] = mapped_column(String)
    address: Mapped[str] = mapped_column(String)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    venue_id: Mapped[str] = mapped_column(String, index=True)
    field: Mapped[str] = mapped_column(String)
    value: Mapped[dict] = mapped_column(JSON)
    source_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String)
    source_group: Mapped[str] = mapped_column(String)
    observed_at: Mapped[str] = mapped_column(String)
    fetched_at: Mapped[str] = mapped_column(String, default=now)
    expires_at: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    request: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String, default=now)


class SavedVenue(Base):
    __tablename__ = "saved_venues"
    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    venue_id: Mapped[str] = mapped_column(String, primary_key=True)


class Visit(Base):
    __tablename__ = "visits"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    venue_id: Mapped[str] = mapped_column(String)
    rating: Mapped[int] = mapped_column(Integer)
    dimensions: Mapped[dict] = mapped_column(JSON)
    note: Mapped[str] = mapped_column(Text, default="")
    occasion: Mapped[str] = mapped_column(String, default="casual")
    visited_on: Mapped[str] = mapped_column(String)
    experience: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String, default=now)


class DishEntry(Base):
    __tablename__ = "dish_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    venue_id: Mapped[str] = mapped_column(String, index=True)
    offering_key: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    note: Mapped[str] = mapped_column(Text, default="")
    tried_on: Mapped[str | None] = mapped_column(String, nullable=True)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    url: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="queued")
    created_at: Mapped[str] = mapped_column(String, default=now)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    key: Mapped[str] = mapped_column(String, unique=True)
    kind: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String, default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=20)
    due_at: Mapped[str] = mapped_column(String, default=now, index=True)
    lease_until: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String, default=now)
    completed_at: Mapped[str | None] = mapped_column(String, nullable=True)


class Audit(Base):
    __tablename__ = "audit"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Investigation(Base):
    __tablename__ = "investigations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    query: Mapped[str] = mapped_column(String)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String, default="queued", index=True)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[str] = mapped_column(String, default=now)
    updated_at: Mapped[str] = mapped_column(String, default=now)


class ResearchTask(Base):
    __tablename__ = "research_tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String)
    ordinal: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String, default="pending")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    completed_at: Mapped[str | None] = mapped_column(String, nullable=True)


class ResearchSource(Base):
    __tablename__ = "research_sources"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(String, index=True)
    canonical_url: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String)
    creator: Mapped[str] = mapped_column(String, default="")
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String, default="lead")
    created_at: Mapped[str] = mapped_column(String, default=now)


class SourceAssessment(Base):
    __tablename__ = "source_assessments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    source_id: Mapped[str] = mapped_column(String, index=True)
    creator_identity: Mapped[str] = mapped_column(String, index=True)
    evidence_group: Mapped[str] = mapped_column(String, index=True)
    outcome: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    evidence_url: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=now)


class ResearchCorrection(Base):
    __tablename__ = "research_corrections"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    source_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String)
    scope: Mapped[str] = mapped_column(String)
    original: Mapped[str] = mapped_column(Text)
    corrected: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String, default=now)


class Counter(Base):
    __tablename__ = "counters"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)


class IdentifiedSpot(Base):
    __tablename__ = "identified_spots"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    identity_key: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String, default="food")
    area: Mapped[str] = mapped_column(String, default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="identified", index=True)
    venue_id: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[str] = mapped_column(String, default=now)
    updated_at: Mapped[str] = mapped_column(String, default=now)


def make_engine(url):
    if url.startswith("sqlite:///./"):
        path = ROOT / url.removeprefix("sqlite:///./")
        path.parent.mkdir(parents=True, exist_ok=True)
        url = "sqlite:///" + str(path)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {},
        pool_pre_ping=True,
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def configure(connection, _):
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")

    return engine


engine = make_engine(settings().database_url)
Session = sessionmaker(engine, expire_on_commit=False)


def operational_indexes():
    specs = [
        ("uq_source_case_url", ResearchSource, ("case_id", "canonical_url"), True),
        ("uq_task_case_ordinal", ResearchTask, ("case_id", "ordinal"), True),
        ("ix_job_dispatch", Job, ("state", "priority", "due_at"), False),
        ("ix_job_recovery", Job, ("state", "lease_until"), False),
        ("ix_spot_owner_status", IdentifiedSpot, ("user_id", "status"), False),
        ("ix_claim_current", Claim, ("venue_id", "status", "expires_at"), False),
        ("ix_case_owner_state", Investigation, ("user_id", "state"), False),
        ("ix_audit_owner_action", Audit, ("actor", "action"), False),
        ("uq_dish_owner_venue_item", DishEntry, ("user_id", "venue_id", "offering_key"), True),
        ("uq_visit_owner_venue_date", Visit, ("user_id", "venue_id", "visited_on"), True),
    ]
    result = []
    for name, model, columns, unique in specs:
        existing = next((i for i in model.__table__.indexes if i.name == name), None)
        result.append(
            existing
            if existing is not None
            else Index(name, *(model.__table__.c[c] for c in columns), unique=unique)
        )
    return result


def migrate(target_engine=None):
    """Serialized, transactional additive migration; duplicates fail closed without deleting evidence."""
    target_engine = target_engine or engine
    with target_engine.connect() as connection:
        if target_engine.dialect.name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            connection.begin()
            if target_engine.dialect.name == "postgresql":
                connection.execute(text("SELECT pg_advisory_xact_lock(672806)"))
        try:
            existing = inspect(connection).get_table_names()
            version = (
                connection.execute(text("SELECT value FROM counters WHERE key='schema_version'")).scalar()
                if "counters" in existing
                else None
            )
            if version and version > SCHEMA_VERSION:
                raise RuntimeError("Database schema is newer than this application; refusing downgrade")
            if "jobs" in existing and "priority" not in {
                c["name"] for c in inspect(connection).get_columns("jobs")
            }:
                connection.execute(text("ALTER TABLE jobs ADD COLUMN priority INTEGER NOT NULL DEFAULT 20"))
            if "visits" in existing and "experience" not in {
                c["name"] for c in inspect(connection).get_columns("visits")
            }:
                connection.execute(
                    text("ALTER TABLE visits ADD COLUMN experience JSON NOT NULL DEFAULT '{}'")
                )
            Base.metadata.create_all(connection)
            for index in operational_indexes():
                index.create(connection, checkfirst=True)
            for number, description in [
                (5, "Existing application baseline; earlier migration timestamps unknown"),
                (6, "Serialized migrations and evidence/queue integrity indexes"),
                (7, "Private dish diary and reversible visit preference snapshots"),
            ]:
                if not connection.execute(
                    text("SELECT version FROM schema_migrations WHERE version=:v"), {"v": number}
                ).scalar():
                    connection.execute(
                        SchemaMigration.__table__.insert().values(
                            version=number, description=description, applied_at=now()
                        )
                    )
            if version is None:
                connection.execute(
                    Counter.__table__.insert().values(key="schema_version", value=SCHEMA_VERSION)
                )
            else:
                connection.execute(
                    Counter.__table__.update()
                    .where(Counter.key == "schema_version")
                    .values(value=SCHEMA_VERSION)
                )
            if target_engine.dialect.name == "postgresql":
                for table in Base.metadata.sorted_tables:
                    connection.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def get_db():
    with Session() as db:
        yield db
