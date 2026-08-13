"""Testfixtures voor het berichten-domein.

Elke test krijgt een eigen, kortlevende SQLite-database (een bestand in `tmp_path`, niet
in-memory: een async engine met meerdere verbindingen naar hetzelfde in-memory-bestand deelt
anders geen state). Het schema wordt opgezet met een gewone SYNCHRONE engine
(`metadata.create_all`) — dat vermijdt elke event-loop-koppeling vooraf; de ASYNC engine (met
aiosqlite, zoals de app 'm ook gebruikt) opent zijn verbindingen pas tijdens de requests die de
TestClient zelf uitvoert.

De router leunt op de store-abstractie (werkwijze-ADR-0007): deze fixture overschrijft alleen
`get_store`, de routercode zelf blijft ongewijzigd.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from app.features.berichten.models import metadata
from app.features.berichten.router import get_store
from app.features.berichten.store import SqlAlchemyBerichtenStore
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER


@pytest.fixture
def db_pad(tmp_path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def client(db_pad) -> Iterator[TestClient]:
    sync_engine = create_engine(f"sqlite:///{db_pad}")
    metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    store = SqlAlchemyBerichtenStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)
