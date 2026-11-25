"""Check an outside list of places (a saved web page or a plain list) against our database.

Usage (from the project root):
    backend\\.venv\\Scripts\\python.exe scripts\\compare_external_list.py data\\favhiker\\page.html [more files...]

Accepts saved pages (.html/.htm, any number, e.g. one per results page) or text files with one
name per line. Reads the live database read-only. Writes data/<folder of first file>/comparison.csv
and prints a summary: found (and in what state), likely matches to check, and missing.
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.spot_identity import LOCALITIES, name_key  # noqa: E402

DB = ROOT / "data" / "local-research.db"
NOISE = {"restaurant", "restaurants", "hotel", "cafe", "family", "veg", "pure", "the", "and", "a", "multi", "cuisine"}
LOCAL = {w for place in LOCALITIES for w in name_key(place).split()}


def core(name: str) -> str:
    """Name without areas and filler, for matching branches written differently."""
    words = [w for w in name_key(name).split() if w not in LOCAL and w not in NOISE]
    return " ".join(words) or name_key(name)


def names_from_html(path: Path) -> list[str]:
    from lxml import html as lh

    tree = lh.fromstring(path.read_bytes())
    found = []
    # Restaurant cards link to a restaurant page; take the card heading (or link text) as the name.
    for a in tree.xpath("//a[@href]"):
        href = a.get("href", "")
        if re.search(r"/(restaurant|restaurants|place|places|venue)/[^/?#]+", href) and "/city/" not in href:
            heading = a.xpath(".//h1|.//h2|.//h3|.//h4|.//strong")
            name = " ".join((heading[0] if heading else a).text_content().split())
            if 2 <= len(name) <= 90:
                found.append(name)
    # JSON-LD item lists, if the page has them.
    for script in tree.xpath("//script[@type='application/ld+json']/text()"):
        try:
            data = json.loads(script)
        except ValueError:
            continue
        for item in (data.get("itemListElement", []) if isinstance(data, dict) else []):
            thing = item.get("item", item) if isinstance(item, dict) else {}
            if isinstance(thing, dict) and thing.get("name"):
                found.append(thing["name"])
    return found


def load_names(paths: list[Path]) -> list[str]:
    names = []
    for path in paths:
        if path.suffix.lower() in {".html", ".htm"}:
            names += names_from_html(path)
        else:
            names += [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    seen, out = set(), []
    for n in names:
        if name_key(n) and name_key(n) not in seen:
            seen.add(name_key(n))
            out.append(n)
    return out


def ours():
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = []
    for name, area, status, data in db.execute("select name, area, status, data from identified_spots"):
        aliases = json.loads(data or "{}").get("aliases", []) or []
        for n in {name, *aliases}:
            rows.append({"name": name, "said": n, "area": area or "", "status": status})
    for name, area, status in db.execute("select name, area, status from venues where is_demo = 0"):
        rows.append({"name": name, "said": name, "area": area or "", "status": "venue:" + status})
    return rows


RANK = {"venue:published": 0, "approved": 1, "identified": 2, "quarantined": 3, "merged": 4, "rejected": 5}


def best(name: str, rows, by_key, by_core):
    key, c = name_key(name), core(name)
    for kind, pool in (("exact", by_key.get(key)), ("same name, different branch words", by_core.get(c))):
        if pool:
            hit = min(pool, key=lambda r: RANK.get(r["status"], 9))
            return kind, hit, 1.0
    scored = max(((difflib.SequenceMatcher(None, c, core(r["said"])).ratio(), r) for r in rows), key=lambda t: t[0])
    if scored[0] >= 0.86:
        return "likely (check)", scored[1], scored[0]
    return "missing", scored[1] if scored[0] >= 0.7 else None, scored[0]


def main(argv):
    paths = [Path(a) for a in argv]
    if not paths or not all(p.exists() for p in paths):
        sys.exit("Give one or more saved pages or name lists that exist.")
    theirs = load_names(paths)
    if not theirs:
        sys.exit("No place names found in those files. Save the page fully loaded, or paste the names one per line into a .txt file.")
    rows = ours()
    by_key, by_core = {}, {}
    for r in rows:
        by_key.setdefault(name_key(r["said"]), []).append(r)
        by_core.setdefault(core(r["said"]), []).append(r)
    out = ROOT / "data" / paths[0].parent.name / "comparison.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    tally = {}
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["their_name", "match", "our_name", "our_status", "our_area", "score"])
        for name in theirs:
            kind, hit, score = best(name, rows, by_key, by_core)
            state = hit["status"] if hit and kind != "missing" else ""
            if kind in {"missing", "likely (check)"}:
                bucket = kind
            else:
                bucket = "found, live" if state in {"venue:published", "approved"} else f"found, {state}"
            tally[bucket] = tally.get(bucket, 0) + 1
            w.writerow([name, kind, hit["name"] if hit else "", hit["status"] if hit else "", hit["area"] if hit else "", f"{score:.2f}"])
    print(f"{len(theirs)} names checked against {len({r['name'] for r in rows})} of ours.")
    for bucket, n in sorted(tally.items(), key=lambda t: -t[1]):
        print(f"  {bucket}: {n}")
    print(f"Details: {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
