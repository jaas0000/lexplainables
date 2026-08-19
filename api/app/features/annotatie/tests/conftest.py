"""Testfixtures voor het annotatie-domein.

Elke test krijgt een eigen, kortlevende SQLite-database (bestand in `tmp_path`, niet in-memory:
een async engine met meerdere verbindingen naar hetzelfde in-memory-bestand deelt anders geen
state). Het schema wordt opgezet met een synchrone engine (`metadata.create_all`) — dat vermijdt
event-loop-koppeling vooraf; de async engine opent zijn verbindingen pas tijdens de requests die
de TestClient uitvoert.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from app.features.annotatie.models import metadata
from app.features.annotatie.router import get_store
from app.features.annotatie.store import SqlAlchemyAnnotatieStore
from app.main import app
from app.shared.auth import huidige_gebruiker

GEBRUIKER_A = "analist-A"
GEBRUIKER_B = "analist-B"


@pytest.fixture
def db_pad(tmp_path: Path) -> Path:
    return tmp_path / "test_annotatie.db"


@pytest.fixture
def client(db_pad: Path) -> Iterator[TestClient]:
    sync_engine = create_engine(f"sqlite:///{db_pad}")
    metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    store = SqlAlchemyAnnotatieStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_gebruiker] = lambda: GEBRUIKER_A

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_gebruiker, None)
