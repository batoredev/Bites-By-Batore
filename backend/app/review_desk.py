"""Quick review desk: walk the owner through the spot-check sheets one row at a time.

Each row is shown with the evidence already gathered for it (matching places, sources,
corroboration, websites, coordinates) and a map, so the owner only answers. Answers are
written straight back into the sheet's last column; nothing else in the sheet changes.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from .auth import admin_user
from .config import ROOT
from .db import Audit, IdentifiedSpot, Venue, get_db

router = APIRouter(prefix="/api/admin/review-desk")

SHEET_DIR = ROOT / "data" / "city-collection"
SHEETS = {
    "decisions": ("spotcheck-claude-decisions-50.csv", {"yes", "no", ""}),
    "overture": ("spotcheck-overture-50.csv", {"yes", "no", "closed", ""}),
}

DECISION_WORDS = {
    ("reject", "not_a_venue"): "I removed this: the name isn't one specific place (it reads like a generic phrase or a page name).",
    ("reject", "out_of_scope"): "I removed this: it falls outside your scope rules.",
    ("reject", "duplicate"): "I removed this as a duplicate of a place we already have.",
    ("real", None): "I confirmed this is a real, specific place.",
}
OTHER_DECISIONS = {
    "same_as": "I merged this into “{d}” because they look like the same place.",
    "distinct": "I kept this apart from “{d}”: I think they are different branches or places.",
    "category": "I changed its category to “{d}”.",
    "rename": "I renamed it to “{d}”.",
    "area": "I set its area to “{d}”.",
}


def _sheet_path(sheet: str) -> Path:
    if sheet not in SHEETS:
        raise HTTPException(404, "Unknown sheet")
    return SHEET_DIR / SHEETS[sheet][0]


def _read(sheet: str) -> tuple[list[str], list[list[str]]]:
    path = _sheet_path(sheet)
    if not path.exists():
        return [], []
    rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
    return (rows[0], rows[1:]) if rows else ([], [])


def _write(sheet: str, header: list[str], rows: list[list[str]]) -> None:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    _sheet_path(sheet).write_text(out.getvalue(), encoding="utf-8-sig")


def _short(value, limit: int = 90) -> str:
    if isinstance(value, dict):
        for key in ("title", "name", "label", "kind", "type", "source", "url", "value", "text"):
            if value.get(key):
                return str(value[key])[:limit]
        return json.dumps(value, ensure_ascii=False)[:limit]
    return str(value)[:limit]


def _list(value, limit: int = 4) -> list[str]:
    if not value:
        return []
    items = value if isinstance(value, list) else [value]
    return [s for s in (_short(v) for v in items[:limit]) if s]


def _coords(data: dict, venue) -> list[float] | None:
    if venue is not None and venue.lat and venue.lng:
        return [float(venue.lat), float(venue.lng)]
    c = data.get("coordinates")
    try:
        if isinstance(c, dict) and c.get("lat") and (c.get("lng") or c.get("lon")):
            return [float(c["lat"]), float(c.get("lng") or c.get("lon"))]
        if isinstance(c, (list, tuple)) and len(c) == 2:
            return [float(c[0]), float(c[1])]
    except (TypeError, ValueError):
        return None
    return None


def _evidence(db, name: str) -> list[dict]:
    """Every stored place with this exact name (case-insensitive), with what we know about it."""
    key = (name or "").strip().lower()
    if not key:
        return []
    out = []
    spots = db.execute(select(IdentifiedSpot).where(func.lower(IdentifiedSpot.name) == key).limit(4)).scalars().all()
    for spot in spots:
        data = spot.data if isinstance(spot.data, dict) else json.loads(spot.data or "{}")
        venue = db.get(Venue, spot.venue_id) if spot.venue_id else None
        corr = data.get("corroboration")
        out.append({
            "name": spot.name, "area": spot.area or (venue.area if venue else ""), "category": spot.category,
            "status": spot.status, "coords": _coords(data, venue),
            "address": (venue.address if venue and venue.address else ", ".join(_list(data.get("address_clues"), 2))),
            "sources": _list(data.get("sources")),
            "corroboration": _short(corr, 40) if corr else "",
            "websites": _list(data.get("website_candidates"), 2),
            "search": _list(data.get("web_search_results"), 3),
            "notes": _list(data.get("review_notes"), 2),
            "taught": bool(data.get("taught_by")),
        })
    if not out:
        for venue in db.execute(select(Venue).where(func.lower(Venue.name) == key).limit(4)).scalars().all():
            out.append({"name": venue.name, "area": venue.area, "category": venue.category, "status": venue.status,
                        "coords": [float(venue.lat), float(venue.lng)] if venue.lat and venue.lng else None,
                        "address": venue.address or "", "sources": [], "corroboration": "", "websites": [],
                        "search": [], "notes": [], "taught": False})
    return out


def _embed(name: str, coords) -> str:
    if coords:
        return f"https://maps.google.com/maps?q={coords[0]},{coords[1]}&z=17&output=embed"
    return f"https://maps.google.com/maps?q={quote_plus(name + ' Coimbatore')}&z=14&output=embed"


def _decision_item(db, row: list[str], index: int) -> dict:
    decision, name, detail, note, link = (row + [""] * 6)[:5]
    answer = row[5].strip().lower() if len(row) > 5 else ""
    claim = (DECISION_WORDS.get((decision, detail)) or DECISION_WORDS.get((decision, None))
             or OTHER_DECISIONS.get(decision, "{d}").format(d=detail or decision))
    matches = _evidence(db, name)
    coords = next((m["coords"] for m in matches if m["coords"]), None)
    hints = [f"{len(matches)} stored places share this name."] if len(matches) > 1 else []
    if note:
        hints.append(note)
    return {"sheet": "decisions", "row": index, "title": name, "question": "Was I right?",
            "claim": claim, "answer": answer, "options": ["yes", "no"], "maps_link": link,
            "embed": _embed(name, coords), "matches": matches, "hints": hints}


def _overture_item(db, row: list[str], index: int) -> dict:
    name, category, area, confidence, link = (row + [""] * 6)[:5]
    answer = row[5].strip().lower() if len(row) > 5 else ""
    matches = _evidence(db, name)
    coords = next((m["coords"] for m in matches if m["coords"]), None)
    hints = []
    try:
        hints.append(f"Overture is {round(float(confidence) * 100)}% sure about this place.")
    except ValueError:
        pass
    multi = [m for m in matches if "multi" in (m["corroboration"] or "")]
    hints.append("Another source agrees it exists." if multi else "Only Overture knows this place so far.")
    if len(matches) > 1:
        hints.append(f"{len(matches)} branches share this name; the map shows the first one.")
    return {"sheet": "overture", "row": index, "title": name, "question": "Does this place exist, and is it right?",
            "claim": f"A {category or 'place'} in {area or 'Coimbatore'}, from Overture Maps.", "answer": answer,
            "options": ["yes", "no", "closed"], "maps_link": link, "embed": _embed(name, coords),
            "matches": matches, "hints": hints}


@router.get("/items")
def items(user=Depends(admin_user), db=Depends(get_db)):
    out = []
    for sheet, build in (("decisions", _decision_item), ("overture", _overture_item)):
        _, rows = _read(sheet)
        out.extend(build(db, row, i) for i, row in enumerate(rows) if any(cell.strip() for cell in row))
    return {"items": out, "total": len(out), "done": sum(1 for i in out if i["answer"])}


class Answer(BaseModel):
    sheet: str
    row: int
    answer: str


@router.post("/answer")
def answer(body: Answer, user=Depends(admin_user), db=Depends(get_db)):
    value = body.answer.strip().lower()
    if body.sheet not in SHEETS or value not in SHEETS[body.sheet][1]:
        raise HTTPException(400, "Unsupported answer")
    header, rows = _read(body.sheet)
    if not 0 <= body.row < len(rows):
        raise HTTPException(404, "No such row")
    row = rows[body.row]
    width = max(len(header), 6)
    row.extend([""] * (width - len(row)))
    row[width - 1] = value
    _write(body.sheet, header, rows)
    name = row[1] if body.sheet == "decisions" else row[0]
    db.add(Audit(actor=str(getattr(user, "id", None) or user), action="review_desk.answer",
                 target=f"{body.sheet}:{body.row}", detail={"answer": value, "name": name}))
    db.commit()
    return {"ok": True, "sheet": body.sheet, "row": body.row, "answer": value}
