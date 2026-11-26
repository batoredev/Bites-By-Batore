"""Build the live-places accuracy sheet for Quick review.

Draws a seeded random sample of places customers can currently see (approved spots),
spread across categories in proportion to how many live places each has, with a small
minimum per category so rare categories are measured too. Writes
data/city-collection/spotcheck-live-200.csv. Reads the database only.

Refuses to replace a sheet that already has answers unless --force is given, because
those answers are the accuracy measurement.

Usage (from the project root):
    backend\\.venv\\Scripts\\python.exe scripts\\make_live_audit.py [--size 200] [--seed 26] [--force]
"""

from __future__ import annotations

import argparse
import csv
import io
import random
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.db import IdentifiedSpot, Session  # noqa: E402
from app.review_desk import ANSWER_COL, LIVE_HEADER, SHEET_DIR, SHEETS  # noqa: E402

MIN_PER_CATEGORY = 4


def allocate(counts: dict[str, int], size: int) -> dict[str, int]:
    """Proportional shares with a floor, never more than a category has, summing to size when possible."""
    total = sum(counts.values())
    size = min(size, total)
    share = {c: min(n, max(MIN_PER_CATEGORY, round(size * n / total))) for c, n in counts.items()}
    order = sorted(counts, key=counts.get, reverse=True)
    while sum(share.values()) > size:
        trimmed = False
        for c in order:
            if sum(share.values()) <= size:
                break
            if share[c] > MIN_PER_CATEGORY:
                share[c] -= 1
                trimmed = True
        if not trimmed:
            break
    while sum(share.values()) < size:
        grown = False
        for c in order:
            if sum(share.values()) >= size:
                break
            if share[c] < counts[c]:
                share[c] += 1
                grown = True
        if not grown:
            break
    return share


def sample(spots: list, size: int, seed: int) -> list:
    by_cat = defaultdict(list)
    for spot in sorted(spots, key=lambda s: s.id):
        by_cat[spot.category or "other"].append(spot)
    rng = random.Random(seed)
    picked = []
    for cat, n in allocate({c: len(v) for c, v in by_cat.items()}, size).items():
        picked.extend(rng.sample(by_cat[cat], n))
    rng.shuffle(picked)
    return picked


def row_for(spot) -> list[str]:
    data = spot.data or {}
    kinds = sorted({(s.get("type") or "web") for s in data.get("sources") or [] if isinstance(s, dict)})
    query = quote_plus(" ".join(p for p in (spot.name, spot.area, "Coimbatore") if p))
    link = f"https://www.google.com/maps/search/?api=1&query={query}"
    return [spot.name, spot.category or "", spot.area or "", ";".join(kinds), link, "", "", spot.id]


def has_answers(path: Path) -> bool:
    if not path.exists():
        return False
    rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"))))[1:]
    return any(len(r) > ANSWER_COL and r[ANSWER_COL].strip() for r in rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=26)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    path = SHEET_DIR / SHEETS["live"][0]
    if has_answers(path) and not args.force:
        print(f"{path.name} already has answers; not replacing it (use --force).")
        return 1
    with Session() as db:
        live = list(db.scalars(select(IdentifiedSpot).where(
            IdentifiedSpot.user_id == "local-operator", IdentifiedSpot.status == "approved")))
    rows = [row_for(s) for s in sample(live, args.size, args.seed)]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(LIVE_HEADER)
    writer.writerows(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(out.getvalue(), encoding="utf-8-sig")
    cats = defaultdict(int)
    for r in rows:
        cats[r[1]] += 1
    print(f"Wrote {len(rows)} of {len(live)} live places to {path}")
    print(", ".join(f"{c} {n}" for c, n in sorted(cats.items(), key=lambda x: -x[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
