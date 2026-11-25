"""Check outside place leads for whether they still operate, then (optionally) add them.

    backend\\.venv\\Scripts\\python.exe scripts\\check_leads.py data\\favhiker\\missing.txt            # check only
    backend\\.venv\\Scripts\\python.exe scripts\\check_leads.py data\\favhiker\\missing.txt --apply    # add after checking

A lead is a name only. Evidence comes from independent places: the saved Overture Maps file and a
public web search (the agents' own search). The site the list came from never counts as evidence.

    active  - two or more independent pages from the past year name the place with Coimbatore or one
              of its areas, and nothing says it closed
    closed  - a matching page says it closed permanently
    unsure  - anything else

--apply backs up the database, adds active and unsure leads as drafts through the normal duplicate
checks, publishes only the active ones that have a map point (all normal publish rules still apply),
and queues every added draft for the enrichment agent. A receipt lists exactly what was added.
"""
from __future__ import annotations

import csv
import difflib
import json
import re
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.spot_identity import LOCALITIES, infer_area, name_key  # noqa: E402

OVERTURE = ROOT / "data" / "city-collection" / "overture-places.geojsonl"
CENTRE = (11.0168, 76.9558)
SOURCE_SITE = "favhiker.com"
CLOSED = re.compile(r"permanently closed|closed permanently|closed down|has shut|shut down|no longer (open|operating)")
CITY = re.compile(r"\b(coimbatore|kovai|cbe)\b|" + "|".join(re.escape(p.casefold()) for p in LOCALITIES))
FILLER = {"restaurant", "restaurants", "hotel", "cafe", "the", "and", "coimbatore", "kovai", "cbe", "family", "veg",
          "pure", "multi", "cuisine", "biryani", "biriyani", "mess", "bakery", "kitchen", "foods", "food"}


def short(name: str) -> str:
    """The listed name without tails like "| Pure Veg Homemade Food", "@ Kovai", "- Coimbatore" or "(...)"."""
    s = re.split(r"\s+[|@–-]\s+|\s*\|\s*", name)[0]
    return re.sub(r"\s*\([^)]*\)", "", s).strip() or name


def tokens(name: str) -> list[str]:
    return [w for w in name_key(short(name)).split() if len(w) >= 3 and w not in FILLER] or name_key(short(name)).split()


def km(a, b):
    from math import asin, cos, radians, sin, sqrt

    (la1, lo1), (la2, lo2) = a, b
    h = sin(radians(la2 - la1) / 2) ** 2 + cos(radians(la1)) * cos(radians(la2)) * sin(radians(lo2 - lo1) / 2) ** 2
    return 6371 * 2 * asin(sqrt(h))


def overture_index():
    index = defaultdict(list)
    with OVERTURE.open(encoding="utf-8") as handle:
        for line in handle:
            f = json.loads(line)
            p = f.get("properties") or {}
            name = ((p.get("names") or {}).get("primary") or "").strip()
            coords = (f.get("geometry") or {}).get("coordinates") or []
            if not name or len(coords) != 2 or km((coords[1], coords[0]), CENTRE) > 40:
                continue
            srcs = [s for s in p.get("sources") or [] if s.get("dataset") != "Overture"]
            item = {
                "feature": f, "name": name, "lat": coords[1], "lng": coords[0],
                "confidence": float(p.get("confidence") or 0),
                "updated": max((s.get("update_time") or "" for s in srcs), default=""),
                "datasets": sorted({s.get("dataset") for s in srcs}),
            }
            for t in tokens(name)[:1]:
                index[t].append(item)
    return index


def overture_match(name, index):
    want = " ".join(tokens(name))
    best, score = None, 0.0
    for t in tokens(name)[:1]:
        for item in index.get(t, []):
            s = difflib.SequenceMatcher(None, want, " ".join(tokens(item["name"]))).ratio()
            if s > score:
                best, score = item, s
    return (best, score) if score >= 0.9 else (None, score)


RECENT_TEXT = re.compile(r"\b(2025|2026)\b|\b\d{1,2} (days?|weeks?|months?) ago\b")


def search(query: str):
    """(rows, dated). DuckDuckGo honours the past-year filter; Yahoo is the fallback and ignores it."""
    from ddgs import DDGS
    from ddgs.exceptions import DDGSException

    errors = 0
    for backend, dated in (("duckduckgo", True), ("yahoo", False), ("duckduckgo", True), ("yahoo", False)):
        try:
            rows = DDGS(timeout=12).text(query, max_results=10, backend=backend, timelimit="y" if dated else None)
            if rows:
                return rows, dated
        except DDGSException as exc:
            if "no results" not in str(exc).lower():
                errors += 1  # a refusal or timeout, not an empty answer
        except Exception:
            errors += 1
        time.sleep(3)
    return (None, False) if errors >= 3 else ([], False)


def web_evidence(name):
    words = tokens(name)
    need = min(2, len(words))
    out = {"recent": [], "older": [], "closed": [], "search_failed": False, "dated": False, "recent_text": False}
    rows, dated = search(f'"{short(name)}" Coimbatore')
    if rows is None:
        out["search_failed"] = True
        return out
    out["dated"] = dated
    for r in rows:
        url = r.get("href", "")
        host = (urlparse(url).hostname or "").removeprefix("www.")
        if not url.startswith("https://") or host.endswith(SOURCE_SITE):
            continue
        text = f"{r.get('title', '')} {r.get('body', '')}".casefold()
        if sum(w in text for w in words) < need or not (CITY.search(text) or CITY.search(url.casefold())):
            continue
        hit = {"url": url, "host": host, "title": r.get("title", "")[:200]}
        if CLOSED.search(text):
            out["closed"].append(hit)
        out["recent_text"] = out["recent_text"] or bool(RECENT_TEXT.search(text))
        (out["recent"] if dated else out["older"]).append(hit)
    return out


def verdict(ev, overture_updated=""):
    pages = ev["recent"] or ev["older"]
    hosts = {h["host"] for h in pages}
    if ev["closed"]:
        return "closed", "a matching page says it closed: " + ev["closed"][0]["url"]
    if ev["search_failed"]:
        return "unsure", "web search was unavailable"
    recent = [
        reason
        for reason, ok in (
            ("pages dated in the past year", bool(ev["recent"])),
            ("a 2025/2026 date on a matching page", ev.get("recent_text")),
            ("Overture updated it in the past year", overture_updated >= "2025-11"),
        )
        if ok
    ]
    if len(hosts) >= 2 and recent:
        return "active", f"{len(hosts)} independent pages; recent because of {recent[0]}"
    if len(hosts) >= 2:
        return "unsure", f"{len(hosts)} independent pages, but nothing shows it is still open this year"
    if hosts:
        return "unsure", "only one independent page"
    return "unsure", "no independent page found"


def check(path: Path):
    names = [n.strip() for n in path.read_text(encoding="utf-8-sig").splitlines() if n.strip()]
    index = overture_index()
    out = path.parent / "lead-check.csv"
    saved = path.parent / "lead-check.json"
    # Resume: keep earlier results, redo only names whose search was unavailable.
    earlier = {r["name"]: r for r in json.loads(saved.read_text(encoding="utf-8"))} if saved.exists() else {}
    results = []
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["name", "verdict", "why", "recent_pages", "hosts", "overture_conf", "overture_updated", "lat", "lng", "evidence_urls"])
        for n, name in enumerate(names, 1):
            again = earlier.get(name)
            if again and not again["evidence"]["search_failed"]:
                ev = again["evidence"]
            else:
                ev = web_evidence(name)
                time.sleep(2)
            match, _ = overture_match(name, index)
            kind, why = verdict(ev, match["updated"] if match else "")
            results.append({"name": name, "verdict": kind, "why": why, "evidence": ev, "overture": match})
            pages = ev["recent"] or ev["older"]
            w.writerow([name, kind, why, len(ev["recent"]), " ".join(sorted({h["host"] for h in pages})),
                        match["confidence"] if match else "", match["updated"][:10] if match else "",
                        match["lat"] if match else "", match["lng"] if match else "",
                        " ".join(h["url"] for h in pages[:3])])
            f.flush()
            print(f"[{n}/{len(names)}] {kind:7} {name[:60]}", flush=True)
            if n % 10 == 0:  # checkpoint so a stopped run resumes where it was
                saved.write_text(json.dumps(results + [earlier[x] for x in names[n:] if x in earlier], ensure_ascii=False), encoding="utf-8")
    saved.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
    return results


def apply(path: Path):
    from app import overture, test_inventory
    from app.categories import classify
    from app.db import Audit, Session
    from app.jobs import enqueue
    from app.learned import TEACHER, TEACHER_ACTOR
    from app.spots import upsert_spot

    from app.config import settings

    results = json.loads((path.parent / "lead-check.json").read_text(encoding="utf-8"))
    url = settings().database_url
    if not url.startswith("sqlite:///"):
        sys.exit("Back up this database yourself first; automatic backup handles SQLite only.")
    db_file = Path(url.removeprefix("sqlite:///"))
    if not db_file.is_absolute():
        db_file = ROOT / db_file  # same rule as app/db.py: relative SQLite paths are from the project root
    if not db_file.exists():
        sys.exit(f"Database file not found: {db_file}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = ROOT / "data" / "backups" / f"local-research-{stamp}-pre-favhiker-leads.db"
    backup.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_file) as src, sqlite3.connect(backup) as dst:
        src.backup(dst)
    owner = "local-operator"
    added, publish_ids, skipped = [], [], []
    token = TEACHER.set(TEACHER_ACTOR)
    try:
        with Session() as db:
            for r in results:
                if r["verdict"] == "closed":
                    skipped.append({"name": r["name"], "why": r["why"]})
                    continue
                pages = r["evidence"]["recent"] or r["evidence"]["older"]
                checked = datetime.now(timezone.utc).isoformat()
                data = {
                    "sources": [{"type": "web_candidate", "url": h["url"], "collected_at": checked,
                                 "basis": "Independent page found while checking a lead; branch and details unverified"}
                                for h in pages[:4]],
                    "lead": {"from": "competitor list saved by the owner (name only)", "checked_by": TEACHER_ACTOR,
                             "verdict": r["verdict"], "why": r["why"], "checked_at": checked},
                }
                area, category = "", classify(short(r["name"]))
                if r["overture"]:
                    feature = r["overture"]["feature"]
                    # Our own confidence gate was applied when deciding; read the place fields regardless.
                    item = overture.place({**feature, "properties": {**feature["properties"], "confidence": 1}})
                    if item is None:  # an Overture type our importer doesn't map; keep its point and evidence
                        props = feature.get("properties") or {}
                        address = next(iter(props.get("addresses") or []), {}) or {}
                        item = {
                            "id": feature.get("id"), "name": r["overture"]["name"], "category": None,
                            "type": (props.get("taxonomy") or {}).get("primary") or "",
                            "lat": r["overture"]["lat"], "lng": r["overture"]["lng"], "confidence": r["overture"]["confidence"],
                            "address": ", ".join(x for x in [address.get("freeform"), address.get("locality"), address.get("postcode")] if x),
                            "locality": address.get("locality") or "",
                            "websites": [w for w in props.get("websites") or [] if str(w).startswith("https://")][:3],
                            "socials": [w for w in props.get("socials") or [] if str(w).startswith("https://")][:3],
                            "phones": [str(p) for p in props.get("phones") or []][:2],
                            "datasets": r["overture"]["datasets"],
                        }
                    if item:
                        evidence = overture._evidence(item)
                        evidence["overture"]["confidence"] = r["overture"]["confidence"]
                        data = {**evidence, **data, "sources": evidence["sources"] + data["sources"],
                                "coordinates": overture._point(item)}
                        category = item["category"] or category
                        area = infer_area([item["address"], item["locality"]]) or ""
                row = upsert_spot(db, owner, short(r["name"]), category, area, data)
                if row is None:
                    skipped.append({"name": r["name"], "why": "held back by the name and scope rules"})
                    continue
                db.flush()
                added.append({"id": row.id, "name": row.name, "status": row.status, "verdict": r["verdict"],
                              "has_point": bool(data.get("coordinates"))})
                if r["verdict"] == "active" and data.get("coordinates") and row.status == "identified":
                    publish_ids.append(row.id)
                enqueue(db, "spot_enrich", {"spot_id": row.id}, f"spot-enrich:{row.id}", priority=60)
            db.commit()
            published = test_inventory.publish(db, owner, ids=publish_ids) if publish_ids else {"published": 0}
            db.add(Audit(actor=TEACHER_ACTOR, action="leads.added", target=path.name,
                         detail={"added": len(added), "publish_candidates": len(publish_ids), "backup": backup.name}))
            db.commit()
    finally:
        TEACHER.reset(token)
    receipt = {"backup": str(backup), "added": added, "published": published, "skipped": skipped}
    (path.parent / "added.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"added": len(added), "publish_candidates": len(publish_ids), "skipped": len(skipped),
                      "backup": backup.name, "published": published}, default=str)[:2000])


if __name__ == "__main__":
    target = Path(sys.argv[1])
    if "--apply" in sys.argv:
        apply(target)
    else:
        rows = check(target)
        tally = defaultdict(int)
        for r in rows:
            tally[r["verdict"]] += 1
        print(dict(tally))
