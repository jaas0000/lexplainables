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


def maak_test_engine(*metadatas: MetaData, tmp_path) -> AsyncEngine:
    """Zet een test-database op en geef de async engine terug.

    Accepteert één of meer `MetaData`-objecten (sommige features gebruiken meerdere tabellen
    uit verschillende feature-`MetaData`s in dezelfde test — zie llm_calls/projecten).

    Standaard: een kortlevende SQLite-bestand in `tmp_path` — snelle, geïsoleerde tests. Als
    `TEST_DATABASE_URL_SYNC` én `TEST_DATABASE_URL` gezet zijn (CI-matrix voor Postgres), draaien
    de tests tegen een gedeelde Postgres met een `drop_all → create_all` reset per test, zodat
    elke test met een schone DB begint.

    Zie ADR-0003 (SQLite in tests, Postgres in productie én CI). De schema-opbouw gebruikt een
    sync-engine (`metadata.create_all`) om event-loop-koppeling van de async-engine te vermijden.
    """
    # NullPool voor test-engines: elke request opent+sluit z'n eigen verbinding, geen pool die
    # bij testeinde nog open connections aanhoudt. Bij ~166 tests × ~5 pool-connecties zou
    # Postgres' default max_connections=100 anders uitputten (`FATAL: sorry, too many clients`).
    pg_sync = os.environ.get("TEST_DATABASE_URL_SYNC")
    pg_async = os.environ.get("TEST_DATABASE_URL")
    if pg_sync and pg_async:
        sync_engine = create_engine(pg_sync, poolclass=NullPool)
        for metadata in metadatas:
            metadata.drop_all(sync_engine)
            metadata.create_all(sync_engine)
        sync_engine.dispose()
        return create_async_engine(pg_async, poolclass=NullPool)

    db_pad = tmp_path / "test.db"
    sync_engine = create_engine(f"sqlite:///{db_pad}", poolclass=NullPool)
    for metadata in metadatas:
        metadata.create_all(sync_engine)
    sync_engine.dispose()
    return create_async_engine(f"sqlite+aiosqlite:///{db_pad}", poolclass=NullPool)


def sync_engine_voor(async_engine: AsyncEngine) -> Engine:
    """Maak een sync-engine met dezelfde DB als een async-engine.

    Voor tests die directe (dialect-agnostische) SQL willen uitvoeren zonder de app-flow —
    bijvoorbeeld voor het seeden van rijen of het inspecteren van een cascade. De async-engine
    blijft ongewijzigd; de sync-engine moet door de aanroeper gedisposed worden. Gebruikt
    NullPool om verbindingsuitputting in de test-run te voorkomen (zie `maak_test_engine`).
    """
    url = async_engine.url
    if url.drivername == "sqlite+aiosqlite":
        return create_engine(f"sqlite:///{url.database}", poolclass=NullPool)
    if url.drivername == "postgresql+asyncpg":
        return create_engine(url.set(drivername="postgresql"), poolclass=NullPool)
    raise ValueError(f"Onbekende driver voor test: {url.drivername}")
