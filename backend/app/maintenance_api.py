from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from .auth import admin_user
from .db import get_db, IdentifiedSpot, Audit, now
from .maintenance import maintenance_report, schedule_maintenance, approval_packet
from .config import settings

router = APIRouter(prefix="/api/admin/maintenance")


@router.get("")
def report(user=Depends(admin_user), db=Depends(get_db)):
    return maintenance_report(db, user.id)


@router.post("/schedule")
def schedule(user=Depends(admin_user), db=Depends(get_db)):
    if settings().app_mode == "demo":
        raise HTTPException(409, "Real-source maintenance is disabled in demo")
    from .db import Counter

    paused = db.get(Counter, "research_paused")
    if paused and paused.value:
        raise HTTPException(409, "Resume collection before scheduling source checks")
    ids = schedule_maintenance(db, user.id)
    return {"queued": len(ids), "job_ids": ids, "published": False}


@router.get("/packets/{spot_id}")
def packet(spot_id: str, user=Depends(admin_user), db=Depends(get_db)):
    row = db.get(IdentifiedSpot, spot_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Spot not found")
    return approval_packet(db, row)


class Resolution(BaseModel):
    checked_original: bool
    reason: str = Field(min_length=20, max_length=1000)
    evidence_url: str = Field(pattern=r"^https://", max_length=2000)


@router.post("/packets/{spot_id}/alerts/{alert_id}/resolve")
def resolve(spot_id: str, alert_id: str, data: Resolution, user=Depends(admin_user), db=Depends(get_db)):
    row = db.get(IdentifiedSpot, spot_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Spot not found")
    if not data.checked_original:
        raise HTTPException(422, "Inspect the source and review changed facts before resolving")
    alerts = [dict(a) for a in row.data.get("maintenance_alerts", [])]
    item = next((a for a in alerts if a["id"] == alert_id and a["state"] == "open"), None)
    if not item:
        raise HTTPException(404, "Open alert not found")
    item.update(state="reviewed", reviewed_by=user.id, reviewed_at=now(), **data.model_dump())
    row.data = {**row.data, "maintenance_alerts": alerts}
    db.add(
        Audit(
            actor=user.id,
            action="maintenance.alert_reviewed",
            target=row.id,
            detail={"alert_id": alert_id, "reason": data.reason},
        )
    )
    db.commit()
    return {
        "reviewed": True,
        "published": False,
        "message": "Alert reviewed. Essential fact acceptance and location approval remain separate.",
    }
