"""Reversible learning from private experiences. Edits/deletions remove their contribution."""

from collections import defaultdict
from sqlalchemy import select
from .db import Visit, Venue, DishEntry
from .spot_identity import name_key
from .categories import FOOD

CONTEXT = {"quiet", "social", "outdoor", "indoor", "active"}


def rebuild_taste(db, user):
    db.flush()
    scores, occasions = defaultdict(float), defaultdict(lambda: defaultdict(float))
    visits = list(db.scalars(select(Visit).where(Visit.user_id == user.id)))
    for visit in visits:
        venue = db.get(Venue, visit.venue_id)
        snapshot = visit.experience or {}
        tags = {name_key(t) for t in snapshot.get("tags", venue.tags if venue else []) if name_key(t)}
        category = snapshot.get("category", venue.category if venue else "")
        dimension = "food" if category in FOOD else "activity"
        if dimension in visit.dimensions:
            for tag in set(tags) - CONTEXT:
                scores[name_key(tag)] += (visit.dimensions[dimension] - 3) * 0.2
        if "atmosphere" in visit.dimensions:
            for tag in set(tags) & CONTEXT:
                occasions[visit.occasion][tag] += (visit.dimensions["atmosphere"] - 3) * 0.2
    for entry in db.scalars(select(DishEntry).where(DishEntry.user_id == user.id)):
        delta = 0.4 if entry.status == "favourite" else -0.4 if entry.status == "not_for_me" else 0
        for tag in {name_key(t) for t in entry.preferences.get("tags", []) if name_key(t)} - CONTEXT:
            if tag:
                scores[name_key(tag)] += delta
    enabled = user.profile.get("learn_from_visits", True)
    user.profile = {
        **user.profile,
        "inferred": {
            tag: round(max(-3, min(3, value)), 2) for tag, value in scores.items() if round(value, 2)
        }
        if enabled
        else {},
        "occasion_preferences": {
            occasion: {
                tag: round(max(-3, min(3, value)), 2) for tag, value in tags.items() if round(value, 2)
            }
            for occasion, tags in occasions.items()
        }
        if enabled
        else {},
        "learning_basis": "Confirmed dimension ratings and private dish favourites/dislikes; wishlist saves and free-text notes do not establish taste",
    }
