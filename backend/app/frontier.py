"""Finite, rotating Coimbatore discovery, with durable cooldowns and feedback topics."""

from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from .config import settings
from .db import Investigation, ResearchCorrection, Counter
from .providers import increment_bounded, Unavailable
from .research import start_case

CATEGORIES = [
    "sushi restaurants",
    "cafes",
    "bowling gaming arcade",
    "go karting adventure",
    "parks",
    "cinema",
    "vegetarian restaurants",
    "South Indian breakfast restaurants",
    "biryani restaurants",
    "desserts bakeries ice cream",
    "street food snacks",
    "family restaurants",
]
AREAS = [
    "RS Puram",
    "Peelamedu",
    "Saibaba Colony",
    "Gandhipuram",
    "Race Course",
    "Saravanampatti",
    "Ukkadam",
    "Singanallur",
    "Thudiyalur",
    "Nava India",
    "Vadavalli",
    "Ganapathy",
    "Podanur",
    "Sundarapuram",
]


def next_query(db, user_id):
    topics = [f"Coimbatore {category} {area}" for area in AREAS for category in CATEGORIES]
    scopes = list(
        db.scalars(
            select(ResearchCorrection.scope)
            .where(ResearchCorrection.user_id == user_id, ResearchCorrection.active.is_(True))
            .distinct()
            .limit(20)
        )
    )
    topics = [f"Coimbatore {scope} food entertainment" for scope in scopes] + topics
    seen = {}
    for case in db.scalars(select(Investigation).where(Investigation.user_id == user_id)):
        seen[case.query] = max(seen.get(case.query, ""), case.created_at)
    return min(topics, key=lambda query: seen.get(query, ""))


def start_next(db, user_id, scheduled=False):
    if settings().app_mode == "demo":
        raise Unavailable("Autonomous real-source discovery is disabled in demo")
    paused = db.get(Counter, "research_paused")
    if paused and paused.value:
        raise Unavailable("Discovery is paused by the operator")
    active = db.scalar(
        select(Investigation)
        .where(Investigation.user_id == user_id, Investigation.state.in_(["queued", "running"]))
        .order_by(Investigation.created_at)
    )
    if active:
        return active
    last = db.scalar(
        select(Investigation)
        .where(Investigation.user_id == user_id)
        .order_by(Investigation.created_at.desc())
    )
    if (
        scheduled
        and last
        and datetime.fromisoformat(last.created_at) > datetime.now(timezone.utc) - timedelta(hours=4)
    ):
        return None
    day = datetime.now(timezone.utc).date().isoformat()
    if not increment_bounded(db, f"autonomous:{user_id}:{day}", settings().research_daily_limit):
        raise Unavailable("Daily autonomous investigation limit reached; next cycle resumes tomorrow")
    return start_case(
        db, user_id, next_query(db, user_id), {"autonomous": True, "learning": "reviewed scoped examples"}
    )
