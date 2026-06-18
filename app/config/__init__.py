from functools import lru_cache

from pydantic_settings import BaseSettings

from app.config.api import ApiSettings
from app.config.base import BaseAppSettings
from app.config.database import DatabaseSettings
from app.config.logging import LoggingSettings
from app.config.security import SecuritySettings
from app.config.tournament import TournamentImportSettings


class AppSettings(BaseSettings):
    base: BaseAppSettings = BaseAppSettings()
    db: DatabaseSettings = DatabaseSettings()
    log: LoggingSettings = LoggingSettings()
    api: ApiSettings = ApiSettings()
    security: SecuritySettings = SecuritySettings()
    tournament: TournamentImportSettings = TournamentImportSettings()

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.base.environment == "production"

    @property
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.base.debug

    def __repr__(self) -> str:
        tmp: list[str] = []
        tmp.append(f"<Settings env={self.base.environment}>")
        tmp.append(self.base.__repr__())
        tmp.append(self.db.__repr__())
        tmp.append(self.log.__repr__())
        tmp.append(self.api.__repr__())
        tmp.append(self.security.__repr__())
        tmp.append(self.tournament.__repr__())
        return "\n" + "\n\t".join(tmp) + "\n</Settings>"

    @property
    def project_version(self) -> str:
        return f"{self.base.project_name} v{self.base.version}"

    @property
    def _project_version(self) -> str:
        """Compatibilité ascendante: ancien alias interne."""
        return self.project_version


@lru_cache
def get_settings() -> AppSettings:
    """Get the singleton application settings instance.

    Uses lru_cache to ensure settings are loaded only once,
    even across multiple imports.

    Returns:
        AppSettings: Configured settings instance
    """
    return AppSettings()


settings = get_settings()

__all__ = ["get_settings", "settings"]
