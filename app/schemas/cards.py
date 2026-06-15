from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.sets import Set


class Card(BaseModel):
    name: str
    aka: str = ""
    type_: str = Field(..., alias="type")
    capacity: int | None = None
    clan: str = ""
    path: str = ""
    card_text: str = ""
    set: Set
    banned: bool = False
    artist: str


class CryptCard(Card):
    id: int = Field(..., ge=100001, lt=200000)
    adv: bool = False
    group: int | Literal["Any"]
    disciplines: list[str] = Field(default_factory=list)
    title: str = ""


class LibraryCard(Card):
    id: int = Field(..., ge=200001, lt=300000)
    discipline: str = ""
    pool_cost: int = 0
    blood_cost: int = 0
    conviction_cost: int = 0
    burn_option: bool = False
    flavor_text: str = ""
    requirement: str = ""  # data from vteslibmeta.csv
