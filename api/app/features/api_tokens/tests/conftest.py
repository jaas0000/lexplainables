"""Testfixtures voor het api_tokens-domein.

Elke test krijgt een schoon schema op de gedeelde Postgres-testserver (ADR-0003). De router
leunt op de store-abstractie (werkwijze-ADR-0007): deze fixture overschrijft `get_store`, de
routercode blijft ongewijzigd.

Voor de auth-integratietest is er een aparte `auth_client`-fixture die `db._engine` patchet
zodat `vereist_api_token` dezelfde engine gebruikt als de test-store.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.features.api_tokens.models import metadata
from app.features.api_tokens.router import get_store
from app.features.api_tokens.store import SqlAlchemyApiTokenStore
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER, maak_test_engine


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    """Standaard fixture — huidige_beheerder en get_store zijn geoverrideerd."""
    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = SqlAlchemyApiTokenStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)


@pytest.fixture
def auth_client(tmp_path, monkeypatch) -> Iterator[tuple[TestClient, SqlAlchemyApiTokenStore]]:
    """Auth-integratietest fixture — huidige_beheerder is NIET geoverrideerd.

    `db._engine` wordt gepatchet zodat `vereist_api_token` dezelfde engine gebruikt als de
    test-store. API_TOKEN wordt leeggemaakt zodat de statische check niet slaagt.
    """
    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = SqlAlchemyApiTokenStore(async_engine)

    # Zorg dat get_store in de router ook de test-engine gebruikt (voor de token-aanmaak via API).
    app.dependency_overrides[get_store] = lambda: store

    # Patch de globale engine zodat vereist_api_token dezelfde DB gebruikt.
    monkeypatch.setattr(db_module, "_engine", async_engine)

    # Wis statisch token zodat de DB-check het overnemen.
    monkeypatch.setattr("app.shared.auth.API_TOKEN", "")

    with TestClient(app) as test_client:
        yield test_client, store

    app.dependency_overrides.pop(get_store, None)
