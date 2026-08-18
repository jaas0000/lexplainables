"""app_instellingen tabel — runtime-configuratie (story 019)

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-18
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_instellingen",
        sa.Column("sleutel", sa.Text(), nullable=False),
        sa.Column("waarde", sa.Text(), nullable=False),
        sa.Column("bijgewerkt", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sleutel"),
    )


def downgrade() -> None:
    op.drop_table("app_instellingen")
