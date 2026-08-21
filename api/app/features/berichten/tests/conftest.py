"""Testfixtures voor het berichten-domein.

Elke test krijgt een schoon schema op de gedeelde Postgres-testserver (ADR-0003). De router
leunt op de store-abstractie (werkwijze-ADR-0007): deze fixture overschrijft alleen
`get_store`, de routercode zelf blijft ongewijzigd.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.features.berichten.models import metadata
from app.features.berichten.router import get_store
from app.features.berichten.store import SqlAlchemyBerichtenStore
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER, maak_test_engine


@pytest.fixture
def async_engine(tmp_path) -> AsyncEngine:
    return maak_test_engine(metadata, tmp_path=tmp_path)


@pytest.fixture
def client(async_engine: AsyncEngine) -> Iterator[TestClient]:
    store = SqlAlchemyBerichtenStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)
