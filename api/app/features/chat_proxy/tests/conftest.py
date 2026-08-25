"""Testfixture voor de chat-proxy: geen database nodig (stateless doorgeefluik), dus alleen
`huidige_beheerder` wordt overridden — geen `async_engine`/`store`-fixture zoals bij de
DB-backed features."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(huidige_beheerder, None)
