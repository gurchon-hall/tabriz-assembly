import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class UserRole(enum.StrEnum):
    """Rôles utilisateur classés par niveau d'accès croissant.

    La propriété `level` est utilisée par require_role() pour les comparaisons
    hiérarchiques — ne jamais comparer les noms directement.
    """

    user = "user"  # niveau 1
    advanced = "advanced"  # niveau 2 — Utilisateur avec privilèges améliorés
    ml_developer = "ml_developer"  # niveau 3 — Développeur Machine Learning
    admin = "admin"  # niveau 4

    @property
    def level(self) -> int:
        """Niveau ordinal du rôle (1 = user, 4 = admin)."""
        return {
            UserRole.user: 1,
            UserRole.advanced: 2,
            UserRole.ml_developer: 3,
            UserRole.admin: 4,
        }[self]


class User(Base):
    """Modèle SQLAlchemy pour la table `users`."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"),
        nullable=False,
        default=UserRole.user,
        server_default="user",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    token_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
