from sqlalchemy.orm import DeclarativeBase

from app.config.database import DatabaseSettings

TABLE_PREFIX = DatabaseSettings().table_prefix


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class for all ORM models."""

    pass
