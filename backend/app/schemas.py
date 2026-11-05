from datetime import datetime, date
from zoneinfo import ZoneInfo
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

Category = Literal["food", "cafe", "park", "cinema", "gaming", "bowling", "adventure"]


class OutingRequest(BaseModel):
    query: str = Field(default="Something different", max_length=500)
    start_label: str = Field(default="RS Puram, Coimbatore", min_length=2, max_length=200)
    lat: float = Field(default=11.008, ge=-90, le=90)
    lng: float = Field(default=76.948, ge=-180, le=180)
    duration_minutes: int = Field(default=180, ge=30, le=720)
    party_size: int = Field(default=2, ge=1, le=20)
    budget: int = Field(default=2000, ge=50, le=100000)
    budget_unit: Literal["group", "person"] = "group"
    departure: datetime
    transport: Literal["walk", "drive", "taxi", "bike"] = "drive"
    categories: list[Category] = Field(default_factory=lambda: ["food", "cafe", "gaming", "bowling"])
    outing_type: Literal["any", "food", "entertainment", "combined"] = "any"
    mood: Literal["different", "comfort", "quiet", "social", "active"] = "different"
    vegetarian: bool = False
    wheelchair: bool = False
    children: bool = False
    avoid_tags: list[str] = Field(default_factory=list, max_length=30)
    companion_interests: list[str] = Field(default_factory=list, max_length=30)
    exclude_ids: list[str] = Field(default_factory=list, max_length=50)
    lock_ids: list[str] = Field(default_factory=list, max_length=4)
    max_stops: int = Field(default=2, ge=1, le=4)
    occasion: str = Field(default="casual", max_length=60)
    companion_preferences: list[list[str]] = Field(default_factory=list, max_length=19)

    @field_validator("departure")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("Departure must include a timezone")
        return value

    @model_validator(mode="after")
    def compatible(self):
        if not self.categories:
            raise ValueError("Choose at least one category")
        if set(self.lock_ids) & set(self.exclude_ids):
            raise ValueError("A stop cannot be both locked and excluded")
        if len(self.lock_ids) > self.max_stops:
            raise ValueError("Locked stops exceed the selected maximum stops")
        if len(self.companion_preferences) >= self.party_size or any(
            len(x) > 20 for x in self.companion_preferences
        ):
            raise ValueError("Provide up to 20 interests per companion, within the party size")
        return self


class ProfileUpdate(BaseModel):
    name: str = Field(default="Explorer", min_length=1, max_length=60)
    liked_tags: list[str] = Field(default_factory=list, max_length=30)
    avoided_tags: list[str] = Field(default_factory=list, max_length=30)
    vegetarian: bool = False
    wheelchair: bool = False
    learn_from_visits: bool = True


class Feedback(BaseModel):
    venue_id: str
    rating: int = Field(ge=1, le=5)
    dimensions: dict[str, int] = Field(default_factory=dict)
    note: str = Field(default="", max_length=1000)
    occasion: str = Field(default="casual", max_length=60)
    visited_on: date

    @field_validator("dimensions")
    @classmethod
    def valid_scores(cls, value):
        allowed = {"food", "atmosphere", "service", "activity", "value"}
        if any(k not in allowed or v not in range(1, 6) for k, v in value.items()):
            raise ValueError("Use scores 1–5 for food, atmosphere, service, activity or value")
        return value

    @field_validator("visited_on")
    @classmethod
    def past_visit(cls, value):
        if value > datetime.now(ZoneInfo("Asia/Kolkata")).date():
            raise ValueError("A confirmed visit cannot be in the future")
        return value


class SocialInput(BaseModel):
    url: str = Field(default="", max_length=2000)
    caption: str = Field(default="", max_length=10000)
    comments: str = Field(default="", max_length=15000)
    transcript: str = Field(default="", max_length=20000)
    creator: str = Field(default="", max_length=100)
    likes: int | None = Field(default=None, ge=0)
    views: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def has_content(self):
        if not any([self.url, self.caption, self.comments, self.transcript]):
            raise ValueError("Add a link or supplied content")
        return self


class ClaimInput(BaseModel):
    venue_id: str
    field: Literal[
        "price_per_person",
        "hours",
        "closed",
        "speciality",
        "wheelchair",
        "vegetarian",
        "address",
        "packages",
        "dated_sessions",
    ]
    value: dict
    source_url: str = Field(min_length=5, max_length=2000)
    source_type: Literal["merchant", "official", "visitor", "social", "demo"] = "visitor"
    source_group: str = Field(min_length=2, max_length=200)
    observed_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def valid_times(self):
        if self.observed_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("Evidence timestamps require timezones")
        if self.expires_at <= self.observed_at:
            raise ValueError("Expiry must follow observation")
        if "value" not in self.value:
            raise ValueError("Supply a value inside the evidence object")
        return self


class ReviewInput(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(min_length=5, max_length=1000)


class VenueInput(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    category: Category
    area: str = Field(min_length=2, max_length=100)
    address: str = Field(min_length=5, max_length=500)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    tags: list[str] = Field(default_factory=list, max_length=30)
    details: dict = Field(default_factory=dict)


class ActivityPackage(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    price: float = Field(ge=0, le=100000, allow_inf_nan=False)
    unit: Literal["person", "group"]
    people_per_unit: int = Field(default=1, ge=1, le=100)
    duration_minutes: int = Field(ge=5, le=480)
    expires_at: datetime
    source_url: str = Field(pattern=r"^https://", max_length=2000)

    @field_validator("expires_at")
    @classmethod
    def aware_expiry(cls, value):
        if value.tzinfo is None:
            raise ValueError("Package expiry requires a timezone")
        return value


class DatedSession(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    starts_at: datetime
    duration_minutes: int = Field(ge=5, le=480)
    price_per_person: float = Field(ge=0, le=100000, allow_inf_nan=False)
    available_places: int | None = Field(default=None, ge=0, le=100000)
    expires_at: datetime
    source_url: str = Field(pattern=r"^https://", max_length=2000)

    @field_validator("starts_at", "expires_at")
    @classmethod
    def aware_session(cls, value):
        if value.tzinfo is None:
            raise ValueError("Session dates require timezones")
        return value


class VenueOperations(BaseModel):
    visit_minutes: int = Field(default=60, ge=5, le=480)
    wait_minutes: int = Field(default=15, ge=0, le=180)
    fee_per_group: int = Field(default=0, ge=0, le=10000)
    max_group: int = Field(default=6, ge=1, le=100)
    child_friendly: bool = False
    min_age: int = Field(default=0, ge=0, le=21)
    sessions: list[str] = Field(default_factory=list, max_length=30)
    google_place_id: str = Field(default="", max_length=250)
    booking_url: str = Field(default="", max_length=2000)
    description: str = Field(default="", max_length=1000)
    speciality: str = Field(default="", max_length=300)
    branch_confirmed: bool = False
    packages: list[ActivityPackage] = Field(default_factory=list, max_length=10)
    dated_sessions: list[DatedSession] = Field(default_factory=list, max_length=60)

    @field_validator("sessions")
    @classmethod
    def session_times(cls, value):
        for item in value:
            datetime.strptime(item, "%H:%M")
        return sorted(set(value))

    @field_validator("booking_url")
    @classmethod
    def booking_link(cls, value):
        from urllib.parse import urlparse

        if value and urlparse(value).scheme != "https":
            raise ValueError("Booking links must use HTTPS")
        return value
