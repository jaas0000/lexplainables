"""gebruikers tabel

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-13
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gebruikers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gebruikersnaam", sa.String(length=64), nullable=False),
        sa.Column("wachtwoord_hash", sa.Text(), nullable=False),
        sa.Column("rol", sa.String(length=16), nullable=False, server_default="beheerder"),
        sa.Column("actief", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("aangemaakt_op", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gebruikersnaam"),
    )


def downgrade() -> None:
    op.drop_table("gebruikers")
