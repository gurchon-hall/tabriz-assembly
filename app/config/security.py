from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jose import JWTError, jwt
from pydantic import Field
from pydantic_settings import BaseSettings

from app.schemas.auth import TokenData

_hasher = PasswordHasher()
_DUMMY_HASH: str = _hasher.hash("dummy_value_for_timing_equalization")


class SecuritySettings(BaseSettings):
    secret_key: str = Field(
        default="CHANGE_ME_GENERATE_WITH_OPENSSL",
        description="Clé secrète pour JWT (openssl rand -hex 32)",
    )
    access_token_expire_minutes: int = Field(
        default=30, description="Durée de validité du token JWT en minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Durée de validité du refresh token JWT en jours"
    )
    algorithm: str = Field(default="HS256", description="Algorithme de signature JWT")
    allowed_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Origins autorisées pour CORS",
    )

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def __repr__(self) -> str:
        return (
            f"<BaseSettings algo={self.algorithm} token_val={self.access_token_expire_minutes}min>"
        )

    # Crypt tool: Argon2id hash, JWT tokens

    # Passwords
    def hash_password(self, plain: str) -> str:
        return _hasher.hash(plain)

    def verify_password(self, plain: str, hashed: str) -> bool:
        try:
            return _hasher.verify(hashed, plain)
        except VerificationError, InvalidHashError:
            # VerifyMismatchError hérite de VerificationError — couvert implicitement.
            return False

    def dummy_verify(self, plain: str) -> None:
        """Call to equalize verifications for an unknown user."""
        try:
            _hasher.verify(_DUMMY_HASH, plain)
        except VerificationError, InvalidHashError:
            pass

    # Tokens
    def create_access_token(self, data: dict[Any, Any]) -> str:
        """Crée un access token JWT signé.

        `data` doit contenir la clé `"tkv"` (token_version de l'utilisateur).
        Le claim `type: "access"` empêche l'utilisation d'un refresh token à sa place.
        """
        to_encode = data.copy()
        to_encode["type"] = "access"
        expire = datetime.now(UTC) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode["exp"] = expire
        return jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def decode_access_token(self, token: str) -> TokenData:
        """Décode et valide un access token.

        Lève `JWTError` si le token est invalide, expiré ou si le claim `type`
        n'est pas "access".
        """
        payload = jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
        )
        if payload.get("type") != "access":
            raise JWTError("Token type invalide — attendu: access")
        return TokenData(
            sub=payload["sub"],
            role=payload["role"],
            email=payload["email"],
            token_version=payload["tkv"],
        )

    def create_refresh_token(self, data: dict[Any, Any]) -> str:
        """Crée un refresh token JWT signé (longue durée).

        `data` doit contenir `"tkv"` (token_version).
        Le claim `type: "refresh"` empêche son utilisation comme access token.
        """
        to_encode = data.copy()
        to_encode["type"] = "refresh"
        expire = datetime.now(UTC) + timedelta(days=self.refresh_token_expire_days)
        to_encode["exp"] = expire
        return jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def decode_refresh_token(self, token: str) -> TokenData:
        """Décode et valide un refresh token.

        Lève `JWTError` si le token est invalide, expiré ou si le claim `type`
        n'est pas "refresh".
        """
        payload = jwt.decode(
            token,
            self.secret_key,
            algorithms=[self.algorithm],
        )
        if payload.get("type") != "refresh":
            raise JWTError("Token type invalide — attendu: refresh")
        return TokenData(
            sub=payload["sub"],
            role=payload["role"],
            email=payload["email"],
            token_version=payload["tkv"],
        )
