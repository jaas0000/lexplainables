"""annotatie_documenten en annotatie_audit tabellen (story 022)

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-19
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "annotatie_documenten",
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("client_id", sa.Text(), nullable=False),
        sa.Column("werkgebied", sa.Text(), nullable=False),
        sa.Column("bwb_id", sa.Text(), nullable=False),
        sa.Column("artikel", sa.Text(), nullable=False),
        sa.Column("lid", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.Text(), nullable=False, server_default="voorgesteld"),
        sa.Column("elementen", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("aangemaakt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bijgewerkt", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("slug"),
    )
    op.create_index("ix_annotatie_documenten_client_id", "annotatie_documenten", ["client_id"])

    op.create_table(
        "annotatie_audit",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("document_slug", sa.Text(), nullable=False),
        sa.Column("client_id", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("actie", sa.Text(), nullable=False),
        sa.Column("element_id", sa.Text(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("tijdstip", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_annotatie_audit_document_slug", "annotatie_audit", ["document_slug"]
    )


def downgrade() -> None:
    op.drop_index("ix_annotatie_audit_document_slug", table_name="annotatie_audit")
    op.drop_table("annotatie_audit")
    op.drop_index("ix_annotatie_documenten_client_id", table_name="annotatie_documenten")
    op.drop_table("annotatie_documenten")
