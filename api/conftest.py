from __future__ import annotations

import os

import pytest
from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.shared.auth import GebruikerContext

TEST_BEHEERDER = GebruikerContext(gebruikersnaam="beheerder-test", rol="beheerder")


@pytest.fixture
def test_beheerder() -> GebruikerContext:
    return TEST_BEHEERDER


def maak_test_engine(*metadatas: MetaData, tmp_path=None) -> AsyncEngine:  # noqa: ARG001
    """Zet een test-database op en geef de async engine terug.

    Accepteert één of meer `MetaData`-objecten (sommige features gebruiken meerdere tabellen
    uit verschillende feature-`MetaData`s in dezelfde test — zie llm_calls/projecten).

    Draait tegen een gedeelde Postgres (`TEST_DATABASE_URL_SYNC` + `TEST_DATABASE_URL` vereist)
    met een `drop_all → create_all` reset per test, zodat elke test met een schone DB begint.
    `tmp_path` blijft in de signature voor backwards-compatibiliteit met bestaande fixtures,
    maar wordt niet meer gebruikt — zie ADR-0003 (Postgres-only).

    NullPool voor test-engines: elke request opent+sluit z'n eigen verbinding, geen pool die
    bij testeinde nog open connections aanhoudt. Bij ~166 tests × ~5 pool-connecties zou
    Postgres' default max_connections=100 anders uitputten (`FATAL: sorry, too many clients`).
    """
    pg_sync = os.environ.get("TEST_DATABASE_URL_SYNC")
    pg_async = os.environ.get("TEST_DATABASE_URL")
    if not (pg_sync and pg_async):
        raise RuntimeError(
            "Tests vereisen een draaiende Postgres — zet TEST_DATABASE_URL_SYNC + "
            "TEST_DATABASE_URL. Lokaal: `docker compose up -d postgres` en zie ADR-0003."
        )
    sync_engine = create_engine(pg_sync, poolclass=NullPool)
    for metadata in metadatas:
        metadata.drop_all(sync_engine)
        metadata.create_all(sync_engine)
    sync_engine.dispose()
    return create_async_engine(pg_async, poolclass=NullPool)


def sync_engine_voor(async_engine: AsyncEngine) -> Engine:
    """Maak een sync-engine met dezelfde Postgres-DB als een async-engine.

    Voor tests die directe SQL willen uitvoeren zonder de app-flow — bijvoorbeeld voor het
    seeden van rijen of het inspecteren van een cascade. De async-engine blijft ongewijzigd;
    de sync-engine moet door de aanroeper gedisposed worden. Gebruikt NullPool om
    verbindingsuitputting in de test-run te voorkomen (zie `maak_test_engine`).
    """
    url = async_engine.url
    if url.drivername != "postgresql+asyncpg":
        raise ValueError(f"Verwacht postgresql+asyncpg, kreeg: {url.drivername}")
    return create_engine(url.set(drivername="postgresql"), poolclass=NullPool)
