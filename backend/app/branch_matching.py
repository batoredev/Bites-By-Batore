"""Explainable multimodal branch candidates, including conflicting evidence."""

from difflib import SequenceMatcher
from urllib.parse import urlparse
from .spot_identity import name_key, names_match, area_key, infer_area, branch_clues, quality_issues


def rank_google(candidate, places):
    """Rank fresh API results transiently; callers persist IDs only."""
    from .planner import km

    name, clues = candidate.get("name", ""), candidate.get("address_clues", [])
    area = infer_area(clues)
    result = []
    for place in places:
        coords = place.get("location", {})
        if (
            not {"latitude", "longitude"}.issubset(coords)
            or km((coords["latitude"], coords["longitude"]), (11.0168, 76.9558)) > 40
        ):
            continue
        similarity = SequenceMatcher(
            None, name_key(name), name_key(place.get("displayName", {}).get("text", ""))
        ).ratio()
        address = place.get("formattedAddress", "")
        area_agrees = bool(area) and area_key(area) in area_key(address)
        a, b = branch_clues({"address_clues": clues}), branch_clues({"address": address})
        conflict = any(a[k] and b[k] and a[k] != b[k] for k in a)
        result.append(
            {
                **place,
                "match_review": {
                    "name_similarity": round(similarity, 3),
                    "area_agrees": area_agrees,
                    "address_conflict": conflict,
                    "status": "candidate_only",
                },
            }
        )
    return sorted(
        result,
        key=lambda p: (
            not p["match_review"]["address_conflict"],
            p["match_review"]["name_similarity"] + 0.1 * p["match_review"]["area_agrees"],
        ),
        reverse=True,
    )


def branch_match(candidate, spot, visual_matches=()):
    name = candidate.get("name", "")
    clues = candidate.get("address_clues", [])
    area = infer_area(clues)
    data = spot.data
    reasons, conflicts = [], []
    similarity = max(
        SequenceMatcher(None, name_key(name), name_key(n)).ratio()
        for n in [spot.name, *data.get("aliases", [])]
    )
    equivalent = any(names_match(name, n) for n in [spot.name, *data.get("aliases", [])])
    visual = [v for v in visual_matches if v.get("spot_id") == spot.id and v.get("matched")]
    if similarity < 0.55 and not equivalent and not visual:
        return None
    score = 0
    if equivalent or similarity >= 0.9:
        reasons.append("Name agrees with existing name/alias")
        score += 3
    elif similarity >= 0.7:
        reasons.append("Similar name only")
        score += 1
    if area and spot.area:
        if area_key(area) == area_key(spot.area):
            reasons.append("Neighbourhood agrees")
            score += 1
        else:
            conflicts.append("Neighbourhood conflicts")
    a, b = branch_clues({"address_clues": clues}), branch_clues(data)
    for field in a:
        if a[field] and b[field]:
            if a[field] != b[field]:
                conflicts.append(field + " conflicts")
            else:
                reasons.append(field + " agrees")
                score += 2
    address = name_key(data.get("address", ""))
    if len(address) >= 15 and address in name_key(" ".join(clues)):
        reasons.append("Full address agrees")
        score += 4
    if visual:
        reasons.append("Reference-image geometry match (not branch proof)")
        score += 2
    conflicts.extend(quality_issues(name, area, {"address_clues": clues}))
    identity = data.get("maps_identity", {})
    reference_domains = sorted(
        {
            urlparse(s.get("url", "")).hostname
            for s in data.get("sources", [])
            if urlparse(s.get("url", "")).hostname
        }
    )
    strong_address = "Full address agrees" in reasons or any(
        x in reasons for x in ["numbers agrees", "postal agrees"]
    )
    return {
        "spot_id": spot.id,
        "name_similarity": round(similarity, 3),
        "score": score,
        "support": reasons,
        "conflicts": conflicts,
        "status": "conflicting"
        if conflicts
        else "corroborated_candidate"
        if score >= 6 and strong_address
        else "ambiguous_candidate",
        "place_id": identity.get("place_id"),
        "reference_domains": reference_domains,
        "independence": "Different domains or modalities can still repeat the same source",
        "rule": "Scores rank review candidates; they are not calibrated probabilities and never approve a location",
    }
