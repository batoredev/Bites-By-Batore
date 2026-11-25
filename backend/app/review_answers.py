"""Read the owner's own words on a Quick review row: a verdict, corrections to teach, and a note.

Clear phrasings are read by rules first ("it's a bakery", "in Peelamedu", "called X", a Maps
link, "not a real place", "not in Coimbatore", "different branch", "closed"). When the rules
find nothing, the local model gets one try, and anything it returns must appear in the owner's
own words or it is dropped. Nothing here changes data; the desk shows the reading for the owner
to confirm before it is applied.
"""
from __future__ import annotations

import json
import re

from .categories import CATEGORIES, label, match as category_match
from .spot_identity import LOCALITIES

CLOSED = re.compile(r"\b(closed|shut( down)?|no longer (open|there|exists)|not open any ?more|permanently closed)\b")
NO = re.compile(r"^\s*(no|nope|wrong|incorrect|not right|nah)\b|\b(that'?s|is|was|you'?re|you are) (wrong|incorrect|not right)\b")
YES = re.compile(
    r"^\s*(yes|yeah|yep|correct|right|true|exactly|approved?)\b|"
    r"\b(looks? (good|fine|right|correct|ok(ay)?)|(that'?s|it'?s|you'?re|you are) (right|correct)|all good|spot on|good call)\b"
)
NOT_VENUE = re.compile(
    r"\b(not (a |an )?(real |specific |actual )?(place|venue|restaurant|shop|business|location)|"
    r"(just|only) a (dish|phrase|word|description|page)|generic (name|phrase|word)|page name|blogger|creator handle)\b"
)
WRONG_CITY = re.compile(
    r"\b(not in (coimbatore|cbe|kovai)|outside (coimbatore|cbe|kovai)|"
    r"(it'?s |is |located )?in (kerala|palakkad|tiruppur|tirupur|erode|ooty|chennai|bangalore|bengaluru|salem|pollachi|mettupalayam))\b"
)
DIFFERENT = re.compile(r"\b(different (branch|place|shop|outlet|restaurant)|not the same|separate (branch|place)|two different)\b")
SAME = re.compile(r"\b(same (place|shop|restaurant|outlet|branch)|(is|are) the same|duplicate)\b")
MAPS = re.compile(r"https://(?:www\.)?(?:google\.[a-z.]+/maps\S*|maps\.google\.[a-z.]+\S*|maps\.app\.goo\.gl/\S+|goo\.gl/maps/\S+)")
NAME = re.compile(
    r"\b(?:called|named|name is|real name is|correct name is|proper name is|actual name is|rename(?: it)? to|spelt|spelled)\s+"
    r"[\"“']?([A-Za-z0-9][A-Za-z0-9 &'.-]{1,60}?)[\"”']?(?=\s+(?:in|at|near|on|and|but|which|it|its|it's)\b|[,.;!?]|$)",
    re.IGNORECASE,
)
KIND = re.compile(
    r"\b(?:it'?s|it is|this is|its|actually|more like|should be|category is|category should be|is a|is an|it'?s just)\s+"
    r"(?:a |an |just a |more of a |actually a )?([a-z][a-z &'-]{2,30})",
)
NEGATED = re.compile(r"\bnot (?:a |an |really a )?[a-z&'-]+(?: [a-z&'-]+)?")
# Words owners use that the category rules spell differently.
KIND_WORDS = {
    "bakery": "dessert", "sweet shop": "dessert", "sweets": "dessert", "ice cream": "dessert", "dessert": "dessert",
    "mess": "street_food", "street food": "street_food", "stall": "street_food", "cart": "street_food",
    "restaurant": "food", "hotel": "food", "dhaba": "food", "biryani": "food",
    "cafe": "cafe", "café": "cafe", "coffee shop": "cafe", "tea shop": "cafe",
    "bar": "nightlife", "pub": "nightlife", "lounge": "nightlife", "club": "nightlife",
    "theatre": "cinema", "theater": "cinema", "cinema": "cinema", "multiplex": "cinema",
    "arcade": "gaming", "gaming": "gaming", "bowling": "bowling", "turf": "sports", "court": "sports",
    "park": "park", "lake": "park", "museum": "attraction", "temple": "attraction",
    "water park": "amusement", "theme park": "amusement", "workshop": "workshop", "go karting": "adventure",
}


def _clean(text: str) -> str:
    return " ".join((text or "").split())[:600]


def _kind(phrase: str) -> str | None:
    phrase = phrase.casefold().strip()
    for word in sorted(KIND_WORDS, key=len, reverse=True):
        if re.search(rf"\b{re.escape(word)}\b", phrase):
            return KIND_WORDS[word]
    return category_match(phrase)


def _area(text: str) -> str | None:
    lower = text.casefold()
    found = [(lower.find(p.casefold()), p) for p in LOCALITIES if re.search(rf"\b{re.escape(p.casefold())}\b", lower)]
    return max(found, key=lambda f: (len(f[1]), f[0]))[1] if found else None


def _edit(action, value, text):
    labels = {
        "category": lambda v: f"category → {label(v)}",
        "area": lambda v: f"area → {v}",
        "rename": lambda v: f"name → “{v}”",
        "maps": lambda v: "Maps pin from your link",
        "reject": lambda v: {"not_a_venue": "remove: not a real place", "wrong_city": "remove: not in Coimbatore"}[v],
        "distinct": lambda v: f"keep apart from “{v}”",
        "same_as": lambda v: f"same place as “{v}”",
    }
    return {"action": action, "value": value, "label": labels[action](value)}


def interpret(text: str, item: dict, ask_model=None) -> dict:
    """The owner's reading of one row. `item` is the desk item (title, sheet, matches, ...)."""
    said = _clean(text)
    lower = said.casefold()
    edits: list[dict] = []
    current = (item.get("matches") or [{}])[0] if item.get("matches") else {}

    if NOT_VENUE.search(lower):
        edits.append(_edit("reject", "not_a_venue", said))
    elif WRONG_CITY.search(lower):
        edits.append(_edit("reject", "wrong_city", said))
    else:
        maps = MAPS.search(said)
        if maps:
            edits.append(_edit("maps", maps.group(0).rstrip(").,"), said))
        name = NAME.search(said)
        if name and name.group(1).strip().casefold() != (item.get("title") or "").casefold():
            edits.append(_edit("rename", name.group(1).strip(), said))
        positive = NEGATED.sub(" ", lower)
        kind = next((k for k in (_kind(m.group(1)) for m in KIND.finditer(positive)) if k), None)
        if kind and kind != current.get("category"):
            edits.append(_edit("category", kind, said))
        area = _area(said)
        if area and area.casefold() != (current.get("area") or "").casefold() and not (name and area in name.group(1)):
            edits.append(_edit("area", area, said))
        other = item.get("other") or ""
        if other and DIFFERENT.search(lower):
            edits.append(_edit("distinct", other, said))
        elif other and SAME.search(lower):
            edits.append(_edit("same_as", other, said))

    verdict = ""
    if CLOSED.search(lower) and "closed" in item.get("options", []):
        verdict = "closed"
    elif YES.search(lower) and not NO.search(lower):
        verdict = "yes"
    elif NO.search(lower) or edits:
        verdict = "no"  # a correction means the row was not right as shown
    used_model = False
    if not edits and ask_model and verdict != "closed" and len(lower.split()) >= 4:
        reading = ask_model(said, item)
        if reading:
            used_model = True
            checked = validate(reading, said, item)
            edits = checked["edits"]
            verdict = verdict or checked["verdict"]
    return _summary(verdict, edits, said, used_model)


def _summary(verdict, edits, said, used_model=False) -> dict:
    head = {"yes": "Yes", "no": "No", "closed": "Closed", "": "No verdict"}[verdict]
    parts = [e["label"] for e in edits]
    return {
        "verdict": verdict,
        "edits": edits,
        "note": said,
        "used_model": used_model,
        "summary": head + (": " + "; ".join(parts) if parts else "") + ". Your words are saved as a note.",
    }


def validate(reading: dict, text: str, item: dict) -> dict:
    """Keep only what the owner actually said. Used on model output and on anything a client sends back."""
    said = _clean(text)
    lower = said.casefold()
    verdict = reading.get("verdict") if reading.get("verdict") in {"yes", "no", "closed", ""} else ""
    if verdict and verdict not in item.get("options", []):
        verdict = ""
    kept = []
    for e in reading.get("edits") or []:
        action, value = e.get("action"), str(e.get("value") or "").strip()
        ok = (
            (action == "category" and value in CATEGORIES)
            or (action == "area" and value in LOCALITIES and value.casefold() in lower)
            or (action == "rename" and 2 <= len(value) <= 60 and value.casefold() in lower)
            or (action == "maps" and MAPS.fullmatch(value) is not None and value in said)
            or (action == "reject" and value in {"not_a_venue", "wrong_city"})
            or (action in {"distinct", "same_as"} and value and value == item.get("other"))
        )
        if ok and action == "category":  # the category must come from a word the owner used
            ok = any(_kind(w) == value for w in re.findall(r"[a-z][a-z &'-]{2,30}", NEGATED.sub(" ", lower)))
        if ok and action == "reject":
            ok = bool((NOT_VENUE if value == "not_a_venue" else WRONG_CITY).search(lower))
        if ok and not any(k["action"] == action for k in kept):
            kept.append(_edit(action, value, said))
    if kept and (not verdict or (verdict == "yes" and not YES.search(lower))):
        verdict = "no"  # a correction is a "no" unless the owner themselves said yes
    return _summary(verdict, kept, said, bool(reading.get("used_model")))


MODEL_PROMPT = """You read a restaurant-database owner's spoken or typed answer about one place.
Return only what the owner actually said. Never guess. Copy names and areas exactly as written.
verdict: "yes" if they agree the row is right, "no" if not, "closed" if the place has closed, "" if unclear.
category: one of {cats}, only if the owner states what kind of place it is; otherwise "".
area: a Coimbatore locality the owner names for this place; otherwise "".
name: the place's correct name only if the owner gives one; otherwise "".
not_a_venue: true only if the owner says this is not a real specific place.
wrong_city: true only if the owner says it is outside Coimbatore."""

MODEL_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"enum": ["yes", "no", "closed", ""]},
        "category": {"enum": CATEGORIES + [""]},
        "area": {"type": "string", "maxLength": 60},
        "name": {"type": "string", "maxLength": 60},
        "not_a_venue": {"type": "boolean"},
        "wrong_city": {"type": "boolean"},
    },
    "required": ["verdict", "category", "area", "name", "not_a_venue", "wrong_city"],
    "additionalProperties": False,
}


def model_reading(text: str, item: dict) -> dict | None:
    """One local-model pass. Returns the raw reading in `validate` form, or None if the model is unavailable."""
    from .config import settings
    from .local_models import endpoint, inference_client

    cfg = settings()
    try:
        response = inference_client().post(
            endpoint() + "/api/chat",
            timeout=40,
            json={
                "model": cfg.ollama_text_model or cfg.ollama_model,
                "stream": False,
                "think": False,
                "format": MODEL_SCHEMA,
                "keep_alive": cfg.ollama_keep_alive,
                "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 200},
                "messages": [
                    {"role": "system", "content": MODEL_PROMPT.format(cats=", ".join(CATEGORIES))},
                    {"role": "user", "content": f"Place shown: {item.get('title', '')}\nOwner said: {text}"},
                ],
            },
        )
        response.raise_for_status()
        raw = json.loads(response.json()["message"]["content"])
    except Exception:  # the rules' reading stands on its own when the model can't help
        return None
    edits = []
    if raw.get("not_a_venue"):
        edits.append({"action": "reject", "value": "not_a_venue"})
    elif raw.get("wrong_city"):
        edits.append({"action": "reject", "value": "wrong_city"})
    else:
        for action, key in (("rename", "name"), ("category", "category"), ("area", "area")):
            if raw.get(key):
                edits.append({"action": action, "value": raw[key]})
    return {"verdict": raw.get("verdict", ""), "edits": edits, "used_model": True}
