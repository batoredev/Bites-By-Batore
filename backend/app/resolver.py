"""Resolve observations into candidate place identities without inventing confirmation."""

import re
from difflib import SequenceMatcher
from sqlalchemy import select
from .db import Venue, Claim
from .providers import google_search, Unavailable


def normalized(value):
    return re.sub(r"\W+", " ", str(value).casefold()).strip()


def resolve_candidates(db, analysis):
    records = list(db.scalars(select(Venue).where(Venue.is_demo.is_(False))))
    resolved = []
    candidates = analysis.get("venue_candidates", [])
    for candidate in candidates[:3]:
        if not isinstance(candidate, dict) or not isinstance(candidate.get("name"), str):
            continue
        name = candidate["name"][:150]
        matches = []
        for v in records:
            similarity = SequenceMatcher(None, normalized(name), normalized(v.name)).ratio()
            if similarity >= 0.7:
                matches.append(
                    {
                        "venue_id": v.id,
                        "name_similarity": round(similarity, 2),
                        "status": "candidate",
                        "reason": "Name similarity is not exact-branch verification",
                    }
                )
        row = {
            "observed_name": name,
            "inventory_candidates": matches[:5],
            "status": "needs_branch_verification",
        }
        try:
            clues = candidate.get("address_clues", [])
            clue = " ".join(str(x)[:150] for x in clues[:2]) if isinstance(clues, list) else ""
            places = google_search(db, f"{name} {clue} Coimbatore", 11.0168, 76.9558)
            # Permanent place-ID storage is supported; other Google content is transient.
            row["google_place_ids"] = [p["id"] for p in places[:5] if p.get("id")]
            row["next_step"] = (
                "Check these IDs against fresh Google details and the original address/signage. Confirm dishes and prices separately."
            )
        except Unavailable as exc:
            row["lookup_unavailable"] = str(exc)
        resolved.append(row)
    return resolved


def source_track_record(db, source_group):
    if not source_group:
        return {"status": "unestablished", "reason": "No canonical source identity supplied"}
    claims = list(db.scalars(select(Claim).where(Claim.source_group == source_group)))
    return {
        "status": "review_history_only",
        "accepted": sum(c.status == "accepted" for c in claims),
        "rejected": sum(c.status == "rejected" for c in claims),
        "pending": sum(c.status == "review" for c in claims),
        "limitations": "Review outcomes are not a universal creator truth score. Old prices, copied posts and taste differences must be assessed separately.",
    }
