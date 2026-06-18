import datetime
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TABLE_PREFIX, Base


class Set(Base):
    __tablename__ = TABLE_PREFIX + "sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    release_date: Mapped[datetime.date | None]
    full_name: Mapped[str] = mapped_column(index=True)
    abbrev: Mapped[str] = mapped_column(index=True, unique=True)
    company: Mapped[str]

    library_cards: Mapped[list[LibraryCard]] = relationship(
        secondary=lambda: LibraryCardSet.__table__,
        back_populates="sets",
        lazy="select",
    )
    crypt_cards: Mapped[list[CryptCard]] = relationship(
        secondary=lambda: CryptCardSet.__table__,
        back_populates="sets",
        lazy="select",
    )

    __table_args__ = (CheckConstraint("id >= 300001 AND id <= 399999", name="ck_sets_id_range"),)


class LibraryCardSet(Base):
    """Table d'association LibraryCard ↔ Set."""

    __tablename__ = TABLE_PREFIX + "library_card_sets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    library_card_id: Mapped[int] = mapped_column(
        ForeignKey(TABLE_PREFIX + "library.id", ondelete="CASCADE"),
        index=True,
    )
    set_id: Mapped[int] = mapped_column(
        ForeignKey(TABLE_PREFIX + "sets.id", ondelete="CASCADE"),
        index=True,
    )

    __table_args__ = (UniqueConstraint("library_card_id", "set_id", name="uq_library_card_sets"),)


class CryptCardSet(Base):
    """Table d'association CryptCard ↔ Set."""

    __tablename__ = TABLE_PREFIX + "crypt_card_sets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Composite FK
    crypt_card_id: Mapped[int] = mapped_column(index=True)
    crypt_card_group: Mapped[str]
    crypt_card_adv: Mapped[bool]

    set_id: Mapped[int] = mapped_column(
        ForeignKey(TABLE_PREFIX + "sets.id", ondelete="CASCADE"),
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("crypt_card_id", "set_id", name="uq_crypt_card_sets"),
        ForeignKeyConstraint(
            ["crypt_card_id", "crypt_card_group", "crypt_card_adv"],
            [
                TABLE_PREFIX + "crypt.id",
                TABLE_PREFIX + "crypt.group",
                TABLE_PREFIX + "crypt.adv",
            ],
            ondelete="CASCADE",
            name="fk_crypt_card_sets_crypt",
        ),
        UniqueConstraint(
            "crypt_card_id",
            "crypt_card_group",
            "crypt_card_adv",
            "set_id",
            name="uq_crypt_card_sets",
        ),
    )


class LibraryCard(Base):
    __tablename__ = TABLE_PREFIX + "library"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    type: Mapped[str] = mapped_column(index=True)
    artist: Mapped[str]

    capacity: Mapped[str] = mapped_column(default="")
    pool_cost: Mapped[str | None] = mapped_column(default=None)
    blood_cost: Mapped[str | None] = mapped_column(default=None)
    conviction_cost: Mapped[str | None] = mapped_column(default=None)
    clan: Mapped[str] = mapped_column(default="", index=True)
    path: Mapped[str] = mapped_column(default="")
    requirement: Mapped[str] = mapped_column(default="")
    flavor_text: Mapped[str] = mapped_column(default="")
    card_text: Mapped[str] = mapped_column(default="")
    discipline: Mapped[str] = mapped_column(default="")
    banned: Mapped[bool] = mapped_column(default=False)
    burn_option: Mapped[bool] = mapped_column(default=False)

    first_print_set_id: Mapped[int | None] = mapped_column(
        ForeignKey(TABLE_PREFIX + "sets.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )

    sets: Mapped[list[Set]] = relationship(
        secondary=lambda: LibraryCardSet.__table__,
        back_populates="library_cards",
        lazy="select",
    )

    first_print: Mapped[Set | None] = relationship(
        "Set",
        foreign_keys="[LibraryCard.first_print_set_id]",
        lazy="select",
    )

    __table_args__ = (CheckConstraint("id >= 100001 AND id <= 199999", name="ck_library_id_range"),)


class CryptCard(Base):
    __tablename__ = TABLE_PREFIX + "crypt"

    id: Mapped[int] = mapped_column(primary_key=True)
    group: Mapped[str] = mapped_column(primary_key=True)  # int ou "Any" => stocké en String
    adv: Mapped[bool] = mapped_column(primary_key=True, default=False)

    name: Mapped[str] = mapped_column(index=True)
    clan: Mapped[str] = mapped_column(index=True)
    type: Mapped[str]
    artist: Mapped[str]

    capacity: Mapped[int] = mapped_column(default=0)
    path: Mapped[str] = mapped_column(default="")
    title: Mapped[str] = mapped_column(default="")
    disciplines: Mapped[str] = mapped_column(default="")  # liste séparée par virgules
    card_text: Mapped[str] = mapped_column(default="")
    banned: Mapped[bool] = mapped_column(default=False)

    first_print_set_id: Mapped[int | None] = mapped_column(
        ForeignKey(TABLE_PREFIX + "sets.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        index=True,
    )

    sets: Mapped[list[Set]] = relationship(
        secondary=lambda: CryptCardSet.__table__,
        back_populates="crypt_cards",
        lazy="select",
    )

    first_print: Mapped[Set | None] = relationship(
        "Set",
        foreign_keys="[CryptCard.first_print_set_id]",
        lazy="select",
    )

    __table_args__ = (CheckConstraint("id >= 200001 AND id <= 299999", name="ck_crypt_id_range"),)


__all__ = ["CryptCard", "CryptCardSet", "LibraryCard", "LibraryCardSet", "Set"]
