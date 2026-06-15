import enum


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
