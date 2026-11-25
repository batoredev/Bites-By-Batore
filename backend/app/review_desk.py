"""Quick review desk: walk the owner through the spot-check sheets one row at a time.

Each row is shown with the evidence already gathered for it (matching places, sources,
corroboration, websites, coordinates) and a map, so the owner only answers. Answers are
written straight back into the sheet's last column; nothing else in the sheet changes.
"""
from __future__ import annotations

import csv
import hashlib
import io
import ipaddress
import json
import re
import socket
import subprocess
import sys
import threading
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
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


def _evidence(db, name: str) -> tuple[list[dict], list[dict]]:
    """Every stored place with this exact name (case-insensitive), what we know about it, and its source links."""
    key = (name or "").strip().lower()
    if not key:
        return [], []
    out, raw = [], []
    spots = db.execute(select(IdentifiedSpot).where(func.lower(IdentifiedSpot.name) == key).limit(4)).scalars().all()
    for spot in spots:
        data = spot.data if isinstance(spot.data, dict) else json.loads(spot.data or "{}")
        raw.append(data)
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
    return out, _links(raw)


SOURCE_LABELS = {
    "instagram": "Instagram post", "overture": "Overture listing", "openstreetmap": "OpenStreetMap",
    "monitored_page": "Watched page", "web_candidate": "Web page", "web": "Web page", "website": "Website",
}
INSTAGRAM_POST = re.compile(r"^https://(?:www\.)?instagram\.com/(?:[\w.]+/)?(p|reel|tv)/([\w-]+)")


def _host(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def source_embed(url: str) -> str:
    """A frame URL the source's own site allows, when one is known without fetching anything."""
    post = INSTAGRAM_POST.match(url)
    if post:
        return f"https://www.instagram.com/{post.group(1)}/{post.group(2)}/embed/"
    if _host(url) in {"facebook.com", "m.facebook.com"}:
        return f"https://www.facebook.com/plugins/page.php?href={quote_plus(url)}&tabs=timeline&width=500&height=600"
    return ""


def _links(spot_data: list[dict]) -> list[dict]:
    """Every distinct https source link behind the matching places, Instagram first."""
    seen, out = set(), []
    for data in spot_data:
        entries = [(s.get("type") or "web", s.get("url")) for s in data.get("sources") or [] if isinstance(s, dict)]
        entries += [("website", w) for w in data.get("website_candidates") or [] if isinstance(w, str)]
        for kind, url in entries:
            if not isinstance(url, str) or not url.startswith("https://") or url in seen:
                continue
            seen.add(url)
            out.append({"kind": kind, "label": f"{SOURCE_LABELS.get(kind, 'Source')} · {_host(url)}",
                        "url": url, "embed": source_embed(url)})
    out.sort(key=lambda link: link["kind"] != "instagram")
    return out[:8]


def _embed(name: str, coords) -> str:
    if coords:
        return f"https://maps.google.com/maps?q={coords[0]},{coords[1]}&z=17&output=embed"
    return f"https://maps.google.com/maps?q={quote_plus(name + ' Coimbatore')}&z=14&output=embed"


def _decision_item(db, row: list[str], index: int) -> dict:
    decision, name, detail, note, link = (row + [""] * 6)[:5]
    answer = row[5].strip().lower() if len(row) > 5 else ""
    claim = (DECISION_WORDS.get((decision, detail)) or DECISION_WORDS.get((decision, None))
             or OTHER_DECISIONS.get(decision, "{d}").format(d=detail or decision))
    matches, links = _evidence(db, name)
    coords = next((m["coords"] for m in matches if m["coords"]), None)
    hints = [f"{len(matches)} stored places share this name."] if len(matches) > 1 else []
    if note:
        hints.append(note)
    return {"sheet": "decisions", "row": index, "title": name, "question": "Was I right?",
            "claim": claim, "answer": answer, "options": ["yes", "no"], "maps_link": link,
            "embed": _embed(name, coords), "matches": matches, "links": links, "hints": hints}


def _overture_item(db, row: list[str], index: int) -> dict:
    name, category, area, confidence, link = (row + [""] * 6)[:5]
    answer = row[5].strip().lower() if len(row) > 5 else ""
    matches, links = _evidence(db, name)
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
            "matches": matches, "links": links, "hints": hints}


@router.get("/items")
def items(user=Depends(admin_user), db=Depends(get_db)):
    out = []
    for sheet, build in (("decisions", _decision_item), ("overture", _overture_item)):
        _, rows = _read(sheet)
        out.extend(build(db, row, i) for i, row in enumerate(rows) if any(cell.strip() for cell in row))
    return {"items": out, "total": len(out), "done": sum(1 for i in out if i["answer"])}


class _PageMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}
        self._in_title = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key in {"og:title", "og:description", "description", "og:site_name"} and a.get("content"):
                self.meta.setdefault(key, a["content"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and len(self.title) < 200:
            self.title += data


def _frame_blocked(headers) -> bool:
    if headers.get("x-frame-options"):
        return True
    for directive in headers.get("content-security-policy", "").split(";"):
        parts = directive.split()
        if parts and parts[0].lower() == "frame-ancestors":
            return "*" not in parts[1:]
    return False


def _public_https(url: str) -> bool:
    p = urlparse(url)
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in (None, 443):
        return False
    try:
        addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
    except OSError:
        return False
    return bool(addresses) and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses)


PREVIEW_CACHE: dict[str, dict] = {}


def page_preview(url: str, fetch=None) -> dict:
    """Whether a source page can be shown in a frame here, plus its title and summary for when it can't."""
    if url in PREVIEW_CACHE:
        return PREVIEW_CACHE[url]
    embed = source_embed(url)
    result = {"url": url, "embed": embed, "frameable": bool(embed), "status": 0, "title": "", "description": "", "site": _host(url)}
    current = url
    try:
        with (fetch or httpx.Client(timeout=6, follow_redirects=False, trust_env=False)) as client:
            for _ in range(4):
                if not _public_https(current):
                    result["error"] = "The page isn't on a public https address."
                    break
                with client.stream("GET", current, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; BatoreReviewDesk/1.0)", "Accept": "text/html"}) as r:
                    if r.is_redirect and r.headers.get("location"):
                        current = urljoin(current, r.headers["location"])
                        continue
                    result["status"] = r.status_code
                    result["url"] = current
                    if not embed:
                        result["frameable"] = r.status_code == 200 and not _frame_blocked(r.headers)
                    if "html" in r.headers.get("content-type", ""):
                        raw = bytearray()
                        for chunk in r.iter_bytes():
                            raw.extend(chunk)
                            if len(raw) > 512 * 1024:
                                break
                        parser = _PageMeta()
                        parser.feed(raw.decode("utf-8", errors="replace"))
                        m = parser.meta
                        result["title"] = unescape((m.get("og:title") or parser.title).strip())[:160]
                        result["description"] = unescape((m.get("og:description") or m.get("description") or "").strip())[:300]
                        result["site"] = m.get("og:site_name") or result["site"]
                    break
    except httpx.HTTPError:
        result["error"] = "The page didn't answer."
    if len(PREVIEW_CACHE) > 500:
        PREVIEW_CACHE.clear()
    PREVIEW_CACHE[url] = result
    return result


@router.get("/preview")
def preview(url: str, user=Depends(admin_user)):
    if not url.startswith("https://"):
        raise HTTPException(400, "Only https source links can be previewed")
    return page_preview(url)


SHOT_DIR = ROOT / "data" / "review-desk-shots"
_SHOT_LOCK = threading.Lock()


def page_shot_path(url: str, run=subprocess.run) -> Path | None:
    """A cached JPEG of the page as a browser renders it, for sites that refuse to be framed."""
    path = SHOT_DIR / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".jpg")
    failed = path.with_suffix(".failed")  # sites that show automated browsers nothing aren't retried
    if path.exists():
        return path
    if failed.exists() or not _public_https(url):
        return None
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    with _SHOT_LOCK:  # one browser at a time
        if not path.exists():
            try:
                run([sys.executable, "-m", "app.page_shot", url, str(path)], cwd=str(ROOT / "backend"),
                    timeout=40, capture_output=True, check=False)
            except subprocess.TimeoutExpired:
                pass
    if path.exists() and path.stat().st_size > 0:
        return path
    failed.write_text(url, encoding="utf-8")
    return None


@router.get("/shot")
def shot(url: str, user=Depends(admin_user)):
    if not url.startswith("https://"):
        raise HTTPException(400, "Only https source links can be shown")
    path = page_shot_path(url)
    if path is None:
        raise HTTPException(404, "The page couldn't be rendered")
    return FileResponse(path, media_type="image/jpeg")


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
