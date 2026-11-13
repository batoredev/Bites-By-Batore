"""Bounded open-directory collection and honest Coimbatore coverage reporting."""

import hashlib
import json
import math
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from sqlalchemy import select
from .config import ROOT, settings
from .db import IdentifiedSpot, Investigation, ResearchSource, Counter, now
from .providers import Unavailable, DeferredCollection, renew_job
from .spots import upsert_spot, merge_data, lock_inventory, INACTIVE
from .spot_identity import name_key, names_match, infer_area, quality_issues, branch_clues
from .planner import km

ATTRIBUTION = "© OpenStreetMap contributors"
LICENSE_URL = "https://www.openstreetmap.org/copyright"
QUERY = (
    '[out:json][timeout:120];rel["boundary"="administrative"]["name"~"Coimbatore",i](10.4,76.5,11.6,77.5)'
    "->.boundary;.boundary out tags bb;.boundary map_to_area->.a;("
    + "".join(
        f'nwr(area.a)["name"]{selector}(10.75,76.65,11.35,77.3);'
        for selector in (
            '["amenity"~"^(restaurant|cafe|fast_food|food_court|ice_cream|cinema|bar|pub|nightclub)$"]',
            '["shop"~"^(bakery|confectionery|pastry|tea|coffee)$"]',
            '["leisure"~"^(park|garden|amusement_arcade|bowling_alley|miniature_golf|escape_game|water_park|trampoline_park|indoor_play|sports_centre)$"]',
            '["leisure"="pitch"]["sport"~"^(soccer|cricket|futsal|badminton|tennis)$"]',
            '["sport"~"^(karting|bowling|climbing|paintball)$"]',
            '["tourism"~"^(museum|zoo|aquarium|theme_park|gallery)$"]',
        )
    )
    + ");out center;"
)


def area_scope(payload):
    boundaries = [
        e
        for e in payload.get("elements", [])
        if e.get("type") == "relation"
        and e.get("tags", {}).get("boundary") == "administrative"
        and e.get("tags", {}).get("name", "").casefold() == "coimbatore"
        and e.get("tags", {}).get("admin_level") == "5"
    ]
    if not boundaries:
        raise Unavailable("Coimbatore administrative boundary missing; broad-radius fallback disabled")
    return {
        "boundary_refs": ["relation/" + str(e["id"]) for e in boundaries],
        "name": "Coimbatore district within the existing 40km operating radius",
        "basis": "OSM administrative-area query; not independent municipal/branch verification",
    }


def category(tags):
    amenity, leisure, sport = tags.get("amenity"), tags.get("leisure"), tags.get("sport")
    from .categories import match

    shop = tags.get("shop")
    if shop in {"bakery", "confectionery", "pastry"}:
        return "dessert"
    if shop in {"tea", "coffee"}:
        return "cafe"

    named = match(tags.get("name", ""))
    if amenity == "ice_cream":
        return "dessert"
    if amenity in {"bar", "pub", "nightclub"}:
        return "nightlife"
    if amenity in {"restaurant", "fast_food", "food_court"}:
        # The directory tag proves it serves food; the name only picks the kind.
        return named if named in {"street_food", "dessert", "cafe", "nightlife"} else "food"
    if amenity in {"cafe", "cinema"}:
        return amenity
    if leisure in {"park", "garden"}:
        return "park"
    if leisure in {"amusement_arcade", "indoor_play"}:
        return "gaming"
    if leisure == "trampoline_park":
        return "adventure"
    if leisure in {"sports_centre", "pitch"}:
        return "sports"
    if leisure == "bowling_alley" or sport == "bowling":
        return "bowling"
    if leisure == "water_park" or tags.get("tourism") == "theme_park":
        return "amusement"
    if tags.get("tourism") in {"museum", "zoo", "aquarium", "gallery"}:
        return "attraction"
    if leisure in {"miniature_golf", "escape_game"} or sport in {
        "karting",
        "climbing",
        "paintball",
    }:
        return "adventure"
    return None


def coordinates(element):
    point = element.get("center", element)
    try:
        lat, lng = float(point["lat"]), float(point["lon"])
        if not math.isfinite(lat + lng) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return None
        if km((lat, lng), (11.0168, 76.9558)) > 40:
            return None
        return {
            "lat": lat,
            "lng": lng,
            "basis": "OpenStreetMap point or geometry centre; exact branch/entrance unverified",
        }
    except (KeyError, TypeError, ValueError):
        return None


def public_link(value):
    import ipaddress

    try:
        p = urlparse(value)
        if p.scheme == "https" and p.hostname and not p.username and not p.password and p.port in (None, 443):
            if p.hostname in {"localhost", "localhost.localdomain"} or p.hostname.endswith(".local"):
                return None
            try:
                if not ipaddress.ip_address(p.hostname).is_global:
                    return None
            except ValueError:
                pass
            return value
    except ValueError:
        pass
    return None


def import_directory(db, user_id, payload, fetched_at=None, scope=None):
    if payload.get("remark") or not isinstance(payload.get("elements"), list):
        raise Unavailable("Directory response is incomplete or malformed; no completeness claim can be made")
    fetched_at = fetched_at or now()
    counts = {
        "received": len(payload["elements"]),
        "created": 0,
        "updated": 0,
        "held": 0,
        "outside_or_unsupported": 0,
    }
    rows = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id)))
    for element in payload["elements"]:
        renew_job(db)
        tags = element.get("tags", {})
        name = tags.get("name:en") or tags.get("name")
        point = coordinates(element)
        kind = category(tags)
        ref = f"{element.get('type')}/{element.get('id')}"
        if (
            not name
            or not kind
            or not point
            or element.get("type") not in {"node", "way", "relation"}
            or type(element.get("id")) is not int
            or element["id"] <= 0
        ):
            counts["outside_or_unsupported"] += 1
            continue
        url = "https://www.openstreetmap.org/" + ref
        parts = [
            tags[k]
            for k in ("addr:housenumber", "addr:street", "addr:suburb", "addr:city", "addr:postcode")
            if tags.get(k)
        ]
        address = ", ".join(parts) if tags.get("addr:street") else ""
        area = infer_area(parts) or str(tags.get("addr:suburb", ""))[:100]
        data = {
            "directory_refs": [ref],
            "aliases": [n for n in (tags.get("name"), tags.get("name:en")) if n],
            "sources": [
                {
                    "url": url,
                    "type": "openstreetmap",
                    "collected_at": fetched_at,
                    "published_at": None,
                    "basis": "Crowdsourced directory lead, not a current operating/Maps verification",
                    "attribution": ATTRIBUTION,
                    "license_url": LICENSE_URL,
                }
            ],
            "source_licenses": [{"attribution": ATTRIBUTION, "url": LICENSE_URL, "license": "ODbL 1.0"}],
            "address_clues": parts,
            "coordinates": point,
            "strict_identity": True,
            "review_notes": [
                "Directory name, location and tags require independent branch and current-fact review"
            ],
        }
        if scope:
            data["directory_scope"] = scope
        if address:
            data["address"] = address
        if tags.get("opening_hours"):
            data["hours_candidates"] = [
                {
                    "value": tags["opening_hours"],
                    "source_url": url,
                    "basis": "OSM raw tag; current hours unverified",
                }
            ]
        if tags.get("cuisine"):
            data["cuisine_candidates"] = [t.strip() for t in tags["cuisine"].split(";") if t.strip()]
        links = [public_link(tags.get(k, "")) for k in ("website", "contact:website", "website:menu")]
        data["website_candidates"] = [x for x in links if x]
        if tags.get("outdoor_seating") == "yes":
            data["vibes"] = [
                {
                    "tag": "outdoor",
                    "source_url": url,
                    "basis": "OSM outdoor_seating tag; unverified",
                    "evidence": "outdoor_seating=yes",
                }
            ]
        existing = next((r for r in rows if ref in r.data.get("directory_refs", [])), None)
        visited = set()
        while existing and existing.status == "merged":
            if existing.id in visited:
                raise Unavailable("Cyclic merged directory identity requires operator review")
            visited.add(existing.id)
            target = db.get(IdentifiedSpot, existing.data.get("merged_into"))
            if not target or target.user_id != user_id:
                raise Unavailable("Missing or inaccessible merged directory identity")
            existing = target
        if existing is None:
            # Directory node/way duplicates can represent one footprint. Require
            # the same name, nearby centres and no conflicting house/postcode.
            nearby = []
            for row in rows:
                if row.status in INACTIVE or not names_match(row.name, name):
                    continue
                coord = row.data.get("coordinates", {})
                if coord.get("lat") is None or coord.get("lng") is None:
                    continue
                a, b = branch_clues(row.data), branch_clues(data)
                if any(a[k] and b[k] and a[k] != b[k] for k in a):
                    continue
                if row.data.get("address") and address and name_key(row.data["address"]) != name_key(address):
                    continue
                if (
                    name_key(row.name) == name_key(name)
                    and km((coord["lat"], coord["lng"]), (point["lat"], point["lng"])) <= 0.025
                ):
                    nearby.append(row)
            if len(nearby) == 1:
                existing = nearby[0]
        if existing is not None:
            lock_inventory(db)
            db.refresh(existing)
            existing.data = merge_data(existing.data, data)
            existing.updated_at = now()
            row = existing
            counts["updated"] += 1
        else:
            old_ids = {r.id for r in rows}
            row = upsert_spot(db, user_id, name, kind, area, data)
            if row is None:
                # Retain unusual named map candidates for review, not as active locations.
                ident = hashlib.sha256(f"{user_id}|osm|{ref}".encode()).hexdigest()
                row = db.scalar(select(IdentifiedSpot).where(IdentifiedSpot.identity_key == ident))
                if row is None:
                    row = IdentifiedSpot(
                        user_id=user_id,
                        identity_key=ident,
                        name=name[:150],
                        category=kind,
                        area=area,
                        data={**data, "quality_issues": quality_issues(name, area, data)},
                        status="quarantined",
                    )
                    db.add(row)
                    db.flush()
            if row.id not in old_ids:
                rows.append(row)
                counts["created"] += 1
            else:
                counts["updated"] += 1
        if tags.get("disused") == "yes" or tags.get("abandoned") == "yes":
            if not row.venue_id:
                row.status = "quarantined"
                row.data = {
                    **row.data,
                    "quality_issues": [
                        "Directory marks disused/abandoned; independent operating review required"
                    ],
                }
        counts["held"] += int(row.status in INACTIVE)
        db.commit()
    return {
        **counts,
        "at": now(),
        "published": 0,
        "city_complete": False,
        "attribution": ATTRIBUTION,
        "scope": scope or "Unverified directory candidates; no independent boundary check",
    }


def reconcile_scope(db, user_id, payload, scope):
    """Retain earlier broad-search originals, but keep out-of-area leads held."""
    allowed = {
        f"{e.get('type')}/{e.get('id')}"
        for e in payload["elements"]
        if coordinates(e) and category(e.get("tags", {}))
    }
    held = []
    for row in db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id)):
        refs = set(row.data.get("directory_refs", []))
        if not refs or refs & allowed or row.status in INACTIVE:
            continue
        lock_inventory(db)
        db.refresh(row)
        row.data = merge_data(
            row.data,
            {
                "directory_scope_review": {
                    "scope": scope,
                    "at": now(),
                    "reason": "Earlier directory reference not present in scoped extract; independently check geography/continued existence",
                },
                "quality_issues": [
                    "Directory geographic scope/continued existence needs review; original retained"
                ],
            },
        )
        if row.venue_id:
            from .maintenance import alert, hold_published

            alert(row, "directory_scope", "", {"scope": scope})
            hold_published(db, row, "Directory geographic scope mismatch")
        else:
            row.status = "quarantined"
        row.updated_at = now()
        held.append(row.id)
        db.commit()
    return held


def collect_directory(db, user_id):
    import httpx

    folder = ROOT / "data" / "city-collection"
    folder.mkdir(parents=True, exist_ok=True)
    cached = folder / "osm-coimbatore-candidates.json"
    receipt = folder / "osm-fetch.json"
    recent = False
    if cached.exists() and receipt.exists():
        try:
            meta = json.loads(receipt.read_text(encoding="utf-8"))
            at = datetime.fromisoformat(meta["at"])
            recent = meta.get("query") == QUERY and timedelta(0) <= datetime.now(
                timezone.utc
            ) - at < timedelta(days=7)
        except (KeyError, ValueError, TypeError):
            pass
    if not recent:
        week = datetime.now(timezone.utc).strftime("%G-%V")
        from .collection_control import bulk_enabled, count_request

        if not count_request(db, "city-directory:" + user_id + ":" + week, 0 if bulk_enabled() else 2):
            raise DeferredCollection("Weekly open-directory request allowance reached", 86400)
        with httpx.Client(timeout=110, follow_redirects=False, trust_env=False) as client:
            response = client.post(
                settings().city_directory_url,
                data={"data": QUERY},
                headers={"User-Agent": "BitesByBatore-LocalResearch/0.1 (bounded city POI research)"},
            )
            if response.status_code in {429, 503, 504}:
                raise DeferredCollection("Open-directory server busy; cached work retained", 3600)
            response.raise_for_status()
            payload = response.json()
        if payload.get("remark"):
            raise Unavailable("Open-directory response was partial")
        area_scope(payload)
        cached.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        receipt.write_text(
            json.dumps(
                {
                    "at": now(),
                    "attribution": ATTRIBUTION,
                    "license": LICENSE_URL,
                    "endpoint": settings().city_directory_url,
                    "query": QUERY,
                    "elements": len(payload.get("elements", [])),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    payload = json.loads(cached.read_text(encoding="utf-8"))
    if payload.get("remark"):
        raise Unavailable("Cached open-directory response was partial")
    scope = area_scope(payload)
    result = import_directory(
        db,
        user_id,
        payload,
        json.loads(receipt.read_text(encoding="utf-8"))["at"],
        scope=scope,
    )
    result["scope_holds"] = len(reconcile_scope(db, user_id, payload, scope))
    return result


def coverage(db, user_id):
    from .frontier import AREAS, CATEGORIES, CITY_TOPICS
    from .collection_control import daily_limits

    rows = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == user_id)))
    active = [r for r in rows if r.status not in INACTIVE]
    cases = list(db.scalars(select(Investigation).where(Investigation.user_id == user_id)))
    grid = []
    for area in AREAS:
        for topic in CATEGORIES:
            query = f"Coimbatore {topic} {area}"
            found = [c for c in cases if c.query == query]
            grid.append(
                {
                    "area": area,
                    "topic": topic,
                    "query": query,
                    "state": max(found, key=lambda c: c.created_at).state if found else "not_scheduled",
                }
            )
    return {
        "at": now(),
        "city": "Coimbatore",
        "collection_limits": daily_limits(),
        "active_drafts": len(active),
        "retained_originals": len(rows),
        "directory_linked": sum(bool(r.data.get("directory_refs")) for r in active),
        "missing_menu_or_price": sum(
            not (r.data.get("offerings") or r.data.get("menu_links")) for r in active
        ),
        "missing_hours_observation": sum(
            not (r.data.get("hours") or r.data.get("hours_candidates")) for r in active
        ),
        "missing_vibes": sum(not r.data.get("vibes") for r in active),
        "maps_unreviewed": sum(not r.data.get("maps_identity", {}).get("confirmed_by") for r in active),
        "discovery_queries": len(grid),
        "queries_scheduled": sum(c["state"] != "not_scheduled" for c in grid),
        "grid": grid,
        "city_topics": [
            {
                "topic": topic,
                "query": f"Coimbatore {topic}",
                "state": next(
                    (
                        c.state
                        for c in sorted(cases, key=lambda c: c.created_at, reverse=True)
                        if c.query == f"Coimbatore {topic}"
                    ),
                    "not_scheduled",
                ),
            }
            for topic in CITY_TOPICS
        ],
        "city_complete": False,
        "source_attribution": ATTRIBUTION,
        "limitation": "Finite search grid and directory coverage are not an exhaustive venue census. Current facts, exact branches and operator approvals remain required.",
    }


def start_collection(db, user_id):
    from .jobs import enqueue

    pause = db.get(Counter, "research_paused")
    if pause:
        pause.value = 0
        db.commit()
    week = datetime.now(timezone.utc).strftime("%G-%V")
    directory = enqueue(
        db, "city_directory", {"user_id": user_id}, f"city-directory-v2:{user_id}:{week}", priority=96
    )
    queued = []
    for source in db.scalars(
        select(ResearchSource)
        .join(Investigation, ResearchSource.case_id == Investigation.id)
        .where(Investigation.user_id == user_id, Investigation.state != "cancelled")
    ):
        if (
            source.content.get("caption")
            and source.analysis.get("caption", {}).get("status") != "observations_only"
        ):
            job = enqueue(
                db,
                "source_quality_upgrade",
                {"user_id": user_id, "source_id": source.id, "case_id": source.case_id},
                f"city-caption:{source.id}",
                priority=94,
            )
            queued.append(job.id)
    return {
        "directory_job_id": directory.id,
        "caption_jobs": queued,
        "mode": "local",
        "city_complete": False,
        "scope": "Open-directory baseline plus existing autonomous discovery and enrichment; approval remains manual",
    }
