"""Reviewed menu evidence and private recommendations. No invented popularity counts."""

import hashlib
from datetime import datetime, timezone
from sqlalchemy import select
from .db import Claim, DishEntry
from .spot_identity import name_key

DINING_FORMATS = {
    "cafe",
    "casual_dining",
    "fine_dining",
    "quick_service",
    "street_food",
    "food_court",
    "bakery",
    "dessert_shop",
}


def item_key(name):
    return hashlib.sha256(name_key(name).encode()).hexdigest()[:24]


def menu_tags(item):
    values = [
        *item.get("tags", []),
        item.get("cuisine", ""),
        item.get("category", ""),
        item.get("spice") or "",
        "spicy" if item.get("spice") == "hot" else "",
    ]
    return {name_key(t) for t in values if name_key(t)}


def review_support(evidence):
    """A reviewed sample, deduplicated by origin group; conflicting views remain mixed."""
    groups = {}
    current = datetime.now(timezone.utc)
    parents = {}

    def find(key):
        parents.setdefault(key, key)
        if parents[key] != key:
            parents[key] = find(parents[key])
        return parents[key]

    retained = []
    for row in evidence:
        expiry = row["expires_at"]
        if (datetime.fromisoformat(expiry) if isinstance(expiry, str) else expiry) <= current:
            continue
        url = row["source_url"]
        parents[find("url:" + url)] = find("group:" + row["evidence_group"])
        retained.append(row)
    for row in retained:
        url = row["source_url"]
        group = find("url:" + url)
        item = groups.setdefault(group, {"sentiments": set(), "sources": []})
        item["sentiments"].add(row["sentiment"])
        if url not in {s["url"] for s in item["sources"]}:
            item["sources"].append(
                {"url": url, "observed_at": row["observed_at"], "expires_at": row["expires_at"]}
            )
    counts = {key: 0 for key in ["praise", "complaint", "mixed", "mention"]}
    for item in groups.values():
        sentiments = item.pop("sentiments")
        kind = (
            "mixed"
            if "mixed" in sentiments or {"praise", "complaint"} <= sentiments
            else "praise"
            if "praise" in sentiments
            else "complaint"
            if "complaint" in sentiments
            else "mention"
        )
        item["sentiment"] = kind
        counts[kind] += 1
    return {
        "groups": len(groups),
        "counts": counts,
        "sources": list(groups.values()),
        "basis": "Current reviewed source groups; a bounded sample, not all customer reviews or platform ratings",
    }


def text_matches(query, text):
    needle, haystack = name_key(query), name_key(text)
    return not needle or f" {needle} " in f" {haystack} "


def current_fact(claims, field):
    return next(
        iter(
            sorted(
                (
                    c
                    for c in claims
                    if c.field == field
                    and c.status == "accepted"
                    and datetime.fromisoformat(c.expires_at) > datetime.now(timezone.utc)
                ),
                key=lambda c: c.observed_at,
                reverse=True,
            )
        ),
        None,
    )


def menu_view(db, venue, user=None, claims=None):
    claims = (
        claims if claims is not None else list(db.scalars(select(Claim).where(Claim.venue_id == venue.id)))
    )
    claim = current_fact(claims, "offerings")
    entries = (
        list(
            db.scalars(select(DishEntry).where(DishEntry.user_id == user.id, DishEntry.venue_id == venue.id))
        )
        if user
        else []
    )
    by_key = {e.offering_key: e for e in entries}
    items = []
    profile = user.profile if user else {}
    likes = set(profile.get("liked_tags", [])) | set(profile.get("preferred_cuisines", []))
    avoid = set(profile.get("avoided_tags", []))
    if profile.get("learn_from_visits", True):
        likes |= {t for t, score in profile.get("inferred", {}).items() if score > 0}
    for raw in claim.value["value"] if claim else []:
        from .schemas import MenuOffering
        from pydantic import ValidationError

        try:
            item = MenuOffering.model_validate(raw).model_dump(mode="json")
        except ValidationError:
            continue
        item["key"] = item_key(item["name"])
        tags = menu_tags(item)
        reasons = []
        state = by_key.get(item["key"])
        item["diary_status"] = state.status if state else None
        if state and state.status == "favourite":
            reasons.append("You marked this dish as a favourite")
        match = tags & likes
        if match:
            reasons.append("Matches your tastes: " + ", ".join(sorted(match)))
        if profile.get("spice_preference", "any") == item["spice"]:
            reasons.append("Matches your preferred spice level")
        support = review_support(item.pop("review_evidence"))
        item["review_support"] = support
        if support["groups"]:
            reasons.append(
                f"Reviewed source groups: {support['counts']['praise']} praise, {support['counts']['complaint']} complaints, {support['counts']['mixed']} mixed"
            )
        item["matches_diet"] = not profile.get("vegetarian") or item["vegetarian"] is True
        item["eligible_pick"] = (
            item["matches_diet"]
            and not (tags & avoid)
            and item["available"] is not False
            and not (state and state.status == "not_for_me")
        )
        item["reasons"] = reasons or [
            "Listed in the currently reviewed menu; no personal preference match established"
        ]
        item["source_url"], item["expires_at"], item["observed_at"] = (
            claim.source_url,
            claim.expires_at,
            claim.observed_at,
        )
        item["_score"] = (
            (8 if state and state.status == "favourite" else 0)
            + 3 * len(match)
            + (1 if profile.get("spice_preference") == item["spice"] else 0)
            + min(3, support["counts"]["praise"])
            - min(3, support["counts"]["complaint"])
        )
        items.append(item)
    items.sort(key=lambda i: (-int(i["eligible_pick"]), -i["_score"], name_key(i["name"])))
    for item in items:
        item.pop("_score")
    format_claim, amenities_claim = current_fact(claims, "dining_format"), current_fact(claims, "amenities")
    return {
        "status": "current"
        if claim
        else "expired"
        if any(c.field == "offerings" and c.status == "accepted" for c in claims)
        else "not_reviewed",
        "items": items,
        "dining_format": format_claim.value["value"] if format_claim else None,
        "amenities": amenities_claim.value["value"] if amenities_claim else {},
        "basis": "Reviewed menu evidence, any reviewed review samples and your private preferences; no community awards inferred",
        "price_note": "Menu item and package prices are separate from an itinerary's per-person spending estimate",
    }
