from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from .auth import admin_user
from .db import get_db, ResearchCorrection, ResearchSource, Investigation, Counter, Audit
from .providers import Unavailable
from .research import public_case

router = APIRouter(prefix="/api/admin")


class CorrectionInput(BaseModel):
    role: Literal["caption", "comments", "video"]
    scope: str = Field(min_length=3, max_length=120)
    original: str = Field(min_length=2, max_length=1000)
    corrected: str = Field(min_length=2, max_length=1000)
    reason: str = Field(min_length=15, max_length=1000)


def correction_dict(row):
    return {
        key: getattr(row, key)
        for key in [
            "id",
            "source_id",
            "role",
            "scope",
            "original",
            "corrected",
            "reason",
            "active",
            "created_at",
        ]
    }


@router.post("/research-sources/{source_id}/corrections")
def correct(source_id: str, data: CorrectionInput, user=Depends(admin_user), db=Depends(get_db)):
    source = db.get(ResearchSource, source_id)
    case = db.get(Investigation, source.case_id) if source else None
    if not case or case.user_id != user.id:
        raise HTTPException(404, "Your research source was not found")
    row = ResearchCorrection(user_id=user.id, source_id=source.id, **data.model_dump())
    db.add(row)
    db.flush()
    db.add(Audit(actor=user.id, action="research.correction", target=row.id, detail={"source_id": source.id}))
    db.commit()
    return correction_dict(row)


@router.get("/research-corrections")
def corrections(user=Depends(admin_user), db=Depends(get_db)):
    return [
        correction_dict(r)
        for r in db.scalars(
            select(ResearchCorrection)
            .where(ResearchCorrection.user_id == user.id)
            .order_by(ResearchCorrection.created_at.desc())
        )
    ]


@router.delete("/research-corrections/{correction_id}")
def revoke(correction_id: str, user=Depends(admin_user), db=Depends(get_db)):
    row = db.get(ResearchCorrection, correction_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Correction not found")
    row.active = False
    db.add(Audit(actor=user.id, action="research.correction_revoked", target=row.id, detail={}))
    db.commit()
    return {"active": False}


@router.post("/research-next")
def research_next(user=Depends(admin_user), db=Depends(get_db)):
    from .frontier import start_next

    try:
        return public_case(db, start_next(db, user.id))
    except Unavailable as exc:
        raise HTTPException(409, str(exc)) from exc


class PauseInput(BaseModel):
    paused: bool


@router.post("/research-control")
def control(data: PauseInput, user=Depends(admin_user), db=Depends(get_db)):
    row = db.get(Counter, "research_paused") or Counter(key="research_paused")
    row.value = int(data.paused)
    db.add(row)
    db.commit()
    return {
        "paused": data.paused,
        "note": "Pauses new discovery; active investigations finish. Cancel a case separately to stop it.",
    }


@router.get("/research-runtime")
def runtime(user=Depends(admin_user), db=Depends(get_db)):
    import httpx
    from .config import settings
    from .local_models import endpoint

    cfg = settings()
    from .collection_control import daily_limits, bulk_enabled

    available, error = [], ""
    if cfg.app_mode == "local" or cfg.analysis_provider == "ollama":
        try:
            with httpx.Client(timeout=3, trust_env=False) as client:
                response = client.get(endpoint() + "/api/tags")
                response.raise_for_status()
                available = [m["name"] for m in response.json().get("models", [])]
        except (httpx.HTTPError, ValueError, KeyError, Unavailable):
            error = "Local model runtime unavailable"
    paused = db.get(Counter, "research_paused")
    return {
        "mode": cfg.app_mode,
        "model": cfg.ollama_model,
        "model_installed": cfg.ollama_model in available,
        "runtime_error": error,
        "paused": bool(paused and paused.value),
        "autonomous": cfg.autonomous_discovery,
        "public_search": cfg.local_search_enabled,
        "direct_browser": cfg.instagram_browser_enabled,
        "browser_daily_limit": daily_limits()["browser"],
        "bulk_collection": bulk_enabled(),
        "instagram_connector": cfg.instagram_provider,
        "learning": "Scoped human corrections retrieved into future investigations; no weight training",
        "source_limit": cfg.research_max_sources,
        "source_batch_size": cfg.research_max_sources,
        "selection_order": "Newest dated sources first; all discovered relevant sources retained",
        "daily_case_limit": daily_limits()["investigations"],
    }
