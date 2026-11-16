"""Import Overture Maps places (open data) for Coimbatore.

Overture combines Meta, Microsoft, Foursquare and other place data under open
licences (mostly CDLA-Permissive-2.0), so names, points, addresses, websites and
phone numbers may be kept. Get the file with the official downloader, e.g.:

    uvx overturemaps download --bbox=76.62,10.66,77.30,11.38 -f geojsonseq \
        --type=place -o data/city-collection/overture-places.geojsonl

Each in-scope place either enriches a draft we already have (and gives it
coordinates when the match is unambiguous) or becomes a new draft through the
usual identity, scope and learned-rule checks. Nothing is approved here.
"""

import json
from collections import Counter

from sqlalchemy import select

from .categories import match
from .db import IdentifiedSpot, now
from .planner import km
from .spot_identity import infer_area, name_key, possible_match, signature
from .spots import INACTIVE, merge_data, upsert_spot

CENTRE = (11.0168, 76.9558)
MIN_CONFIDENCE = 0.6
FOOD_TYPES = {
    "restaurant", "indian_restaurant", "fast_food_restaurant", "pizza_restaurant", "chicken_restaurant",
    "vegetarian_restaurant", "chinese_restaurant", "burger_restaurant", "asian_restaurant",
    "barbecue_restaurant", "theme_restaurant", "sandwich_shop", "diner", "bar_and_grill_restaurant",
    "seafood_restaurant", "dumpling_restaurant", "middle_eastern_restaurant", "italian_restaurant",
    "delicatessen", "doner_kebab_restaurant", "arabian_restaurant", "asian_fusion_restaurant",
    "american_restaurant", "mexican_restaurant", "indo_chinese_restaurant", "european_restaurant",
    "nepalese_restaurant", "burmese_restaurant", "breakfast_and_brunch_restaurant", "malaysian_restaurant",
    "persian_restaurant", "british_restaurant", "comfort_food_restaurant", "live_and_raw_food_restaurant",
    "food_and_drink", "food_court", "south_indian_restaurant", "north_indian_restaurant",
}  # fmt: skip
TYPES = {
    **{t: "food" for t in FOOD_TYPES},
    "food_truck_stand": "street_food",
    "cafe": "cafe", "coffee_shop": "cafe", "tea_room": "cafe", "bubble_tea_shop": "cafe",
    "bakery": "dessert", "ice_cream_shop": "dessert", "dessert_shop": "dessert", "candy_store": "dessert",
    "chocolatier": "dessert", "cupcake_shop": "dessert", "donut_shop": "dessert", "gelato_shop": "dessert",
    "smoothie_juice_bar": "dessert", "milk_bar": "dessert", "japanese_confectionery_shop": "dessert",
    "pastry_shop": "dessert", "cake_shop": "dessert",
    "bar": "nightlife", "lounge": "nightlife", "pub": "nightlife", "cocktail_bar": "nightlife",
    "beer_bar": "nightlife", "wine_bar": "nightlife", "dance_club": "nightlife", "brewery": "nightlife",
    "movie_theater": "cinema", "drive_in_theater": "cinema",
    "pool_billiards": "gaming", "escape_room": "gaming", "arcade": "gaming", "gaming_venue": "gaming",
    "bowling_alley": "bowling",
    "go_kart_club": "adventure", "race_track": "adventure", "shooting_range": "adventure",
    "archery_range": "adventure", "horse_riding": "adventure", "laser_tag": "adventure",
    "trampoline_park": "adventure",
    "amusement_park": "amusement", "water_park": "amusement",
    "park": "park", "dog_park": "park", "national_park": "park", "hiking_trail": "park",
    "museum": "attraction", "science_museum": "attraction", "art_gallery": "attraction",
    "aquarium": "attraction", "zoo": "attraction", "wildlife_sanctuary": "attraction",
    "planetarium": "attraction",
    "badminton_court": "sports", "tennis_court": "sports", "cricket_ground": "sports",
    "swimming_pool": "sports", "golf_course": "sports", "skating_rink": "sports",
    "glass_blowing_venue": "workshop", "arts_and_crafts_space": "workshop",
}  # fmt: skip
LICENCE = {
    "attribution": "© Overture Maps Foundation and its data providers",
    "url": "https://docs.overturemaps.org/attribution/",
    "license": "CDLA-Permissive-2.0 and source licences",
}


def category(primary, name):
    """Overture's type decides food vs activity; the name only refines the kind of food."""
    kind = TYPES.get(primary)
    if kind in {"food", "cafe"}:
        named = match(name)
        if named in {"street_food", "dessert", "nightlife"}:
            return named
    return kind


def place(feature):
    """In-scope fields of one Overture feature, or None."""
    props = feature.get("properties") or {}
    name = ((props.get("names") or {}).get("primary") or "").strip()
    coords = (feature.get("geometry") or {}).get("coordinates") or []
    taxonomy = props.get("taxonomy") or {}
    primary = taxonomy.get("primary") or (props.get("categories") or {}).get("primary")
    confidence = float(props.get("confidence") or 0)
    if not name or len(coords) != 2 or confidence < MIN_CONFIDENCE:
        return None
    lng, lat = float(coords[0]), float(coords[1])
    if km((lat, lng), CENTRE) > 40:
        return None
    kind = category(primary, name)
    if not kind:
        return None
    address = next(iter(props.get("addresses") or []), {}) or {}
    parts = [address.get("freeform"), address.get("locality"), address.get("postcode")]
    datasets = sorted(
        {s.get("dataset") for s in props.get("sources") or [] if s.get("dataset") != "Overture"}
    )
    return {
        "id": feature.get("id") or props.get("id"),
        "name": name,
        "category": kind,
        "type": primary,
        "lat": lat,
        "lng": lng,
        "confidence": round(confidence, 3),
        "address": ", ".join(x for x in parts if x),
        "locality": address.get("locality") or "",
        "websites": [w for w in props.get("websites") or [] if str(w).startswith("https://")][:3],
        "socials": [w for w in props.get("socials") or [] if str(w).startswith("https://")][:3],
        "phones": [str(p) for p in props.get("phones") or []][:2],
        "datasets": datasets,
    }


def read(path):
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                found = place(json.loads(line))
                if found:
                    yield found


def _evidence(item):
    link = (item["websites"] or item["socials"] or ["https://overturemaps.org/"])[0]
    data = {
        "sources": [
            {
                "type": "overture",
                "url": link,
                "collected_at": now(),
                "basis": "Overture Maps place ("
                + ", ".join(item["datasets"])
                + "); existence and details not independently verified",
            }
        ],
        "source_licenses": [LICENCE],
        "overture": {
            "id": item["id"],
            "type": item["type"],
            "confidence": item["confidence"],
            "datasets": item["datasets"],
            "phones": item["phones"],
        },
        "website_candidates": item["websites"],
        "strict_identity": True,
    }
    if item["address"]:
        data["address_clues"] = [item["address"]]
    return data


def _point(item):
    return {
        "lat": item["lat"],
        "lng": item["lng"],
        "source_url": "https://overturemaps.org/",
        "basis": "Overture Maps point; entrance and branch unverified",
    }


def _has_point(row):
    return (row.data.get("coordinates") or {}).get("lat") is not None


def import_file(db, owner, path):
    places = list(read(path))
    counts = Counter(signature(p["name"]) or name_key(p["name"]) for p in places)
    everything = list(db.scalars(select(IdentifiedSpot).where(IdentifiedSpot.user_id == owner)))
    rows = [r for r in everything if r.status not in INACTIVE]
    result = Counter(considered=len(places))
    for n, item in enumerate(places):
        data = _evidence(item)
        here = (item["lat"], item["lng"])
        candidates = [
            r
            for r in rows
            if any(possible_match(x, item["name"]) for x in [r.name, *r.data.get("aliases", [])])
        ]
        near = [
            r
            for r in candidates
            if _has_point(r)
            and km((float(r.data["coordinates"]["lat"]), float(r.data["coordinates"]["lng"])), here) <= 0.3
        ]
        unique_name = counts[signature(item["name"]) or name_key(item["name"])] == 1
        area = infer_area([item["address"], item["locality"]])
        pointless = [r for r in candidates if not _has_point(r)]
        target = None
        if near:
            target = near[0]
            result["enriched_nearby"] += 1
        elif len(pointless) == 1 and (unique_name or (area and pointless[0].area == area)):
            target = pointless[0]
            target.data = {**target.data, "coordinates": _point(item)}
            result["gave_coordinates"] += 1
        if target is not None:
            if item["address"] and not target.data.get("address"):
                data["address"] = item["address"]
            target.data = merge_data(target.data, data)
            if not target.area and area:
                target.area = area
            target.updated_at = now()
        else:
            row = upsert_spot(
                db,
                owner,
                item["name"],
                item["category"],
                area,
                {**data, "coordinates": _point(item)},
                records=everything,
            )
            if row is None:
                result["skipped_by_rules"] += 1
            else:
                result["created_held" if row.status == "quarantined" else "created"] += 1
                if row not in everything:
                    everything.append(row)
                    rows.append(row)
        if n % 50 == 49:
            db.commit()
    db.commit()
    return dict(result)
