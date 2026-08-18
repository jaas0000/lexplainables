"""Testfixtures voor het wetcatalogus-domein.

De store is stateloos (hardcoded data), dus er is geen database-fixture nodig.
De router-dependency `get_store` wordt overgeschreven met een verse instantie van
`HardgecodeerdeWetcatalogusStore` — de echte implementatie, geen fake. Zo blijft
gedrag gedekt zonder mock-specifieke testkennis.

`huidige_gebruiker` wordt overgeslagen via een override die een vaste gebruikersnaam
teruggeeft, zodat de auth-check niet afhankelijk is van headers in de tests.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.features.wetcatalogus.router import get_store
from app.features.wetcatalogus.store import HardgecodeerdeWetcatalogusStore
from app.main import app
from app.shared.auth import huidige_gebruiker


@pytest.fixture
def client() -> Iterator[TestClient]:
    store = HardgecodeerdeWetcatalogusStore()
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-test"

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_gebruiker, None)
