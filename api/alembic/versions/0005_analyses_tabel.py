"""analyses tabel

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-18
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("naam", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("bronnen", sa.JSON(), nullable=False),
        sa.Column("model_profiel", sa.String(length=128), nullable=True),
        sa.Column("omschrijving", sa.Text(), nullable=True),
        sa.Column("analysefocus", sa.Text(), nullable=True),
        sa.Column("human_in_the_loop", sa.Boolean(), nullable=False),
        sa.Column("begrippenlijst", sa.JSON(), nullable=True),
        sa.Column("huidige_fase", sa.Text(), nullable=True),
        sa.Column("foutmelding", sa.Text(), nullable=True),
        sa.Column("aangemaakt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bijgewerkt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gebruiker_id", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analyses_gebruiker_id", "analyses", ["gebruiker_id"])
    op.create_index("ix_analyses_bijgewerkt", "analyses", ["bijgewerkt"])


def downgrade() -> None:
    op.drop_index("ix_analyses_bijgewerkt", table_name="analyses")
    op.drop_index("ix_analyses_gebruiker_id", table_name="analyses")
    op.drop_table("analyses")
