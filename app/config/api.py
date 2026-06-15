from pydantic import Field
from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    api_str: str = Field(default="/api/v1", description="Préfixe des routes API")

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def __repr__(self) -> str:
        return f"<BaseSettings prefix={self.api_str}>"
