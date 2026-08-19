"""api_tokens-tabel — programmatische DB-tokens voor externe toegang (story 018)

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False, server_default=""),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("token_prefix", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False, server_default="beheerder"),
        sa.Column("actief", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("aangemaakt_door", sa.Text(), nullable=False, server_default=""),
        sa.Column("aangemaakt_op", sa.DateTime(timezone=True), nullable=False),
        sa.Column("laatste_gebruik", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("api_tokens")
