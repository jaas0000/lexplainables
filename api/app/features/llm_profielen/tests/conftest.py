"""Testfixtures voor het llm_profielen-domein.

Elke test krijgt een schoon schema op de gedeelde Postgres-testserver (ADR-0003).
`FERNET_KEY_FILE` wordt via `monkeypatch.setenv` (wijzend naar een `tmp_path`-bestand) gezet
per test die encryptie nodig heeft.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.features.llm_profielen.models import metadata
from app.features.llm_profielen.router import get_store
from app.features.llm_profielen.store import SqlAlchemyLlmProfielenStore
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER, maak_test_engine


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = SqlAlchemyLlmProfielenStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)
