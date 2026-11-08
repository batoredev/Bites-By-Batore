from datetime import datetime, timedelta, timezone
from .db import Venue, Claim


def seed_demo(db):
    if db.get(Venue, "demo-sushi"):
        seed_demo_menus(db)
        return
    # Invented places, prices, hours and coordinates for testing. Never a city guide.
    rows = [
        (
            "sushi",
            "Nori & Rice",
            "food",
            "RS Puram",
            11.009,
            76.951,
            480,
            55,
            ["sushi", "japanese", "quiet", "vegetarian"],
            "Avocado maki & miso bowls",
            "A small counter for a slower, different kind of dinner.",
            True,
            True,
            "leaf",
        ),
        (
            "kongu",
            "Kongu Table",
            "food",
            "Saibaba Colony",
            11.029,
            76.950,
            260,
            45,
            ["kongu", "south indian", "spicy", "social"],
            "Kongu-style lunch plate",
            "Familiar flavours, generous plates and room for friends.",
            True,
            False,
            "sun",
        ),
        (
            "coffee",
            "Chapter Coffee",
            "cafe",
            "RS Puram",
            11.011,
            76.946,
            220,
            40,
            ["coffee", "dessert", "quiet", "vegetarian"],
            "Filter coffee & chocolate tart",
            "An easy pause with coffee, books and a quiet corner.",
            True,
            True,
            "coffee",
        ),
        (
            "korean",
            "Seoul Little Kitchen",
            "food",
            "Race Course",
            10.998,
            76.977,
            520,
            60,
            ["korean", "spicy", "different", "social"],
            "Tofu bibimbap",
            "Bright bowls for an evening outside your usual routine.",
            True,
            True,
            "sun",
        ),
        (
            "dosa",
            "Dosa Corner",
            "food",
            "Gandhipuram",
            11.017,
            76.967,
            140,
            30,
            ["dosa", "south indian", "vegetarian", "casual"],
            "Podi dosa & filter coffee",
            "A quick, inexpensive stop before the next thing.",
            True,
            False,
            "leaf",
        ),
        (
            "bowl",
            "Lane Nine",
            "bowling",
            "Brookefields area",
            11.008,
            76.959,
            350,
            65,
            ["bowling", "social", "active", "indoor"],
            "One bowling game, shoe hire included",
            "A little friendly competition. Beginner friendly.",
            False,
            True,
            "bowl",
        ),
        (
            "arcade",
            "Pixel Yard",
            "gaming",
            "Gandhipuram",
            11.021,
            76.969,
            300,
            60,
            ["arcade", "gaming", "social", "indoor"],
            "One-hour arcade credit bundle",
            "Co-op games, racing cabinets and a dose of nostalgia.",
            False,
            True,
            "pixel",
        ),
        (
            "park",
            "Green Loop Park",
            "park",
            "Race Course",
            11.001,
            76.975,
            30,
            45,
            ["park", "quiet", "outdoor", "active"],
            "Garden walk",
            "An unhurried loop with benches and open space.",
            False,
            True,
            "leaf",
        ),
        (
            "cinema",
            "Frame House",
            "cinema",
            "Peelamedu",
            11.025,
            77.004,
            240,
            140,
            ["movies", "cinema", "indoor", "quiet"],
            "Fictional matinee screening",
            "A full-length film and an easy afternoon indoors.",
            False,
            True,
            "pixel",
        ),
        (
            "kart",
            "Apex Kart Club",
            "adventure",
            "Peelamedu",
            11.038,
            77.020,
            650,
            70,
            ["go karting", "adventure", "active", "outdoor"],
            "Briefing & one karting session",
            "For a faster-paced change of scene. Age 16+ in this demo.",
            False,
            False,
            "bowl",
        ),
        (
            "climb",
            "Boulder Room",
            "adventure",
            "Saibaba Colony",
            11.033,
            76.944,
            450,
            75,
            ["climbing", "adventure", "active", "indoor"],
            "Introductory bouldering session",
            "A hands-on challenge with an introductory briefing.",
            False,
            False,
            "sun",
        ),
        (
            "gelato",
            "Sunday Scoop",
            "cafe",
            "Race Course",
            11.000,
            76.979,
            180,
            30,
            ["dessert", "gelato", "vegetarian", "social"],
            "Two-scoop tasting cup",
            "A sweet final stop, especially with friends.",
            True,
            True,
            "coffee",
        ),
    ]
    observed = datetime.now(timezone.utc)
    for (
        code,
        name,
        category,
        area,
        lat,
        lng,
        price,
        duration,
        tags,
        speciality,
        description,
        veg,
        access,
        art,
    ) in rows:
        hours = {str(day): [[600, 1320]] for day in range(7)}
        if category == "park":
            hours = {str(day): [[360, 1140]] for day in range(7)}
        details = dict(
            price_per_person=price,
            visit_minutes=duration,
            wait_minutes=10,
            hours=hours,
            speciality=speciality,
            description=description,
            vegetarian=veg,
            wheelchair=access,
            child_friendly=category != "adventure",
            min_age=16 if code == "kart" else 0,
            art=art,
            fee_per_group=30,
            booking_url="",
            closed=False,
            max_group=10,
            city="Coimbatore",
        )
        if category == "cinema":
            details["sessions"] = ["11:00", "14:30", "18:00"]
        v = Venue(
            id="demo-" + code,
            name=name,
            category=category,
            area=area,
            address=f"Fictional venue in {area}, Coimbatore — demonstration only",
            lat=lat,
            lng=lng,
            tags=tags,
            details=details,
            status="published",
            is_demo=True,
        )
        db.add(v)
        for field in ["price_per_person", "hours", "closed", "vegetarian", "wheelchair"]:
            db.add(
                Claim(
                    venue_id=v.id,
                    field=field,
                    value={"value": details[field]},
                    source_url="demo://fixture/" + code,
                    source_type="demo",
                    source_group="fixture",
                    observed_at=observed.isoformat(),
                    expires_at=(observed + timedelta(days=365)).isoformat(),
                    status="accepted",
                    reason="Fictional test fixture; not real-world verification",
                )
            )
    # One deliberately contradictory claim exercises the review flow.
    db.add(
        Claim(
            venue_id="demo-sushi",
            field="price_per_person",
            value={"value": 75},
            source_url="demo://visitor/price-report",
            source_type="visitor",
            source_group="visitor-demo",
            observed_at=observed.isoformat(),
            expires_at=(observed + timedelta(days=1)).isoformat(),
            status="review",
            reason="Unusual price drop; independent confirmation required",
        )
    )
    db.commit()
    seed_demo_menus(db)


def seed_demo_menus(db):
    from sqlalchemy import select

    dishes = {
        "demo-sushi": [
            {
                "name": "Avocado maki",
                "cuisine": "Japanese",
                "tags": ["sushi", "japanese"],
                "vegetarian": True,
                "spice": "mild",
                "price_inr": 280,
            },
            {
                "name": "Miso soup",
                "cuisine": "Japanese",
                "tags": ["soup", "japanese"],
                "vegetarian": True,
                "spice": "mild",
                "price_inr": 120,
            },
        ],
        "demo-coffee": [
            {
                "name": "Filter coffee",
                "cuisine": "South Indian",
                "tags": ["coffee"],
                "vegetarian": True,
                "price_inr": 80,
            },
            {
                "name": "Chocolate tart",
                "cuisine": "Bakery",
                "tags": ["dessert"],
                "vegetarian": True,
                "price_inr": 140,
            },
        ],
    }
    observed = datetime.now(timezone.utc)
    for venue in db.scalars(
        select(Venue).where(Venue.is_demo.is_(True), Venue.category.in_(["food", "cafe"]))
    ):
        if db.scalar(select(Claim.id).where(Claim.venue_id == venue.id, Claim.field == "offerings")):
            continue
        menu = [
            {**dish, "unit": "item", "available": True}
            for dish in dishes.get(
                venue.id,
                [
                    {
                        "name": venue.details["speciality"],
                        "price_inr": venue.details["price_per_person"],
                        "tags": venue.tags,
                        "vegetarian": venue.details.get("vegetarian"),
                    }
                ],
            )
        ]
        for field, value in {
            "offerings": menu,
            "dining_format": "cafe" if venue.category == "cafe" else "casual_dining",
            "amenities": {"parking": None, "washroom": True},
        }.items():
            db.add(
                Claim(
                    venue_id=venue.id,
                    field=field,
                    value={"value": value},
                    source_url="demo://fixture/menu",
                    source_type="demo",
                    source_group="fixture",
                    observed_at=observed.isoformat(),
                    expires_at=(observed + timedelta(days=365)).isoformat(),
                    status="accepted",
                    reason="Fictional menu fixture; not real-world evidence",
                )
            )
    db.commit()
