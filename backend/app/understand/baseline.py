"""Today's keyword reader, as a baseline the trained model must beat.

It reproduces what the planner can read from typed text today: category words (planner
SYNONYMS and the categories.py rules) and the fixed interest list in planner.parse_interest.
Everything else (people, budget, time, diet, access, area) only comes from form fields
today, so this reader leaves them empty.
"""

from __future__ import annotations

import re

from .. import categories
from ..planner import SYNONYMS, parse_interest

CATEGORY_WORDS = {c: c for c in categories.CATEGORIES} | {"street food": "street_food"}


def keyword_reading(text: str) -> dict:
    q = text.casefold()
    found = []
    for word, category in SYNONYMS.items():
        if re.search(r"(?<!\w)" + word + r"(?!\w)", q):
            found.append(category.replace(" ", "_"))
    for word, category in CATEGORY_WORDS.items():
        if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", q):
            found.append(category)
    for piece in re.split(r",|\band\b|\bthen\b", q):
        category = categories.match(piece)
        if category:
            found.append(category)
    found = list(dict.fromkeys(found))
    interests = [t for t in parse_interest(text) if t not in CATEGORY_WORDS and t not in {"movies", "quiet"}]
    return {"categories": found, "interests": interests}
