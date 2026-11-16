"""What the agent has learned from the owner's own edits to places.

Nothing here trains a model. The owner's decisions stay on the places they were
made on, and these functions read them back as rules:

- a name rejected as "not a venue" is never proposed again;
- a category the owner set is reused for the same name, and for a distinctive
  word once two edited names agree on it;
- a creator the owner blocked is skipped.

Renames need no rule: the old name stays as an alias of the corrected place, so
later reels using the old spelling attach to it.
"""

from collections import Counter, defaultdict
from contextvars import ContextVar

from sqlalchemy import select

from .db import IdentifiedSpot
from .spot_identity import DESCRIPTORS, LOCALITIES, name_key

LEARN_FROM_REJECTION = {"not_a_venue", "out_of_scope", "wrong_city"}
# Set while Claude teaches on the owner's behalf; every decision is then tagged.
TEACHER = ContextVar("batore_teacher", default="")
TEACHER_ACTOR = "agent:claude-teacher"


def actor(user_id):
    return TEACHER.get() or user_id


_LOCAL_WORDS = {word for place in LOCALITIES for word in name_key(place).split()}


def _words(name):
    """Words that could carry a category: not filler, not a locality, not tiny."""
    return [
        w
        for w in name_key(name).split()
        if len(w) >= 4 and w not in DESCRIPTORS and w not in _LOCAL_WORDS and not w.isdigit()
    ]


def rules(rows):
    """Derive the rule set from the owner's place records."""
    rejected, categories, votes, creators = {}, {}, defaultdict(Counter), set()
    real, chains, distinct = set(), set(), defaultdict(set)
    for row in rows:
        data = row.data or {}
        if row.status not in {"merged", "rejected"} and data.get("operator_named"):
            real.add(name_key(row.name))  # A name the owner confirmed or typed is a real venue name.
        for other in data.get("distinct_from", []):
            distinct[row.id].add(other)
            distinct[other].add(row.id)
        if data.get("chain"):
            chains.add(name_key(row.name))
        rejection = data.get("rejection") or {}
        if row.status == "rejected":
            creators.update(str(c).casefold().lstrip("@") for c in rejection.get("blocked_creators", []))
            if rejection.get("kind") in LEARN_FROM_REJECTION:
                rejected[name_key(row.name)] = rejection["kind"]
            continue
        category = data.get("operator_category")
        if category and row.status != "merged":
            for name in {row.name, *data.get("aliases", [])}:
                categories[name_key(name)] = category
            for word in set(_words(row.name)):
                votes[word][category] += 1
    words = {w: next(iter(c)) for w, c in votes.items() if len(c) == 1 and sum(c.values()) >= 2}
    return {
        "rejected": rejected,
        "categories": categories,
        "words": words,
        "creators": creators,
        "real": real - set(rejected),
        "chains": chains,
        "distinct": distinct,
    }


def load(db, owner):
    return rules(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == owner)))


def blocked_creators(db, owner):
    return load(db, owner)["creators"]


def category_for(learned, name):
    """The owner's category for this name, or for a word two of their edits agree on."""
    exact = learned["categories"].get(name_key(name))
    if exact:
        return exact
    return next((learned["words"][w] for w in _words(name) if w in learned["words"]), None)


def summary(db, owner):
    """Plain description of the current rules, for the owner to inspect."""
    rows = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == owner)))
    learned = rules(rows)
    renamed = [
        {"from": e["from"], "to": e["to"]}
        for r in rows
        for e in (r.data or {}).get("operator_edits", [])
        if e.get("field") == "name"
    ]
    return {
        "rejected_names": sorted(learned["rejected"]),
        "category_by_name": len(learned["categories"]),
        "category_by_word": learned["words"],
        "blocked_creators": sorted(learned["creators"]),
        "confirmed_real_names": len(learned["real"]),
        "chains": sorted(learned["chains"]),
        "kept_apart_pairs": sum(len(v) for v in learned["distinct"].values()) // 2,
        "merged_by_decision": sum(
            r.status == "merged" and not (r.data or {}).get("merged_automatically", False) for r in rows
        ),
        "taught_by_claude": sum(bool((r.data or {}).get("taught_by")) for r in rows),
        "renames": renamed[-50:],
        "places_added_by_you": sum(
            any(s.get("type") == "owner" for s in (r.data or {}).get("sources", [])) for r in rows
        ),
        "note": "Rules come only from your own edits and are removed when you undo the edit.",
    }
