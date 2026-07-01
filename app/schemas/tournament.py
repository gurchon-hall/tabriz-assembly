"""Schémas Pydantic pour les fichiers YAML de tournois (eternal-vigilance).

Structure du YAML (cf. `YYYY/MM/<event_id>.yaml`) :
    métadonnées du tournoi (name, location, date_start, ...) + un deck gagnant.
Le deck contient une crypt (liste de vampires) et des sections library
(Master, Action, ...), chaque section listant des cartes avec un count.
"""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

ADV_SUFFIX = " (ADV)"


class YamlCryptEntry(BaseModel):
    """Une entrée de crypt (un vampire) dans le deck gagnant."""

    count: int
    name: str  # nom brut, peut se terminer par " (ADV)"
    # id krcg canonique (channel-ten >= 0.9.0) ; absent sur les fichiers plus anciens.
    id: int | None = None
    capacity: int = 0
    disciplines: str = ""
    clan: str = ""
    title: str | None = None
    grouping: int | Literal["ANY"]

    @field_validator("grouping", mode="before")
    @classmethod
    def _coerce_grouping(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip().upper() == "ANY":
            return "ANY"
        return v

    @property
    def is_adv(self) -> bool:
        """Vrai si le vampire est en version avancée (suffixe ' (ADV)')."""
        return self.name.endswith(ADV_SUFFIX)

    @property
    def clean_name(self) -> str:
        """Nom du vampire sans le suffixe ' (ADV)'."""
        return self.name.removesuffix(ADV_SUFFIX)


class YamlLibraryCardEntry(BaseModel):
    """Une carte library (count + nom) au sein d'une section."""

    count: int
    name: str
    # id krcg canonique (channel-ten >= 0.9.0) ; absent sur les fichiers plus anciens.
    id: int | None = None


class YamlLibrarySection(BaseModel):
    """Une section de la library (Master, Action, ...)."""

    name: str
    count: int
    cards: list[YamlLibraryCardEntry]


class YamlDeck(BaseModel):
    """Le deck gagnant d'un tournoi."""

    name: str | None = None  # certains decks n'ont pas de nom dans la source
    created_by: str | None = None
    description: str = ""
    crypt_count: int
    crypt_min: int
    crypt_max: int
    crypt_avg: float
    crypt: list[YamlCryptEntry]
    library_count: int
    library_sections: list[YamlLibrarySection]

    @field_validator("created_by", mode="before")
    @classmethod
    def _empty_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


class YamlTournament(BaseModel):
    """Un tournoi validé + son deck gagnant."""

    model_config = ConfigDict(extra="ignore")

    name: str
    location: str
    date_start: date
    date_end: date | None = None
    rounds_format: str
    players_count: int
    winner: str
    vekn_number: int | None = None
    event_url: str
    event_id: int
    forum_post_url: str | None = None
    vp_comment: str | None = None
    deck: YamlDeck

    @field_validator("date_start", "date_end", mode="before")
    @classmethod
    def _parse_date(cls, v: Any) -> Any:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        if isinstance(v, date):  # PyYAML parse déjà YYYY-MM-DD en date
            return v
        if isinstance(v, str):
            return date.fromisoformat(v.strip())
        return v

    @field_validator("forum_post_url", "vp_comment", mode="before")
    @classmethod
    def _empty_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v.strip() if isinstance(v, str) else v
