"""Pure duplicate evidence policy. A merge is never factual or Maps approval.

Inputs may be IdentifiedSpot-like objects, dictionaries with a ``data`` member,
or flat candidate dictionaries. Ownership, lifecycle and transaction checks are
the caller's responsibility. No network, database, model or freshness writes.
"""

import math
import re
import unicodedata
from collections.abc import Mapping

from .spot_identity import AREAS, area_key, name_key, names_match, possible_match

_SUFFIXES = {
    "coimbatore",
    "kovai",
    "cbe",
    "cafe",
    "cafes",
    "coffee",
    "restaurant",
    "restaurants",
    "food",
    "foods",
    "grill",
    "grills",
}
_AREA_SUFFIXES = {area_key(area) for area in AREAS}
_ROADS = {"rd": "road", "st": "street", "ave": "avenue", "av": "avenue", "ln": "lane"}
_ROAD_WORDS = {"road", "street", "avenue", "lane", "salai", "marg", "highway", "drive"}
_RELATIVE = re.compile(r"\b(?:near|opposite|opp\.?|behind|beside|next\s+to|landmark)\b", re.IGNORECASE)
_HOUSE = re.compile(
    r"(?:\b(?:door\s+)?(?:no\.?|number)\s*[:.-]?\s*|#\s*)(\d+[a-z]?(?:\s*[-/]\s*[a-z0-9]+)?)",
    re.IGNORECASE,
)
_LEADING_HOUSE = re.compile(r"^\s*(\d+[a-z]?(?:\s*[-/]\s*[a-z0-9]+)?)(?=\s|,|$)", re.IGNORECASE)
_POSTAL = re.compile(r"\b[1-9]\d{5}\b")
_UNIT = re.compile(r"\b(?:shop|unit|suite)\s*(?:no\.?\s*)?([a-z]?\d+[a-z]?(?:[-/]\w+)?)\b", re.IGNORECASE)


def name_variant_key(value):
    """Order-preserving candidate key; punctuation/suffixes do not prove identity."""
    value = re.sub(r"['’ʼ]", "", str(value))
    tokens = name_key(value).split()
    while tokens:
        if tokens[-1] in _SUFFIXES:
            tokens.pop()
            continue
        suffix_length = next(
            (
                length
                for length in range(1, len(tokens))
                if area_key(" ".join(tokens[-length:])) in _AREA_SUFFIXES
            ),
            None,
        )
        if suffix_length:
            del tokens[-suffix_length:]
            continue
        break
    return " ".join(tokens)


def _parts(record):
    if isinstance(record, Mapping):
        nested = record.get("data")
        data = dict(nested) if isinstance(nested, Mapping) else dict(record)
        return str(record.get("name", data.get("name", ""))), str(record.get("area", "")), data
    return (
        str(getattr(record, "name", "")),
        str(getattr(record, "area", "")),
        getattr(record, "data", {}) or {},
    )


def _names(record):
    name, _, data = _parts(record)
    return [str(n) for n in [name, *data.get("aliases", [])] if isinstance(n, str) and n.strip()]


def _name_match(left, right):
    a, b = _names(left), _names(right)
    exact = any(name_key(x).replace(" ", "") == name_key(y).replace(" ", "") for x in a for y in b)
    variants_a = {name_variant_key(x) for x in a} - {""}
    variants_b = {name_variant_key(x) for x in b} - {""}
    shared = sorted(variants_a & variants_b)
    # Name variants are only a name compatibility signal. A separate branch
    # anchor and every conflict check are still required below.
    compatible = exact or bool(shared) or any(names_match(x, y) for x in a for y in b)
    return exact or bool(shared), compatible, shared


def _coordinate(data):
    value = data.get("coordinates")
    if not value:
        return None, False
    if not isinstance(value, Mapping):
        return None, True
    try:
        if isinstance(value["lat"], bool) or isinstance(value["lng"], bool):
            return None, True
        lat, lng = float(value["lat"]), float(value["lng"])
        if not math.isfinite(lat) or not math.isfinite(lng) or not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return None, True
        return (lat, lng), False
    except (KeyError, ValueError, TypeError, OverflowError):
        return None, True


def _distance(a, b):
    lat_a, lat_b = math.radians(a[0]), math.radians(b[0])
    dlat, dlng = lat_b - lat_a, math.radians(b[1] - a[1])
    term = math.sin(dlat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(dlng / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, term))))


def _address(data):
    """Extract explicit own-address components, never relative landmarks."""
    values = []
    if isinstance(data.get("address"), str) and data["address"].strip():
        values.append(data["address"])
    clues = [x for x in data.get("address_clues", []) if isinstance(x, str) and x.strip()]
    values.extend(clues)
    if clues and not any(_RELATIVE.search(x) for x in clues):
        values.append(", ".join(clues))
    structured = data.get("address_components", {})
    if isinstance(structured, Mapping):

        def component(*keys):
            return next((str(structured[k]) for k in keys if structured.get(k)), "")

        house = component("house_number", "housenumber", "addr:housenumber")
        street = component("street", "road", "addr:street")
        postal = component("postcode", "postal_code", "addr:postcode")
        if street:
            values.append(", ".join(x for x in (house, street, postal) if x))
    houses, postcodes, streets, units = set(), set(), set(), set()
    for value in values:
        value = unicodedata.normalize("NFKC", value).casefold()
        if _RELATIVE.search(value):
            continue
        postcodes.update(_POSTAL.findall(value))
        units.update(name_key(m).replace(" ", "") for m in _UNIT.findall(value))
        own_value = _UNIT.sub("", value)
        match = _HOUSE.search(own_value) or _LEADING_HOUSE.search(own_value)
        if match and len(re.sub(r"\D", "", match[1])) <= 5:
            houses.add(re.sub(r"\s+", "", match[1]).casefold())
        for segment in own_value.split(","):
            house_match = _HOUSE.search(segment) or _LEADING_HOUSE.search(segment)
            if house_match:
                segment = segment[house_match.end() :]
            tokens = [_ROADS.get(t, t) for t in name_key(segment).split()]
            for i, token in enumerate(tokens):
                if token not in _ROAD_WORDS or not i:
                    continue
                stem = tokens[:i]
                # A road suffix plus a real name (including D B Road) is useful;
                # a neighbourhood, bare postcode or bare "road" is insufficient.
                if sum(len(t) for t in stem if any(c.isalpha() for c in t)) >= 2:
                    streets.add(" ".join([*stem, token]))
                break
    return {"houses": houses, "postcodes": postcodes, "streets": streets, "units": units}


def identity_conflicts(left, right):
    """Return concrete blockers, including malformed/non-finite coordinates.

    Use this before following an old identity hash or merged redirect. It does
    not assert that a conflict-free pair has enough evidence to merge.
    """
    _, area_a, a = _parts(left)
    _, area_b, b = _parts(right)
    conflicts = []
    map_a, map_b = a.get("maps_identity", {}).get("place_key"), b.get("maps_identity", {}).get("place_key")
    if map_a and map_b and map_a != map_b:
        conflicts.append("Different explicit Google Maps place identities")
    branch_a, branch_b = a.get("branch_key"), b.get("branch_key")
    if branch_a and branch_b and name_key(branch_a) != name_key(branch_b):
        conflicts.append("Different explicit branch keys")
    if area_a and area_b and area_key(area_a) != area_key(area_b):
        conflicts.append("Different recorded neighbourhoods")
    address_a, address_b = _address(a), _address(b)
    for field, label in [
        ("houses", "house numbers"),
        ("postcodes", "postcodes"),
        ("streets", "street addresses"),
        ("units", "shop or unit numbers"),
    ]:
        if address_a[field] and address_b[field] and address_a[field].isdisjoint(address_b[field]):
            conflicts.append("Different concrete " + label)
    point_a, invalid_a = _coordinate(a)
    point_b, invalid_b = _coordinate(b)
    if invalid_a or invalid_b:
        conflicts.append("Invalid or non-finite coordinate evidence")
    elif point_a and point_b and _distance(point_a, point_b) > 0.15:
        conflicts.append("Recorded coordinates are more than 150 metres apart")
    return conflicts


def _cross_script(left, right):
    def scripts(value):
        return {
            unicodedata.name(c, "").split(" ")[0] for c in value if unicodedata.category(c).startswith("L")
        }

    a, b = scripts(_parts(left)[0]), scripts(_parts(right)[0])
    return bool(a and b and a.isdisjoint(b))


def assess_pair(left, right):
    """Assess one pair; callers must validate whole groups against bridge merges."""
    conflicts = identity_conflicts(left, right)
    exact_name, compatible, shared = _name_match(left, right)
    name_reason = (
        "Compatible normalized names: " + ", ".join(shared)
        if shared
        else "Compatible recorded names or explicit aliases"
    )
    reasons = [name_reason] if compatible else []
    if conflicts:
        return {
            "decision": "separate",
            "reasons": reasons + ["Concrete branch evidence conflicts"],
            "conflicts": conflicts,
        }
    _, _, a = _parts(left)
    _, _, b = _parts(right)
    own_a, own_b = _address(a), _address(b)
    ambiguous = any(
        len(address[key]) > 1
        for address in (own_a, own_b)
        for key in ("houses", "postcodes", "streets", "units")
    )
    if ambiguous:
        return {
            "decision": "review",
            "reasons": reasons + ["Multiple concrete address alternatives need branch review"],
            "conflicts": [],
        }
    map_a, map_b = a.get("maps_identity", {}).get("place_key"), b.get("maps_identity", {}).get("place_key")
    if map_a and map_a == map_b:
        return {
            "decision": "merge",
            "reasons": reasons + ["Same explicit Google Maps place identity; approval unchanged"],
            "conflicts": [],
        }
    refs_a = {
        x
        for x in a.get("directory_refs", [])
        if isinstance(x, str) and re.fullmatch(r"(?:node|way|relation)/[1-9]\d*", x)
    }
    refs_b = {x for x in b.get("directory_refs", []) if isinstance(x, str)}
    if refs_a & refs_b:
        return {
            "decision": "merge",
            "reasons": reasons + ["Same exact OpenStreetMap object reference"],
            "conflicts": [],
        }
    detailed_address = bool(own_a["streets"] & own_b["streets"]) and bool(
        (own_a["houses"] & own_b["houses"]) or (own_a["postcodes"] & own_b["postcodes"])
    )
    if compatible and detailed_address:
        return {
            "decision": "merge",
            "reasons": reasons
            + ["Equivalent detailed own-address with matching house number or postcode and named street"],
            "conflicts": [],
        }
    point_a, _ = _coordinate(a)
    point_b, _ = _coordinate(b)
    if exact_name and point_a and point_b and _distance(point_a, point_b) <= 0.025:
        return {
            "decision": "merge",
            "reasons": reasons
            + [
                "Coordinates within 25 metres with exact normalized names or explicit aliases; branch remains unapproved"
            ],
            "conflicts": [],
        }
    if (
        compatible
        or _cross_script(left, right)
        or any(possible_match(x, y) for x in _names(left) for y in _names(right))
    ):
        reasons.append("No unambiguous stable identity, detailed own-address or nearby coordinate anchor")
        return {"decision": "review", "reasons": reasons, "conflicts": []}
    return {
        "decision": "separate",
        "reasons": ["No compatible recorded name or shared stable identity"],
        "conflicts": [],
    }
