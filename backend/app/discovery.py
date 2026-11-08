"""Conversational preference elicitation that never rewrites hard constraints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
import re
from .auth import current_user
from .db import get_db, Visit

router = APIRouter(prefix="/api")


class DiscoveryInput(BaseModel):
    message: str = Field(default="", max_length=500)
    answers: dict[str, str] = Field(default_factory=dict, max_length=5)


QUESTIONS = [
    (
        "purpose",
        "What would make this outing feel worthwhile?",
        [
            ("food", "Try a new flavour"),
            ("entertainment", "Do something fun"),
            ("combined", "A little of both"),
        ],
    ),
    (
        "energy",
        "How much energy do you want to spend?",
        [("quiet", "Relax and talk"), ("social", "Play together"), ("active", "Get moving")],
    ),
    (
        "novelty",
        "How different should it feel?",
        [
            ("nearby", "A new place with familiar tastes"),
            ("different", "Something outside my usual choices"),
            ("comfort", "Something I already enjoy"),
        ],
    ),
]


@router.post("/discovery/conversation")
def converse(data: DiscoveryInput, user=Depends(current_user), db=Depends(get_db)):
    answers = {k: v for k, v in data.answers.items() if k in {q[0] for q in QUESTIONS}}
    text = data.message.casefold()

    def mentions(words):
        return any(
            re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text)
            and not re.search(
                r"(?:no|not|without|avoid|don't want|do not want)\s+(?:\w+\s+){0,2}" + re.escape(word), text
            )
            for word in words
        )

    if "purpose" not in answers:
        food_intent = mentions(["eat", "food", "sushi", "coffee", "hungry"])
        fun_intent = mentions(["bowling", "gaming", "play", "movie", "adventure"])
        if food_intent and fun_intent:
            answers["purpose"] = "combined"
        elif food_intent:
            answers["purpose"] = "food"
        elif fun_intent:
            answers["purpose"] = "entertainment"
    if "energy" not in answers:
        if mentions(["tired", "relax", "quiet", "peaceful"]):
            answers["energy"] = "quiet"
        elif mentions(["active", "exercise", "adventure"]):
            answers["energy"] = "active"
    for key, question, choices in QUESTIONS:
        if answers.get(key) not in {c[0] for c in choices}:
            return {
                "ready": False,
                "answers": answers,
                "key": key,
                "question": question,
                "choices": [{"value": value, "label": label} for value, label in choices],
                "message": "Let's narrow it down without changing your budget or available time.",
            }
    visited = len(list(db.scalars(select(Visit.id).where(Visit.user_id == user.id))))
    profile = user.profile
    likes = list(profile.get("liked_tags", [])) + list(profile.get("preferred_cuisines", []))
    if profile.get("learn_from_visits", True):
        likes += [
            k
            for k, v in sorted(profile.get("inferred", {}).items(), key=lambda x: x[1], reverse=True)
            if v > 0
        ]
    purpose, energy, novelty = answers["purpose"], answers["energy"], answers["novelty"]
    food = ["food", "cafe"]
    entertainment = (
        ["park", "cinema"] if energy == "quiet" else ["gaming", "bowling", "adventure", "park", "cinema"]
    )
    categories = (
        food if purpose == "food" else entertainment if purpose == "entertainment" else food + entertainment
    )
    query = "Something different"
    if novelty in {"nearby", "comfort"} and likes:
        query = "Something different " + " ".join(dict.fromkeys(likes[:3]))
    return {
        "ready": True,
        "answers": answers,
        "suggestion": {
            "query": query,
            "categories": categories,
            "outing_type": purpose,
            "mood": "comfort" if novelty == "comfort" else energy if energy != "social" else "different",
            "novelty": {"nearby": "new_place", "different": "new_taste", "comfort": "familiar"}[novelty],
        },
        "message": (
            "We'll look for familiar tastes in a new setting."
            if novelty == "nearby"
            else "We'll explore beyond your confirmed visits."
            if novelty == "different"
            else "We'll favor your saved tastes."
        ),
        "memory_basis": f"{visited} confirmed visits; preferences remain editable",
        "constraint_policy": "Starting point, time, party size, dietary/access needs and budget remain unchanged",
    }
