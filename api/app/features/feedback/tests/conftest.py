"""Testfixtures voor het feedback-domein.

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

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from app.features.feedback.models import metadata
from app.features.feedback.router import get_store
from app.features.feedback.store import SqlAlchemyFeedbackStore
from app.main import app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    db_pad = tmp_path / "test.db"

    sync_engine = create_engine(f"sqlite:///{db_pad}")
    metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    store = SqlAlchemyFeedbackStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
