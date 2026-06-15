from datetime import date

from pydantic import BaseModel, Field


class Set(BaseModel):
    id: int = Field(..., ge=300001, lt=400000)
    release_date: date
    full_name: str
    abbrev: str
    company: str
