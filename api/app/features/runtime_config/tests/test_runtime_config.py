"""Gedragstests voor het runtime_config-domein (feature-bouwen regel 6).

Alle tests gaan via de echte HTTP-laag (router + store + Postgres), zodat de acceptatiecriteria
van story 019 end-to-end gedekt zijn. Auth wordt overgeslagen via de conftest.py-override.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.features.runtime_config.models import metadata
from app.features.runtime_config.router import get_store
from app.features.runtime_config.store import RuntimeConfigStore, _cache_leeg
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER, maak_test_engine, sync_engine_voor


@pytest.fixture(autouse=True)
def wis_cache():
    """Wis de module-niveau TTL-cache vóór elke test, zodat tests onafhankelijk zijn."""
    _cache_leeg()
    yield
    _cache_leeg()


@pytest.fixture
def async_engine(tmp_path) -> AsyncEngine:
    return maak_test_engine(metadata, tmp_path=tmp_path)


@pytest.fixture
def client(async_engine: AsyncEngine) -> Iterator[TestClient]:
    store = RuntimeConfigStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)


# --- Standaardwaarden lezen --------------------------------------------------------


def test_lees_defaults_zonder_rijen_in_db(client):
    """Ontbrekende rijen → standaardwaarden; geen fout."""
    resp = client.get("/v1/admin/instellingen")
    assert resp.status_code == 200
    data = resp.json()
    assert data["capture_llm_calls"] is False


# --- Schrijven + lezen -----------------------------------------------------------


def test_schrijf_en_lees_capture_llm_calls_aan(client):
    resp = client.put("/v1/admin/instellingen", json={"capture_llm_calls": True})
    assert resp.status_code == 200
    assert resp.json()["capture_llm_calls"] is True

    resp2 = client.get("/v1/admin/instellingen")
    assert resp2.json()["capture_llm_calls"] is True


def test_schrijf_en_lees_capture_llm_calls_uit(client):
    # Zet aan, dan uit.
    client.put("/v1/admin/instellingen", json={"capture_llm_calls": True})
    _cache_leeg()
    resp = client.put("/v1/admin/instellingen", json={"capture_llm_calls": False})
    assert resp.status_code == 200
    assert resp.json()["capture_llm_calls"] is False


# --- TTL-cache -------------------------------------------------------------------


def test_ttl_cache_geeft_zelfde_object_terug_zonder_db_hit(client, async_engine):
    """Na een GET is de cache gevuld; een tweede GET raakt de DB niet (module-niveau cache)."""
    # Vul de cache via de eerste GET.
    resp1 = client.get("/v1/admin/instellingen")
    assert resp1.status_code == 200

    # Schrijf direct in de DB via een synchrone engine (dialect-agnostisch — update-dan-insert
    # via SQLAlchemy Core i.p.v. asyncpg direct — houdt de test simpel), maar wis
    # de cache NIET. De cache is gevuld → GET geeft nog steeds de gecachte waarde (False).
    sync = sync_engine_voor(async_engine)
    with sync.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE app_instellingen SET waarde = :waarde, bijgewerkt = :bijgewerkt "
                "WHERE sleutel = 'capture_llm_calls'"
            ),
            {"waarde": "true", "bijgewerkt": "2026-01-01T00:00:00+00:00"},
        )
        if result.rowcount == 0:
            conn.execute(
                text(
                    "INSERT INTO app_instellingen (sleutel, waarde, bijgewerkt) "
                    "VALUES ('capture_llm_calls', :waarde, :bijgewerkt)"
                ),
                {"waarde": "true", "bijgewerkt": "2026-01-01T00:00:00+00:00"},
            )
    sync.dispose()

    # Cache nog actief → nog steeds False.
    resp2 = client.get("/v1/admin/instellingen")
    assert resp2.json()["capture_llm_calls"] is False

    # Na wissen van de cache → True (leest uit de DB).
    _cache_leeg()
    resp3 = client.get("/v1/admin/instellingen")
    assert resp3.json()["capture_llm_calls"] is True


# --- PUT met lege patch (geen mutatie) -------------------------------------------


def test_put_met_lege_patch_muteert_niet(client):
    """PUT met alleen null-velden → geen schrijfactie; huidige waarden blijven."""
    # Zet aan.
    client.put("/v1/admin/instellingen", json={"capture_llm_calls": True})
    _cache_leeg()

    # Lege patch (alle velden null) → huidige waarden ongewijzigd.
    resp = client.put("/v1/admin/instellingen", json={})
    assert resp.status_code == 200
    assert resp.json()["capture_llm_calls"] is True


# --- Auth -----------------------------------------------------------------------


def test_zonder_auth_geeft_401(monkeypatch, tmp_path):
    """Zonder geldig API-token → 401."""
    import importlib

    import app.shared.auth as auth_module

    monkeypatch.setenv("API_TOKEN", "test-token-voor-auth-check")
    importlib.reload(auth_module)

    from app.features.runtime_config.models import metadata
    from app.features.runtime_config.router import get_store
    from app.features.runtime_config.store import RuntimeConfigStore
    from app.main import app

    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = RuntimeConfigStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    # Geen huidige_beheerder-override → echte auth-check actief.

    with TestClient(app) as client_no_auth:
        resp = client_no_auth.get("/v1/admin/instellingen")
        assert resp.status_code == 401

    app.dependency_overrides.pop(get_store, None)
    importlib.reload(auth_module)
