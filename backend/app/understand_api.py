"""POST /api/understand: what Bites understood from a person's words, before they plan.

The Discover page calls this as the person types. It returns the form fields to fill,
"I understood" chips the person can remove, and notices (for example, out of scope). It
never plans and never stores the text.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .auth import current_user
from .db import get_db
from .understand.apply import form_and_chips, read

router = APIRouter(prefix="/api")


class Words(BaseModel):
    text: str = Field(min_length=1, max_length=500)


@router.post("/understand")
def understand(body: Words, user=Depends(current_user), db=Depends(get_db)):
    reading, reader = read(body.text)
    form, chips, notices = form_and_chips(reading, db)
    return {"reading": reading, "form": form, "chips": chips, "notices": notices, "reader": reader}
