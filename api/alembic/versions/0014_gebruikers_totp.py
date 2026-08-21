"""gebruikers: TOTP-kolommen voor 2FA

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-21

Story 017 (2FA/TOTP). Voegt twee kolommen toe aan `gebruikers`:

- `totp_secret_enc TEXT NULLABLE` — het TOTP-secret versleuteld via Fernet
  (`shared/crypto.encrypt`). Nullable want alleen gevuld als de gebruiker 2FA start of aan
  heeft staan.
- `totp_ingeschakeld BOOLEAN NOT NULL DEFAULT false` — schakelaar; pas `true` na een
  succesvolle activate-check zodat een half-opgezette koppeling nog geen tweestapsdwang wordt.

`sa.false()` (i.p.v. `"0"`/`"false"` string) — Postgres-only sinds ADR-0003; consistent met
migratie 0003's fix voor `actief`.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gebruikers", sa.Column("totp_secret_enc", sa.Text(), nullable=True))
    op.add_column(
        "gebruikers",
        sa.Column("totp_ingeschakeld", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("gebruikers", "totp_ingeschakeld")
    op.drop_column("gebruikers", "totp_secret_enc")
