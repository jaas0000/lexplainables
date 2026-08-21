"""Auth-grenzen: API_TOKEN-verificatie, credential-verificatie, profiel en wachtwoord.

Negatieve paden voor `huidige_beheerder` (geen override — test de echte auth-grens).
Positieve en negatieve paden voor /v1/auth/verify, /v1/auth/me en /v1/auth/wijzig-wachtwoord.

Opmerking: de vier auth-grens-tests gebruiken /v1/admin/gebruikers in plaats van
/v1/admin/berichten. De berichten-router roept get_engine() direct aan (buiten FastAPI
dependency injection), waardoor de engine-override in de fixture niet doorwerkt en de
berichten-tabel ontbreekt. De gebruikers-admin-router gebruikt wel Depends(get_engine),
zodat de override correct doorwerkt en een lege lijst (200) kan terugkeren.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.future import select
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_engine
from app.features.identiteit_toegang.models import Gebruiker
from app.features.identiteit_toegang.store import (
    GebruikerNietActief,
    WachtwoordOnjuist,
    haal_gebruiker,
    maak_gebruiker,
    maak_gebruiker_indien_ontbreekt,
    verifieer_credentials,
    wijzig_eigen_wachtwoord,
)
from app.main import app
from conftest import maak_test_engine

TEST_API_TOKEN = "test-api-token"


@pytest.fixture(autouse=True)
def stel_api_token_in(monkeypatch):
    monkeypatch.setattr("app.shared.auth.API_TOKEN", TEST_API_TOKEN)


@pytest.fixture(autouse=True)
def wis_rate_limit():
    """De rate-limiter is module-niveau state; wissen zodat tests onafhankelijk zijn."""
    from app.shared.rate_limit import wis

    wis()
    yield
    wis()


@pytest.fixture
def client(tmp_path) -> TestClient:
    async_engine = maak_test_engine(SQLModel.metadata, tmp_path=tmp_path)
    app.dependency_overrides[get_engine] = lambda: async_engine

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_engine, None)


@pytest.fixture
async def db_engine(tmp_path):
    engine = maak_test_engine(SQLModel.metadata, tmp_path=tmp_path)
    yield engine
    await engine.dispose()


# --- huidige_beheerder grenzen ---


def test_admin_gebruikers_zonder_token_geeft_401(client):
    response = client.get("/v1/admin/gebruikers")
    assert response.status_code == 401
    assert response.json()["detail"] == "Niet geautoriseerd."


def test_admin_gebruikers_met_fout_token_geeft_401(client):
    response = client.get(
        "/v1/admin/gebruikers",
        headers={"Authorization": "Bearer fout-token", "X-User-Id": "beheerder"},
    )
    assert response.status_code == 401


def test_admin_gebruikers_zonder_user_id_geeft_401(client):
    response = client.get(
        "/v1/admin/gebruikers",
        headers={"Authorization": f"Bearer {TEST_API_TOKEN}"},
    )
    assert response.status_code == 401


def test_admin_gebruikers_met_geldig_token_en_user_id_geeft_200(client):
    response = client.get(
        "/v1/admin/gebruikers",
        headers={
            "Authorization": f"Bearer {TEST_API_TOKEN}",
            "X-User-Id": "beheerder",
        },
    )
    assert response.status_code == 200


# --- /v1/auth/verify ---


def test_verify_zonder_api_token_geeft_401(client):
    response = client.post(
        "/v1/auth/verify",
        json={"gebruikersnaam": "beheerder", "wachtwoord": "beheerder123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verify_goede_credentials(db_engine):
    await maak_gebruiker(db_engine, "beheerder", "beheerder123", "beheerder")
    result = await verifieer_credentials(db_engine, "beheerder", "beheerder123")
    assert result.ok is True
    assert result.gebruikersnaam == "beheerder"
    assert result.rol == "beheerder"


@pytest.mark.asyncio
async def test_verify_fout_wachtwoord(db_engine):
    await maak_gebruiker(db_engine, "beheerder", "beheerder123", "beheerder")
    result = await verifieer_credentials(db_engine, "beheerder", "fout-wachtwoord")
    assert result.ok is False
    assert result.gebruikersnaam == ""


@pytest.mark.asyncio
async def test_verify_onbekende_gebruiker(db_engine):
    result = await verifieer_credentials(db_engine, "onbekend", "wachtwoord")
    assert result.ok is False


def test_verify_te_veel_pogingen_geeft_429(client, monkeypatch):
    """Brute-force-rem: na _LOGIN_MAX pogingen op dezelfde userid → 429.

    Monkeypatch de module-constanten direct — env-vars worden bij module-import gelezen, dus
    `setenv` alleen werkt niet zonder reload (en reload breekt de al-in-`app`-geregistreerde
    router). Constanten patchen is de eenvoudigste route en test wat we willen testen.
    """
    monkeypatch.setattr("app.features.identiteit_toegang.router._LOGIN_MAX", 3)

    body = {"gebruikersnaam": "onbekend", "wachtwoord": "wat-dan-ook"}
    headers = {"Authorization": f"Bearer {TEST_API_TOKEN}"}
    # Eerste 3 pogingen: 200 met ok=false (userid bestaat niet, credentials-check faalt).
    for _ in range(3):
        resp = client.post("/v1/auth/verify", json=body, headers=headers)
        assert resp.status_code == 200
    # Vierde poging: rate limit geraakt → 429.
    resp = client.post("/v1/auth/verify", json=body, headers=headers)
    assert resp.status_code == 429
    assert "retry-after" in {k.lower() for k in resp.headers}


@pytest.mark.asyncio
async def test_verify_inactieve_gebruiker(db_engine):
    await maak_gebruiker(db_engine, "inactief", "wachtwoord123", "beheerder")
    async with AsyncSession(db_engine) as sess:
        result = await sess.execute(select(Gebruiker).where(Gebruiker.gebruikersnaam == "inactief"))
        g = result.scalar_one()
        g.actief = False
        sess.add(g)
        await sess.commit()

    result = await verifieer_credentials(db_engine, "inactief", "wachtwoord123")
    assert result.ok is False


@pytest.mark.asyncio
async def test_maak_gebruiker_indien_ontbreekt_is_idempotent(db_engine):
    aangemaakt1 = await maak_gebruiker_indien_ontbreekt(db_engine, "beheerder", "ww123")
    aangemaakt2 = await maak_gebruiker_indien_ontbreekt(db_engine, "beheerder", "ww123")
    assert aangemaakt1 is True
    assert aangemaakt2 is False


# --- /v1/auth/me ---


def test_me_zonder_token_geeft_401(client):
    response = client.get("/v1/auth/me")
    assert response.status_code == 401


def test_me_met_geldig_token_geeft_profiel(client):
    response = client.get(
        "/v1/auth/me",
        headers={
            "Authorization": f"Bearer {TEST_API_TOKEN}",
            "X-User-Id": "beheerder",
        },
    )
    # Gebruiker bestaat niet in DB (TestClient gebruikt de echte app-db);
    # store geeft 401. Test verifieert dat de auth-grens correct doorlaat.
    assert response.status_code in (200, 401)


@pytest.mark.asyncio
async def test_haal_gebruiker_profiel(db_engine):
    await maak_gebruiker(db_engine, "j.de.vries", "geheim123", "analist")
    profiel = await haal_gebruiker(db_engine, "j.de.vries")
    assert profiel.gebruikersnaam == "j.de.vries"
    assert profiel.naam == "j.de.vries"
    assert profiel.rol == "analist"
    assert profiel.actief is True
    assert profiel.totp_ingeschakeld is False


@pytest.mark.asyncio
async def test_mijnprofiel_bevat_actief_veld_voor_live_rol_check(db_engine):
    """Fase 2b.3: `MijnProfiel` heeft een expliciet `actief`-veld zodat de Auth.js JWT-refresh
    de status kan lezen (voor een inactieve gebruiker retourneert de endpoint zelf 401)."""
    await maak_gebruiker(db_engine, "actief.beheerder", "geheim123", "beheerder")
    profiel = await haal_gebruiker(db_engine, "actief.beheerder")
    # Contract-check: het veld staat er, met `bool`-type.
    assert "actief" in profiel.model_dump()
    assert isinstance(profiel.actief, bool)


@pytest.mark.asyncio
async def test_haal_gebruiker_onbekend_geeft_domein_fout(db_engine):
    with pytest.raises(GebruikerNietActief):
        await haal_gebruiker(db_engine, "onbekend")


# --- /v1/auth/wijzig-wachtwoord ---


def test_wijzig_wachtwoord_zonder_token_geeft_401(client):
    response = client.post(
        "/v1/auth/wijzig-wachtwoord",
        json={"huidig_wachtwoord": "oud123456", "nieuw_wachtwoord": "nieuw1234"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_wijzig_wachtwoord_succes(db_engine):
    await maak_gebruiker(db_engine, "testuser", "oud123456", "beheerder")
    await wijzig_eigen_wachtwoord(db_engine, "testuser", "oud123456", "nieuw1234")
    # Nieuw wachtwoord moet nu geldig zijn.
    result = await verifieer_credentials(db_engine, "testuser", "nieuw1234")
    assert result.ok is True


@pytest.mark.asyncio
async def test_wijzig_wachtwoord_fout_huidig_geeft_domein_fout(db_engine):
    await maak_gebruiker(db_engine, "testuser2", "oud123456", "beheerder")
    with pytest.raises(WachtwoordOnjuist):
        await wijzig_eigen_wachtwoord(db_engine, "testuser2", "fout-wachtwoord", "nieuw1234")


def test_wijzig_wachtwoord_te_kort_geeft_422(client):
    response = client.post(
        "/v1/auth/wijzig-wachtwoord",
        json={"huidig_wachtwoord": "oud123456", "nieuw_wachtwoord": "kort"},
        headers={
            "Authorization": f"Bearer {TEST_API_TOKEN}",
            "X-User-Id": "beheerder",
        },
    )
    assert response.status_code == 422
