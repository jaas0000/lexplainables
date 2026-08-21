"""Testfixtures voor het wetcatalogus-domein (story 020).

Elke test krijgt een eigen, kortlevende SQLite-database. Het schema wordt opgezet
met een synchrone engine; de async engine (aiosqlite) wordt gebruikt door de store.
De seeddata (drie wetten) weerspiegelt de hardgecodeerde data uit story 010.

`huidige_gebruiker` en `huidige_beheerder` worden overgeslagen via dependency-overrides.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.features.wetcatalogus.models import metadata
from app.features.wetcatalogus.router import get_store
from app.features.wetcatalogus.store import DatabaseWetcatalogusStore
from app.main import app
from app.shared.auth import huidige_beheerder, huidige_gebruiker
from conftest import TEST_BEHEERDER, maak_test_engine

_SEED_WETTEN = [
    ("BWBR0011823", "Wet werk en bijstand"),
    ("BWBR0015703", "Wet structuur uitvoeringsorganisatie werk en inkomen"),
    ("BWBR0020183", "Participatiewet"),
]


async def _seed_wetten(async_engine: AsyncEngine) -> None:
    """Seed drie standaard-wetten via de async engine (dialect-agnostisch)."""
    async with async_engine.begin() as conn:
        for bwb_id, naam in _SEED_WETTEN:
            await conn.execute(
                text(
                    "INSERT INTO wet_catalogus (bwb_id, naam, bijgewerkt_door, bijgewerkt) "
                    "VALUES (:bwb_id, :naam, '', '2026-01-01T00:00:00+00:00')"
                ),
                {"bwb_id": bwb_id, "naam": naam},
            )


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    asyncio.run(_seed_wetten(async_engine))
    store = DatabaseWetcatalogusStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-test"
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_gebruiker, None)
    app.dependency_overrides.pop(huidige_beheerder, None)


@pytest.fixture
def lege_client(tmp_path) -> Iterator[TestClient]:
    """Client met een lege catalogus (geen seeddata)."""
    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = DatabaseWetcatalogusStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-test"
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_gebruiker, None)
    app.dependency_overrides.pop(huidige_beheerder, None)
