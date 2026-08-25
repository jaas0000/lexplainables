"""annotatie_documenten: laatste_run-kolom (agent-provenance)

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-25

graph-qa krijgt een schrijfpad naar het annotatie-domein (agent/wetsanalyse_api.py +
agent/beurt.py). `laatste_run` bewaart welk model/agent-versie de laatste keer voorstellen
deed — puur provenance, geen levenscyclus-impact.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("annotatie_documenten", sa.Column("laatste_run", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("annotatie_documenten", "laatste_run")
