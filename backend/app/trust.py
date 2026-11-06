"""Uncertainty-aware review history; popularity never substitutes for evidence."""

import math
from datetime import datetime, timezone, timedelta


def wilson(supported, total):
    if total == 0:
        return None
    p, z = supported / total, 1.96
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [round(max(0, centre - radius), 4), round(min(1, centre + radius), 4)]


def review_statistics(rows):
    latest = {}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
    for row in sorted(rows, key=lambda r: r.created_at, reverse=True):
        if row.created_at >= cutoff:
            latest.setdefault(row.evidence_group, row)
    counts = {
        k: sum(r.outcome == k for r in latest.values())
        for k in ("supported", "refuted", "outdated", "unresolved")
    }
    total = counts["supported"] + counts["refuted"]
    interval = wilson(counts["supported"], total)
    return {
        **counts,
        "independent_review_groups": len(latest),
        "judged_groups": total,
        "observed_support_rate": round(counts["supported"] / total, 3) if total else None,
        "support_interval_95": interval,
        "window_days": 180,
        "status": "unestablished"
        if total == 0
        else "limited_review_history"
        if total < 20
        else "reviewed_history",
        "calibration": "not_validated_on_future_outcomes",
        "limitations": "Human-selected evidence groups, not random samples. The interval does not correct review bias. Subjective preferences/outdated facts are excluded from the support denominator. Not a probability a future video is true.",
    }


def calibration(predictions):
    # Only forecasts recorded before the independent judgement are eligible.
    usable = {
        r["origin"]: r
        for r in sorted(predictions, key=lambda item: item.get("judged_at", ""))
        if r.get("predicted_at", "z") < r.get("judged_at", "")
        and isinstance(r.get("probability"), (int, float))
        and 0 <= r["probability"] <= 1
        and r.get("outcome") in (0, 1)
    }
    rows = list(usable.values())
    return {
        "groups": len(rows),
        "brier_score": round(sum((r["probability"] - r["outcome"]) ** 2 for r in rows) / len(rows), 4)
        if rows
        else None,
        "status": "insufficient_prospective_labels" if len(rows) < 30 else "measured_selected_sample",
        "limitation": "A measured Brier score is not validation across creators, cuisines or languages",
    }
