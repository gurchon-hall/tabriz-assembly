"""Modèles SQLAlchemy pour les tournois importés depuis eternal-vigilance.

Schéma relationnel :
    Tournament (ta_tournaments)  1 ──── 1  Deck (ta_decks)
                                              │
                                ┌─────────────┴─────────────┐
                  DeckCryptCard (ta_deck_crypt_cards)   DeckLibraryCard (ta_deck_library_cards)
                  FK nullable → ta_crypt                FK nullable → ta_library

Les tables d'association portent un ``count`` par carte ainsi que le nom brut
(``raw_name``) issu du YAML : la résolution vers les tables de cartes existantes
est opportuniste (FK nullable), de sorte qu'aucune carte n'est perdue si la base
de cartes est en retard sur la curation des tournois.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    and_,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TABLE_PREFIX, Base
from app.models.vtes import CryptCard, LibraryCard


class Tournament(Base):
    """Un tournoi VTES validé (TWD)."""

    __tablename__ = TABLE_PREFIX + "tournaments"

    # event_id == nom de fichier YAML, identifiant naturel global.
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    location: Mapped[str] = mapped_column(String, nullable=False)
    date_start: Mapped[datetime.date] = mapped_column(nullable=False, index=True)
    date_end: Mapped[datetime.date | None] = mapped_column(nullable=True)
    rounds_format: Mapped[str] = mapped_column(String, nullable=False)
    players_count: Mapped[int] = mapped_column(Integer, nullable=False)
    winner: Mapped[str] = mapped_column(String, nullable=False)
    vekn_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_url: Mapped[str] = mapped_column(String, nullable=False)
    forum_post_url: Mapped[str | None] = mapped_column(String, nullable=True)
    vp_comment: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    deck: Mapped[Deck | None] = relationship(
        back_populates="tournament",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )


class Deck(Base):
    """Le deck gagnant d'un tournoi (un seul par tournoi)."""

    __tablename__ = TABLE_PREFIX + "decks"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tournament_event_id: Mapped[int] = mapped_column(
        ForeignKey(TABLE_PREFIX + "tournaments.event_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # force la relation 1:1
        index=True,
    )

    name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(String, nullable=False, default="", server_default="")
    crypt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    crypt_min: Mapped[int] = mapped_column(Integer, nullable=False)
    crypt_max: Mapped[int] = mapped_column(Integer, nullable=False)
    crypt_avg: Mapped[float] = mapped_column(Float, nullable=False)
    library_count: Mapped[int] = mapped_column(Integer, nullable=False)

    tournament: Mapped[Tournament] = relationship(back_populates="deck", lazy="select")
    crypt_cards: Mapped[list[DeckCryptCard]] = relationship(
        back_populates="deck",
        cascade="all, delete-orphan",
        lazy="select",
    )
    library_cards: Mapped[list[DeckLibraryCard]] = relationship(
        back_populates="deck",
        cascade="all, delete-orphan",
        lazy="select",
    )


class DeckCryptCard(Base):
    """Lien deck ↔ carte de crypt, avec count et FK nullable vers ta_crypt.

    La clé de ``ta_crypt`` est composite (id, group, adv). On stocke toujours
    ``raw_name`` + ``raw_grouping`` ; les colonnes FK sont nullables et restent
    NULL si la résolution du nom échoue (une FK composite est satisfaite quand
    ses trois colonnes sont NULL).
    """

    __tablename__ = TABLE_PREFIX + "deck_crypt_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(TABLE_PREFIX + "decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_name: Mapped[str] = mapped_column(String, nullable=False)
    # str, pas int : le YAML source peut porter le groupe "ANY" (vampire multi-groupe).
    raw_grouping: Mapped[str] = mapped_column(String, nullable=False)

    crypt_card_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crypt_card_group: Mapped[str | None] = mapped_column(String, nullable=True)
    crypt_card_adv: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    deck: Mapped[Deck] = relationship(back_populates="crypt_cards", lazy="select")
    crypt_card: Mapped[CryptCard | None] = relationship(
        "CryptCard",
        primaryjoin=lambda: and_(
            DeckCryptCard.crypt_card_id == CryptCard.id,
            DeckCryptCard.crypt_card_group == CryptCard.group,
            DeckCryptCard.crypt_card_adv == CryptCard.adv,
        ),
        foreign_keys=lambda: [
            DeckCryptCard.crypt_card_id,
            DeckCryptCard.crypt_card_group,
            DeckCryptCard.crypt_card_adv,
        ],
        viewonly=True,
        lazy="select",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["crypt_card_id", "crypt_card_group", "crypt_card_adv"],
            [
                TABLE_PREFIX + "crypt.id",
                TABLE_PREFIX + "crypt.group",
                TABLE_PREFIX + "crypt.adv",
            ],
            ondelete="SET NULL",
            name="fk_deck_crypt_cards_crypt",
        ),
        Index(
            "ix_deck_crypt_cards_crypt",
            "crypt_card_id",
            "crypt_card_group",
            "crypt_card_adv",
        ),
    )


class DeckLibraryCard(Base):
    """Lien deck ↔ carte library, avec count et FK nullable vers ta_library."""

    __tablename__ = TABLE_PREFIX + "deck_library_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(TABLE_PREFIX + "decks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section: Mapped[str] = mapped_column(String, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_name: Mapped[str] = mapped_column(String, nullable=False)

    library_card_id: Mapped[int | None] = mapped_column(
        ForeignKey(TABLE_PREFIX + "library.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    deck: Mapped[Deck] = relationship(back_populates="library_cards", lazy="select")
    library_card: Mapped[LibraryCard | None] = relationship(
        "LibraryCard",
        foreign_keys=lambda: [DeckLibraryCard.library_card_id],
        viewonly=True,
        lazy="select",
    )


__all__ = ["Deck", "DeckCryptCard", "DeckLibraryCard", "Tournament"]
