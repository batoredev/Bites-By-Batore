"""Administrative CLI. No network calls or publication by default."""

import argparse
import json
from datetime import datetime, timezone
from sqlalchemy import select
from .config import ROOT, settings
from .db import migrate, Session, Venue, Claim, Job, Counter, SCHEMA_VERSION, engine
from .seed import seed_demo


def main():
    parser = argparse.ArgumentParser(description="Batore database and launch operations")
    parser.add_argument(
        "command",
        choices=[
            "migrate",
            "seed-demo",
            "status",
            "backup-demo",
            "check-spots",
            "clean-spots",
            "review-pack",
            "db-check",
            "schema-sql",
            "performance-report",
            "sync-inventory",
            "city-collection-start",
            "city-collection-report",
            "bulk-collection-resume",
            "duplicates-run",
            "retune-drafts",
            "test-inventory-publish",
            "test-inventory-revert",
            "geocode-drafts",
        ],
    )
    parser.add_argument("--user-id", default="local-operator")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dialect", choices=["sqlite", "postgresql"], default="sqlite")
    args = parser.parse_args()
    if args.command == "geocode-drafts":
        from .geocode import geocode_drafts

        if settings().app_mode != "local":
            raise SystemExit("Draft coordinate lookup is available only in local mode")
        from .geocode import coordinates_from_links

        with Session() as db:
            result = {"from_links": coordinates_from_links(db, args.user_id)}
            db.commit()
            if args.limit:
                # Optional public geocoder pass; low yield for Coimbatore, off by default.
                result["geocoder"] = geocode_drafts(db, args.user_id, args.limit)
            print(json.dumps(result, indent=2))
    elif args.command in {"retune-drafts", "test-inventory-publish", "test-inventory-revert"}:
        from . import test_inventory

        if settings().app_mode != "local":
            raise SystemExit("The agent-approved test inventory is available only in local mode")
        action = {
            "retune-drafts": test_inventory.retune_drafts,
            "test-inventory-publish": test_inventory.publish,
            "test-inventory-revert": test_inventory.revert,
        }[args.command]
        with Session() as db:
            result = action(db, args.user_id)
            db.commit()
            print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.command == "duplicates-run":
        from .duplicate_agent import request_scan

        if settings().app_mode not in {"local", "demo"}:
            raise SystemExit("Use the authenticated operator interface for hosted data")
        with Session() as db:
            job = request_scan(db, args.user_id, force=True)
            print(json.dumps({"job_id": job.id, "state": job.state}, indent=2))
    elif args.command == "bulk-collection-resume":
        from .collection_control import resume_bulk

        with Session() as db:
            print(json.dumps(resume_bulk(db, args.user_id), indent=2))
    elif args.command == "city-collection-start":
        from .city_collection import start_collection

        if settings().app_mode != "local" or not settings().city_directory_enabled:
            raise SystemExit("Enable the local city collection profile first")
        with Session() as db:
            print(json.dumps(start_collection(db, args.user_id), indent=2))
    elif args.command == "city-collection-report":
        from .city_collection import coverage

        with Session() as db:
            print(json.dumps(coverage(db, args.user_id), indent=2))
    elif args.command == "sync-inventory":
        from .spots import sync_inventory

        with Session() as db:
            print(json.dumps(sync_inventory(db, args.user_id), indent=2))
    elif args.command == "performance-report":
        from .performance import owner_report

        with Session() as db:
            print(json.dumps(owner_report(db, args.user_id), indent=2))
    elif args.command == "db-check":
        from .database_audit import audit_database

        result = audit_database(engine)
        print(json.dumps(result, indent=2))
        if not result["healthy"]:
            raise SystemExit(1)
    elif args.command == "schema-sql":
        from .database_audit import schema_sql

        print(schema_sql(args.dialect))
    elif args.command == "review-pack":
        from .maintenance import maintenance_report

        if settings().app_mode != "local":
            raise SystemExit("Private review-pack export is available only in local mode")
        with Session() as db:
            report = maintenance_report(db, args.user_id)
        folder = ROOT / "data" / "review-packs"
        folder.mkdir(parents=True, exist_ok=True)
        prefix = folder / datetime.now(timezone.utc).strftime("review-%Y%m%dT%H%M%SZ")
        prefix.with_suffix(".json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        def safe(value):
            return str(value).replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")

        lines = [
            "# Private Coimbatore location review pack",
            "",
            report["at"],
            "",
            f"{report['draft_count']} active candidates; {report['approved_count']} approved; {report['open_alerts']} open alerts.",
            "",
            "Collection is not verification. Review each exact branch, source evidence and current critical facts in the app, then explicitly approve that location.",
            "",
            "Open the app at http://127.0.0.1:8000. Data readiness contains source monitoring and evaluation; Identified spots contains Maps review/preparation; Venue desk contains fact acceptance and final approval.",
            "",
            report["coverage"],
            "",
        ]
        for p in report["packets"]:
            lines += [
                "## " + safe(p["name"]),
                "",
                f"ID: {p['id']}",
                "",
                f"Area: {safe(p['area'])}; category: {safe(p['category'])}; status: {p['status']}",
                "",
                "Maps lead: " + p["maps_url"],
                "",
                "Approval blockers:",
                "",
            ]
            lines += ["- " + safe(b) for b in p["blockers"]] or [
                "- Ready for your final decision; not automatically approved."
            ]
            lines += ["", "Sources:", ""]
            lines += [
                "- " + safe(s.get("url", "")) + " (" + safe(s.get("collected_at", "date unknown")) + ")"
                for s in p["sources"]
            ]
            for label, value in [
                ("Missing draft fields", p["missing"]),
                ("Conflicts", p["conflicts"]),
                ("Open alerts", p["alerts"]),
                ("Page observations (unverified)", p["page_checks"]),
                ("Fact evidence", p["fact_evidence"]),
            ]:
                lines += [
                    "",
                    label + ":",
                    "",
                    "```json",
                    json.dumps(value, indent=2, ensure_ascii=False),
                    "```",
                ]
            lines += [""]
        prefix.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
        print(
            json.dumps(
                {
                    "json": str(prefix.with_suffix(".json")),
                    "markdown": str(prefix.with_suffix(".md")),
                    "drafts": report["draft_count"],
                    "approved": report["approved_count"],
                },
                indent=2,
            )
        )
    elif args.command in {"check-spots", "clean-spots"}:
        from .spots import reconcile_spots

        if settings().app_mode not in {"local", "demo"}:
            raise SystemExit("Use the authenticated operator interface for a hosted inventory")
        with Session() as db:
            result = reconcile_spots(db, args.user_id)
            if args.command == "clean-spots":
                db.commit()
            else:
                db.rollback()
            print(json.dumps({"applied": args.command == "clean-spots", **result}, indent=2))
    elif args.command == "migrate":
        migrate()
        print(
            f"Schema version {SCHEMA_VERSION} ready; PostgreSQL backend tables use RLS. Run db-check for structural validation."
        )
    elif args.command == "seed-demo":
        if settings().app_mode != "demo":
            raise SystemExit("Demo seed is disabled in live mode")
        migrate()
        with Session() as db:
            seed_demo(db)
        print("Fictional demonstration venues ready")
    elif args.command == "status":
        with Session() as db:
            result = {
                "mode": settings().app_mode,
                "schema_version": db.get(Counter, "schema_version").value,
                "venues": len(list(db.scalars(select(Venue.id)))),
                "claims": len(list(db.scalars(select(Claim.id)))),
                "queued_jobs": len(list(db.scalars(select(Job.id).where(Job.state == "queued")))),
            }
            print(json.dumps(result, indent=2))
    elif args.command == "backup-demo":
        if settings().app_mode not in {"demo", "local"} or not settings().database_url.startswith("sqlite"):
            raise SystemExit("Use PostgreSQL backups for live databases; see docs/OPERATIONS.md")
        import sqlite3

        folder = ROOT / "data" / "backups"
        folder.mkdir(exist_ok=True, parents=True)
        target = folder / ("batore-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".db")
        source = sqlite3.connect(engine.url.database)
        destination = sqlite3.connect(target)
        with destination:
            source.backup(destination)
        destination.close()
        source.close()
        print("Consistent SQLite snapshot created:", target)


if __name__ == "__main__":
    main()
