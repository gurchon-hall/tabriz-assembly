import datetime

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TABLE_PREFIX, Base


class Set(Base):
    __tablename__ = TABLE_PREFIX + "sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    release_date: Mapped[datetime.date]
    full_name: Mapped[str] = mapped_column(index=True)
    abbrev: Mapped[str]
    company: Mapped[str]

    __table_args__ = (CheckConstraint("id >= 300001 AND id <= 399999", name="ck_sets_id_range"),)


class LibraryCard(Base):
    __tablename__ = TABLE_PREFIX + "library"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    type: Mapped[str] = mapped_column(index=True)
    artist: Mapped[str]

    capacity: Mapped[int] = mapped_column(default=0)
    pool_cost: Mapped[int] = mapped_column(default=0)
    blood_cost: Mapped[int] = mapped_column(default=0)
    conviction_cost: Mapped[int] = mapped_column(default=0)
    clan: Mapped[str] = mapped_column(default="", index=True)
    path: Mapped[str] = mapped_column(default="")
    requirement: Mapped[str] = mapped_column(default="")
    flavor_text: Mapped[str] = mapped_column(default="")
    card_text: Mapped[str] = mapped_column(default="")
    discipline: Mapped[str] = mapped_column(default="")
    banned: Mapped[bool] = mapped_column(default=False)
    burn_option: Mapped[bool] = mapped_column(default=False)

    set_id: Mapped[int] = mapped_column(ForeignKey(Set.id))
    set: Mapped[Set] = relationship()

    __table_args__ = (CheckConstraint("id >= 200001 AND id <= 299999", name="ck_library_id_range"),)


class CryptCard(Base):
    __tablename__ = TABLE_PREFIX + "crypt"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    clan: Mapped[str] = mapped_column(index=True)
    type: Mapped[str]
    artist: Mapped[str]
    group: Mapped[str]  # int or ANY => stored as String

    capacity: Mapped[int] = mapped_column(default=0)
    path: Mapped[str] = mapped_column(default="")
    title: Mapped[str] = mapped_column(default="")
    disciplines: Mapped[str] = mapped_column(default="")  # comma-separated list
    card_text: Mapped[str] = mapped_column(default="")
    banned: Mapped[bool] = mapped_column(default=False)
    adv: Mapped[bool] = mapped_column(default=False)

    set_id: Mapped[int] = mapped_column(ForeignKey(Set.id))
    set: Mapped[Set] = relationship()

    __table_args__ = (CheckConstraint("id >= 100001 AND id <= 199999", name="ck_crypt_id_range"),)


__all__ = ["CryptCard", "LibraryCard", "Set"]
