"""Conservative identity checks. Similar names alone never prove the same branch."""

import re
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import parse_qs, urlparse

AREAS = [
    "RS Puram",
    "Peelamedu",
    "Race Course",
    "Saibaba Colony",
    "Gandhipuram",
    "Saravanampatti",
    "Karumathampatti",
    "Anaikatti",
    "Ukkadam",
    "Singanallur",
    "Avinashi Road",
    "Sathy Road",
    "Thudiyalur",
    "Nava India",
    "Bharathi Park",
    "Vadavalli",
    "Ganapathy",
    "Podanur",
    "Sundarapuram",
]
DESCRIPTORS = set(
    "the and at in cafe cafes coffee restaurant restaurants grills grill japanese coimbatore kovai cbe".split()
)
GENERIC = set(
    "a an new best first hidden gem aesthetic inspired pinterest food foods foodie foodies spot spots place location venue facility track unknown unspecified unnamed for you page lounge go karting simulator motion racing launch tea shop stall park sushi ramen momo kalan british date night".split()
)


def name_key(value):
    # Strip Latin accents but preserve Tamil and other non-Latin scripts.
    value = "".join(
        unicodedata.normalize("NFKD", c)[0] if "LATIN" in unicodedata.name(c, "") else c
        for c in unicodedata.normalize("NFKC", str(value))
    )
    value = value.casefold().replace("&", " and ").replace("_", " ")
    return " ".join(
        "".join(c if unicodedata.category(c)[0] in {"L", "N", "M"} else " " for c in value).split()
    )


def clean_name(value):
    value = unicodedata.normalize("NFKC", str(value)).strip().lstrip("@")
    return " ".join(value.replace("_", " ").split())[:150]


def signature(value):
    return " ".join(sorted(set(name_key(value).split()) - DESCRIPTORS))


def area_key(value):
    value = (
        name_key(value).replace("saravanampatty", "saravanampatti").replace("saravanapatti", "saravanampatti")
    )
    return value.replace(" ", "")


def infer_area(clues):
    text = area_key(" ".join(clues))
    return next((a for a in AREAS if area_key(a) in text), "")


def quality_issues(name, area="", data=None):
    data = data or {}
    key = name_key(name)
    tokens = set(key.split()) - DESCRIPTORS
    issues = []
    if len(key) < 2 or not (tokens - GENERIC) or area_key(key) in {area_key(a) for a in AREAS}:
        issues.append("Generic description or neighbourhood, not an identifiable venue name")
    if re.search(
        r"\b(first|best|new)\b.*\b(in|launch|opening|opened)\b|\b(foodspots|viralreels|trendingreels)\b", key
    ):
        issues.append("Promotional caption or creator handle needs a real venue identity")
    if re.match(
        r"^(?:the |a |an )?(?:cafe|restaurant|stall|shop|place|venue|food spot)\s+(?:near|opposite|behind|beside|next to)\b",
        key,
    ):
        issues.append("Relative location description does not provide a venue name")
    address = name_key(" ".join([name, area, data.get("address", ""), *data.get("address_clues", [])]))
    # A nearby business such as 'Mumbai Kulfi' is not evidence of a Mumbai address.
    address = re.sub(
        r"\b(mumbai|delhi|chennai)\s+(kulfi|chaat|kitchen|express)\b", "nearby business", address
    )
    if re.search(
        r"\b(chennai|bengaluru|bangalore|mumbai|hyderabad|delhi|kochi|madurai|salem|ooty|pondicherry|puducherry)\b",
        address,
    ):
        issues.append("Address evidence includes a city outside the Coimbatore scope; verify the branch")
    if re.search(r"\b(textiles|jewellery|jewelry|salon|hospital|clinic|real estate)\b", key):
        issues.append("Candidate appears outside food and entertainment scope")
    observations = data.get("observations", [])
    mentioned = [o for o in observations if key in name_key(o.get("text", ""))]
    if mentioned and all(o.get("basis") in {"speech", "inference"} for o in mentioned):
        issues.append("Name is supported only by speech/inference; corroborate spelling and identity")
    if any(
        re.search(
            r"\b(near|opposite|beside|next to)\s+(?:the\s+)?" + re.escape(key) + r"\b",
            name_key(o.get("text", "")),
        )
        for o in mentioned
    ):
        issues.append("Name may be a nearby landmark rather than the reviewed venue")
    return issues


def source_urls(data):
    return {x.get("url") for x in data.get("sources", []) if x.get("url")}


def branch_clues(data):
    """Strong conflicting address tokens block a merge, even within one neighbourhood."""
    clues = " ".join([data.get("address", ""), *data.get("address_clues", [])])
    postal = set(re.findall(r"\b6\d{5}\b", clues))
    numbers = set(re.findall(r"\bno\.?\s*(\d+[A-Za-z]?(?:[-/]\w+)?)\b", clues, re.I))
    return {"postal": sorted(postal), "numbers": sorted(n.casefold() for n in numbers)}


def names_match(left, right):
    return name_key(left).replace(" ", "") == name_key(right).replace(" ", "") or (
        bool(signature(left)) and signature(left) == signature(right)
    )


def same_branch(row, name, area, data):
    identity = row.data.get("maps_identity", {})
    incoming = data.get("maps_identity", {})
    if identity.get("place_key") and incoming.get("place_key"):
        return identity["place_key"] == incoming["place_key"]
    if (
        row.data.get("branch_key")
        and data.get("branch_key")
        and name_key(row.data["branch_key"]) != name_key(data["branch_key"])
    ):
        return False
    if not any(names_match(alias, name) for alias in [row.name, *row.data.get("aliases", [])]):
        return False
    if row.area and area and area_key(row.area) != area_key(area):
        return False
    old_address, new_address = row.data.get("address"), data.get("address")
    if old_address and new_address and name_key(old_address) != name_key(new_address):
        return False
    left_clues, right_clues = branch_clues(row.data), branch_clues(data)
    if any(left_clues[k] and right_clues[k] and left_clues[k] != right_clues[k] for k in left_clues):
        return False
    shared_source = bool(source_urls(row.data) & source_urls(data))
    exact = any(
        name_key(alias).replace(" ", "") == name_key(name).replace(" ", "")
        for alias in [row.name, *row.data.get("aliases", [])]
    )
    return (
        shared_source
        or (exact and bool(area) and area_key(row.area) == area_key(area))
        or (bool(old_address) and name_key(old_address) == name_key(new_address or ""))
    )


def possible_match(left, right):
    a, b = signature(left).replace(" ", ""), signature(right).replace(" ", "")
    return bool(a and b) and (names_match(left, right) or SequenceMatcher(None, a, b).ratio() >= 0.82)


def maps_reference(url):
    """Accept a specific Google place reference, never a generic search/coordinate pin."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("Use an HTTPS Google Maps place link")
    if parsed.hostname not in {
        "google.com",
        "www.google.com",
        "maps.google.com",
        "google.co.in",
        "www.google.co.in",
    }:
        raise ValueError("Open the short link and paste the full Google Maps place URL")
    if not (parsed.path.startswith("/maps") or parsed.hostname == "maps.google.com"):
        raise ValueError("Use a Google Maps place link")
    query = parse_qs(parsed.query)
    pid = (query.get("query_place_id") or query.get("place_id") or [""])[0]
    q = (query.get("q") or [""])[0]
    if not pid and q.startswith("place_id:"):
        pid = q.removeprefix("place_id:")
    path_id = re.search(r"!1s([A-Za-z0-9_-]{8,255})(?:!|/|$)", parsed.path)
    if not pid and path_id:
        pid = path_id[1]
    if pid and re.fullmatch(r"[A-Za-z0-9_-]{8,255}", pid):
        return {"place_key": "pid:" + pid, "place_id": pid, "maps_url": url}
    cid = (query.get("cid") or query.get("ludocid") or [""])[0]
    feature = re.search(r"!1s0x[0-9a-f]+:0x([0-9a-f]+)", parsed.path, re.I)
    if feature:
        cid = str(int(feature[1], 16))
    if cid.isdigit() and 0 < int(cid) < 2**64:
        return {"place_key": "cid:" + str(int(cid)), "maps_url": url}
    raise ValueError(
        "This is a search or coordinate link. Open the exact place and copy its place-ID or CID link"
    )
