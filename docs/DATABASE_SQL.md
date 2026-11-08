# Local SQL database completion and operation

## Latest schema 7 — 7 November, 18:39 IST

Actual local DB is now **schema 7**. The schema-6 section below is historical. Added private `dish_entries`, `visits.experience` JSON snapshots, unique owner/venue/dish and owner/venue/date indexes. Export, erasure, memory clearing and audits include new records. No real fixture menus or approvals inserted.

`data/parity-migration-rehearsal.json` records two migrations on a restored backup, preserving existing counts. `data/parity-live-schema7.json` records two actual migrations with every pre-existing count preserved: 61 sources, 90 spot originals, zero venues/claims. Final snapshot `data/backups/parity-final-20261107T130916Z.db` restored separately to `parity-final-restore-20261107T130916Z.db` passed integrity/index/duplicate/orphan checks. Live DB was not replaced. Receipt `data/parity-final-status.json`.

Current empty-schema exports: [SQLite 7](../resources/sql/schema-v7-sqlite.sql), [PostgreSQL 7](../resources/sql/schema-v7-postgresql.sql). These create empty databases; existing databases use `python -m app.manage migrate`. PostgreSQL execution/RLS-role behavior remains unverified. See [shared features](FAVHIKER_DEEP_REVIEW.md) and newest [verification](VERIFICATION.md).

---

Updated 7 November 2026. The application already persisted real research in SQLite. SQLite is a SQL database; missing verified venue facts did not mean SQL storage was absent. The active database remains `data/local-research.db`, with local inference and storage. No cloud migration was performed.

## Work completed

- Schema version **6**, with a `schema_migrations` ledger. Version 5 is recorded as an adopted baseline, not a claim that its historical migration time is known.
- Serialized transactional migrations: SQLite `BEGIN IMMEDIATE`; PostgreSQL advisory transaction lock in the implementation. A newer schema is rejected instead of silently downgraded.
- Unique SQL indexes for `(case_id, canonical_url)` source identity and `(case_id, ordinal)` processing tasks. Repeated posts in different investigations remain separate records intentionally. Existing ambiguous spot branches remain review candidates rather than being arbitrarily merged.
- Composite indexes for job dispatch/recovery, owner/status spot access, current venue claims, owner/state investigations and owner/action audit records.
- Fixed the live startup check: it previously required version 4 although migration produced version 5. Startup now uses the shared schema-version constant.
- Read-only `db-check`: schema/index presence, integrity, row counts, duplicate groups and audited application relationships. PostgreSQL RLS inspection is included in code.
- Generated empty-database SQL for SQLite and PostgreSQL, with PostgreSQL backend-table RLS statements. These contain schema only, not private data or credentials.
- Browser/provider allowance reservation is now atomic: a blocked request cannot consume the other allowance. Historical counters were preserved; no unused historical visits were refunded or invented.

The current ORM uses application-managed relationships; it does **not** declare SQL foreign keys for every relationship. The audit reports that explicitly and detects orphaned references. Unique constraints and the audit are not a claim of universal SQL-level referential enforcement.

## Actual verification

Before upgrade: online snapshot `data/backups/batore-20261106T185613Z.db` (7 November in India).

1. Restored the snapshot to `data/backups/schema6-rehearsal-20261107.db`.
2. Migrated that isolated copy twice; the second run was idempotent.
3. Compared every pre-existing table's row count: all preserved.
4. Migrated the actual local research DB while API/worker were stopped.
5. Ran the read-only audit: schema 6, integrity `ok`, WAL mode, no missing tables/indexes, no detected duplicate groups or orphaned audited relationships.

Actual counts at upgrade: 83 identified-spot originals (49 active, 10 merged, 24 held), 51 sources, 12 investigations, 96 tasks, 228 jobs, one operator; zero accepted venue claims and zero venues. Drafts are deliberately not silently converted to accepted facts or published venues.

Receipts: `data/sql-migration-rehearsal-20261107.json`, `data/sql-live-audit-20261107.json`.

Tests cover fresh/repeated migrations, concurrent startup, future-version rejection, preserved rows, duplicate rejection with transactional rollback, orphan reporting and executing generated SQLite SQL. The PostgreSQL SQL is compiled and inspected in tests; **no running PostgreSQL server/RLS-role or production restore validation is claimed**. Docker CLI exists, but its engine was unavailable. Local mode remains SQLite as requested.

## Commands

From `backend/`:

```powershell
uv run python -m app.manage backup-demo
uv run python -m app.manage migrate
uv run python -m app.manage db-check
uv run python -m app.manage schema-sql --dialect sqlite
uv run python -m app.manage schema-sql --dialect postgresql
uv run python -m app.manage review-pack
```

`backup-demo` is the existing command name; it supports both local and demo SQLite. `db-check` returns a nonzero exit status for structural problems and never repairs or deletes evidence. `schema-sql` prints an empty schema, not an upgrade script. Use `migrate` for an existing database. If duplicate evidence prevents migration, retain the snapshot and resolve the conflicting records through review; do not delete rows to force success.

Prepared files: [SQLite schema](../resources/sql/schema-v6-sqlite.sql), [PostgreSQL schema](../resources/sql/schema-v6-postgresql.sql). Do not execute these empty-schema scripts against an existing research database.

## What SQL completion does not establish

Database integrity does not verify a Maps branch, price, opening hour, video interpretation or creator. Production PostgreSQL/Supabase deployment remains separate from the current local-only requirement. Stages 1/2/3/6 still require independent accuracy evidence, sufficient checked city coverage, explicit operator location approvals and sustained operation.
