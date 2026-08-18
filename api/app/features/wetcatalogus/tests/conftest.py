"""Testfixtures voor het wetcatalogus-domein (story 020).

Elke test krijgt een eigen, kortlevende SQLite-database. Het schema wordt opgezet
met een synchrone engine; de async engine (aiosqlite) wordt gebruikt door de store.
De seeddata (drie wetten) weerspiegelt de hardgecodeerde data uit story 010.

`huidige_gebruiker` en `huidige_beheerder` worden overgeslagen via dependency-overrides.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from app.features.wetcatalogus.models import metadata
from app.features.wetcatalogus.router import get_store
from app.features.wetcatalogus.store import DatabaseWetcatalogusStore
from app.main import app
from app.shared.auth import huidige_beheerder, huidige_gebruiker
from conftest import TEST_BEHEERDER

_SEED_WETTEN = [
    ("BWBR0011823", "Wet werk en bijstand"),
    ("BWBR0015703", "Wet structuur uitvoeringsorganisatie werk en inkomen"),
    ("BWBR0020183", "Participatiewet"),
]


def _maak_db(db_pad):
    """Maak schema en seed de drie standaard-wetten."""
    from sqlalchemy import text

    sync_engine = create_engine(f"sqlite:///{db_pad}")
    metadata.create_all(sync_engine)
    with sync_engine.begin() as conn:
        for bwb_id, naam in _SEED_WETTEN:
            conn.execute(
                text(
                    "INSERT INTO wet_catalogus (bwb_id, naam, bijgewerkt_door, bijgewerkt) "
                    "VALUES (:bwb_id, :naam, '', '2026-01-01T00:00:00+00:00')"
                ),
                {"bwb_id": bwb_id, "naam": naam},
            )
    sync_engine.dispose()


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    db_pad = tmp_path / "test.db"
    _maak_db(db_pad)

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
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
    db_pad = tmp_path / "leeg.db"

    from sqlalchemy import create_engine

    sync_engine = create_engine(f"sqlite:///{db_pad}")
    metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    store = DatabaseWetcatalogusStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-test"
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_gebruiker, None)
    app.dependency_overrides.pop(huidige_beheerder, None)
