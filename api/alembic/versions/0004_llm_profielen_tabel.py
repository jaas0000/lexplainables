"""llm_profielen tabel

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-18
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_profielen",
        sa.Column("naam", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("api_base", sa.Text(), nullable=False),
        sa.Column("api_versie", sa.String(length=64), nullable=True),
        sa.Column("temperatuur", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("api_sleutel_enc", sa.Text(), nullable=True),
        sa.Column("is_standaard", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("naam"),
    )


def downgrade() -> None:
    op.drop_table("llm_profielen")
