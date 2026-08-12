"""Maak berichten en bericht_leesbewijzen aan.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-12

Tweede migratie van de api-service (werkwijze-ADR-0005). Schema komt 1-op-1 uit
app/features/berichten/models.py.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "berichten",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("titel", sa.Text(), nullable=False),
        sa.Column("inhoud", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("versie", sa.String(length=32), nullable=True),
        sa.Column("gepubliceerd", sa.Boolean(), nullable=False),
        sa.Column("gepubliceerd_op", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aangemaakt_door", sa.String(length=128), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_berichten_gepubliceerd_created", "berichten", ["gepubliceerd", "created"])

    op.create_table(
        "bericht_leesbewijzen",
        sa.Column("bericht_id", sa.Integer(), nullable=False),
        sa.Column("userid", sa.String(length=128), nullable=False),
        sa.Column("gelezen_op", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("bericht_id", "userid"),
    )


def downgrade() -> None:
    op.drop_table("bericht_leesbewijzen")
    op.drop_index("ix_berichten_gepubliceerd_created", table_name="berichten")
    op.drop_table("berichten")
