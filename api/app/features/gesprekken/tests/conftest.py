"""Testfixtures voor het gesprekken-domein.

Elke test krijgt een schoon schema op de gedeelde Postgres-testserver (ADR-0003). Zie
`api/conftest.py` § `maak_test_engine` voor de implementatie.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.features.gesprekken.models import metadata
from app.features.gesprekken.router import get_store
from app.features.gesprekken.store import SqlAlchemyGesprekStore
from app.main import app
from app.shared.auth import GebruikerContext, huidige_beheerder
from conftest import maak_test_engine

GEBRUIKER_A = GebruikerContext(gebruikersnaam="jurist-a", rol="beheerder")
GEBRUIKER_B = GebruikerContext(gebruikersnaam="jurist-b", rol="beheerder")


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = SqlAlchemyGesprekStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_beheerder] = lambda: GEBRUIKER_A

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)
