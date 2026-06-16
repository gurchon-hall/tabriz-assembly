from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Set(BaseModel):
    id: int = Field(..., alias="Id", ge=300001, lt=400000)
    release_date: date | None = Field(alias="Release Date")
    full_name: str = Field(alias="Full Name")
    abbrev: str = Field(alias="Abbrev")
    company: str = Field(alias="Company")

    @field_validator("release_date", mode="before")
    @classmethod
    def parse_release_date(cls, v: str) -> date | None:
        if not v:
            return None
        return date(int(v[0:4]), int(v[4:6]), int(v[6:8]))  # format observé : YYYYMMDD


def parse_set_abbrevs(v: str) -> list[str]:
    """Parse le champ 'Set' du CSV, ex: "FN:U2, POD:DTC" -> ["FN", "POD"]."""
    if not v:
        return []
    abbrevs: list[str] = []
    for chunk in v.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        abbrev = chunk.split(":", 1)[0].strip()
        if abbrev:
            abbrevs.append(abbrev)
    return abbrevs


class Card(BaseModel):
    name: str = Field(alias="Name")
    type_: str = Field(alias="Type")
    set_abbrevs: list[str] = Field(alias="Set")
    artist: str = Field(alias="Artist")

    aka: str = Field(alias="Aka", default="")
    clan: str = Field(alias="Clan", default="")
    path: str = Field(alias="Path", default="")
    card_text: str = Field(alias="Card Text", default="")
    capacity: int = Field(alias="Capacity", default=-1)
    banned: bool = Field(alias="Banned", default=False)

    @field_validator("set_abbrevs", mode="before")
    @classmethod
    def parse_set_field(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return parse_set_abbrevs(v)
        return v

    @field_validator("capacity", mode="before")
    @classmethod
    def empty_to_default(cls, v: Any) -> Any:
        if v == "":
            return -1
        return v

    @field_validator("banned", mode="before")
    @classmethod
    def coerce_banned(cls, v: Any) -> Any:
        if v == "":
            return False
        return v


class CryptCard(Card):
    id: int = Field(..., alias="Id", ge=200001, lt=300000)
    group: int | Literal["Any"] = Field(alias="Group")
    disciplines: str = Field(alias="Disciplines", default="")
    adv: bool = Field(alias="Adv", default=False)
    title: str = Field(alias="Title", default="")

    @field_validator("group", mode="before")
    @classmethod
    def coerce_grouping(cls, v: Any) -> int | Literal["Any"]:
        if v == "Any":
            return "Any"
        try:
            int_v = int(v)
            if 1 <= int_v <= 7:
                return int_v
            else:
                raise TypeError(f"Can't assign {v} to grouping ANY nor 1 to 7: {int_v}")
        except Exception as e:
            raise TypeError(f"Can't assign {v} to grouping ANY nor 1 to 7: {e}")

    @field_validator("adv", mode="before")
    @classmethod
    def coerce_adv(cls, v: Any) -> Any:
        if v == "":
            return False
        return v


class LibraryCard(Card):
    id: int = Field(..., alias="Id", ge=100001, lt=200000)
    discipline: str = Field(alias="Discipline", default="")
    pool_cost: int = Field(alias="Pool Cost", default=-1)
    blood_cost: int = Field(alias="Blood Cost", default=-1)
    conviction_cost: int = Field(alias="Conviction Cost", default=-1)
    burn_option: bool = Field(alias="Burn Option", default=False)
    flavor_text: str = Field(alias="Flavor Text", default="")

    @field_validator("pool_cost", "blood_cost", "conviction_cost", mode="before")
    @classmethod
    def empty_cost_to_default(cls, v: Any) -> Any:
        if v == "":
            return -1
        return v

    @field_validator("burn_option", mode="before")
    @classmethod
    def coerce_burn_option(cls, v: Any) -> Any:
        if v == "":
            return False
        return v


class LibraryMeta(BaseModel):
    id: int = Field(..., alias="Id", ge=100001, le=199999)
    name: str = Field(alias="Name")
    requirement: str = Field(alias="Requirement", default="")
