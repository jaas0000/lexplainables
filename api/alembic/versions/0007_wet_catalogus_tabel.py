"""wet_catalogus tabel + seed hardgecodeerde wetten

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-18
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wet_catalogus",
        sa.Column("bwb_id", sa.Text(), nullable=False),
        sa.Column("naam", sa.Text(), nullable=False),
        sa.Column("bijgewerkt_door", sa.Text(), nullable=False, server_default=""),
        sa.Column("bijgewerkt", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("bwb_id"),
    )
    # Seed: kopieer de hardgecodeerde wetten uit de vorige implementatie (story 010).
    op.execute(
        sa.text(
            "INSERT INTO wet_catalogus (bwb_id, naam, bijgewerkt_door, bijgewerkt) VALUES "
            "(:bwb1, :naam1, '', '2026-01-01T00:00:00+00:00'), "
            "(:bwb2, :naam2, '', '2026-01-01T00:00:00+00:00'), "
            "(:bwb3, :naam3, '', '2026-01-01T00:00:00+00:00')"
        ).bindparams(
            bwb1="BWBR0011823",
            naam1="Wet werk en bijstand",
            bwb2="BWBR0015703",
            naam2="Wet structuur uitvoeringsorganisatie werk en inkomen",
            bwb3="BWBR0020183",
            naam3="Participatiewet",
        )
    )


def downgrade() -> None:
    op.drop_table("wet_catalogus")
