"""Training data for the understanding model: labelled requests built from parts.

Each example is assembled from parts (activities, people, budget, time, place, diet, access,
mood, things to avoid...), each phrased many ways, in shuffled order with varied joins,
spellings and Tanglish. Every part carries its own labels, so the labels are exact. Some
parts are deliberate traps that must NOT set a field ("one veg" in a group is not a veg
group; "family" alone is not kids; "not too sweet" is not something to avoid).

This file never reads frozen_test.jsonl; tests check that no generated text equals a frozen
request.
"""

from __future__ import annotations

import random

from .lexicon import AREAS, CATEGORY_WORDS, INTERESTS, VARIANTS, normalize

TAGS = ("PARTY", "BUDGET", "DURATION", "AREA", "INTEREST", "AVOID", "STOPS")
WORD_NUMBERS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
                9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 15: "fifteen", 20: "twenty"}
TAMIL_NUMBERS = {2: "rendu", 3: "moonu", 4: "naalu", 5: "anju", 6: "aaru", 7: "ezhu", 8: "ettu", 10: "pathu"}
SPELLINGS: dict[str, list[str]] = {}
for _variant, _canonical in VARIANTS.items():
    if " " not in _variant and _variant.isalpha():
        SPELLINGS.setdefault(_canonical, []).append(_variant)
BY_CATEGORY: dict[str, list[str]] = {}
for _interest, _category in INTERESTS.items():
    BY_CATEGORY.setdefault(_category, []).append(_interest)
# How often each category is asked for (food and cafes most).
CATEGORY_WEIGHTS = {"food": 9, "street_food": 3, "cafe": 5, "dessert": 4, "nightlife": 2, "cinema": 4,
                    "gaming": 3, "bowling": 2, "adventure": 2, "amusement": 1, "park": 2, "workshop": 1,
                    "attraction": 1, "sports": 2}
MEAL_TIMES = {"dinner": "evening", "lunch": "afternoon", "breakfast": "morning"}


class Example:
    def __init__(self):
        self.parts: list[list[tuple[str, str | None]]] = []
        self.r = {"categories": set(), "interests": [], "party_size": None, "budget": None, "budget_unit": None,
                  "duration_minutes": None, "vegetarian": False, "children": False, "wheelchair": False,
                  "novelty": None, "mood": None, "max_stops": None, "area": None, "transport": None,
                  "avoid": [], "time_of_day": None, "surprise": False, "out_of_scope": False}

    def add(self, *segments):
        self.parts.append([s if isinstance(s, tuple) else (s, None) for s in segments if s != ""])

    def set(self, field, value):
        if self.r[field] in (None, False):
            self.r[field] = value


def _num(rng, n):
    if n in WORD_NUMBERS and rng.random() < 0.35:
        return WORD_NUMBERS[n]
    return str(n)


def _spell(rng, word):
    if word in SPELLINGS and rng.random() < 0.2:
        return rng.choice(SPELLINGS[word])
    return word


def _money(rng, m):
    forms = [str(m), str(m), f"₹{m}", f"rs {m}", f"rs. {m}", f"{m} rupees", f"{m} rs", f"rs{m}"]
    if m >= 1000:
        forms += [f"{m:,}", f"₹{m:,}"]
        if m % 1000 == 0:
            forms += [f"{m // 1000}k"] * 2
        elif m % 500 == 0:
            forms.append(f"{m / 1000:g}k")
    return rng.choice(forms)


def activity(rng, ex: Example):
    k = rng.choices([1, 2, 3, 4], weights=[48, 38, 10, 4])[0]
    cats: list[str] = []
    while len(cats) < k:
        c = rng.choices(list(CATEGORY_WEIGHTS), weights=list(CATEGORY_WEIGHTS.values()))[0]
        if c not in cats:
            cats.append(c)
    items = []
    for c in cats:
        ex.r["categories"].add(c)
        pool = BY_CATEGORY.get(c, [])
        adj = rng.choice(["", "", "", "cheap ", "good ", "best ", "nice ", "some ", "authentic ", "a "])
        if pool and rng.random() < 0.55:
            interest = rng.choice(pool)
            ex.r["interests"].append(interest)
            tail = rng.choice(["", "", "", " place", " spot", " joint"])
            if c in ("adventure", "amusement") and rng.random() < 0.3:
                tail = " park"
            if c == "dessert" and rng.random() < 0.3:
                tail = rng.choice([" shop", " parlour", " corner"])
            if interest == "lake" and rng.random() < 0.5:
                tail = rng.choice([" side", "side"])
            if c == "workshop" and rng.random() < 0.5:
                tail = " workshop"
            if c == "sports" and rng.random() < 0.4:
                tail = rng.choice([" court", " turf", " game"])
            if c == "food" and rng.random() < 0.15:
                ex.r["interests"].append("meals")
                items.append([adj, (_spell(rng, interest), "INTEREST"), " style ", ("meals", "INTEREST")])
                continue
            items.append([adj, (_spell(rng, interest), "INTEREST"), tail])
        else:
            word = rng.choice(CATEGORY_WORDS[c])
            if word in MEAL_TIMES:
                ex.set("time_of_day", MEAL_TIMES[word])
            if word == "mess" and rng.random() < 0.4:
                ex.r["interests"].append("meals")
                items.append([adj, "mess style ", ("meals", "INTEREST")])
                continue
            items.append([adj, _spell(rng, word)])
    lead = rng.choice(["", "", "", "i want ", "looking for ", "plan ", "suggest ", "need ", "we want ",
                       "find me ", "craving ", "let's do ", "any good ", "can you plan ", "take us for "])
    segments = [lead]
    for n, item in enumerate(items):
        if n:
            segments.append(rng.choice([" and ", " then ", ", ", " followed by ", " and then ", " & ",
                                        " after that ", " + ", " with "]))
        segments.extend(item)
    ex.add(*segments)


def party(rng, ex: Example):
    roll = rng.random()
    if roll < 0.12:
        phrase, n = rng.choice([("just me", 1), ("alone", 1), ("solo", 1), ("only me", 1), ("myself", 1)])
        ex.set("party_size", n)
        ex.add((phrase, "PARTY"))
        return
    if roll < 0.24:
        phrase = rng.choice(["both of us", "the two of us", "me and my wife", "me and my husband",
                             "me and my girlfriend", "a couple", "me and my partner", "my wife and i",
                             "my husband and i", "my friend and i", "my girlfriend and i", "me and my friend"])
        ex.set("party_size", 2)
        ex.add((phrase, "PARTY"))
        return
    if roll < 0.29:
        ex.set("party_size", 2)
        ex.set("time_of_day", "evening")
        ex.add(("date", "PARTY"), " night")
        return
    n = rng.choice([2, 2, 3, 3, 4, 4, 4, 5, 5, 6, 6, 7, 8, 10, 12, 15, 20])
    if roll < 0.37 and n in TAMIL_NUMBERS:
        ex.set("party_size", n)
        ex.add((f"{TAMIL_NUMBERS[n]} {rng.choice(['peru', 'per', 'perukku', 'per ku'])}", "PARTY"))
        return
    template = rng.choice(["{n} of us", "for {n}", "for {n} people", "{n} people", "we are {n}", "group of {n}",
                           "{n} pax", "party of {n}", "{n} persons", "{n} friends", "team of {n}", "with {n} friends",
                           "{n} guys", "{n} ppl", "{n} kids", "a group of {n}", "with {n} guys", "with {n} people",
                           "{n} colleagues", "with {n} colleagues", "{n} cousins", "with {n} cousins",
                           "we're {n}", "total {n} people"])
    ex.set("party_size", n)
    if "friends" in template:
        ex.set("mood", "social")
    if "kids" in template:
        ex.set("children", True)
    ex.add((template.format(n=_num(rng, n)), "PARTY"))


def budget(rng, ex: Example):
    m = rng.choice([100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500, 2000, 2500, 3000,
                    4000, 5000, 8000, 10000])
    money = _money(rng, m)
    unit = rng.choices([None, "person", "group"], weights=[40, 30, 30])[0]
    if unit is None:
        phrase = rng.choice(["under {m}", "below {m}", "within {m}", "budget {m}", "max {m}", "{m} max",
                             "around {m}", "upto {m}", "less than {m}", "{m} budget", "budget is {m}",
                             "not more than {m}"]).format(m=money)
    elif unit == "person":
        phrase = rng.choice(["{m} per head", "{m} per person", "{m} each", "{m} pp", "{m} a head",
                             "under {m} per person", "budget {m} each", "{m} per person max", "{m} per head max"]
                            ).format(m=money)
    else:
        if rng.random() < 0.15:
            ex.set("budget", m)
            ex.set("budget_unit", "group")
            ex.set("party_size", 2)
            ex.add((f"under {money}", "BUDGET"), " for ", ("both of us", "PARTY"))
            return
        phrase = rng.choice(["{m} total", "{m} in total", "total {m}", "total budget {m}", "{m} for all of us",
                             "{m} overall", "budget {m} total", "{m} for the whole group"]).format(m=money)
    ex.set("budget", m)
    ex.set("budget_unit", unit)
    ex.add((phrase, "BUDGET"))


def duration(rng, ex: Example):
    roll = rng.random()
    if roll < 0.12:
        phrase, value = rng.choice([("an hour", 60), ("half an hour", 30), ("one and a half hours", 90),
                                    ("1.5 hours", 90), ("couple of hours", 120), ("a couple of hours", 120)])
    elif roll < 0.35:
        value = rng.choice([30, 45, 60, 90, 120, 150])
        phrase = rng.choice([f"{value} minutes", f"{value} mins", f"{value} min"])
    else:
        n = rng.choice([1, 2, 2, 3, 3, 4, 5, 6])
        value = n * 60
        phrase = rng.choice(["{n} hours", "{n} hrs", "{n} hour", "{n} hr"]).format(n=_num(rng, n))
    lead = rng.choice(["", "", "", "for ", "we have ", "about ", "around ", "only ", "just "])
    tail = rng.choice(["", "", "", " free", " max", " only"])
    ex.set("duration_minutes", value)
    ex.add(lead, (phrase, "DURATION"), tail)


def stops(rng, ex: Example):
    roll = rng.random()
    if roll < 0.25:
        ex.set("max_stops", 1)
        ex.add((rng.choice(["just one place", "only one place", "one stop only", "single stop", "one place only"]),
                "STOPS"))
        return
    n = rng.choice([2, 2, 3, 3, 4])
    shown = _num(rng, n)
    ex.set("max_stops", n)
    if roll < 0.5:
        tail = rng.choice(["evening", "outing", "plan", "day"])
        if tail == "evening":
            ex.set("time_of_day", "evening")
        ex.add(rng.choice(["a ", "plan a ", ""]), (f"{shown} stop", "STOPS"), " " + tail)
    else:
        ex.add((rng.choice(["{n} stops", "{n} places", "max {n} stops", "{n} stops max", "{n} places max",
                            "not more than {n} stops"]).format(n=shown), "STOPS"))


def area(rng, ex: Example):
    name = rng.choice(AREAS)
    shown = name if rng.random() < 0.6 else name.lower()
    ex.set("area", name)
    if rng.random() < 0.12:
        ex.set("transport", "walk")
        ex.add(rng.choice(["walking distance from ", "walkable from "]), (shown, "AREA"))
        return
    lead = rng.choice(["near ", "in ", "around ", "from ", "starting from ", "close to ", "at ", "", "nearby "])
    tail = "" if lead else rng.choice([" side", " area", ""])
    ex.add(lead, (shown, "AREA"), tail)


def transport(rng, ex: Example):
    mode, phrase = rng.choice([
        ("walk", "on foot"), ("walk", "we'll walk"), ("walk", "walking distance"), ("walk", "walkable"),
        ("bike", "by bike"), ("bike", "on bike"), ("bike", "on my scooty"), ("bike", "two wheeler"),
        ("drive", "driving"), ("drive", "by car"), ("drive", "in my car"), ("drive", "we have a car"),
        ("taxi", "cab"), ("taxi", "by cab"), ("taxi", "taxi"), ("taxi", "uber"), ("taxi", "we will take a cab"),
        ("taxi", "auto"),
    ])
    ex.set("transport", mode)
    ex.add(phrase)


def time_of_day(rng, ex: Example):
    value, phrase = rng.choice([
        ("morning", "morning"), ("morning", "in the morning"), ("morning", "tomorrow morning"),
        ("morning", "early morning"), ("afternoon", "afternoon"), ("afternoon", "this afternoon"),
        ("afternoon", "at noon"), ("evening", "tonight"), ("evening", "this evening"), ("evening", "evening"),
        ("evening", "at night"), ("evening", "saayangalam"), ("evening", "after office"),
        ("late_night", "late night"), ("late_night", "after 11"), ("late_night", "after midnight"),
        ("late_night", "after 10 pm"), ("late_night", "past midnight"), ("now", "right now"), ("now", "now"),
        ("now", "asap"), ("now", "immediately"),
    ])
    ex.set("time_of_day", value)
    ex.add(phrase)


def diet(rng, ex: Example):
    if rng.random() < 0.2:
        ex.add(rng.choice(["one veg", "one of us is veg", "one vegetarian in the group", "non veg ok"]))
        return
    ex.set("vegetarian", True)
    phrase = rng.choice(["veg", "pure veg", "veg only", "only veg", "vegetarian", "jain", "jain food",
                         "strictly veg", "only vegetarian", "veg food only", "fully veg", "veg food"])
    if "food" in phrase:
        ex.r["categories"].add("food")
    ex.add(phrase)


def kids(rng, ex: Example):
    if rng.random() < 0.25:
        ex.add(rng.choice(["with family", "family friendly", "with my parents", "family outing", "with my family"]))
        return
    ex.set("children", True)
    if rng.random() < 0.3:
        # Ages are not group sizes: "my nephew who is 8" is one child, not eight people.
        age = rng.randint(2, 14)
        ex.add(rng.choice([f"with my nephew who is {age}", f"my son is {age}", f"my daughter is {age}",
                           f"kids aged {age} and {age + 2}", f"a {age} year old", f"{age} yr old kid",
                           f"my niece is {age}", f"with my {age} year old", f"kid of {age}"]))
        return
    ex.add(rng.choice(["with kids", "kids with us", "with my son", "with my daughter", "for the kids",
                       f"for a {rng.randint(3, 12)} year old", "children too", "with a toddler",
                       "my kids are coming", "kid friendly", "with small kids", "for my son's birthday",
                       "my daughter's birthday", "for my son", "for my daughter", "kids birthday"]))


def access(rng, ex: Example):
    ex.set("wheelchair", True)
    ex.add(rng.choice(["wheelchair", "wheelchair accessible", "my dad uses a wheelchair",
                       "my mom can't climb stairs", "no stairs please", "grandpa uses a walker",
                       "accessible for my grandmother", "step free entry", "she can't walk much"]))


def mood(rng, ex: Example):
    value, phrase = rng.choice([
        ("comfort", "comfort food"), ("comfort", "something cozy"), ("comfort", "comforting"),
        ("quiet", "quiet"), ("quiet", "peaceful"), ("quiet", "calm place"), ("quiet", "to read"),
        ("quiet", "to work from"), ("quiet", "somewhere silent"),
        ("social", "with friends"), ("social", "with the gang"), ("social", "hangout with friends"),
        ("social", "team outing"), ("social", "office team outing"),
        ("active", "something active"), ("active", "want to sweat"), ("active", "something energetic"),
        ("active", "physical activity"),
    ])
    ex.set("mood", value)
    if phrase == "comfort food":
        ex.r["categories"].add("food")
    ex.add(phrase)


def novelty(rng, ex: Example):
    value, phrase = rng.choice([
        ("new_place", "somewhere new"), ("new_place", "a place i've never been to"), ("new_place", "never been there"),
        ("new_place", "new place"), ("new_taste", "a new cuisine"), ("new_taste", "something i've never tasted"),
        ("new_taste", "a cuisine we have never tried"), ("new_taste", "try new food"),
        ("familiar", "our usual"), ("familiar", "our favourite spots"), ("familiar", "nothing new"),
        ("familiar", "same as always"), ("familiar", "the regular place"),
    ])
    ex.set("novelty", value)
    if "cuisine" in phrase or "food" in phrase:
        ex.r["categories"].add("food")
    ex.add(phrase)


def surprise(rng, ex: Example):
    phrase = rng.choice(["surprise me", "i don't know what to do", "dont know where to go", "no idea what to do",
                         "suggest something", "anything is fine", "enga ponalam", "what can we do",
                         "bored, suggest something", "something different", "something different please",
                         "i'm not sure", "not sure what to do", "show me something good", "idk",
                         "you decide", "recommend something", "what's good around"])
    ex.set("surprise", True)
    if "different" in phrase:
        ex.set("mood", "different")
    ex.add(phrase)


def out_of_scope(rng, ex: Example):
    getaway = rng.choice(["ooty", "kodaikanal", "munnar", "valparai", "coorg", "wayanad", "mysore", "kovalam"])
    phrase = rng.choice(["a concert", "comedy show", "standup comedy show", "music festival", "ipl match",
                         f"a trip to {getaway}", f"weekend trip to {getaway}", f"plan a trip to {getaway}",
                         f"{getaway} weekend getaway", f"{getaway} getaway", f"{getaway} road trip",
                         "weekend getaway", "road trip", "scenic drive", "long drive", "hotel room", "book a hotel",
                         "resort stay", "in chennai", "in bangalore", "in madurai", "flight tickets",
                         "a wedding venue", "match screening"])
    ex.set("out_of_scope", True)
    ex.add(phrase)


def avoid(rng, ex: Example):
    if rng.random() < 0.2:
        ex.add(rng.choice(["not too sweet", "not too spicy", "not too far", "not too expensive", "not very loud"]))
        return
    thing = rng.choice(["spicy", "alcohol", "smoking", "mall", "crowded", "onion", "garlic", "egg", "oily",
                        "meat", "beef", "pork", "loud music", "queues"])
    lead = rng.choice(["no ", "avoid ", "without ", "not a ", "nothing ", "no ", "please no "])
    if thing == "mall" and lead not in ("not a ", "no "):
        lead = "not a "
    ex.r["avoid"].append(thing)
    tail = rng.choice(["", "", " please", " places", " food", " food please"])
    if "food" in tail:
        ex.r["categories"].add("food")
    ex.add(lead, (thing, "AVOID"), tail)


# Phrases that set nothing (or only what is listed): they teach the model what NOT to read.
FILLERS = [("please", {}), ("today", {}), ("this weekend", {}), ("tomorrow", {}), ("something nice", {}),
           ("good vibes", {}), ("nearby", {}), ("pls", {}), ("any ideas", {}), ("help", {}), ("half day", {}),
           ("whole evening", {"time_of_day": "evening"}), ("full day out", {}), ("with parking", {}),
           ("budget friendly", {}), ("cheap", {}), ("something romantic", {}), ("anniversary", {}),
           ("birthday", {}), ("something fun", {}), ("something to do after", {}), ("something exciting", {}),
           ("on a rainy day", {}), ("it's raining", {}), ("something chill", {}), ("chill vibes", {}),
           ("something close", {}), ("something for everyone", {}), ("half day out", {}), ("anything open", {}),
           ("anything nearby", {}), ("anything open now", {"time_of_day": "now"})]
PARTS = [(party, 0.4), (budget, 0.3), (duration, 0.25), (stops, 0.08), (area, 0.25), (transport, 0.12),
         (time_of_day, 0.3), (diet, 0.12), (kids, 0.1), (access, 0.05), (mood, 0.12), (novelty, 0.06),
         (avoid, 0.1)]


def example(rng: random.Random) -> dict:
    ex = Example()
    if rng.random() < 0.08:
        surprise(rng, ex)
    elif rng.random() < 0.06:
        out_of_scope(rng, ex)
        if rng.random() < 0.4:
            activity(rng, ex)
    else:
        activity(rng, ex)
    for part, chance in PARTS:
        if rng.random() < chance:
            part(rng, ex)
    if rng.random() < 0.22:
        phrase, effects = rng.choice(FILLERS)
        for field, value in effects.items():
            ex.set(field, value)
        ex.add(phrase)
    head, rest = ex.parts[0], ex.parts[1:]
    rng.shuffle(rest)
    order = [head, *rest] if rng.random() < 0.7 else rng.sample(ex.parts, len(ex.parts))
    segments: list[tuple[str, str | None]] = []
    for n, part in enumerate(order):
        if n:
            segments.append((rng.choice([", ", ", ", " ", ". ", " - ", " and ", "; "]), None))
        segments.extend(part)
    text = "".join(s for s, _ in segments).strip()
    if rng.random() < 0.05:
        text = text.upper()
    elif rng.random() < 0.3:
        text = text[:1].upper() + text[1:]
    words, tags = [], []
    for raw, tag in segments:
        toks = normalize(raw)
        words.extend(toks)
        tags.extend([f"B-{tag}" if i == 0 else f"I-{tag}" for i in range(len(toks))] if tag else ["O"] * len(toks))
    reading = dict(ex.r)
    reading["categories"] = sorted(reading["categories"])
    reading["interests"] = list(dict.fromkeys(reading["interests"]))
    if reading["budget"] is None:
        reading["budget_unit"] = None
    return {"text": text, "words": words, "tags": tags, "reading": reading}


def dataset(n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    return [example(rng) for _ in range(n)]
