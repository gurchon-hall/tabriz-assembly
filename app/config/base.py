from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class BaseAppSettings(BaseSettings):
    # Metadata
    project_name: str = Field(default="Barrin's Project", description="Nom du projet")
    version: str = Field(default="1.0.0", description="Version de l'application")

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environnement (development, staging, production)",
    )
    debug: bool = Field(default=False, description="Mode debug")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def __repr__(self) -> str:
        return f"<BaseSettings env={self.environment} debug={self.debug}>"
