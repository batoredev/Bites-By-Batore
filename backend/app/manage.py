"""Administrative CLI. No network calls or publication by default."""

import argparse
import json
from datetime import datetime, timezone
from sqlalchemy import select
from .config import ROOT, settings
from .db import migrate, Session, Venue, Claim, Job, Counter
from .seed import seed_demo


def main():
    parser = argparse.ArgumentParser(description="Batore database and launch operations")
    parser.add_argument("command", choices=["migrate", "seed-demo", "status", "backup-demo"])
    args = parser.parse_args()
    if args.command == "migrate":
        migrate()
        print("Schema version 5 ready. PostgreSQL tables have RLS enabled; access is through the API.")
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
        from .db import engine

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
