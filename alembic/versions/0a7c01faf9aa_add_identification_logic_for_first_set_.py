"""Add identification logic for first set in which a card is printed

Revision ID: 0a7c01faf9aa
Revises: 0608a1ab3607
Create Date: 2026-06-17 18:48:37.575977

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0a7c01faf9aa"
down_revision: str | Sequence[str] | None = "0608a1ab3607"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("crypt", sa.Column("first_print_set_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_crypt_first_print_set_id"), "crypt", ["first_print_set_id"], unique=False
    )
    op.create_foreign_key(
        "fk_crypt_first_print_set",
        "crypt",
        "sets",
        ["first_print_set_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("library", sa.Column("first_print_set_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_library_first_print_set_id"), "library", ["first_print_set_id"], unique=False
    )
    op.create_foreign_key(
        "fk_library_first_print_set",
        "library",
        "sets",
        ["first_print_set_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_library_first_print_set", "library", type_="foreignkey")
    op.drop_index(op.f("ix_library_first_print_set_id"), table_name="library")
    op.drop_column("library", "first_print_set_id")
    op.drop_constraint("fk_crypt_first_print_set", "crypt", type_="foreignkey")
    op.drop_index(op.f("ix_crypt_first_print_set_id"), table_name="crypt")
    op.drop_column("crypt", "first_print_set_id")
