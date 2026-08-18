"""rapport-kolom op analyses + llm_calls-tabel (story 024)

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-18
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Voeg 'rapport' toe aan analyses (nullable JSON — gevuld na afgeronde analyse).
    op.add_column("analyses", sa.Column("rapport", sa.JSON(), nullable=True))

    # Nieuwe tabel voor vastgelegde LLM-calls (capture-toggle via runtime_config).
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("analyse_id", sa.String(length=36), nullable=False),
        sa.Column("activiteit", sa.String(length=32), nullable=False),
        sa.Column("bron_id", sa.String(length=32), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("ruwe_respons", sa.Text(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("aangemaakt", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_calls_analyse_id", "llm_calls", ["analyse_id"])


def downgrade() -> None:
    op.drop_index("ix_llm_calls_analyse_id", table_name="llm_calls")
    op.drop_table("llm_calls")
    op.drop_column("analyses", "rapport")
