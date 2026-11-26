"""The Reading: everything the planner needs to know from a person's words."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

TIMES = ("morning", "afternoon", "evening", "late_night", "now")
MOODS = ("different", "comfort", "quiet", "social", "active")
NOVELTY = ("new_place", "new_taste", "familiar")
TRANSPORT = ("walk", "bike", "drive", "taxi")


@dataclass
class Reading:
    categories: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    party_size: int | None = None
    budget: int | None = None
    budget_unit: str | None = None  # "person" | "group"
    duration_minutes: int | None = None
    vegetarian: bool = False
    children: bool = False
    wheelchair: bool = False
    novelty: str | None = None
    mood: str | None = None
    max_stops: int | None = None
    area: str | None = None
    transport: str | None = None
    avoid: list[str] = field(default_factory=list)
    time_of_day: str | None = None
    surprise: bool = False
    out_of_scope: bool = False

    def as_dict(self) -> dict:
        return asdict(self)


FIELDS = list(Reading.__dataclass_fields__)
LIST_FIELDS = {"categories", "interests", "avoid"}
# Getting these wrong breaks a promise to the person, so the target is 100%.
CRITICAL = ("party_size", "budget", "budget_unit", "vegetarian")


def expected(spec: dict) -> dict:
    """A frozen-test 'expect' block filled out with defaults for the fields it leaves out."""
    unknown = set(spec) - set(FIELDS)
    if unknown:
        raise ValueError(f"unknown Reading fields: {sorted(unknown)}")
    return {**Reading().as_dict(), **spec}
