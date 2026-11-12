"""Find coordinates for reel-derived drafts with the public OpenStreetMap geocoder.

A match needs a place-type result inside the Coimbatore box whose name agrees
with the draft. Ambiguous multi-branch names without an area are left alone.
Coordinates stay unverified leads; this never approves a location.
"""

import json
import re
import time
from difflib import SequenceMatcher

from sqlalchemy import select

from .categories import FOOD
from .config import ROOT
from .db import IdentifiedSpot, now
from .spot_identity import name_key, quality_issues, signature

URL = "https://nominatim.openstreetmap.org/search"
AGENT = "BitesByBatore-LocalResearch/0.1 (bounded city POI research)"
BOX = "76.70,11.35,77.25,10.75"  # left, top, right, bottom
CENTRE = (11.0168, 76.9558)
PLACE_CLASSES = {"amenity", "leisure", "tourism", "shop", "sport", "craft", "club"}
ATTRIBUTION = {
    "attribution": "© OpenStreetMap contributors",
    "url": "https://www.openstreetmap.org/copyright",
    "license": "ODbL 1.0",
}


def names_agree(draft, found):
    a, b = name_key(draft).replace(" ", ""), name_key(found).replace(" ", "")
    if not a or not b:
        return False
    left, right = set(signature(draft).split()), set(signature(found).split())
    return a == b or (len(left) >= 1 and left == right) or SequenceMatcher(None, a, b).ratio() >= 0.93


def choose(name, area, results):
    from .planner import km

    hits = []
    for item in results:
        try:
            point = (float(item["lat"]), float(item["lon"]))
        except (KeyError, TypeError, ValueError):
            continue
        found = item.get("name") or str(item.get("display_name", "")).split(",")[0]
        if item.get("category", item.get("class")) not in PLACE_CLASSES or km(point, CENTRE) > 40:
            continue
        if names_agree(name, found):
            hits.append((point, found, item))
    if not hits:
        return None, "no_match"
    if area:
        local = [h for h in hits if name_key(area) in name_key(h[2].get("display_name", ""))]
        hits = local or hits
    # Several distant results are different branches; do not guess which one.
    if len(hits) > 1 and max(km(hits[0][0], h[0]) for h in hits) > 0.5:
        return None, "several_branches"
    return hits[0], "matched"


LINK_POINT = re.compile(
    r"(?:destination|query|q|ll)=(-?\d{1,2}\.\d{3,})(?:,|%2C)(-?\d{1,3}\.\d{3,})"
    r"|@(-?\d{1,2}\.\d{3,}),(-?\d{1,3}\.\d{3,})"
    r"|!3d(-?\d{1,2}\.\d{3,})!4d(-?\d{1,3}\.\d{3,})"
)


def link_points(links):
    points = []
    for link in links:
        for groups in LINK_POINT.findall(str(link)):
            numbers = [g for g in groups if g]
            points.append((float(numbers[0]), float(numbers[1]), str(link)))
    return points


def coordinates_from_links(db, owner):
    """Use a Maps coordinate already collected for the draft when every link agrees."""
    from .planner import km

    counts = {"set": 0, "links_disagree": 0, "outside_40_km": 0}
    for row in db.scalars(
        select(IdentifiedSpot).where(IdentifiedSpot.user_id == owner, IdentifiedSpot.status == "identified")
    ):
        if row.venue_id or row.data.get("coordinates"):
            continue
        points = link_points(row.data.get("maps_links", []))
        if not points:
            continue
        first = points[0]
        if any(km(first[:2], p[:2]) > 0.3 for p in points):
            counts["links_disagree"] += 1
            continue
        if km(first[:2], CENTRE) > 40:
            counts["outside_40_km"] += 1
            continue
        row.data = {
            **row.data,
            "coordinates": {
                "lat": first[0],
                "lng": first[1],
                "source_url": first[2],
                "basis": "Coordinate in a Maps link collected from the venue's web pages; branch unverified",
            },
        }
        row.updated_at = now()
        counts["set"] += 1
    db.flush()
    return counts


def geocode_drafts(db, owner, limit=2000, sleep=time.sleep):
    import httpx

    folder = ROOT / "data" / "city-collection"
    folder.mkdir(parents=True, exist_ok=True)
    cache_file = folder / "geocode-cache.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
    rows = [
        r
        for r in db.scalars(
            select(IdentifiedSpot).where(
                IdentifiedSpot.user_id == owner, IdentifiedSpot.status == "identified"
            )
        )
        if not r.venue_id
        and not r.data.get("coordinates")
        and not r.data.get("geocode")
        and not quality_issues(r.name, r.area, r.data)
    ]
    # Activities are scarce in the directory import, so look those up first.
    rows.sort(key=lambda r: (r.category in FOOD, -len(r.data.get("sources", []))))
    counts = {"matched": 0, "no_match": 0, "several_branches": 0, "requests": 0, "failed": 0}
    with httpx.Client(timeout=25, follow_redirects=False, trust_env=False) as client:
        for row in rows[:limit]:
            queries = [f"{row.name}, {row.area}, Coimbatore"] if row.area else []
            queries.append(f"{row.name}, Coimbatore")
            hit, status = None, "no_match"
            for query in queries:
                if query not in cache:
                    try:
                        response = client.get(
                            URL,
                            params={
                                "q": query,
                                "format": "jsonv2",
                                "limit": 6,
                                "viewbox": BOX,
                                "bounded": 1,
                                "countrycodes": "in",
                            },
                            headers={"User-Agent": AGENT},
                        )
                        counts["requests"] += 1
                        sleep(1.2)  # public geocoder policy: at most one request per second
                        if response.status_code != 200:
                            counts["failed"] += 1
                            if response.status_code in {403, 429, 503}:
                                db.commit()
                                cache_file.write_text(json.dumps(cache), encoding="utf-8")
                                return {**counts, "stopped": f"geocoder returned {response.status_code}"}
                            continue
                        cache[query] = response.json()
                    except (httpx.HTTPError, ValueError):
                        counts["failed"] += 1
                        continue
                hit, status = choose(row.name, row.area, cache[query])
                if hit:
                    break
            counts[status] += 1
            record = {"at": now(), "status": status}
            data = {**row.data, "geocode": record}
            if hit:
                point, found, item = hit
                url = f"https://www.openstreetmap.org/{item.get('osm_type', 'node')}/{item.get('osm_id', '')}"
                data["geocode"] = {**record, "matched_name": found, "source_url": url}
                data["coordinates"] = {
                    "lat": point[0],
                    "lng": point[1],
                    "source_url": url,
                    "basis": "OpenStreetMap geocoder name match; exact branch unverified",
                }
                licences = data.get("source_licenses", [])
                if ATTRIBUTION not in licences:
                    data["source_licenses"] = [*licences, ATTRIBUTION]
            row.data, row.updated_at = data, now()
            if (counts["matched"] + counts["no_match"] + counts["several_branches"]) % 25 == 0:
                db.commit()
                cache_file.write_text(json.dumps(cache), encoding="utf-8")
    db.commit()
    cache_file.write_text(json.dumps(cache), encoding="utf-8")
    return {**counts, "considered": min(len(rows), limit)}
