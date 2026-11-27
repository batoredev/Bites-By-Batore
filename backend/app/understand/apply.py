"""From a Reading to the planner: form fields, "I understood" chips and the planner query.

Only details the person actually said are filled; nothing is switched off because it
wasn't mentioned. Values outside what the planner accepts are not forced in; they become a
notice instead. If the trained model can't be used, the keyword reader answers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from ..categories import label as category_label
from .baseline import keyword_reading
from .reading import Reading

IST = ZoneInfo("Asia/Kolkata")
START_MINUTES = {"morning": 9 * 60, "afternoon": 13 * 60, "evening": 19 * 60, "late_night": 22 * 60 + 30}
TIME_WORDS = {"morning": "Morning", "afternoon": "Afternoon", "evening": "Evening", "late_night": "Late night",
              "now": "Right now"}
MOOD_WORDS = {"different": "Something different", "comfort": "Comfort", "quiet": "Quiet", "social": "With friends",
              "active": "Active"}
NOVELTY_WORDS = {"new_place": "Somewhere new", "new_taste": "A new taste", "familiar": "Familiar favourites"}
TRANSPORT_WORDS = {"walk": "On foot", "bike": "By bike", "drive": "By car", "taxi": "By cab"}
OUT_OF_SCOPE = ("Bites plans food and outings inside Coimbatore. It doesn't plan events, trips, stays or "
                "other cities yet.")
log = logging.getLogger(__name__)


def read(text: str) -> tuple[dict, str]:
    """The trained model's reading, or the keyword reader's if the model can't be used."""
    try:
        from .model import read as model_read

        return model_read(text), "understand-v1"
    except Exception as error:  # a missing or broken model file must never stop planning
        log.warning("understanding model unavailable, using keywords: %s", error)
        return {**Reading().as_dict(), **keyword_reading(text)}, "keyword"


def departure(time_of_day: str, now: datetime | None = None) -> str:
    now = (now or datetime.now(IST)).astimezone(IST)
    if time_of_day == "now":
        start = now + timedelta(minutes=15)
        start = start.replace(minute=(start.minute // 5) * 5, second=0, microsecond=0)
    else:
        minutes = START_MINUTES[time_of_day]
        start = now.replace(hour=minutes // 60, minute=minutes % 60, second=0, microsecond=0)
        if start <= now + timedelta(minutes=30):
            start += timedelta(days=1)
    return start.isoformat()


def area_point(db, area: str) -> tuple[float, float] | None:
    """Centre of the live places stored in that area, if there are any."""
    from ..db import Venue

    row = db.execute(
        select(func.avg(Venue.lat), func.avg(Venue.lng), func.count())
        .where(Venue.area == area, Venue.status == "published", Venue.is_demo.is_(False))
    ).one()
    return (round(row[0], 5), round(row[1], 5)) if row[2] else None


def _hours(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    hours, rest = divmod(minutes, 60)
    return f"{hours} h" + (f" {rest} min" if rest else "")


def form_and_chips(reading: dict, db=None, now: datetime | None = None) -> tuple[dict, list[dict], list[str]]:
    form: dict = {}
    chips: list[dict] = []
    notices: list[str] = []

    def chip(fields, text):
        chips.append({"fields": fields, "label": text})

    if reading["out_of_scope"]:
        notices.append(OUT_OF_SCOPE)
    if reading["categories"]:
        form["categories"] = reading["categories"]
        chip(["categories"], " + ".join(category_label(c) for c in reading["categories"]))
    if reading["interests"]:
        chip([], ", ".join(reading["interests"]))
    if reading["party_size"]:
        if 1 <= reading["party_size"] <= 20:
            form["party_size"] = reading["party_size"]
            chip(["party_size"], "Just you" if reading["party_size"] == 1 else f"{reading['party_size']} people")
        else:
            notices.append("Bites plans for up to 20 people at a time.")
    if reading["budget"]:
        if 50 <= reading["budget"] <= 100000:
            form["budget"] = reading["budget"]
            unit = reading["budget_unit"]
            if unit:
                form["budget_unit"] = unit
            chip(["budget", "budget_unit"] if unit else ["budget"],
                 f"₹{reading['budget']:,}" + {"person": " per person", "group": " in total"}.get(unit, ""))
        else:
            notices.append("Budgets between ₹50 and ₹1,00,000 can be planned.")
    if reading["duration_minutes"]:
        if 30 <= reading["duration_minutes"] <= 720:
            form["duration_minutes"] = reading["duration_minutes"]
            chip(["duration_minutes"], _hours(reading["duration_minutes"]))
        else:
            notices.append("Outings from 30 minutes to 12 hours can be planned.")
    if reading["max_stops"] and 1 <= reading["max_stops"] <= 4:
        form["max_stops"] = reading["max_stops"]
        chip(["max_stops"], "One stop" if reading["max_stops"] == 1 else f"Up to {reading['max_stops']} stops")
    for field, text in (("vegetarian", "Vegetarian"), ("children", "With kids"), ("wheelchair", "Step-free access")):
        if reading[field]:
            form[field] = True
            chip([field], text)
    mood = reading["mood"] or ("different" if reading["surprise"] else None)
    if mood:
        form["mood"] = mood
        chip(["mood"], MOOD_WORDS[mood])
    if reading["novelty"]:
        form["novelty"] = reading["novelty"]
        chip(["novelty"], NOVELTY_WORDS[reading["novelty"]])
    if reading["transport"]:
        form["transport"] = reading["transport"]
        chip(["transport"], TRANSPORT_WORDS[reading["transport"]])
    if reading["avoid"]:
        form["avoid_tags"] = reading["avoid"]
        chip(["avoid_tags"], "No " + ", no ".join(reading["avoid"]))
    if reading["time_of_day"]:
        form["departure"] = departure(reading["time_of_day"], now)
        chip(["departure"], TIME_WORDS[reading["time_of_day"]])
    if reading["area"]:
        point = area_point(db, reading["area"]) if db is not None else None
        if point:
            form.update({"start_label": f"{reading['area']}, Coimbatore", "lat": point[0], "lng": point[1]})
            chip(["start_label", "lat", "lng"], f"From {reading['area']}")
        else:
            notices.append(f"I couldn't place {reading['area']} on the map yet; choose your starting point.")
    return form, chips, notices


def planner_query(text: str, reading: dict) -> str:
    """The text the planner matches dishes against: the person's words plus the canonical
    names the model read ("briyani" -> biryani). When the model read details but no dish,
    the request is treated as open, so "kids day out" plans instead of "no match"."""
    extra = list(reading["interests"])
    said_something = any(reading[f] for f in ("categories", "party_size", "budget", "duration_minutes", "vegetarian",
                                              "children", "wheelchair", "mood", "novelty", "time_of_day", "area",
                                              "transport", "max_stops", "avoid", "surprise"))
    if not extra and said_something:
        extra.append("something different")
    return f"{text} {' '.join(extra)}".strip()[:500]
