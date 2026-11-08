"""Read-only SQL integrity and schema exports; database health is not venue truth."""

from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import sqlite, postgresql
from .db import Base, SCHEMA_VERSION, operational_indexes, now


RELATIONS = [
    ("research_sources", "case_id", "investigations", "id"),
    ("research_tasks", "case_id", "investigations", "id"),
    ("investigations", "user_id", "users", "id"),
    ("identified_spots", "user_id", "users", "id"),
    ("identified_spots", "venue_id", "venues", "id"),
    ("claims", "venue_id", "venues", "id"),
    ("research_corrections", "source_id", "research_sources", "id"),
    ("research_corrections", "user_id", "users", "id"),
    ("source_assessments", "source_id", "research_sources", "id"),
    ("plans", "user_id", "users", "id"),
    ("visits", "user_id", "users", "id"),
    ("submissions", "user_id", "users", "id"),
    ("saved_venues", "user_id", "users", "id"),
    ("saved_venues", "venue_id", "venues", "id"),
    ("demo_sessions", "user_id", "users", "id"),
    ("dish_entries", "user_id", "users", "id"),
    ("dish_entries", "venue_id", "venues", "id"),
]


def audit_database(engine):
    with engine.connect() as c:
        inspector = inspect(c)
        tables = set(inspector.get_table_names())
        expected = set(Base.metadata.tables)
        missing = sorted(expected - tables)
        version = (
            c.execute(text("SELECT value FROM counters WHERE key='schema_version'")).scalar()
            if "counters" in tables
            else None
        )
        indexes = {i["name"] for t in tables for i in inspector.get_indexes(t)}
        missing_indexes = sorted(i.name for i in operational_indexes() if i.name not in indexes)
        orphans = {}
        for child, column, parent, key in RELATIONS:
            if {child, parent} <= tables:
                count = c.execute(
                    text(
                        f'SELECT COUNT(*) FROM "{child}" c LEFT JOIN "{parent}" p ON c."{column}"=p."{key}" WHERE c."{column}" IS NOT NULL AND c."{column}" <> \'\' AND p."{key}" IS NULL'
                    )
                ).scalar()
                if count:
                    orphans[f"{child}.{column}->{parent}.{key}"] = count
        duplicates = {}
        for table, columns in [
            ("research_sources", "case_id,canonical_url"),
            ("research_tasks", "case_id,ordinal"),
            ("identified_spots", "identity_key"),
            ("visits", "user_id,venue_id,visited_on"),
            ("dish_entries", "user_id,venue_id,offering_key"),
        ]:
            if table in tables:
                count = c.execute(
                    text(
                        f'SELECT COUNT(*) FROM (SELECT {columns} FROM "{table}" GROUP BY {columns} HAVING COUNT(*)>1) d'
                    )
                ).scalar()
                if count:
                    duplicates[table] = count
        integrity, fk_violations, journal, rls = None, [], None, None
        if engine.dialect.name == "sqlite":
            integrity = [r[0] for r in c.exec_driver_sql("PRAGMA quick_check")]
            fk_violations = [list(r) for r in c.exec_driver_sql("PRAGMA foreign_key_check")]
            journal = c.exec_driver_sql("PRAGMA journal_mode").scalar()
        elif engine.dialect.name == "postgresql":
            rls = {
                row[0]: row[1]
                for row in c.execute(
                    text(
                        "SELECT relname,relrowsecurity FROM pg_class JOIN pg_namespace n ON n.oid=relnamespace WHERE n.nspname=current_schema() AND relkind='r'"
                    )
                )
            }
        healthy = version == SCHEMA_VERSION and not (
            missing or missing_indexes or orphans or duplicates or fk_violations
        )
        healthy = (
            healthy and (integrity in (None, ["ok"])) and (rls is None or all(rls.get(t) for t in expected))
        )
        return {
            "at": now(),
            "dialect": engine.dialect.name,
            "schema_version": version,
            "expected_schema_version": SCHEMA_VERSION,
            "healthy": healthy,
            "missing_tables": missing,
            "missing_indexes": missing_indexes,
            "orphan_relationships": orphans,
            "duplicate_groups": duplicates,
            "integrity": integrity,
            "foreign_key_violations": fk_violations,
            "declared_foreign_keys": sum(len(inspector.get_foreign_keys(t)) for t in tables),
            "journal_mode": journal,
            "row_level_security": rls,
            "table_counts": {
                t: c.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() for t in sorted(tables & expected)
            },
            "boundary": "Read-only structural audit. Application-managed relationships are audited, not all enforced by SQL foreign keys. No venue fact or model accuracy is verified.",
        }


def schema_sql(kind):
    dialect = {"sqlite": sqlite.dialect, "postgresql": postgresql.dialect}[kind]()
    operational_indexes()
    parts = [
        "-- Generated empty-database schema, not an upgrade or private-data dump.",
        "-- Use python -m app.manage migrate for existing databases.",
        "BEGIN;",
    ]
    for table in Base.metadata.sorted_tables:
        parts.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
    for table in Base.metadata.sorted_tables:
        for index in sorted(table.indexes, key=lambda i: i.name):
            parts.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
        if kind == "postgresql":
            parts.append(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY;')
    parts.append(f"INSERT INTO counters (key,value) VALUES ('schema_version',{SCHEMA_VERSION});")
    parts.append(
        f"INSERT INTO schema_migrations (version,description,applied_at) VALUES ({SCHEMA_VERSION},'Generated empty-database schema',CURRENT_TIMESTAMP);"
    )
    parts.append("COMMIT;")
    return "\n\n".join(parts) + "\n"
