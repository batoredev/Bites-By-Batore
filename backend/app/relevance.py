"""Decide, before any model time is spent, whether a reel is worth analysing.

A reel is analysed only when its own text ties it to Coimbatore and it is not
plainly about something outside food and entertainment. The check is plain
keyword rules on the caption, creator handle and location tag, so every skip can
be explained. Sources the owner supplied directly are never skipped.
"""

import re

from .db import now
from .spot_identity import LOCALITIES, name_key

CENTRE = (11.0168, 76.9558)
CITY = re.compile(r"coimbatore|kovai|\bcbe\b|\b641\s?\d{3}\b|கோவை|கோயம்புத்தூர்|கோயம்பத்தூர்", re.I)
# Locality names that are also ordinary words are too weak to prove the city.
_WEAK = {"fort", "hopes", "sitra", "kovai", "coimbatore", "tamil nadu", "town hall", "sungam"}
_AREAS = [name_key(a) for a in LOCALITIES if name_key(a) not in _WEAK]
IN_SCOPE = re.compile(
    r"food|eat|restaurant|cafe|café|coffee|biryani|biriyani|dosa|idli|parotta|meals|menu|taste|tasty|dish|buffet|"
    r"dessert|ice ?cream|bakery|cake|juice|tea|chai|snack|chaat|mess|dine|dining|dinner|lunch|breakfast|brunch|"
    r"foodie|pizza|burger|shawarma|grill|bbq|kebab|momo|sushi|ramen|noodles|waffle|shake|sweet|"
    r"movie|cinema|theatre|theater|imax|game|gaming|bowling|kart|trampoline|adventure|arcade|\bvr\b|turf|"
    r"pickleball|pottery|workshop|museum|zoo|water ?park|theme ?park|amusement|park|lake|pub|\bbar\b|brew|lounge|"
    r"hangout|hang out|date night|things to do|fun|ride|play|snooker|escape room|"
    r"உணவு|சாப்பாடு|பிரியாணி|கடை|ஹோட்டல்|காபி|டீ",
    re.I,
)
OUT_OF_SCOPE = re.compile(
    r"\b(\d\s?bhk|for rent|for sale|real estate|plots?|villa|apartments?|sq\.?\s?ft|saree|sarees|jewell?ery|"
    r"bridal|makeup|salon|clinic|hospital|election|vacancy|hiring|admissions?|tuition|loan|insurance)\b",
    re.I,
)
SKIP_ROLES = ("caption", "comments", "video")


def city_signal(text):
    """True when the text itself names Coimbatore or one of its localities."""
    if CITY.search(text):
        return True
    key = name_key(text)
    return any(re.search(r"\b" + re.escape(area) + r"\b", key) for area in _AREAS)


def assess(content, blocked_creators=()):
    """Return a skip reason, or "" when the reel should be analysed."""
    creator = str(content.get("creator", "")).casefold().lstrip("@")
    if creator and creator in {str(c).casefold().lstrip("@") for c in blocked_creators}:
        return "You marked this creator as not relevant"
    caption = str(content.get("caption") or "")
    tag = content.get("location_tag") or {}
    text = " ".join([caption, creator, str(tag.get("name", ""))])
    if len(caption.strip()) < 20 and not tag:
        return ""  # Nothing to judge by; let the analysis decide.
    near = False
    if isinstance(tag.get("lat"), float) and isinstance(tag.get("lng"), float):
        from .planner import km

        near = km((tag["lat"], tag["lng"]), CENTRE) <= 40
        if not near:
            return "Location tag is outside the Coimbatore area"
    if not near and not city_signal(text):
        return "No Coimbatore signal in the caption, creator or location tag"
    if OUT_OF_SCOPE.search(text) and not IN_SCOPE.search(text):
        return "Caption is about something outside food and entertainment"
    return ""


def owner_supplied(case):
    """The owner chose these sources; relevance is their call, not the agent's."""
    context = case.context or {}
    return any(context.get(k) for k in ("submission_id", "url", "curated_leads"))


def try_skip(db, case, source):
    """Mark an irrelevant reel as skipped. Returns True when it was skipped."""
    if source.platform != "instagram" or owner_supplied(case):
        return False
    if source.analysis.get("relevance_skip"):
        return True
    if any(source.analysis.get(r, {}).get("status") == "observations_only" for r in SKIP_ROLES):
        return False  # Already analysed; do not rewrite history.
    from .learned import blocked_creators

    reason = assess(source.content, blocked_creators(db, case.user_id))
    if not reason:
        return False
    analysis = dict(source.analysis)
    analysis["relevance_skip"] = {"reason": reason, "at": now()}
    for role in SKIP_ROLES:
        analysis[role] = {"status": "skipped_irrelevant", "reason": reason, "video_analyzed": False}
    source.analysis = analysis
    source.content = {
        **{
            k: v
            for k, v in source.content.items()
            if k not in {"media", "media_url", "media_alternatives", "audio_url", "video_url"}
        },
        "streamed": True,
        "analysis_pending": False,
        "processing_outcome": "skipped_irrelevant",
    }
    source.state = "irrelevant"
    db.commit()
    return True
