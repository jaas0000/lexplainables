"""Testfixtures voor het feedback-domein.

Elke test krijgt een schoon schema op de gedeelde Postgres-testserver (ADR-0003). Zie
`api/conftest.py` § `maak_test_engine` voor de implementatie (drop_all → create_all met NullPool
om verbindingsuitputting te voorkomen).

De router leunt op de store-abstractie (werkwijze-ADR-0007): deze fixture overschrijft alleen
`get_store`, de routercode zelf blijft ongewijzigd.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.features.feedback.models import metadata
from app.features.feedback.router import get_store
from app.features.feedback.store import SqlAlchemyFeedbackStore
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER, maak_test_engine


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = SqlAlchemyFeedbackStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)
