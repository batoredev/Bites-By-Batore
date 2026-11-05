from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy import select
from .auth import current_user, admin_user, is_admin
from .config import settings
from .db import get_db, Investigation, ResearchTask, ResearchSource, Submission, Venue, Audit, Job, now
from .providers import increment_bounded
from .social import canonical_url
from .research import start_case, public_case, verification_stage
from .schemas import VenueInput
from .db import SourceAssessment
from .research import creator_assessment, creator_key
from .analysts import evidence_fingerprint

router = APIRouter(prefix="/api")


class AssessmentInput(BaseModel):
    outcome: Literal["supported", "refuted", "outdated", "unresolved"]
    reason: str = Field(min_length=15, max_length=1000)
    evidence_url: str = Field(pattern=r"^https://", max_length=2000)


class ConclusionInput(BaseModel):
    decision: Literal["use_verified_venues", "insufficient_evidence"]
    reason: str = Field(min_length=20, max_length=1500)


@router.post("/admin/investigations/{case_id}/conclude")
def conclude(case_id: str, data: ConclusionInput, user=Depends(admin_user), db=Depends(get_db)):
    case = own_case(db, case_id, user)
    if case.state not in {
        "review",
        "complete",
        "unavailable",
        "complete_with_limits",
        "insufficient_evidence",
    }:
        raise HTTPException(409, "Wait for specialist processing before concluding the review")
    verification_stage(db, case, None)
    if data.decision == "use_verified_venues" and not case.result.get("eligible_venue_ids"):
        raise HTTPException(
            409, "No independently verified eligible venue exists; obtain essential evidence first"
        )
    case.state = "complete_with_limits" if data.decision == "use_verified_venues" else "insufficient_evidence"
    case.result = {
        **case.result,
        "human_conclusion": {**data.model_dump(), "reviewed_at": now(), "reviewed_by": user.id},
        "publication_note": "The conclusion does not accept unverified claims; outstanding limitations are retained",
    }
    case.updated_at = now()
    db.add(Audit(actor=user.id, action="investigation.concluded", target=case.id, detail=data.model_dump()))
    db.commit()
    return public_case(db, case)


@router.post("/admin/research-sources/{source_id}/assess")
def assess_source(source_id: str, data: AssessmentInput, user=Depends(admin_user), db=Depends(get_db)):
    source = db.get(ResearchSource, source_id)
    if not source or not source.creator:
        raise HTTPException(422, "A retrieved creator identity is required before recording creator history")
    identity = creator_key(source)
    group = (
        source.content.get("content_fingerprint")
        or evidence_fingerprint(source.content)
        or source.canonical_url
    )
    db.add(
        SourceAssessment(
            source_id=source.id,
            creator_identity=identity,
            evidence_group=group,
            actor=user.id,
            **data.model_dump(),
        )
    )
    db.add(Audit(actor=user.id, action="source.assessed", target=source.id, detail=data.model_dump()))
    db.commit()
    return creator_assessment(db, identity)


class ResearchInput(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    url: str = Field(default="", max_length=2000)
    submission_id: str = Field(default="", max_length=100)


class ResolutionInput(BaseModel):
    venue_id: str = Field(default="", max_length=100)
    venue: VenueInput | None = None
    reason: str = Field(min_length=15, max_length=1000)
    evidence_url: str = Field(min_length=10, max_length=2000)


def own_case(db, case_id, user):
    case = db.get(Investigation, case_id)
    if not case or (case.user_id != user.id and not is_admin(user)):
        raise HTTPException(404, "Investigation not found")
    return case


@router.post("/investigations")
def create(data: ResearchInput, user=Depends(current_user), db=Depends(get_db)):
    context = {}
    if data.url:
        try:
            context["url"] = canonical_url(data.url)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    if data.submission_id:
        sub = db.get(Submission, data.submission_id)
        if not sub or sub.user_id != user.id:
            raise HTTPException(404, "Submission not found")
        context["submission_id"] = sub.id
    existing = db.scalar(
        select(Investigation).where(
            Investigation.user_id == user.id,
            Investigation.query == data.query,
            Investigation.state.in_(["queued", "running"]),
        )
    )
    if existing and existing.context == context:
        return public_case(db, existing)
    date = datetime.now(timezone.utc).date().isoformat()
    if not increment_bounded(db, f"research:{user.id}:{date}", settings().research_daily_limit):
        raise HTTPException(
            429, "Daily investigation allowance reached; existing investigations remain available"
        )
    return public_case(db, start_case(db, user.id, data.query, context))


@router.get("/investigations")
def listing(user=Depends(current_user), db=Depends(get_db)):
    return [
        public_case(db, c)
        for c in db.scalars(
            select(Investigation)
            .where(Investigation.user_id == user.id)
            .order_by(Investigation.created_at.desc())
            .limit(30)
        )
    ]


@router.get("/investigations/{case_id}")
def detail(case_id: str, user=Depends(current_user), db=Depends(get_db)):
    # Private users always own their investigations, including local demo admins.
    case = db.get(Investigation, case_id)
    if not case or case.user_id != user.id:
        raise HTTPException(404, "Investigation not found")
    return public_case(db, case)


@router.post("/investigations/{case_id}/cancel")
def cancel(case_id: str, user=Depends(current_user), db=Depends(get_db)):
    case = db.get(Investigation, case_id)
    if not case or case.user_id != user.id:
        raise HTTPException(404, "Investigation not found")
    case.state, case.updated_at = "cancelled", now()
    for job in db.scalars(select(Job).where(Job.kind == "investigation", Job.state == "queued")):
        if job.payload.get("case_id") == case.id:
            job.state = "cancelled"
    for source in db.scalars(select(ResearchSource).where(ResearchSource.case_id == case.id)):
        source.content = {
            k: v
            for k, v in source.content.items()
            if k not in {"media", "media_url", "video_url", "audio_url"}
        }
    db.commit()
    return public_case(db, case)


@router.post("/investigations/{case_id}/retry")
def retry(case_id: str, user=Depends(current_user), db=Depends(get_db)):
    from .jobs import enqueue

    case = db.get(Investigation, case_id)
    if not case or case.user_id != user.id:
        raise HTTPException(404, "Investigation not found")
    if case.state != "failed":
        raise HTTPException(
            409, "Only a failed investigation can resume; create a new investigation for fresh evidence"
        )
    task = db.scalar(
        select(ResearchTask)
        .where(ResearchTask.case_id == case.id, ResearchTask.state != "done")
        .order_by(ResearchTask.ordinal)
    )
    if not task:
        raise HTTPException(409, "No failed task to retry")
    key = f"case:{case.id}:{task.ordinal}"
    job = db.scalar(select(Job).where(Job.key == key))
    if job:
        job.state, job.attempts, job.due_at, job.error = "queued", 0, now(), ""
    case.state, task.state, task.error = "queued", "pending", ""
    db.commit()
    if not job:
        enqueue(db, "investigation", {"case_id": case.id}, key, priority=90)
    return public_case(db, case)


@router.get("/admin/investigations")
def review_cases(user=Depends(admin_user), db=Depends(get_db)):
    return [
        public_case(db, c)
        for c in db.scalars(select(Investigation).order_by(Investigation.created_at.desc()).limit(50))
    ]


@router.post("/admin/research-sources/{source_id}/resolve")
def resolve(source_id: str, data: ResolutionInput, user=Depends(admin_user), db=Depends(get_db)):
    from urllib.parse import urlparse

    source = db.get(ResearchSource, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    case = own_case(db, source.case_id, user)
    if case.state not in {"review", "complete", "unavailable"}:
        raise HTTPException(409, "Wait for investigation processing before resolving its evidence")
    parsed = urlparse(data.evidence_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(422, "Provide an HTTPS link to the independent branch evidence")
    if bool(data.venue_id) == bool(data.venue):
        raise HTTPException(422, "Choose an existing venue or supply a new venue, not both")
    if data.venue_id:
        venue = db.get(Venue, data.venue_id)
        if not venue or venue.is_demo != (settings().app_mode == "demo"):
            raise HTTPException(404, "Venue not found in this environment")
    else:
        from .planner import km

        if km((data.venue.lat, data.venue.lng), (11.0168, 76.9558)) > 40:
            raise HTTPException(
                422, "The current inventory covers Coimbatore; confirm coordinates within the launch area"
            )
        venue = Venue(
            **data.venue.model_dump(exclude={"details"}),
            details={"branch_confirmed": True},
            is_demo=settings().app_mode == "demo",
            status="pending",
        )
        db.add(venue)
        db.flush()
    venue.details = {**venue.details, "branch_confirmed": True}
    venue.revision += 1
    source.analysis = {
        **source.analysis,
        "human_resolution": {
            "venue_id": venue.id,
            "reason": data.reason,
            "evidence_url": data.evidence_url,
            "reviewed_at": now(),
            "reviewed_by": user.id,
        },
    }
    db.add(
        Audit(
            actor=user.id,
            action="research.branch_confirmed",
            target=source.id,
            detail={"venue_id": venue.id, "reason": data.reason, "evidence_url": data.evidence_url},
        )
    )
    db.flush()
    verification_stage(db, case, None)
    db.commit()
    return public_case(db, case)


@router.post("/admin/investigations/{case_id}/recheck")
def recheck(case_id: str, user=Depends(admin_user), db=Depends(get_db)):
    case = own_case(db, case_id, user)
    if case.state not in {"review", "complete", "unavailable"}:
        raise HTTPException(409, "Wait for the investigation to finish")
    verification_stage(db, case, None)
    case.updated_at = now()
    db.commit()
    return public_case(db, case)
