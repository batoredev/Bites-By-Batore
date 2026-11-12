"""Field-level coverage and explicit pre-test-user release gates."""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from .auth import admin_user
from .config import settings, ROOT
from .db import get_db, Venue, Claim, Job, Counter, Audit, now

router = APIRouter(prefix="/api/admin")


@router.post("/city-collection/start")
def start_city_collection(user=Depends(admin_user), db=Depends(get_db)):
    from .city_collection import start_collection

    if settings().app_mode != "local" or not settings().city_directory_enabled:
        raise HTTPException(409, "Enable the local city collection profile first")
    return start_collection(db, user.id)


@router.get("/city-collection")
def city_collection_status(user=Depends(admin_user), db=Depends(get_db)):
    from .city_collection import coverage

    return coverage(db, user.id)


@router.post("/launch-leads")
def import_launch_leads(user=Depends(admin_user), db=Depends(get_db)):
    import json
    from .db import Investigation
    from .research import start_case

    pack = json.loads((ROOT / "resources" / "coimbatore-launch-leads.json").read_text(encoding="utf-8"))
    existing = {
        c.context.get("lead_id"): c
        for c in db.scalars(select(Investigation).where(Investigation.user_id == user.id))
    }
    imported = []
    for lead in pack["leads"]:
        if lead["id"] in existing:
            imported.append(existing[lead["id"]].id)
            continue
        case = start_case(
            db,
            user.id,
            lead["name"],
            {"curated_leads": True, "lead_id": lead["id"]},
            seed_sources=[
                {
                    "url": lead["url"],
                    "platform": "web",
                    "research_notes": lead["notes"],
                    "access": lead["access"],
                    "checked_on": pack["checked_on"],
                    "missing": lead["missing"],
                }
            ],
        )
        db.commit()
        imported.append(case.id)
    return {
        "investigation_ids": imported,
        "message": "Official-source leads imported for review; no venues were published",
    }


from .categories import CATEGORIES  # noqa: E402


def coverage_report(db):
    cfg = settings()
    venues = list(db.scalars(select(Venue).where(Venue.is_demo == (cfg.app_mode == "demo"))))
    claims = list(db.scalars(select(Claim).where(Claim.status == "accepted")))
    rows, categories = [], {}
    for v in venues:
        fields = {c.field: c.expires_at for c in claims if c.venue_id == v.id and c.expires_at > now()}
        missing = sorted({"price_per_person", "hours", "closed"} - set(fields))
        if not v.details.get("branch_confirmed"):
            missing.append("branch_confirmation")
        if not v.is_demo and not v.details.get("maps_identity", {}).get("confirmed_by"):
            missing.append("maps_name_confirmation")
        if not v.is_demo and not v.details.get("location_approval"):
            missing.append("operator_location_approval")
        rows.append(
            {
                "venue_id": v.id,
                "name": v.name,
                "area": v.area,
                "category": v.category,
                "status": v.status,
                "missing_critical": missing,
                "current_fields": fields,
                "eligible": v.status == "published" and not missing and not v.details.get("closed"),
            }
        )
    for category in CATEGORIES:
        selected = [r for r in rows if r["category"] == category]
        categories[category] = {"records": len(selected), "eligible": sum(r["eligible"] for r in selected)}
    failed = list(
        db.scalars(select(Job).where(Job.state == "failed").order_by(Job.created_at.desc()).limit(50))
    )
    stale_before = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    delayed = list(db.scalars(select(Job).where(Job.state == "queued", Job.due_at < stale_before)))
    heartbeat = db.get(Counter, "worker_heartbeat")
    age = int(datetime.now(timezone.utc).timestamp()) - heartbeat.value if heartbeat else None
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    reserve = db.get(Counter, f"budget-reserved:{month}")
    blockers = []
    if cfg.app_mode == "demo":
        blockers.append("Only fictional demo inventory is being assessed")
    if not any(r["eligible"] for r in rows):
        blockers.append("No eligible verified venues")
    if any(r["status"] == "published" and r["missing_critical"] for r in rows):
        blockers.append("Published venues have missing or expired critical facts")
    if age is None or age > 120:
        blockers.append("Worker heartbeat is missing or stale")
    if failed:
        blockers.append("Failed jobs need operator review")
    return {
        "venues": rows,
        "categories": categories,
        "uncovered_categories": [k for k, v in categories.items() if not v["eligible"]],
        "failed_jobs": [{"id": j.id, "kind": j.kind, "error": j.error} for j in failed],
        "delayed_jobs": len(delayed),
        "worker_age_seconds": age,
        "budget_reserved_inr": (reserve.value / 100) if reserve else 0,
        "monthly_budget_inr": cfg.monthly_budget_inr,
        "budget_note": "Reservations are configurable estimates, not provider invoices; hosting and external bills need separate monitoring",
        "release_stage": cfg.release_stage,
        "launch_blockers": blockers,
        "coverage_note": "Counts describe our inventory, not proof of exhaustive Coimbatore coverage",
    }


@router.get("/quality")
def quality(user=Depends(admin_user), db=Depends(get_db)):
    from .evaluation import report
    from .performance import owner_report

    return {
        **coverage_report(db),
        "evaluation": report(db, user.id),
        "performance": owner_report(db, user.id),
    }


class LaunchReview(BaseModel):
    reason: str = Field(min_length=30, max_length=2000)
    approve: bool
    coverage_checked: bool = False
    provider_smoke_tests_passed: bool = False
    backup_restore_passed: bool = False
    labelled_evaluation_passed: bool = False


@router.post("/launch-review")
def launch_review(data: LaunchReview, user=Depends(admin_user), db=Depends(get_db)):
    report = coverage_report(db)
    if settings().app_mode != "demo":
        from .evaluation import report as evaluation_report

        report["launch_blockers"].extend(evaluation_report(db, user.id)["blockers"])
    if data.approve and (
        report["launch_blockers"]
        or not all(
            [
                data.coverage_checked,
                data.provider_smoke_tests_passed,
                data.backup_restore_passed,
                data.labelled_evaluation_passed,
            ]
        )
    ):
        raise HTTPException(
            409,
            {
                "message": "Resolve data/operation gates and record all checks before inviting test users",
                "blockers": report["launch_blockers"],
            },
        )
    record = db.get(Counter, "launch_data_approved")
    if not record:
        record = Counter(key="launch_data_approved", value=0)
        db.add(record)
    record.value = int(data.approve)
    db.add(Audit(actor=user.id, action="launch.data_review", target="Coimbatore", detail=data.model_dump()))
    db.commit()
    return {
        "approved": data.approve,
        "next": "Release stage and invited user IDs must be configured separately",
    }
