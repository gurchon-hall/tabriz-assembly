from collections.abc import AsyncGenerator

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class for all ORM models."""

    pass


class DatabaseSettings(BaseSettings):
    database_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://user:pass@localhost:5432/foobar"),
        description="URL de connexion PostgreSQL",
    )
    database_echo: bool = Field(default=False, description="Activer les logs SQL")
    table_prefix: str = Field(default="", description="Default table prefix")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def synchrone_url(self) -> str:
        if "asyncpg" in str(self.database_url):
            return str(self.database_url).replace("+asyncpg", "+psycopg2")
        return str(self.database_url)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def asynchrone_url(self) -> str:
        if "psycopg2" in str(self.database_url):
            return str(self.database_url).replace("+psycopg2", "+asyncpg")
        return str(self.database_url)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def engine(self) -> AsyncEngine:
        return create_async_engine(
            str(self.database_url),
            echo=self.database_echo,
            pool_pre_ping=True,  # Verify connections before using them
            pool_size=5,  # Connection pool size
            max_overflow=10,  # Max overflow connections
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_session_local(self) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(self.engine, expire_on_commit=False)

    async def get_db(self) -> AsyncGenerator[AsyncSession]:
        """FastAPI dependency that provides a database session.

        Yields a database session and ensures proper cleanup after request.
        Use this as a dependency in FastAPI route handlers:

        Example:
            @app.get("/users")
            async def get_users(db: AsyncSession = Depends(get_db)):
                result = await db.execute(select(User))
                return result.scalars().all()

        Yields:
            AsyncSession: SQLAlchemy asynchronous database session
        """
        async with self.async_session_local() as session:
            yield session

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def __repr__(self) -> str:
        return (
            "<BaseSettings "
            f"database={str(self.database_url).split('/')[-1]} "
            f"echo={self.database_echo}>"
        )
