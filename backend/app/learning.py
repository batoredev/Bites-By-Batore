"""Private, reversible retrieval learning; this does not train model weights."""

import re
from datetime import datetime, timezone
from sqlalchemy import select
from .db import ResearchCorrection, ResearchSource, Investigation


def relevant_examples(db, user_id, source, role):
    # Held-out origins must never become retrieval examples for other evaluation cases.
    owned = list(
        db.scalars(
            select(ResearchSource)
            .join(Investigation, ResearchSource.case_id == Investigation.id)
            .where(Investigation.user_id == user_id)
        )
    )
    held_origins = {
        s.content.get("content_fingerprint") or s.canonical_url
        for s in owned
        if any(label.get("split") == "holdout" for label in s.analysis.get("evaluation_labels", {}).values())
    }
    excluded = {
        s.id for s in owned if (s.content.get("content_fingerprint") or s.canonical_url) in held_origins
    }
    text = " ".join(
        str(source.content.get(k, "")) for k in ["caption", "transcript", "title", "search_preview"]
    ).casefold()
    results = []
    rows = db.scalars(
        select(ResearchCorrection)
        .where(
            ResearchCorrection.user_id == user_id,
            ResearchCorrection.active == True,
            ResearchCorrection.role == role,
        )
        .order_by(ResearchCorrection.created_at.desc())
        .limit(200)
    )
    for row in rows:
        if row.source_id in excluded:
            continue
        # Exact phrase scope prevents an unrelated branch inheriting a correction.
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(row.created_at)).total_seconds()
        if age > 90 * 86400 or not re.search(r"(?<!\w)" + re.escape(row.scope.casefold()) + r"(?!\w)", text):
            continue
        results.append(
            {
                "correction_id": row.id,
                "scope": row.scope,
                "previous_error": row.original,
                "human_correction": row.corrected,
                "reason": row.reason,
                "instruction": "A reviewed interpretation example, not current venue truth. Verify against this source; retain conflicts.",
            }
        )
        if len(results) == 4:
            break
    return results
