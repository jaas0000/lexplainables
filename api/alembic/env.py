"""Alembic-omgeving voor de api-service (werkwijze-ADR-0005).

Eén migratiehistorie voor deze service. Het doelschema (`target_metadata`) komt uit de feature
zelf (app/features/feedback/models.py) — er is geen apart, met de hand bijgehouden
schemabestand om synchroon te houden met de migraties.

Migraties draaien synchroon (het gebruikelijke Alembic-patroon, ook als de app zelf async is
via aiosqlite/asyncpg): `DATABASE_URL_SYNC` gebruikt daarom een sync-driver
(`sqlite://…`/`postgresql://…`), los van de async `DATABASE_URL` van de app zelf.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.features.feedback.models import metadata  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get("DATABASE_URL_SYNC")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
