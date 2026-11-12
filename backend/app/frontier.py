"""Finite, rotating Coimbatore discovery, with durable cooldowns and feedback topics."""

from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from .config import settings
from .db import Investigation, ResearchCorrection, Counter
from .providers import Unavailable
from .research import start_case
from .collection_control import bulk_enabled, count_request, daily_limits

# Searched once for the whole city, before the area grid. Activities are few and
# city-wide, so repeating them for every neighbourhood wastes searches.
CITY_TOPICS = [
    "go karting",
    "trampoline park adventure activities",
    "water park theme park",
    "escape room VR gaming zone",
    "snooker pool gaming lounge",
    "pottery art workshop",
    "turf pickleball badminton court",
    "museum zoo places to visit",
    "pubs bars breweries",
    "kids play area",
    "things to do with friends",
    "date night places",
    "new cafe opening",
    "hidden gem restaurants",
    "sushi Japanese Korean restaurants",
    "buffet restaurants",
]
# Searched for every area below.
CATEGORIES = [
    "new restaurants",
    "cafes",
    "bowling gaming arcade",
    "rooftop restaurants bars",
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
    topics = (
        [f"Coimbatore {scope} food entertainment" for scope in scopes]
        + [f"Coimbatore {topic}" for topic in CITY_TOPICS]
        + topics
    )
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
    active = list(
        db.scalars(
            select(Investigation)
            .where(Investigation.user_id == user_id, Investigation.state.in_(["queued", "running"]))
            .order_by(Investigation.created_at)
        )
    )
    if active and (not bulk_enabled() or len(active) >= settings().bulk_active_case_limit):
        return active[0]
    last = db.scalar(
        select(Investigation)
        .where(Investigation.user_id == user_id)
        .order_by(Investigation.created_at.desc())
    )
    if (
        scheduled
        and not (bulk_enabled() or (settings().app_mode == "local" and settings().city_directory_enabled))
        and last
        and datetime.fromisoformat(last.created_at) > datetime.now(timezone.utc) - timedelta(hours=4)
    ):
        return None
    day = datetime.now(timezone.utc).date().isoformat()
    if not count_request(db, f"autonomous:{user_id}:{day}", daily_limits()["investigations"]):
        raise Unavailable("Daily autonomous investigation limit reached; next cycle resumes tomorrow")
    return start_case(
        db, user_id, next_query(db, user_id), {"autonomous": True, "learning": "reviewed scoped examples"}
    )
