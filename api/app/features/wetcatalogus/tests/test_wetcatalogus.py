"""Gedragstests voor het wetcatalogus-domein (feature-bouwen regel 6).

Dekt de acceptatiecriteria uit story 010 (analist-routes) en story 020 (admin-CRUD + resolve).
Alle tests gaan via de echte HTTP-laag (router + store + SQLite).

Resolve-tests: `shared.wettenbank.haal_citeertitel_op` (geïmporteerd in de router-module)
wordt via monkeypatch gemockt zodat er geen echte MCP-server nodig is.
"""

from __future__ import annotations

# ============================================================================
# Story 010 — analist-routes (nu database-backed)
# ============================================================================


def test_lijst_wetten_geeft_drie_wetten(client):
    response = client.get("/v1/wetten")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    bwb_ids = [w["bwb_id"] for w in data]
    assert "BWBR0011823" in bwb_ids
    assert "BWBR0015703" in bwb_ids
    assert "BWBR0020183" in bwb_ids


def test_lijst_wetten_bevat_naam(client):
    response = client.get("/v1/wetten")
    assert response.status_code == 200
    wwb = next(w for w in response.json() if w["bwb_id"] == "BWBR0011823")
    assert wwb["naam"] == "Wet werk en bijstand"


def test_structuur_wwb_geeft_zes_artikelen(client):
    response = client.get("/v1/wetten/BWBR0011823/structuur")
    assert response.status_code == 200
    data = response.json()
    assert data["bwb_id"] == "BWBR0011823"
    assert len(data["artikelen"]) == 6


def test_structuur_onbekend_bwb_id_geeft_404(client):
    response = client.get("/v1/wetten/ONBEKEND9999/structuur")
    assert response.status_code == 404


def test_lege_wettenlijst(lege_client):
    response = lege_client.get("/v1/wetten")
    assert response.status_code == 200
    assert response.json() == []


# ============================================================================
# Story 020 — admin-routes: lijst met metadata
# ============================================================================


def test_admin_lijst_bevat_metadata(client):
    resp = client.get("/v1/admin/wetten")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    item = next(i for i in items if i["bwb_id"] == "BWBR0011823")
    assert item["naam"] == "Wet werk en bijstand"
    assert "bijgewerkt_door" in item
    assert "bijgewerkt" in item


def test_admin_lijst_leeg(lege_client):
    resp = lege_client.get("/v1/admin/wetten")
    assert resp.status_code == 200
    assert resp.json() == []


# ============================================================================
# Story 020 — admin-routes: upsert (PUT)
# ============================================================================


def test_upsert_nieuwe_wet(lege_client):
    resp = lege_client.put(
        "/v1/admin/wetten/BWBR0099999",
        json={"bwb_id": "BWBR0099999", "naam": "Testwet"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["bwb_id"] == "BWBR0099999"
    assert data["naam"] == "Testwet"
    assert data["bijgewerkt_door"] == "beheerder-test"


def test_upsert_bestaande_wet_werkt_bij(client):
    resp = client.put(
        "/v1/admin/wetten/BWBR0011823",
        json={"bwb_id": "BWBR0011823", "naam": "Nieuwe naam voor WWB"},
    )
    assert resp.status_code == 200
    assert resp.json()["naam"] == "Nieuwe naam voor WWB"

    # Controleer dat de lijst is bijgewerkt.
    lijst = client.get("/v1/admin/wetten").json()
    item = next(i for i in lijst if i["bwb_id"] == "BWBR0011823")
    assert item["naam"] == "Nieuwe naam voor WWB"


def test_upsert_lege_naam_geeft_422(lege_client):
    resp = lege_client.put(
        "/v1/admin/wetten/BWBR0099999",
        json={"bwb_id": "BWBR0099999", "naam": ""},
    )
    assert resp.status_code == 422


def test_upsert_tweemaal_dezelfde_wet_werkt(lege_client):
    """Dubbele PUT is idempotent (upsert)."""
    lege_client.put("/v1/admin/wetten/BWBR0001", json={"bwb_id": "BWBR0001", "naam": "Wet A"})
    resp = lege_client.put(
        "/v1/admin/wetten/BWBR0001", json={"bwb_id": "BWBR0001", "naam": "Wet A bijgewerkt"}
    )
    assert resp.status_code == 200
    assert resp.json()["naam"] == "Wet A bijgewerkt"


# ============================================================================
# Story 020 — admin-routes: verwijderen (DELETE)
# ============================================================================


def test_verwijder_bekende_wet(client):
    resp = client.delete("/v1/admin/wetten/BWBR0011823")
    assert resp.status_code == 204

    lijst = client.get("/v1/admin/wetten").json()
    bwb_ids = [i["bwb_id"] for i in lijst]
    assert "BWBR0011823" not in bwb_ids


def test_verwijder_onbekend_bwb_id_geeft_404(client):
    resp = client.delete("/v1/admin/wetten/BESTAAT_NIET")
    assert resp.status_code == 404


# ============================================================================
# Story 020 — admin-routes: resolve
# ============================================================================


def test_resolve_succesvol(client, monkeypatch):
    import app.features.wetcatalogus.router as router_mod

    async def _mock_mcp(bwb_id: str) -> str:
        return "Wet werk en bijstand"

    monkeypatch.setattr(router_mod, "haal_citeertitel_op", _mock_mcp)
    resp = client.post("/v1/admin/wetten/BWBR0011823/resolve")
    assert resp.status_code == 200
    assert resp.json()["naam"] == "Wet werk en bijstand"


def test_resolve_mcp_niet_bereikbaar_geeft_502(client, monkeypatch):
    import app.features.wetcatalogus.router as router_mod
    from app.shared.wettenbank import WettenbankNietBereikbaar

    async def _mock_mcp(bwb_id: str) -> str:
        raise WettenbankNietBereikbaar("Wettenbank niet bereikbaar voor test")

    monkeypatch.setattr(router_mod, "haal_citeertitel_op", _mock_mcp)
    resp = client.post("/v1/admin/wetten/BWBR0011823/resolve")
    assert resp.status_code == 502
    assert "niet bereikbaar" in resp.json()["detail"]


def test_resolve_wet_onbekend_bij_mcp_geeft_404(client, monkeypatch):
    import app.features.wetcatalogus.router as router_mod
    from app.shared.wettenbank import WettenbankNietGevonden

    async def _mock_mcp(bwb_id: str) -> str:
        raise WettenbankNietGevonden("Wet niet gevonden in de Wettenbank.")

    monkeypatch.setattr(router_mod, "haal_citeertitel_op", _mock_mcp)
    resp = client.post("/v1/admin/wetten/BWBR9999999/resolve")
    assert resp.status_code == 404
    assert "Wettenbank" in resp.json()["detail"]


# ============================================================================
# Auth
# ============================================================================


def test_admin_zonder_auth_geeft_401(monkeypatch, tmp_path):
    """Admin-endpoints geven 401 terug als de auth-dependency niet is overgeslagen."""
    import importlib

    import app.shared.auth as auth_module

    monkeypatch.setenv("API_TOKEN", "test-token-voor-auth-check")
    importlib.reload(auth_module)

    from fastapi.testclient import TestClient

    from app.features.wetcatalogus.models import metadata
    from app.features.wetcatalogus.router import get_store
    from app.features.wetcatalogus.store import DatabaseWetcatalogusStore
    from app.main import app
    from conftest import maak_test_engine

    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = DatabaseWetcatalogusStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    # Geen huidige_beheerder-override → echte auth actief.

    with TestClient(app) as c:
        resp = c.get("/v1/admin/wetten")
        assert resp.status_code == 401

    app.dependency_overrides.pop(get_store, None)
    importlib.reload(auth_module)
