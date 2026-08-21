"""jobs tabel — async jobstore met lease-mechanisme

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-21

Fase 1 story 3 van de wetsanalyse-migratie. Een generieke jobstore die door meerdere features
(annotatie-generatie, analyse-orkestratie) benut kan worden. Zie
`api/app/shared/jobs/store.py` voor het lease-patroon (`FOR UPDATE SKIP LOCKED`) — dit is de
eerste Postgres-specifieke primitief in de codebase, direct mogelijk sinds ADR-0003.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("soort", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="wachtend"),
        sa.Column("lease_eigenaar", sa.Text(), nullable=True),
        sa.Column("lease_verloopt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fout", sa.Text(), nullable=True),
        sa.Column("pogingen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aangemaakt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bijgewerkt", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('wachtend', 'bezig', 'klaar', 'mislukt')", name="jobs_status_geldig"
        ),
    )
    # Claim-query zoekt op (status, soort) — nodig voor snelle 'volgende wachtende'-lookup.
    op.create_index("ix_jobs_status_soort", "jobs", ["status", "soort"])
    # Reap-query zoekt bezig-jobs waarvan de lease is verlopen.
    op.create_index("ix_jobs_status_lease", "jobs", ["status", "lease_verloopt"])


def downgrade() -> None:
    op.drop_index("ix_jobs_status_lease", table_name="jobs")
    op.drop_index("ix_jobs_status_soort", table_name="jobs")
    op.drop_table("jobs")
