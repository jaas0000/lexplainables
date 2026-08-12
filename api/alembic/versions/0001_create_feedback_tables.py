"""Maak user_feedback en feedback_leesbewijzen aan.

Revision ID: 0001
Revises:
Create Date: 2026-08-12

Eerste migratie van de api-service (werkwijze-ADR-0005) — vervangt een
"maak ontbrekende tabellen aan bij opstarten"-mechanisme. Schema komt 1-op-1 uit
app/features/feedback/models.py.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("userid", sa.String(length=128), nullable=False),
        sa.Column("categorie", sa.String(length=32), nullable=False),
        sa.Column("tekst", sa.Text(), nullable=False),
        sa.Column("pagina", sa.Text(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_feedback_created", "user_feedback", ["created"])

    op.create_table(
        "feedback_leesbewijzen",
        sa.Column("admin_userid", sa.String(length=128), primary_key=True),
        sa.Column("gezien_tot", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("feedback_leesbewijzen")
    op.drop_index("ix_user_feedback_created", table_name="user_feedback")
    op.drop_table("user_feedback")
