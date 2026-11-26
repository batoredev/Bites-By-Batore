"""PostgreSQL rehearsal (week 1, item 1.10).

Proves the app's data and planner work on PostgreSQL before production uses it:

1. Takes a consistent snapshot of the local SQLite database (the worker keeps running).
2. Creates the schema in a local PostgreSQL rehearsal database with the app's own
   migration, then copies every table into it.
3. Checks every table has the same row count and the same content checksum.
4. Runs the database health audit on PostgreSQL.
5. Runs the same planner requests against both databases and compares the plans.

Writes data/postgres-rehearsal-report.json. Never writes to the live SQLite database.
The PostgreSQL server is the private local one from scripts/pg_local.ps1.

Usage (from backend/):
    .\\.venv\\Scripts\\python.exe ..\\scripts\\pg_rehearsal.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app import db as appdb  # noqa: E402
from app.database_audit import audit_database  # noqa: E402
from app.db import Base, Claim, Venue, make_engine, migrate  # noqa: E402
from app.planner import build_plans, demo_leg, live_candidate_order  # noqa: E402
from app.schemas import OutingRequest  # noqa: E402

DATA = ROOT / "data"
SNAPSHOT = DATA / "postgres-rehearsal-source.db"
REPORT = DATA / "postgres-rehearsal-report.json"
DB_NAME = "batore_rehearsal"
BATCH = 500
DEPARTURE = "2026-11-28T18:30:00+05:30"

# Varied requests covering the planner's main paths.
REQUESTS = [
    {"query": "Something different"},
    {"query": "biryani then a movie", "categories": ["food", "cinema"], "party_size": 4, "budget": 2400},
    {"query": "veg dinner and dessert", "categories": ["food", "dessert"], "vegetarian": True},
    {"query": "cafe and board games", "categories": ["cafe", "gaming"], "mood": "quiet"},
    {"query": "kids day out", "categories": ["park", "amusement", "food"], "children": True, "party_size": 5},
    {"query": "wheelchair friendly evening", "categories": ["food", "cinema", "cafe"], "wheelchair": True},
    {"query": "cheap street food", "categories": ["street_food", "dessert"], "budget": 300, "party_size": 2},
    {"query": "per person budget bowling", "categories": ["bowling", "food"], "budget": 600, "budget_unit": "person"},
    {"query": "four stops long outing", "categories": ["food", "cafe", "gaming", "dessert"], "max_stops": 4, "duration_minutes": 360},
    {"query": "late night drinks", "categories": ["nightlife", "food"], "departure": "2026-11-28T22:30:00+05:30"},
    {"query": "adventure with friends", "categories": ["adventure", "sports", "food"], "mood": "active", "party_size": 6},
    {"query": "new place to try", "categories": ["food", "cafe"], "novelty": "new_place", "transport": "bike"},
]


def log(message: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {message}", file=sys.stderr, flush=True)


def pg_url(database: str) -> str:
    if os.environ.get("REHEARSAL_PG_URL"):
        return os.environ["REHEARSAL_PG_URL"].rsplit("/", 1)[0] + "/" + database
    password = (DATA / "postgres-password.txt").read_text(encoding="ascii").strip()
    return f"postgresql+psycopg://batore:{password}@127.0.0.1:5433/{database}"


def ensure_database() -> None:
    admin = make_engine(pg_url("postgres")).execution_options(isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        if not c.execute(text("SELECT 1 FROM pg_database WHERE datname=:n"), {"n": DB_NAME}).scalar():
            c.execute(text(f"CREATE DATABASE \"{DB_NAME}\" ENCODING 'UTF8' TEMPLATE template0"))
    admin.dispose()


def snapshot_sqlite() -> Path:
    live = Path(appdb.engine.url.database)
    SNAPSHOT.unlink(missing_ok=True)
    source = sqlite3.connect(f"file:{live}?mode=ro", uri=True, timeout=60)
    target = sqlite3.connect(SNAPSHOT)
    with target:
        source.backup(target)
    source.close()
    target.close()
    return live


def is_text(column) -> bool:
    try:
        return column.type.python_type is str
    except NotImplementedError:
        return False


def clean(value, fixes: dict, where: str):
    """PostgreSQL text cannot hold NUL characters; SQLite can. Strip them and count."""
    if isinstance(value, str) and "\x00" in value:
        fixes[where] = fixes.get(where, 0) + 1
        return value.replace("\x00", "")
    return value


def copy_tables(src, dst) -> dict:
    tables = Base.metadata.sorted_tables
    with dst.begin() as c:
        c.execute(text("TRUNCATE " + ", ".join(f'"{t.name}"' for t in tables) + " CASCADE"))
    fixes, seconds = {}, {}
    for table in tables:
        started = time.perf_counter()
        text_cols = {col.name for col in table.columns if is_text(col)}
        with src.connect() as s, dst.begin() as d:
            batch = []
            for row in s.execute(select(table)).mappings():
                batch.append(
                    {k: clean(v, fixes, f"{table.name}.{k}") if k in text_cols else v for k, v in row.items()}
                )
                if len(batch) >= BATCH:
                    d.execute(table.insert(), batch)
                    batch = []
            if batch:
                d.execute(table.insert(), batch)
        seconds[table.name] = round(time.perf_counter() - started, 2)
        log(f"copied {table.name} in {seconds[table.name]}s")
    return {"nul_characters_removed": fixes, "copy_seconds": seconds}


def table_fingerprint(engine, table) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    with engine.connect() as c:
        for row in c.execute(select(table).order_by(*table.primary_key.columns)).mappings():
            row = {k: (v.replace("\x00", "") if isinstance(v, str) else v) for k, v in row.items()}
            digest.update(json.dumps(row, sort_keys=True, default=str).encode())
            count += 1
    return count, digest.hexdigest()


def compare(src, dst) -> dict:
    result = {}
    for table in Base.metadata.sorted_tables:
        a, b = table_fingerprint(src, table), table_fingerprint(dst, table)
        log(f"compared {table.name}: {a[0]} rows, same={a == b}")
        result[table.name] = {"sqlite_rows": a[0], "postgres_rows": b[0], "same_content": a == b}
    return result


def run_plans(engine, ordered: bool) -> list[dict]:
    """The local-mode planning path from main.py, against one database."""
    out = []
    with Session(engine) as db:
        query = select(Venue).where(Venue.is_demo.is_(False), Venue.status == "published")
        rows_all = list(db.scalars(query.order_by(Venue.id) if ordered else query))
        ids = [v.id for v in rows_all]
        claim_query = select(Claim).where(Claim.venue_id.in_(ids))
        claims = list(db.scalars(claim_query.order_by(Claim.id) if ordered else claim_query)) if ids else []
        for spec in REQUESTS:
            data = OutingRequest(**{"departure": DEPARTURE, **spec})
            started = time.perf_counter()
            taken, rows = {}, []
            for v in live_candidate_order(data, rows_all, claims):
                if taken.get(v.category, 0) < 6 and len(rows) < 40:
                    taken[v.category] = taken.get(v.category, 0) + 1
                    rows.append(v)

            def route(a, b, origin, destination, data=data):
                return demo_leg(origin, destination, data.transport, data.party_size)

            result = build_plans(data, rows, claims, {}, set(), route)
            options = result.get("options", []) if isinstance(result, dict) else result
            log(f"{engine.dialect.name} ordered={ordered} '{spec['query']}': "
                f"{len(options)} plans in {round((time.perf_counter() - started) * 1000)} ms")
            out.append(
                {
                    "query": spec["query"],
                    "plans": len(options),
                    "fingerprint": hashlib.sha256(
                        json.dumps(result, sort_keys=True, default=str).encode()
                    ).hexdigest(),
                    "ms": round((time.perf_counter() - started) * 1000),
                }
            )
    return out


def main() -> int:
    ensure_database()
    live = snapshot_sqlite()
    src = make_engine(f"sqlite:///{SNAPSHOT}")
    dst = make_engine(pg_url(DB_NAME))

    started = time.perf_counter()
    migrate(dst)
    copied = copy_tables(src, dst)
    copy_seconds = round(time.perf_counter() - started, 1)

    tables = compare(src, dst)
    audit = audit_database(dst)

    planner = {}
    for ordered in (True, False):
        a, b = run_plans(src, ordered), run_plans(dst, ordered)
        planner["ordered_by_id" if ordered else "as_app_queries_today"] = {
            "same_plans": sum(x["fingerprint"] == y["fingerprint"] for x, y in zip(a, b)),
            "requests": len(a),
            "differences": [x["query"] for x, y in zip(a, b) if x["fingerprint"] != y["fingerprint"]],
            "sqlite_ms": [x["ms"] for x in a],
            "postgres_ms": [y["ms"] for y in b],
            "plans_per_request": [y["plans"] for y in b],
        }

    report = {
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": live.name,
        "postgres": "local PostgreSQL 17, 127.0.0.1:5433, database " + DB_NAME,
        "copy_seconds_total": copy_seconds,
        "tables_same": sum(t["same_content"] for t in tables.values()),
        "tables_total": len(tables),
        "rows_total": sum(t["postgres_rows"] for t in tables.values()),
        "tables": tables,
        **copied,
        "audit": {
            k: audit[k]
            for k in ("healthy", "schema_version", "missing_tables", "missing_indexes",
                      "orphan_relationships", "duplicate_groups")
        },
        "row_level_security_on_all_tables": all((audit.get("row_level_security") or {}).values()),
        "planner": planner,
        "boundary": "Rehearsal on a copy. Proves storage and planner parity only; says nothing about venue accuracy.",
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary = {k: report[k] for k in ("tables_same", "tables_total", "rows_total", "copy_seconds_total")}
    summary["audit_healthy"] = report["audit"]["healthy"]
    summary["different_tables"] = [n for n, t in tables.items() if not t["same_content"]]
    summary["planner"] = {k: f'{v["same_plans"]}/{v["requests"]} same' for k, v in planner.items()}
    summary["nul_fixes"] = copied["nul_characters_removed"]
    print(json.dumps(summary, indent=2))
    src.dispose()
    dst.dispose()
    return 0 if report["tables_same"] == report["tables_total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
