"""Fix: Crypt and library id range constraints inverted

Revision ID: da86d1f0323e
Revises: dc60f8c14be4
Create Date: 2026-06-16 10:19:27.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "da86d1f0323e"
down_revision: str | Sequence[str] | None = "dc60f8c14be4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Corrige les plages d'ID : library 100001-199999, crypt 200001-299999."""
    op.drop_constraint("ck_crypt_id_range", "crypt", type_="check")
    op.create_check_constraint(
        "ck_crypt_id_range",
        "crypt",
        "id >= 200001 AND id <= 299999",
    )

    op.drop_constraint("ck_library_id_range", "library", type_="check")
    op.create_check_constraint(
        "ck_library_id_range",
        "library",
        "id >= 100001 AND id <= 199999",
    )


def downgrade() -> None:
    """Restaure les anciennes contraintes (incorrectes)."""
    op.drop_constraint("ck_crypt_id_range", "crypt", type_="check")
    op.create_check_constraint(
        "ck_crypt_id_range",
        "crypt",
        "id >= 100001 AND id <= 199999",
    )

    op.drop_constraint("ck_library_id_range", "library", type_="check")
    op.create_check_constraint(
        "ck_library_id_range",
        "library",
        "id >= 200001 AND id <= 299999",
    )
