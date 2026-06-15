import re
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole

# ---------------------------------------------------------------------------
# Règles de complexité du mot de passe
# ---------------------------------------------------------------------------

# Source de vérité unique — partageable avec le frontend via GET /openapi.json.
# Note : Pydantic v2 utilise le moteur Rust qui ne supporte pas les look-around ;
# Field(pattern=...) est réservé à l'exposition OpenAPI, la validation effective
# passe par AfterValidator.
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])"  # ≥ 1 minuscule
    r"(?=.*[A-Z])"  # ≥ 1 majuscule
    r"(?=.*\d)"  # ≥ 1 chiffre
    r"(?=.*[^\w\s])"  # ≥ 1 symbole (note : _ exclu car inclus dans \w)
    r".{12,}$"
)
PASSWORD_RULE = "Au moins 12 caractères avec 1 majuscule, 1 minuscule, 1 chiffre et 1 symbole."  # noqa: S105


def _check_password_complexity(v: str) -> str:
    """Validateur de complexité — utilisé via Annotated pour éviter la duplication."""
    if not PASSWORD_PATTERN.fullmatch(v):
        raise ValueError(PASSWORD_RULE)
    return v


# Type réutilisable (idiome Pydantic v2) — partagé par UserCreate et UserSignup.
# Pas de min_length=12 : la regex .{12,}$ couvre la contrainte et unifie les messages
# d'erreur (un seul PASSWORD_RULE, quelle que soit la cause d'échec).
PasswordStr = Annotated[
    str,
    Field(
        json_schema_extra={
            "pattern": PASSWORD_PATTERN.pattern,  # OpenAPI seulement
            "description": PASSWORD_RULE,
        }
    ),
    AfterValidator(_check_password_complexity),
]

# ---------------------------------------------------------------------------
# Schémas utilisateur
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    """Payload de création d'un utilisateur par un administrateur.

    Expose les champs privilégiés (role, is_verified) car l'appelant
    est un admin. Ne jamais exposer ce schéma sur un endpoint public.
    extra="forbid" : défense en profondeur — toute clé inconnue produit HTTP 422.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: PasswordStr
    role: UserRole = UserRole.user
    is_verified: bool = False
    display_name: str | None = None


class UserSignup(BaseModel):
    """Payload d'auto-inscription depuis le frontend.

    Sous-ensemble volontairement restreint de UserCreate :
    - `role` absent → forcé à UserRole.user côté serveur (pas d'escalade).
    - `is_verified` absent → forcé à False côté serveur.
    - `extra="forbid"` → HTTP 422 explicite si un champ non déclaré est envoyé
      (détecte une tentative d'escalade de rôle même si le handler la bloquerait).

    ⏳ Endpoint futur — la route n'est pas enregistrée dans le router.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: PasswordStr
    display_name: str | None = None


class UserRead(BaseModel):
    """Représentation publique d'un utilisateur (sans mot de passe)."""

    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    is_verified: bool
    display_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Schémas JWT
# ---------------------------------------------------------------------------


class TokenPair(BaseModel):
    """Paire de tokens retournée par POST /auth/token et POST /auth/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105


class RefreshRequest(BaseModel):
    """Corps de POST /auth/refresh."""

    refresh_token: str


class TokenData(BaseModel):
    """Contenu décodé du payload JWT (claims internes)."""

    sub: str  # user UUID (str)
    role: UserRole
    email: EmailStr
    token_version: int  # claim "tkv" — vérification de révocation
