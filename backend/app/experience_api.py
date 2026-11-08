"""Private dish diary and editable visit history, with reversible preference updates."""

from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .auth import current_user
from .config import settings
from .db import get_db, Venue, DishEntry, Visit, now
from .menu import menu_view, menu_tags
from .schemas import Feedback
from .taste import rebuild_taste

router = APIRouter(prefix="/api")


def published_venue(db, venue_id):
    venue = db.get(Venue, venue_id)
    if not venue or venue.is_demo != (settings().app_mode == "demo") or venue.status != "published":
        raise HTTPException(404, "Published venue not found")
    if not venue.is_demo and not (
        venue.details.get("location_approval") and venue.details.get("maps_identity", {}).get("confirmed_by")
    ):
        raise HTTPException(404, "Location awaits approval")
    return venue


def entry_dict(db, entry):
    venue = db.get(Venue, entry.venue_id)
    return {c.name: getattr(entry, c.name) for c in entry.__table__.columns} | {
        "venue_name": venue.name if venue else "Former venue",
        "counts_as_venue_visit": False,
    }


class DishInput(BaseModel):
    status: Literal["want_to_try", "tried", "favourite", "not_for_me"]
    note: str = Field(default="", max_length=1000)
    tried_on: date | None = None

    @model_validator(mode="after")
    def experience_date(self):
        if self.status != "want_to_try" and self.tried_on is None:
            raise ValueError("Add the date you tried this dish")
        if self.tried_on and self.tried_on > datetime.now(ZoneInfo("Asia/Kolkata")).date():
            raise ValueError("A dish experience cannot be in the future")
        if self.status == "want_to_try":
            self.tried_on = None
        return self


@router.get("/dish-diary")
def diary(user=Depends(current_user), db=Depends(get_db)):
    return [
        entry_dict(db, entry)
        for entry in db.scalars(
            select(DishEntry).where(DishEntry.user_id == user.id).order_by(DishEntry.updated_at.desc())
        )
    ]


@router.put("/venues/{venue_id}/dish-diary/{offering_key}")
def save_dish(
    venue_id: str, offering_key: str, data: DishInput, user=Depends(current_user), db=Depends(get_db)
):
    entry = db.scalar(
        select(DishEntry).where(
            DishEntry.user_id == user.id,
            DishEntry.venue_id == venue_id,
            DishEntry.offering_key == offering_key,
        )
    )
    if not entry:
        venue = published_venue(db, venue_id)
        menu = menu_view(db, venue, user)
        item = next((item for item in menu["items"] if item["key"] == offering_key), None)
        if not item:
            raise HTTPException(404, "Dish not found in the current reviewed menu")
        entry = DishEntry(
            user_id=user.id,
            venue_id=venue_id,
            offering_key=offering_key,
            name=item["name"],
            preferences={"tags": sorted(menu_tags(item))},
        )
        db.add(entry)
    entry.status, entry.note = data.status, data.note
    entry.tried_on = data.tried_on.isoformat() if data.tried_on else None
    entry.updated_at = now()
    try:
        rebuild_taste(db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Dish changed in another request; reload your diary")
    return entry_dict(db, entry)


@router.delete("/dish-diary/{entry_id}")
def remove_dish(entry_id: str, user=Depends(current_user), db=Depends(get_db)):
    entry = db.get(DishEntry, entry_id)
    if not entry or entry.user_id != user.id:
        raise HTTPException(404, "Dish entry not found")
    db.delete(entry)
    rebuild_taste(db, user)
    db.commit()
    return {"deleted": True}


@router.put("/visits/{visit_id}")
def edit_visit(visit_id: str, data: Feedback, user=Depends(current_user), db=Depends(get_db)):
    visit = db.get(Visit, visit_id)
    if not visit or visit.user_id != user.id:
        raise HTTPException(404, "Visit not found")
    if data.venue_id != visit.venue_id:
        raise HTTPException(422, "A visit's venue cannot be changed; remove it and record the correct visit")
    if db.scalar(
        select(Visit.id).where(
            Visit.user_id == user.id,
            Visit.venue_id == data.venue_id,
            Visit.visited_on == data.visited_on.isoformat(),
            Visit.id != visit.id,
        )
    ):
        raise HTTPException(409, "A visit already exists on that date")
    for key, value in data.model_dump(mode="json").items():
        setattr(visit, key, value)
    try:
        rebuild_taste(db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A visit already exists on that date")
    return {c.name: getattr(visit, c.name) for c in visit.__table__.columns}


@router.delete("/visits/{visit_id}")
def remove_visit(visit_id: str, user=Depends(current_user), db=Depends(get_db)):
    visit = db.get(Visit, visit_id)
    if not visit or visit.user_id != user.id:
        raise HTTPException(404, "Visit not found")
    db.delete(visit)
    rebuild_taste(db, user)
    db.commit()
    return {"deleted": True}
