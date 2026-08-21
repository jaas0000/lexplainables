"""Testfixtures voor de jobstore.

Elke test krijgt een schoon schema op de gedeelde Postgres-testserver (ADR-0003). De store
werkt direct tegen de async engine — geen router, dus geen `TestClient`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from app.shared.jobs.models import metadata
from app.shared.jobs.store import PostgresJobStore
from conftest import maak_test_engine


@pytest_asyncio.fixture
async def store(tmp_path) -> AsyncIterator[PostgresJobStore]:
    async_engine: AsyncEngine = maak_test_engine(metadata, tmp_path=tmp_path)
    yield PostgresJobStore(async_engine)
    await async_engine.dispose()
