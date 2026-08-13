"""Auth-grenzen: routes die `huidige_beheerder` vereisen, mogen nooit bereikbaar zijn
zonder geldig Bearer-token. Gelukkig pad (geldige credentials) wordt getest via de
berichten-tests (dependency-override); hier staan uitsluitend de foutpaden.

Tests draaien zonder draaiende Keycloak — de dependency-override is hier bewust NIET
gezet, zodat `huidige_beheerder` de echte JWKS-verificatie uitvoert. Bij een ontbrekend
of misvormd token faalt de verificatie vóórdat `_haal_jwks_op` wordt aangeroepen.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client_zonder_auth_override() -> TestClient:
    """Client zonder dependency-override op huidige_beheerder — test de echte auth-grens."""
    with TestClient(app) as c:
        yield c


def test_admin_bericht_zonder_token_geeft_401(client_zonder_auth_override):
    response = client_zonder_auth_override.get("/v1/admin/berichten")
    assert response.status_code == 401
    assert response.json()["detail"] == "Niet geautoriseerd."


def test_admin_bericht_met_misvormd_token_geeft_401(client_zonder_auth_override):
    response = client_zonder_auth_override.get(
        "/v1/admin/berichten",
        headers={"Authorization": "Bearer dit-is-geen-geldig-jwt"},
    )
    assert response.status_code == 401
    assert "ongeldig token" in response.json()["detail"].lower()


def test_admin_bericht_aanmaken_zonder_token_geeft_401(client_zonder_auth_override):
    response = client_zonder_auth_override.post(
        "/v1/admin/berichten",
        json={"titel": "x", "inhoud": "y", "type": "info"},
    )
    assert response.status_code == 401
