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
    # `server_default=sa.true()` en `DateTime(timezone=True)` i.p.v. `"1"` / naïeve DateTime:
    # SQLite accepteert die naïef gestelde vormen wel, maar asyncpg tegen Postgres weigert (a)
    # "1" als Boolean en (b) een tz-aware waarde in een naive timestamp-kolom. Deze migratie
    # draaide al schoon op beide (`check-migraties`), maar de runtime-INSERT vanuit
    # `Gebruiker` (model schrijft `datetime.now(UTC)`) faalde op Postgres tot deze fix.
    op.create_table(
        "gebruikers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gebruikersnaam", sa.String(length=64), nullable=False),
        sa.Column("wachtwoord_hash", sa.Text(), nullable=False),
        sa.Column("rol", sa.String(length=16), nullable=False, server_default="beheerder"),
        sa.Column("actief", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("aangemaakt_op", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gebruikersnaam"),
    )


def downgrade() -> None:
    op.drop_table("gebruikers")
