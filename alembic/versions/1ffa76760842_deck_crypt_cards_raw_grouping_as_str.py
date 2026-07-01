"""Deck crypt cards raw_grouping as str

Revision ID: 1ffa76760842
Revises: 5182ea0a606f
Create Date: 2026-07-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1ffa76760842"
down_revision: str | Sequence[str] | None = "5182ea0a606f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # channel-ten >= 0.9.0 parses group-independent vampires as grouping "ANY";
    # raw_grouping must hold that literal alongside numeric groups.
    op.alter_column(
        "deck_crypt_cards", "raw_grouping", existing_type=sa.INTEGER(), type_=sa.String()
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "deck_crypt_cards",
        "raw_grouping",
        existing_type=sa.String(),
        type_=sa.INTEGER(),
        postgresql_using="raw_grouping::integer",
    )
