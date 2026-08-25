"""gesprekken + gesprek_berichten: persistente chatgeschiedenis van de werkplek

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-25

Nieuw domein (zie `app/features/gesprekken/__init__.py`): graph-qa legt het resultaat van een
beurt hier zelf vast, zodat een gesloten tabblad geen werk meer kost.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gesprekken",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("gebruiker", sa.Text(), nullable=False),
        sa.Column("titel", sa.Text(), nullable=False, server_default=""),
        sa.Column("aangemaakt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bijgewerkt", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_gesprekken_gebruiker", "gesprekken", ["gebruiker"])

    op.create_table(
        "gesprek_berichten",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("gesprek_id", sa.Text(), nullable=False),
        sa.Column("rol", sa.Text(), nullable=False),
        sa.Column("inhoud", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("aangemaakt", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_gesprek_berichten_gesprek_id", "gesprek_berichten", ["gesprek_id"])


def downgrade() -> None:
    op.drop_index("ix_gesprek_berichten_gesprek_id", table_name="gesprek_berichten")
    op.drop_table("gesprek_berichten")
    op.drop_index("ix_gesprekken_gebruiker", table_name="gesprekken")
    op.drop_table("gesprekken")
