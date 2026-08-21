"""Gedragstests voor het llm_profielen-domein (feature-bouwen regel 6).

Alle tests gaan via de echte HTTP-laag (router + store + Postgres), zodat de acceptatiecriteria
van story 011 end-to-end gedekt zijn. Auth wordt overgeslagen via de conftest.py-override.
"""

from __future__ import annotations

# Een geldige Fernet-key voor tests die versleuteling raken.
TEST_FERNET_KEY = "pHJH9BfOH6gWMJGBpD2bBRHpJE9hCVs0iiqHWH8Xm0k="

BASIS = {
    "naam": "test-profiel",
    "provider": "openai",
    "model": "gpt-4o",
    "api_base": "https://api.openai.com/v1",
}


def _maak(client, naam: str = "test-profiel", **extra) -> dict:
    body = {**BASIS, "naam": naam, **extra}
    response = client.post("/v1/admin/profielen", json=body)
    assert response.status_code == 201, response.json()
    return response.json()


# --- Lijst ophalen -----------------------------------------------------------------


def test_lijst_leeg(client):
    resp = client.get("/v1/admin/profielen")
    assert resp.status_code == 200
    assert resp.json() == []


def test_lijst_gevuld(client):
    _maak(client, "profiel-a")
    _maak(client, "profiel-b")
    resp = client.get("/v1/admin/profielen")
    assert resp.status_code == 200
    namen = [p["naam"] for p in resp.json()]
    assert "profiel-a" in namen
    assert "profiel-b" in namen


# --- Aanmaken -----------------------------------------------------------------------


def test_aanmaken_succesvol(client):
    p = _maak(client, temperatuur=0.2, api_versie="2024-01")
    assert p["naam"] == "test-profiel"
    assert p["provider"] == "openai"
    assert p["model"] == "gpt-4o"
    assert p["temperatuur"] == 0.2
    assert p["api_versie"] == "2024-01"
    assert p["sleutel_ingesteld"] is False
    assert p["is_standaard"] is False


def test_aanmaken_zonder_sleutel_geeft_sleutel_ingesteld_false(client):
    p = _maak(client)
    assert p["sleutel_ingesteld"] is False


def test_aanmaken_met_sleutel_geeft_sleutel_ingesteld_true(monkeypatch, client):
    monkeypatch.setenv("FERNET_KEY", TEST_FERNET_KEY)
    # Reset de lru_cache zodat de nieuwe envvar wordt opgepikt.
    from app.shared import crypto

    crypto._fernet.cache_clear()

    p = _maak(client, api_sleutel="geheime-api-sleutel")
    assert p["sleutel_ingesteld"] is True
    assert "api_sleutel" not in p  # plaintext verlaat de API nooit

    crypto._fernet.cache_clear()


def test_naam_conflict_geeft_409(client):
    _maak(client, "dubbel")
    resp = client.post("/v1/admin/profielen", json={**BASIS, "naam": "dubbel"})
    assert resp.status_code == 409


# --- Bijwerken ----------------------------------------------------------------------


def test_bijwerken_succesvol(client):
    _maak(client)
    resp = client.put(
        "/v1/admin/profielen/test-profiel",
        json={
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "api_base": "https://api.anthropic.com",
            "temperatuur": 0.5,
            "is_standaard": False,
        },
    )
    assert resp.status_code == 200
    bijgewerkt = resp.json()
    assert bijgewerkt["provider"] == "anthropic"
    assert bijgewerkt["model"] == "claude-3-5-sonnet"
    assert bijgewerkt["temperatuur"] == 0.5


def test_bijwerken_lege_sleutel_laat_bestaande_ongewijzigd(monkeypatch, client):
    monkeypatch.setenv("FERNET_KEY", TEST_FERNET_KEY)
    from app.shared import crypto

    crypto._fernet.cache_clear()

    _maak(client, api_sleutel="originele-sleutel")
    assert client.get("/v1/admin/profielen").json()[0]["sleutel_ingesteld"] is True

    # Bijwerken zonder api_sleutel → sleutel_ingesteld blijft True.
    resp = client.put(
        "/v1/admin/profielen/test-profiel",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "api_base": "https://api.openai.com/v1",
            "temperatuur": 0.0,
            "is_standaard": False,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["sleutel_ingesteld"] is True

    crypto._fernet.cache_clear()


def test_bijwerken_onbekende_naam_geeft_404(client):
    resp = client.put(
        "/v1/admin/profielen/bestaat-niet",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "api_base": "https://api.openai.com/v1",
            "temperatuur": 0.0,
            "is_standaard": False,
        },
    )
    assert resp.status_code == 404


def test_is_standaard_flip_bij_bijwerken(client):
    _maak(client, "profiel-a", is_standaard=True)
    _maak(client, "profiel-b", is_standaard=False)

    # profiel-b instellen als standaard → profiel-a verliest standaard.
    resp = client.put(
        "/v1/admin/profielen/profiel-b",
        json={
            "provider": "openai",
            "model": "gpt-4o",
            "api_base": "https://api.openai.com/v1",
            "temperatuur": 0.0,
            "is_standaard": True,
        },
    )
    assert resp.status_code == 200

    profielen = {p["naam"]: p for p in client.get("/v1/admin/profielen").json()}
    assert profielen["profiel-b"]["is_standaard"] is True
    assert profielen["profiel-a"]["is_standaard"] is False


def test_is_standaard_flip_bij_aanmaken(client):
    _maak(client, "profiel-a", is_standaard=True)
    _maak(client, "profiel-b", is_standaard=True)

    profielen = {p["naam"]: p for p in client.get("/v1/admin/profielen").json()}
    assert profielen["profiel-b"]["is_standaard"] is True
    assert profielen["profiel-a"]["is_standaard"] is False


# --- Verwijderen --------------------------------------------------------------------


def test_verwijderen_succesvol(client):
    _maak(client, "te-verwijderen")
    _maak(client, "blijft-staan")

    resp = client.delete("/v1/admin/profielen/te-verwijderen")
    assert resp.status_code == 204

    namen = [p["naam"] for p in client.get("/v1/admin/profielen").json()]
    assert "te-verwijderen" not in namen
    assert "blijft-staan" in namen


def test_verwijderen_enige_profiel_geeft_409(client):
    _maak(client, "enige")
    resp = client.delete("/v1/admin/profielen/enige")
    assert resp.status_code == 409


def test_verwijderen_onbekende_naam_geeft_404(client):
    _maak(client, "bestaat")
    _maak(client, "ook-bestaat")
    resp = client.delete("/v1/admin/profielen/bestaat-niet")
    assert resp.status_code == 404


# --- Auth --------------------------------------------------------------------------


def test_zonder_auth_geeft_401(monkeypatch, tmp_path):
    """Zonder geldig API-token → 401.

    `auth.py` geeft 503 als `API_TOKEN` helemaal niet geconfigureerd is (fail-closed) en 401
    als het token ontbreekt of onjuist is. We zetten een token in de omgeving en sturen het
    request zonder Authorization-header — dat is het echte niet-geautoriseerde scenario.
    """
    import importlib

    import app.shared.auth as auth_module

    monkeypatch.setenv("API_TOKEN", "test-token-voor-auth-check")
    # Herlaad de module-constante die bij import al gelezen is.
    importlib.reload(auth_module)

    from fastapi.testclient import TestClient

    from app.features.llm_profielen.models import metadata
    from app.features.llm_profielen.router import get_store
    from app.features.llm_profielen.store import SqlAlchemyLlmProfielenStore
    from app.main import app
    from conftest import maak_test_engine

    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = SqlAlchemyLlmProfielenStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    # Geen huidige_beheerder-override → echte auth-check actief.

    with TestClient(app) as client_no_auth:
        resp = client_no_auth.get("/v1/admin/profielen")
        assert resp.status_code == 401

    app.dependency_overrides.pop(get_store, None)
    importlib.reload(auth_module)  # herstel de originele staat
