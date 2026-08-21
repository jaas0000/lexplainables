"""Testfixtures voor het projecten-domein.

Elke test krijgt een schoon schema op de gedeelde Postgres-testserver (ADR-0003) met zowel
projecten- als llm_calls-tabellen (samen gebruikt in dezelfde tests).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.features.llm_calls.dependencies import get_llm_calls_store
from app.features.llm_calls.models import metadata as llm_calls_metadata
from app.features.llm_calls.store import SqlAlchemyLlmCallsStore
from app.features.projecten.models import metadata
from app.features.projecten.router import get_store
from app.features.projecten.store import SqlAlchemyAnalyseStore
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER, maak_test_engine


@pytest.fixture
def async_engine(tmp_path) -> AsyncEngine:
    """Async engine met projecten- én llm_calls-schema (dezelfde DB, beide tabellen nodig)."""
    return maak_test_engine(metadata, llm_calls_metadata, tmp_path=tmp_path)


@pytest.fixture
def store(async_engine: AsyncEngine) -> SqlAlchemyAnalyseStore:
    return SqlAlchemyAnalyseStore(async_engine)


@pytest.fixture
def client(store: SqlAlchemyAnalyseStore, async_engine: AsyncEngine) -> Iterator[TestClient]:
    llm_store = SqlAlchemyLlmCallsStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_llm_calls_store] = lambda: llm_store
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(get_llm_calls_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)
