"""One category list for the planner, the collector and the UI.

Rules classify by venue name first, then by the dish/activity context. They are
deterministic keyword rules, not a model, so every assignment can be explained.
"""

import re

# id -> (label, group). Order is the display order.
CATEGORY_INFO = {
    "food": ("Restaurants", "eat"),
    "street_food": ("Street food & messes", "eat"),
    "cafe": ("Cafés", "eat"),
    "dessert": ("Desserts & bakeries", "eat"),
    "nightlife": ("Bars & lounges", "do"),
    "cinema": ("Movies", "do"),
    "gaming": ("Gaming & arcades", "do"),
    "bowling": ("Bowling", "do"),
    "adventure": ("Adventure", "do"),
    "amusement": ("Theme & water parks", "do"),
    "park": ("Parks & lakes", "do"),
    "workshop": ("Creative workshops", "do"),
    "attraction": ("Museums & sights", "do"),
    "sports": ("Turfs & courts", "do"),
}
CATEGORIES = list(CATEGORY_INFO)
FOOD = {c for c, (_, group) in CATEGORY_INFO.items() if group == "eat"}

# Typical figures used only for the labelled test inventory, never as facts.
# (price per person INR, visit minutes, opens, closes) in minutes after midnight.
ESTIMATES = {
    "food": (350, 60, 660, 1350),
    "street_food": (120, 30, 960, 1320),
    "cafe": (300, 60, 600, 1320),
    "dessert": (150, 30, 660, 1350),
    "nightlife": (1200, 120, 1020, 1410),
    "cinema": (220, 180, 600, 1410),
    "gaming": (400, 60, 660, 1290),
    "bowling": (400, 60, 660, 1290),
    "adventure": (600, 60, 600, 1200),
    "amusement": (900, 240, 600, 1080),
    "park": (20, 60, 360, 1140),
    "workshop": (800, 120, 600, 1140),
    "attraction": (50, 90, 600, 1020),
    "sports": (300, 60, 360, 1320),
}

_RULES = [
    ("cinema", r"\b(cinemas?|movies?|multiplex|theatres?|theaters?|talkies|pvr|inox|imax)\b"),
    ("bowling", r"\bbowling\b"),
    (
        "amusement",
        r"\b(water ?park|theme ?park|amusement|snow (world|city|park)|black thunder|kovai kondattam|fun ?city)\b",
    ),
    (
        "adventure",
        r"\b(go ?kart\w*|kart\w*|trampoline|paintball|zip ?line|climbing|bungee|atv|adventure|speedway|circuit|laser tag|rope course)\b",
    ),
    (
        "gaming",
        r"\b(arcade|gaming|game ?zone|games? (lounge|cafe|centre|center)|vr|virtual reality|playstation|ps5|escape rooms?|snooker|billiards|play ?zone|fun ?zone|timezone)\b",
    ),
    (
        "workshop",
        r"\b(workshops?|pottery|painting|tufting|candle making|art studio|craft (studio|class|classes)|resin art|art jam|diy)\b",
    ),
    (
        "sports",
        r"\b(turf|pickleball|badminton|swimming|box cricket|cricket nets?|futsal|skating|golf|tennis court|sports (club|arena|centre|center))\b",
    ),
    ("attraction", r"\b(museum|zoo|aquarium|art gallery|planetarium|science (centre|center|park))\b"),
    (
        "dessert",
        r"\b(ice ?creams?|gelato|desserts?|bakery|bakers|bakes|cakes?|sweets?|juice\w*|milk ?shakes?|shakes|kulfi|waffles?|donuts?|doughnuts?|falooda|creamery|patisserie|chocolat\w*|brownies?|jigarthanda)\b",
    ),
    ("nightlife", r"\b(pub|bar|brewery|brewing|brew ?pub|taproom|lounge|night ?club|resto ?bar)\b"),
    ("cafe", r"\b(cafe|cafes|coffee|kaapi|chai|tea (house|room|shop|stall|kadai)|bistro|roasters)\b"),
    (
        "street_food",
        r"\b(stall|kadai|mess|tiffin|chaat|pani ?puri|kaalan|kalan|thattu ?kadai|bajji|street food|food street|food cart|canteen|bhel|vada pav|thalluvandi|push ?cart)\b",
    ),
    (
        "food",
        r"\b(restaurants?|hotel|biryani|biriyani|kitchen|dhaba|grills?|bhavan|bhawan|unavagam|diner|dining|eatery|parotta|barbeque|bbq|pizza|burger|shawarma|mandi|food court)\b",
    ),
    ("park", r"\b(park|garden|gardens|poonga|lake|kulam|eco park)\b"),
]
_RULES = [(category, re.compile(pattern)) for category, pattern in _RULES]


def _key(value):
    value = str(value or "").casefold().replace("é", "e").replace("&", " and ")
    return " ".join(re.sub(r"[^\w]+", " ", value).split())


def match(text):
    """First matching category for one piece of text, or None."""
    key = _key(text)
    if not key:
        return None
    return next((category for category, rule in _RULES if rule.search(key)), None)


def classify(name, context="", default="food"):
    """Name evidence outranks dish/activity context; unknowns keep the default."""
    return match(name) or match(context) or default


def label(category):
    return CATEGORY_INFO.get(category, (category.replace("_", " ").title(), "do"))[0]
