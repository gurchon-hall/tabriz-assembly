"""Change crypt_card primary key to (id,group,adv)

Revision ID: cb06de418c1f
Revises: 0a7c01faf9aa
Create Date: 2026-06-18 12:35:23.584075

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cb06de418c1f"
down_revision: str | Sequence[str] | None = "0a7c01faf9aa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Supprimer l'unique et la FK auto-générée par dc60f8c14be4
    op.drop_constraint("uq_crypt_card_sets", "crypt_card_sets", type_="unique")
    op.drop_constraint("crypt_card_sets_crypt_card_id_fkey", "crypt_card_sets", type_="foreignkey")

    # 2. Ajouter les deux nouvelles colonnes dans crypt_card_sets
    op.add_column(
        "crypt_card_sets",
        sa.Column("crypt_card_group", sa.String(), nullable=False, server_default=""),
    )
    op.add_column(
        "crypt_card_sets",
        sa.Column("crypt_card_adv", sa.Boolean(), nullable=False, server_default="false"),
    )

    # 3. Recréer la PK composite sur crypt
    op.drop_constraint("ck_crypt_id_range", "crypt", type_="check")
    op.execute("ALTER TABLE crypt DROP CONSTRAINT crypt_pkey")
    op.execute('ALTER TABLE crypt ADD PRIMARY KEY (id, "group", adv)')
    op.create_check_constraint("ck_crypt_id_range", "crypt", "id >= 200001 AND id <= 299999")

    # 4. Recréer FK composite + unique sur crypt_card_sets
    op.create_foreign_key(
        "fk_crypt_card_sets_crypt",
        "crypt_card_sets",
        "crypt",
        ["crypt_card_id", "crypt_card_group", "crypt_card_adv"],
        ["id", "group", "adv"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_crypt_card_sets",
        "crypt_card_sets",
        ["crypt_card_id", "crypt_card_group", "crypt_card_adv", "set_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_crypt_card_sets", "crypt_card_sets", type_="unique")
    op.drop_constraint("fk_crypt_card_sets_crypt", "crypt_card_sets", type_="foreignkey")
    op.drop_column("crypt_card_sets", "crypt_card_group")
    op.drop_column("crypt_card_sets", "crypt_card_adv")
    op.drop_constraint("ck_crypt_id_range", "crypt", type_="check")
    op.execute("ALTER TABLE crypt DROP CONSTRAINT crypt_pkey")
    op.execute("ALTER TABLE crypt ADD PRIMARY KEY (id)")
    op.create_check_constraint("ck_crypt_id_range", "crypt", "id >= 200001 AND id <= 299999")
    op.create_foreign_key(
        "crypt_card_sets_crypt_card_id_fkey",
        "crypt_card_sets",
        "crypt",
        ["crypt_card_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_crypt_card_sets",
        "crypt_card_sets",
        ["crypt_card_id", "set_id"],
    )
