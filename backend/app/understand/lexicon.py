"""Word lists the model uses as features and to turn spans into values.

Areas are the real Coimbatore areas in the place database plus well-known neighbours.
Interests are dishes, cuisines and activities, each mapped to its category. Variants map
spellings, typos and Tanglish to one canonical word, so "biriyani" and "briyani" both read
as "biryani". None of this is copied from the frozen test.
"""

from __future__ import annotations

import re

AREAS = [
    "RS Puram", "Avinashi Road", "Peelamedu", "Saravanampatti", "Race Course", "Saibaba Colony",
    "Gandhipuram", "Thudiyalur", "Vadavalli", "Bharathi Park", "Nava India", "Ukkadam", "Singanallur",
    "Anaikatti", "Sathy Road", "Podanur", "Ganapathy", "Karumathampatti", "Sundarapuram", "Town Hall",
    "Brookefields", "Hopes College", "Kovaipudur", "Ramanathapuram", "Ondipudur", "Kalapatti", "Sitra",
    "Tidel Park", "Lakshmi Mills", "Kuniyamuthur", "Saibaba Kovil", "Ganapathy Pudur", "Trichy Road",
    "Mettupalayam Road", "Marudhamalai", "Perur", "Selvapuram", "Kavundampalayam", "Uppilipalayam",
]

# canonical interest -> category
INTERESTS = {
    # food
    "biryani": "food", "dosa": "food", "idli": "food", "parotta": "food", "salna": "food", "kothu parotta": "food",
    "shawarma": "food", "pizza": "food", "burger": "food", "sushi": "food", "ramen": "food", "korean": "food",
    "japanese": "food", "chinese": "food", "thai": "food", "italian": "food", "mexican": "food",
    "north indian": "food", "chettinad": "food", "kongu": "food", "kerala": "food", "andhra": "food",
    "mandi": "food", "bbq": "food", "grill": "food", "fried chicken": "food", "seafood": "food", "fish": "food",
    "meals": "food", "thali": "food", "momos": "food", "noodles": "food", "pasta": "food", "kebab": "food",
    "tandoori": "food", "naan": "food", "mutton": "food", "chicken": "food", "paneer": "food",
    # street food and messes
    "chaat": "street_food", "pani puri": "street_food", "bajji": "street_food", "tiffin": "street_food",
    "vada pav": "street_food", "bhel": "street_food", "samosa": "street_food", "kalan": "street_food",
    "egg dosa": "street_food", "sundal": "street_food",
    # cafe
    "filter coffee": "cafe", "cold coffee": "cafe", "cold brew": "cafe", "masala chai": "cafe",
    "sandwich": "cafe", "brunch": "cafe",
    # dessert
    "ice cream": "dessert", "cake": "dessert", "gelato": "dessert", "falooda": "dessert", "juice": "dessert",
    "kulfi": "dessert", "waffle": "dessert", "brownie": "dessert", "milkshake": "dessert", "donut": "dessert",
    "jigarthanda": "dessert", "cheesecake": "dessert", "pastry": "dessert", "sweets": "dessert",
    # nightlife
    "cocktails": "nightlife", "craft beer": "nightlife", "beer": "nightlife", "mocktails": "nightlife",
    # gaming
    "vr": "gaming", "escape room": "gaming", "snooker": "gaming", "pool": "gaming", "ps5": "gaming",
    "board games": "gaming", "billiards": "gaming",
    # adventure
    "go karting": "adventure", "trampoline": "adventure", "paintball": "adventure", "zipline": "adventure",
    "rock climbing": "adventure", "laser tag": "adventure", "atv": "adventure", "bungee": "adventure",
    # amusement
    "roller coaster": "amusement", "snow world": "amusement",
    # park
    "lake": "park", "boating": "park", "picnic": "park",
    # workshop
    "pottery": "workshop", "painting": "workshop", "candle making": "workshop", "resin art": "workshop",
    "tufting": "workshop", "baking class": "workshop",
    # attraction
    "zoo": "attraction", "aquarium": "attraction", "planetarium": "attraction", "temple": "attraction",
    # sports
    "football": "sports", "badminton": "sports", "cricket": "sports", "pickleball": "sports",
    "swimming": "sports", "skating": "sports", "tennis": "sports", "box cricket": "sports", "futsal": "sports",
}

# Words that name a category but are not narrower interests.
CATEGORY_WORDS = {
    "food": ["food", "restaurant", "restaurants", "dinner", "lunch", "breakfast", "eat", "meal", "hotel",
             "dhaba", "eatery", "dining", "saapadu", "saapdanum", "sapadu", "non veg", "cuisine", "hungry"],
    "street_food": ["street food", "mess", "stall", "kadai", "thattu kadai", "road side", "roadside"],
    "cafe": ["cafe", "cafes", "coffee", "tea", "chai", "coffee shop", "coffee place"],
    "dessert": ["dessert", "desserts", "bakery", "sweet shop"],
    "nightlife": ["pub", "bar", "drinks", "brewery", "lounge", "club", "nightclub"],
    "cinema": ["movie", "movies", "film", "cinema", "theatre", "theater", "multiplex", "padam"],
    "gaming": ["games", "gaming", "arcade", "game zone", "play area", "play zone", "gaming cafe"],
    "bowling": ["bowling", "bowling alley"],
    "adventure": ["adventure", "adventure park"],
    "amusement": ["water park", "theme park", "amusement park"],
    "park": ["park", "garden", "poonga"],
    "workshop": ["workshop", "class", "art class", "diy"],
    "attraction": ["museum", "gallery", "sightseeing"],
    "sports": ["turf", "court", "sports", "ground"],
}

# spelling variants, typos and Tanglish -> canonical
VARIANTS = {
    "biriyani": "biryani", "briyani": "biryani", "biriani": "biryani", "byriani": "biryani",
    "porotta": "parotta", "barotta": "parotta", "paratha": "parotta", "shawarama": "shawarma",
    "piza": "pizza", "pizzas": "pizza", "burgers": "burger", "bowlin": "bowling", "bowlng": "bowling",
    "movei": "movie", "moive": "movie", "tonite": "tonight", "tonigt": "tonight", "creem": "cream",
    "icecream": "ice cream", "resturant": "restaurant", "restaraunt": "restaurant", "restuarant": "restaurant",
    "gokarting": "go karting", "gokart": "go karting", "karting": "go karting", "lakeside": "lake side",
    "cofee": "coffee", "coffe": "coffee", "desert": "dessert", "deserts": "desserts",
    "panipuri": "pani puri", "golgappa": "pani puri", "momo": "momos",
    "cakes": "cake", "juices": "juice", "milkshakes": "milkshake", "waffles": "waffle",
    "trampolines": "trampoline", "vegetarian": "veg", "veggie": "veg",
    "cinemas": "cinema", "theatres": "theatre", "mins": "minutes", "min": "minutes", "hrs": "hours",
    "hr": "hours", "hour": "hours", "minute": "minutes", "ppl": "people", "persons": "people",
    "frnds": "friends", "rs": "rupees", "inr": "rupees", "₹": "rupees", "bucks": "rupees",
    "pp": "per person", "nite": "night", "tmrw": "tomorrow", "plz": "please", "pls": "please",
    "kidz": "kids", "childrens": "children", "eggless": "no egg", "nonveg": "non veg",
}

NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "hundred": 100, "a": 1, "an": 1, "single": 1, "couple": 2, "pair": 2,
    # Tamil and Tanglish
    "oru": 1, "onnu": 1, "rendu": 2, "irandu": 2, "moonu": 3, "munu": 3, "naalu": 4, "nalu": 4,
    "anju": 5, "aaru": 6, "ezhu": 7, "ettu": 8, "ombodhu": 9, "pathu": 10,
}

AREA_KEYS = {a.casefold(): a for a in AREAS}
CATEGORY_OF_WORD = {w: c for c, words in CATEGORY_WORDS.items() for w in words}
TOKEN = re.compile(r"₹|\d+(?:[.,]\d+)*k?|[a-z]+(?:'[a-z]+)?|[^\sa-z\d]", re.I)


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text)


def normalize(text: str) -> list[str]:
    """Lowercase tokens with spelling variants mapped to canonical words (may expand to two).

    Area names are kept as written ("RS Puram" never becomes "rupees puram"), and an
    expansion never repeats the word before it ("go karting" stays "go karting").
    """
    words = [t.casefold() for t in tokens(text) if t != "-"]
    protected = {i for start, end, _ in phrase_hits(words, AREA_KEYS) for i in range(start, end)}
    out: list[str] = []
    for i, word in enumerate(words):
        parts = [word] if i in protected else VARIANTS.get(word, word).split()
        if len(parts) > 1 and out and out[-1] == parts[0]:
            parts = parts[1:]
        out.extend(parts)
    return out


def phrase_hits(words: list[str], phrases, max_len: int = 3) -> list[tuple[int, int, str]]:
    """(start, end, phrase) for each longest phrase from `phrases` found in the word list."""
    hits, i = [], 0
    while i < len(words):
        for n in range(max_len, 0, -1):
            piece = words[i:i + n]
            if len(piece) == n and " ".join(piece) in phrases:
                hits.append((i, i + n, " ".join(piece)))
                i += n
                break
        else:
            i += 1
    return hits
