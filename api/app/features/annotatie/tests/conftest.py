"""Testfixtures voor het annotatie-domein.

Elke test krijgt een eigen, kortlevende SQLite-database (bestand in `tmp_path`, niet in-memory:
een async engine met meerdere verbindingen naar hetzelfde in-memory-bestand deelt anders geen
state). Het schema wordt opgezet met een synchrone engine (`metadata.create_all`) — dat vermijdt
event-loop-koppeling vooraf; de async engine opent zijn verbindingen pas tijdens de requests die
de TestClient uitvoert.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.features.annotatie.models import metadata
from app.features.annotatie.router import get_store
from app.features.annotatie.store import SqlAlchemyAnnotatieStore
from app.main import app
from app.shared.auth import huidige_gebruiker
from conftest import maak_test_engine

GEBRUIKER_A = "analist-A"
GEBRUIKER_B = "analist-B"


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = SqlAlchemyAnnotatieStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_gebruiker] = lambda: GEBRUIKER_A

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_gebruiker, None)
