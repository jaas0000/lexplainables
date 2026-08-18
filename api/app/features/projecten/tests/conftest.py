"""Testfixtures voor het projecten-domein.

Elke test krijgt een eigen, kortlevende SQLite-database (bestand in `tmp_path`). Het schema
wordt opgezet met een gewone synchrone engine; de async engine (aiosqlite) opent verbindingen
pas tijdens de requests die TestClient uitvoert.

`asyncio.sleep` in de router-module wordt gepatchd naar een no-op zodat de
achtergrond-job (`_voer_analyse_uit`) in tests in milliseconden afloopt in plaats van
seconden — de statusovergangen worden daarna direct via de store getest.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from app.features.projecten.models import metadata
from app.features.projecten.router import get_store
from app.features.projecten.store import SqlAlchemyAnalyseStore
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER


@pytest.fixture(autouse=True)
def versnelde_sleep(monkeypatch):
    """Patchet asyncio.sleep in de router naar een no-op zodat de background-job in tests
    vrijwel direct afloopt en tests niet onnodig vertragen."""

    async def instant_sleep(_seconds: float) -> None:
        pass

    monkeypatch.setattr("app.features.projecten.router.asyncio.sleep", instant_sleep)


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    db_pad = tmp_path / "test.db"

    sync_engine = create_engine(f"sqlite:///{db_pad}")
    metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    store = SqlAlchemyAnalyseStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)
