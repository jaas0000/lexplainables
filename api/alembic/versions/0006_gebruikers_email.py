"""voeg email-kolom toe aan gebruikers

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-18

Bestaande rijen krijgen een lege string als default (NOT NULL DEFAULT '').
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gebruikers",
        sa.Column("email", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("gebruikers", "email")
