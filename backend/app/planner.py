"""Deterministic hard constraints; language models never calculate feasibility."""

import math
import re
from datetime import datetime, timedelta, timezone
from itertools import permutations, chain
from zoneinfo import ZoneInfo
from collections import Counter
from .schemas import OutingRequest
from .menu import current_fact, text_matches

IST = ZoneInfo("Asia/Kolkata")
from .categories import FOOD  # noqa: E402


SYNONYMS = {
    "movies?": "cinema",
    "films?": "cinema",
    "dinner": "food",
    "lunch": "food",
    "restaurants?": "food",
    "ice ?cream": "dessert",
    "sweets?": "dessert",
    "bakery": "dessert",
    "pubs?": "nightlife",
    "bars?": "nightlife",
    "drinks": "nightlife",
    "go ?kart(ing)?": "adventure",
    "water ?park": "amusement",
    "theme ?park": "amusement",
    "museums?": "attraction",
    "turf": "sports",
    "pottery": "workshop",
    "snacks?": "street food",
    "chaat": "street food",
}


def km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def demo_leg(a, b, mode, people):
    distance = km(a, b) * 1.35
    speed = {"walk": 4.5, "bike": 22, "drive": 20, "taxi": 20}[mode]
    minutes = max(2, math.ceil(distance / speed * 60))
    cost = 0 if mode == "walk" else math.ceil(distance * (4 if mode == "bike" else 10))
    if mode == "taxi":
        cost = math.ceil((60 + distance * 18) * math.ceil(people / 4))
    elif mode == "drive":
        cost *= math.ceil(people / 4)
    else:
        cost *= math.ceil(people / 2)
    return {
        "minutes": minutes,
        "km": round(distance, 1),
        "cost": cost,
        "basis": "Simulated road distance and transport cost",
    }


def parse_interest(query):
    vocabulary = [
        "sushi",
        "japanese",
        "korean",
        "dosa",
        "kongu",
        "coffee",
        "dessert",
        "gelato",
        "bowling",
        "arcade",
        "gaming",
        "movies",
        "cinema",
        "park",
        "climbing",
        "go karting",
        "adventure",
        "biryani",
        "street food",
        "ice cream",
        "bakery",
        "juice",
        "pub",
        "water park",
        "trampoline",
        "turf",
        "pottery",
        "workshop",
        "museum",
        "zoo",
        "lake",
        "spicy",
        "quiet",
    ]
    q = query.casefold().replace("go-karting", "go karting")
    return [tag for tag in vocabulary if text_matches(tag, q)]


def window_fits(details, start, end):
    if "provider_windows" in details:
        return any(
            datetime.fromisoformat(a) <= start and end <= datetime.fromisoformat(b)
            for a, b in details["provider_windows"]
        )
    start, end = start.astimezone(IST), end.astimezone(IST)
    # Also support an overnight window starting on the previous day.
    for shift in [-1, 0]:
        day = start.date() + timedelta(days=shift)
        midnight = datetime.combine(day, datetime.min.time(), IST)
        for opening, closing in details.get("hours", {}).get(str(day.weekday()), []):
            if closing <= opening:
                closing += 1440
            if midnight + timedelta(minutes=opening) <= start and end <= midnight + timedelta(
                minutes=closing
            ):
                return True
    return False


def fresh_fields(venue, claims, request):
    needed = ["price_per_person", "hours", "closed"]
    if request.vegetarian and venue.category in FOOD:
        needed.append("vegetarian")
    if request.wheelchair:
        needed.append("wheelchair")
    valid = {
        c.field
        for c in claims
        if c.venue_id == venue.id
        and c.status == "accepted"
        and datetime.fromisoformat(c.expires_at) > datetime.now(timezone.utc)
    }
    if venue.details.get("provider_windows"):
        valid.update({"hours", "closed"})
    return all(f in valid for f in needed)


def live_candidate_order(request, venues, claims):
    """Spend bounded live checks on requested dishes/locked branches before proximity."""
    query = request.query.casefold()
    words = {word for word in re.findall(r"\w+", query) if len(word) > 2} - {
        "something",
        "different",
        "surprise",
        "want",
        "with",
        "near",
        "from",
        "food",
        "place",
        "please",
        "the",
        "and",
        "not",
        "without",
        "avoid",
    }
    words = {
        word
        for word in words
        if not re.search(
            r"(?:no|not|without|avoid|don't want|do not want)\s+(?:\w+\s+){0,2}" + re.escape(word), query
        )
    }

    def relevance(venue):
        fact = current_fact([c for c in claims if c.venue_id == venue.id], "offerings")
        fields = [venue.name, *venue.tags] + (
            [item["name"] for item in fact.value["value"] if item.get("available") is not False]
            if fact
            else []
        )
        return sum(any(text_matches(word, field) for field in fields) for word in words)

    candidates = [v for v in venues if v.id not in request.exclude_ids and v.category in request.categories]
    if request.outing_type == "food":
        candidates = [v for v in candidates if v.category in FOOD]
    elif request.outing_type == "entertainment":
        candidates = [v for v in candidates if v.category not in FOOD]
    return sorted(
        candidates,
        key=lambda v: (
            v.id not in request.lock_ids,
            -relevance(v),
            km((v.lat, v.lng), (request.lat, request.lng)),
            v.id,
        ),
    )


def build_plans(request: OutingRequest, venues, claims, profile, visited, route):
    rejected = Counter()
    selected = []
    q = request.query.casefold()
    # Everyday words for a category count as a request for it.
    q += "".join(
        " " + category
        for word, category in SYNONYMS.items()
        if re.search(r"(?<!\w)" + word + r"(?!\w)", q) and category not in q
    )
    menu_terms = {}
    for v in venues:
        claim = current_fact([c for c in claims if c.venue_id == v.id], "offerings")
        menu_terms[v.id] = (
            [
                term.casefold()
                for item in claim.value["value"]
                if item.get("available") is not False
                for term in [item["name"], item.get("cuisine", "")]
                if term
            ]
            if claim
            else []
        )

    def venue_terms(v):
        return set(v.tags) | set(menu_terms[v.id])

    def requested(v):
        return {t for t in interests if any(text_matches(t, term) for term in venue_terms(v))}

    vocabulary = {t.casefold() for v in venues for t in venue_terms(v)}
    vocabulary |= {
        word
        for terms in menu_terms.values()
        for term in terms
        for word in term.split()
        if len(word) > 2 and word not in {"and", "with", "the"}
    }
    interests = sorted(
        set(parse_interest(q))
        | {t for t in vocabulary if re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", q)}
    )
    negated = {
        t
        for t in interests
        if re.search(r"(?:no|not|without|avoid|don't want|do not want)\s+(?:\w+\s+){0,2}" + re.escape(t), q)
    }
    interests = [t for t in interests if t not in negated]
    explicit = set(profile.get("liked_tags", [])) | set(profile.get("preferred_cuisines", []))
    avoided = set(profile.get("avoided_tags", [])) | set(request.avoid_tags) | negated
    vegetarian = request.vegetarian or profile.get("vegetarian", False)
    accessible = request.wheelchair or profile.get("wheelchair", False)
    request = request.model_copy(update={"vegetarian": vegetarian, "wheelchair": accessible})
    generic = any(
        phrase in q
        for phrase in [
            "something different",
            "surprise",
            "don't know",
            "do not know",
            "not sure",
            "anything",
            "go somewhere",
            "hang out",
            "hangout",
            "something new",
            "familiar",
            "relax",
            "friends",
            "family",
        ]
    )
    novelty = request.novelty or ("new_place" if request.mood == "different" else "familiar")
    familiar_tags = (
        explicit | {t for t, score in profile.get("inferred", {}).items() if score > 0}
        if profile.get("learn_from_visits", True)
        else explicit
    )
    named = [v for v in venues if v.name.casefold() in q]
    if q.strip() and not interests and not generic and not negated and not named:
        return {
            "options": [],
            "excluded": {},
            "interest_tags": [],
            "candidate_count": 0,
            "message": "Your specific request has no supported match in the current inventory. Try a listed cuisine or activity, or choose Surprise me. We have not substituted unrelated places.",
        }
    for v in venues:
        d = v.details
        if v.status != "published" or v.id in request.exclude_ids or v.category not in request.categories:
            continue
        if request.outing_type == "food" and v.category not in FOOD:
            continue
        if request.outing_type == "entertainment" and v.category in FOOD:
            continue
        reason = None
        if not getattr(v, "is_demo", False) and not d.get("location_approval"):
            reason = "location awaits operator approval"
        elif not getattr(v, "is_demo", False) and not d.get("maps_identity", {}).get("confirmed_by"):
            reason = "location name and Maps branch need confirmation"
        elif d.get("closed"):
            reason = "closed"
        elif not fresh_fields(v, claims, request):
            reason = "facts need verification"
        elif avoided.intersection(v.tags):
            reason = "excluded preference"
        elif vegetarian and v.category in FOOD and d.get("vegetarian") is not True:
            reason = "vegetarian suitability unconfirmed"
        elif accessible and d.get("wheelchair") is not True:
            reason = "step-free access unconfirmed"
        elif request.children and (not d.get("child_friendly") or d.get("min_age", 0) > 0):
            reason = "age suitability"
        elif request.party_size > d.get("max_group", 0):
            reason = "group capacity unconfirmed"
        elif not isinstance(d.get("price_per_person"), (int, float)):
            reason = "price unconfirmed"
        if reason:
            rejected[reason] += 1
        else:
            selected.append(v)

    # Bounded candidate pool prioritizes the user's explicit request before combinations.
    def candidate_score(v):
        return (
            len(requested(v)) * 20
            + len(set(v.tags) & explicit) * 4
            + ((v.id not in visited) * 2 if novelty != "familiar" else (v.id in visited) * 2)
        )

    selected = sorted(selected, key=candidate_score, reverse=True)
    locked = [v for v in selected if v.id in request.lock_ids]
    pool_size = 10 if request.max_stops > 2 else 18
    selected = (
        locked + [v for v in selected if v.id not in request.lock_ids][: max(0, pool_size - len(locked))]
    )
    sequences = chain.from_iterable(permutations(selected, n) for n in range(1, request.max_stops + 1))
    options = []
    cap = request.budget * (request.party_size if request.budget_unit == "person" else 1)
    for sequence in sequences:
        ids = {v.id for v in sequence}
        if not set(request.lock_ids).issubset(ids):
            continue
        if interests and not any(requested(v) for v in sequence):
            continue
        if named and not any(v.id in {n.id for n in named} for v in sequence):
            continue
        if request.outing_type == "combined" and not (
            any(v.category in FOOD for v in sequence) and any(v.category not in FOOD for v in sequence)
        ):
            continue
        clock = request.departure
        position = (request.lat, request.lng)
        previous_id = "origin"
        stops, cost, invalid = [], 0, False
        for v in sequence:
            d = v.details
            leg = route(previous_id, v.id, position, (v.lat, v.lng))
            if leg is None:
                rejected["route unavailable"] += 1
                invalid = True
                break
            arrival = clock + timedelta(minutes=leg["minutes"])
            wait = d.get("wait_minutes", 15)
            begin = arrival + timedelta(minutes=wait)
            duration = d.get("visit_minutes", 60)
            item_cost = math.ceil(d["price_per_person"] * request.party_size)
            offering = "Standard visit"
            dated = d.get("dated_sessions", [])
            if dated:
                viable = [
                    s
                    for s in dated
                    if datetime.fromisoformat(s["starts_at"]) >= begin
                    and datetime.fromisoformat(s["expires_at"]) > datetime.now(timezone.utc)
                    and (s.get("available_places") is None or s["available_places"] >= request.party_size)
                ]
                if not viable:
                    invalid = True
                    rejected["no current session availability"] += 1
                    break
                session = min(viable, key=lambda s: datetime.fromisoformat(s["starts_at"]))
                begin = datetime.fromisoformat(session["starts_at"])
                duration, item_cost = (
                    session["duration_minutes"],
                    math.ceil(session["price_per_person"] * request.party_size),
                )
                offering = session["name"]
                wait = math.ceil((begin - arrival).total_seconds() / 60)
            elif v.category == "cinema":
                local = begin.astimezone(IST)
                sessions = [
                    datetime.combine(local.date(), datetime.strptime(s, "%H:%M").time(), IST)
                    for s in d.get("sessions", [])
                ]
                viable = [s for s in sessions if s >= begin]
                if not viable:
                    invalid = True
                    rejected["no suitable screening"] += 1
                    break
                begin = min(viable)
                wait = math.ceil((begin - arrival).total_seconds() / 60)
            elif d.get("packages"):
                packages = [
                    p
                    for p in d["packages"]
                    if datetime.fromisoformat(p["expires_at"]) > datetime.now(timezone.utc)
                ]
                if not packages:
                    invalid = True
                    rejected["package price expired"] += 1
                    break

                def package_cost(p):
                    return math.ceil(
                        p["price"]
                        * (
                            request.party_size
                            if p["unit"] == "person"
                            else math.ceil(request.party_size / p["people_per_unit"])
                        )
                    )

                packages = [
                    p
                    for p in packages
                    if (begin + timedelta(minutes=p["duration_minutes"]) - request.departure).total_seconds()
                    / 60
                    + 15
                    <= request.duration_minutes
                    and window_fits(d, arrival, begin + timedelta(minutes=p["duration_minutes"]))
                    and (cost + package_cost(p) + d.get("fee_per_group", 0) + leg["cost"]) * 1.1 <= cap
                ]
                if not packages:
                    invalid = True
                    rejected["no package fits remaining time or budget"] += 1
                    break
                package = min(packages, key=package_cost)
                item_cost, duration, offering = (
                    package_cost(package),
                    package["duration_minutes"],
                    package["name"],
                )
            end = begin + timedelta(minutes=duration)
            if not window_fits(d, arrival, end):
                invalid = True
                rejected["opening hours"] += 1
                break
            fees = d.get("fee_per_group", 0)
            cost += item_cost + fees + leg["cost"]
            stops.append(
                {
                    "venue_id": v.id,
                    "name": v.name,
                    "category": v.category,
                    "area": v.area,
                    "speciality": d.get("speciality", "Visit"),
                    "art": d.get("art", "leaf"),
                    "arrival": arrival.isoformat(),
                    "start": begin.isoformat(),
                    "end": end.isoformat(),
                    "travel": leg,
                    "wait_minutes": wait,
                    "visit_minutes": duration,
                    "offering": offering,
                    "cost": item_cost,
                    "fees": fees,
                    "revision": v.revision,
                    "lat": v.lat,
                    "lng": v.lng,
                    "evidence_ids": [c.id for c in claims if c.venue_id == v.id and c.status == "accepted"],
                }
            )
            position, previous_id, clock = (v.lat, v.lng), v.id, end
        if invalid:
            continue
        reserve = math.ceil(cost * 0.10)
        buffer = 15
        minutes = math.ceil((clock - request.departure).total_seconds() / 60) + buffer
        if minutes > request.duration_minutes:
            rejected["time budget"] += 1
            continue
        if cost + reserve > cap:
            rejected["spending budget"] += 1
            continue
        tags = set(t for v in sequence for t in v.tags)
        matched_interests = set().union(*(requested(v) for v in sequence))
        novel = sum(v.id not in visited for v in sequence)
        reasons = []
        if interests:
            reasons.append("Matches your request for " + ", ".join(sorted(matched_interests)))
        if explicit & tags:
            reasons.append("Matches saved interests: " + ", ".join(sorted(explicit & tags)))
        if novelty != "familiar" and novel:
            reasons.append("Includes a place outside your confirmed visit history")
        if request.mood in tags:
            reasons.append(f"Suits a {request.mood} outing")
        if request.companion_interests:
            overlap = tags & set(request.companion_interests)
            reasons.append(
                "Companion interests matched: " + ", ".join(overlap)
                if overlap
                else "Companion interests are not confirmed for these stops"
            )
        inferred = profile.get("inferred", {})
        inference_score = (
            sum(float(inferred.get(t, 0)) for t in tags) if profile.get("learn_from_visits", True) else 0
        )
        if profile.get("learn_from_visits", True):
            inference_score += sum(
                float(profile.get("occasion_preferences", {}).get(request.occasion, {}).get(t, 0))
                for t in tags
            )
        score = (
            len(matched_interests) * 20
            + len(explicit & tags) * 5
            + (novel * 6 if novelty != "familiar" else (len(sequence) - novel) * 4)
        )
        if novelty == "new_taste" and familiar_tags:
            food_tags = {t for v in sequence if v.category in FOOD for t in v.tags} - {
                "quiet",
                "social",
                "outdoor",
                "indoor",
                "active",
                "vegetarian",
                "different",
            }
            unfamiliar = food_tags - familiar_tags
            score += min(3, len(unfamiliar)) * 3
            if unfamiliar:
                reasons.append(
                    "Offers tastes beyond your saved preferences: " + ", ".join(sorted(unfamiliar))
                )
        score += (
            (5 if request.mood in tags else 0)
            + len(tags & set(request.companion_interests)) * 3
            + inference_score
        )
        score += len(sequence) * 5 - minutes * 0.02 - (cost + reserve) / cap
        if request.companion_preferences:
            matches = [len(tags & set(person)) for person in request.companion_preferences if person]
            if matches:
                score += min(matches) * 4 + sum(matches)
                reasons.append(
                    f"Matches interests for {sum(n > 0 for n in matches)} of {len(matches)} companions with stated preferences"
                )
        # Two meals, or the same kind of activity twice, make a weak outing.
        kinds = ["meal" if v.category in {"food", "street_food"} else v.category for v in sequence]
        score -= 12 * (len(kinds) - len(set(kinds)))
        options.append(
            {
                "title": " + ".join(v.name for v in sequence),
                "stops": stops,
                "total_cost": cost + reserve,
                "cost_before_reserve": cost,
                "reserve": reserve,
                "total_minutes": minutes,
                "time_buffer": buffer,
                "budget_cap": cap,
                "budget_remaining": cap - cost - reserve,
                "time_remaining": request.duration_minutes - minutes,
                "reasons": reasons or ["Fits your selected categories, time and budget"],
                "score": round(score, 2),
                "is_demo": all(v.is_demo for v in sequence),
                "warnings": [
                    "Costs and travel are estimates; check availability before leaving.",
                    "Duration ends at your last stop. No return journey is included.",
                ],
            }
        )
    # Diversify by stop set rather than showing the same outing in reverse order.
    options.sort(key=lambda p: p["score"], reverse=True)
    distinct, seen = [], set()
    limit = request.max_options
    total_sets = len({tuple(sorted(s["venue_id"] for s in o["stops"])) for o in options})
    # First pass prefers alternatives that share at most one stop with those already
    # chosen; the second pass fills any remaining places with the next best sets.
    for varied_only in (True, False):
        for option in options:
            ids = {s["venue_id"] for s in option["stops"]}
            key = tuple(sorted(ids))
            if key in seen:
                continue
            if varied_only and any(len(ids & set(other)) > min(1, len(ids) - 1) for other in seen):
                continue
            seen.add(key)
            distinct.append(option)
            if len(distinct) == limit:
                break
        if len(distinct) == limit:
            break
    distinct.sort(key=lambda p: p["score"], reverse=True)
    return {
        "options": distinct,
        # Distinct stop sets that fit every constraint, before the limit above.
        "total_options": total_sets,
        "excluded": dict(rejected),
        "interest_tags": interests,
        "message": "Choose the outing that feels right."
        if distinct
        else "No verified option fits all your requirements. Try a longer duration, a different departure time or broader categories; your budget was not changed.",
        "candidate_count": len(selected),
    }
