"""Gedragstests voor het runtime_config-domein (feature-bouwen regel 6).

Alle tests gaan via de echte HTTP-laag (router + store + SQLite), zodat de acceptatiecriteria
van story 019 end-to-end gedekt zijn. Auth wordt overgeslagen via de conftest.py-override.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from app.features.runtime_config.models import metadata
from app.features.runtime_config.router import get_store
from app.features.runtime_config.store import RuntimeConfigStore, _cache_leeg
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER


@pytest.fixture(autouse=True)
def wis_cache():
    """Wis de module-niveau TTL-cache vóór elke test, zodat tests onafhankelijk zijn."""
    _cache_leeg()
    yield
    _cache_leeg()


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    db_pad = tmp_path / "test.db"

    sync_engine = create_engine(f"sqlite:///{db_pad}")
    metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
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


def test_ttl_cache_geeft_zelfde_object_terug_zonder_db_hit(client, tmp_path):
    """Na een GET is de cache gevuld; een tweede GET raakt de DB niet (module-niveau cache)."""
    # Vul de cache via de eerste GET.
    resp1 = client.get("/v1/admin/instellingen")
    assert resp1.status_code == 200

    # Schrijf direct in de DB via een synchrone engine, maar wis de cache NIET.
    # De cache is gevuld → GET geeft nog steeds de gecachte waarde (False) terug.
    import sqlite3

    db_pad = tmp_path / "test.db"
    con = sqlite3.connect(str(db_pad))
    con.execute(
        "INSERT OR REPLACE INTO app_instellingen (sleutel, waarde, bijgewerkt) "
        "VALUES ('capture_llm_calls', 'true', '2026-01-01T00:00:00+00:00')"
    )
    con.commit()
    con.close()

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

    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.features.runtime_config.models import metadata
    from app.features.runtime_config.router import get_store
    from app.features.runtime_config.store import RuntimeConfigStore
    from app.main import app

    db_pad = tmp_path / "auth_test.db"
    sync_engine = create_engine(f"sqlite:///{db_pad}")
    metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    store = RuntimeConfigStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    # Geen huidige_beheerder-override → echte auth-check actief.

    with TestClient(app) as client_no_auth:
        resp = client_no_auth.get("/v1/admin/instellingen")
        assert resp.status_code == 401

    app.dependency_overrides.pop(get_store, None)
    importlib.reload(auth_module)
