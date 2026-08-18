"""Gedragstests voor het wetcatalogus-domein (feature-bouwen regel 6: gedrag, niet vorm).

Dekt de acceptatiecriteria uit docs/stories/010-wetcatalogus.md:
- lijst van beschikbare wetten (bwb-id + naam)
- artikel-structuur van een bekende wet
- 404 bij een onbekend bwb_id
- lege wettenlijst-edge case (via een aparte store-stub)
- wet zonder artikelen (randgeval: geen crash, lege lijst)
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.features.wetcatalogus.models import WetKeuze
from app.features.wetcatalogus.router import get_store
from app.features.wetcatalogus.store import WetStructuur
from app.main import app
from app.shared.auth import huidige_gebruiker

# --- gelukkig pad -----------------------------------------------------------


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
    nummers = [a["artikel"] for a in data["artikelen"]]
    assert "1" in nummers
    assert "31" in nummers


def test_structuur_bevat_pad(client):
    response = client.get("/v1/wetten/BWBR0020183/structuur")
    assert response.status_code == 200
    artikel_8a = next(a for a in response.json()["artikelen"] if a["artikel"] == "8a")
    assert artikel_8a["pad"] == "Hoofdstuk 2 / Artikel 8a"


# --- foutpad ----------------------------------------------------------------


def test_structuur_onbekend_bwb_id_geeft_404(client):
    response = client.get("/v1/wetten/ONBEKEND9999/structuur")
    assert response.status_code == 404


# --- edge cases -------------------------------------------------------------


def test_lege_wettenlijst():
    """Lege catalogus geeft een lege array terug (geen crash)."""

    class LegeStore:
        async def lijst(self):
            return []

        async def structuur(self, bwb_id):
            from app.features.wetcatalogus.store import WetNietGevonden

            raise WetNietGevonden(bwb_id)

    app.dependency_overrides[get_store] = lambda: LegeStore()
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-test"
    with TestClient(app) as c:
        response = c.get("/v1/wetten")
    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_gebruiker, None)

    assert response.status_code == 200
    assert response.json() == []


def test_wet_zonder_artikelen():
    """Wet met een lege artikellijst: geen crash, lege `artikelen`."""

    class WetZonderArtikelen:
        async def lijst(self):
            return [WetKeuze(bwb_id="BWBR0000001", naam="Lege testwet")]

        async def structuur(self, bwb_id):
            return WetStructuur(bwb_id=bwb_id, artikelen=[])

    app.dependency_overrides[get_store] = lambda: WetZonderArtikelen()
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-test"
    with TestClient(app) as c:
        response = c.get("/v1/wetten/BWBR0000001/structuur")
    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_gebruiker, None)

    assert response.status_code == 200
    assert response.json()["artikelen"] == []
