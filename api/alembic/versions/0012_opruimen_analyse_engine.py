"""opruimen analyse-engine: drop JAS-pipeline-kolommen op analyses

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-21

Migratie-plan fase 1 (`docs/project/migratie-wetsanalyse.md`): stories 013 (rapport bekijken)
en 024 (analyse-engine) zijn verwijderd — JAS-pipeline is legacy, annotatie is de enige
analyse-stap. Dropt de kolommen die alleen voor die pipeline bestonden. `llm_calls`-tabel
blijft (story 021). Downgrade zet de kolommen terug in hun originele vorm (bekijk 0005/0009
voor de brondefinities).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Batch-alter voor SQLite-compatibiliteit (ondersteunt geen ALTER TABLE DROP COLUMN
    # natief in oudere versies; batch_alter_table herschrijft de tabel).
    with op.batch_alter_table("analyses") as batch:
        batch.drop_column("rapport")  # uit 0009 (story 013)
        batch.drop_column("model_profiel")  # uit 0005 (engine-config)
        batch.drop_column("analysefocus")  # uit 0005 (act3-input)
        batch.drop_column("human_in_the_loop")  # uit 0005 (review-flow)
        batch.drop_column("begrippenlijst")  # uit 0005 (act3-input)
        batch.drop_column("huidige_fase")  # uit 0005 (engine-status)
        batch.drop_column("foutmelding")  # uit 0005 (engine-status)


def downgrade() -> None:
    with op.batch_alter_table("analyses") as batch:
        batch.add_column(sa.Column("foutmelding", sa.Text(), nullable=True))
        batch.add_column(sa.Column("huidige_fase", sa.Text(), nullable=True))
        batch.add_column(sa.Column("begrippenlijst", sa.JSON(), nullable=True))
        # De originele 0005 zette `human_in_the_loop` op nullable=False; om downgrade zonder
        # backfill mogelijk te maken staat 'ie hier nullable — dat is de bewust geaccepteerde
        # afwijking (rijen aangemaakt na 0012 hebben deze kolom niet gehad).
        batch.add_column(sa.Column("human_in_the_loop", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("analysefocus", sa.Text(), nullable=True))
        batch.add_column(sa.Column("model_profiel", sa.String(length=128), nullable=True))
        batch.add_column(sa.Column("rapport", sa.JSON(), nullable=True))
