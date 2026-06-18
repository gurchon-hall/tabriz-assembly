from pydantic import Field
from pydantic_settings import BaseSettings


class TournamentImportSettings(BaseSettings):
    """Paramètres de l'import des tournois depuis le dépôt eternal-vigilance."""

    source_repo: str = Field(
        default="gurchon-hall/eternal-vigilance",
        description="Dépôt GitHub source (owner/repo) contenant les tournois YAML",
    )
    source_branch: str = Field(
        default="main",
        description="Branche du dépôt source à lire",
    )
    github_token: str | None = Field(
        default=None,
        description=(
            "Token GitHub optionnel. Utilisé pour l'API trees (énumération) afin "
            "d'éviter la limite de débit des requêtes non authentifiées."
        ),
    )
    commit_batch_size: int = Field(
        default=25,
        ge=1,
        description="Nombre de tournois traités entre deux commits",
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
        "env_prefix": "tournament_",
    }

    def __repr__(self) -> str:
        return (
            "<BaseSettings "
            f"repo={self.source_repo}@{self.source_branch} "
            f"token={'set' if self.github_token else 'none'} "
            f"batch={self.commit_batch_size}>"
        )
