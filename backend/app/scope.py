"""The owner's scope rules (16 November 2026), applied to every place the agent finds.

1. Chains: every branch is its own place (handled by branch identity, not here).
2. Malls are not places; the cinemas and restaurants inside them are.
3. College or office canteens and hostel messes the public cannot use are out.
4. Temples and other places of worship are out; parks and lakes stay in.
5. Home bakers, cloud kitchens and delivery-only brands are out.
6. Caterers, event companies, one-off expos and events are out.
7. College and private sports grounds are out; bookable turfs are in.
8. Unnamed street carts are kept but marked for the owner to check personally.
9. Places within 40 km of the city are in (handled by the distance check).
10. Bars, pubs and lounges are in, flagged 21+ with their own filter.
"""

import re

from .spot_identity import name_key

OUT_OF_SCOPE = [
    (
        r"\b(temple|kovil|koil|church|mosque|masjid|dargah|gurudwara|ashram|mutt)\b",
        "Place of worship; out of scope",
    ),
    (
        r"\b(caterers?|catering|event management|events? company|wedding planners?)\b",
        "Caterer or event company",
    ),
    (
        r"\b(expo|exhibition|fest|festival|concert|celebration|meetup|carnival)\b",
        "One-off event, not a place",
    ),
    (
        r"\b(home ?bakers?|home ?made|homemade|home ?cooked|homefood|home food|cloud kitchen|delivery only|"
        r"order online|takeaway only)\b",
        "Home or delivery-only kitchen; nowhere to visit",
    ),
    (r"\b(hostel|pg|paying guest)\b", "Hostel or PG mess; not open to the public"),
    (
        r"\b(college|university|school|institute|polytechnic|campus|office|corporate|it park|tech park)\b"
        r".*\b(canteen|cafeteria|mess|snack shop|food court)\b",
        "Campus or office canteen; not open to the public",
    ),
    (
        r"\b(college|university|school|institute|polytechnic|campus|police|corporation|railway)\b"
        r".*\b(ground|grounds|stadium|pitch|field)\b",
        "Private or institutional ground; not bookable",
    ),
]
OUT_OF_SCOPE = [(re.compile(p), reason) for p, reason in OUT_OF_SCOPE]
MALL = re.compile(r"\b(mall|shopping centre|shopping center|plaza)\b")
# A mall name with one of these is a business inside it, not the mall itself.
INSIDE = re.compile(
    r"\b(cinemas?|multiplex|inox|pvr|food court|restaurant|cafe|bowling|gaming|arcade|"
    r"fun ?city|timezone|kfc|mcdonald|burger|pizza)\b"
)
CART = re.compile(
    r"\b(cart|carts|stall|stalls|thallu ?vandi|vandi|push ?cart|roadside|road side|thattu ?kadai|"
    r"street food|food street|kadai|kiosk)\b"
)
ADULTS = {"nightlife"}
ADULT_WORDS = re.compile(r"\b(pub|bar|brewery|brewing|taproom|lounge|night ?club|resto ?bar|wine|beer)\b")


def out_of_scope(name):
    """Reason the owner excludes this kind of place, or ""."""
    key = name_key(name)
    for rule, reason in OUT_OF_SCOPE:
        if rule.search(key):
            return reason
    if MALL.search(key) and not INSIDE.search(key):
        return "Mall; add the cinemas and restaurants inside it instead"
    return ""


def unnamed_cart(name, issues):
    """A street stall the name check rejected for having no real name of its own."""
    return bool(issues) and bool(CART.search(name_key(name)))


def adults_only(category, name=""):
    return category in ADULTS or bool(ADULT_WORDS.search(name_key(name)))


CART_REASON = "Unnamed street stall; owner checks these personally"
