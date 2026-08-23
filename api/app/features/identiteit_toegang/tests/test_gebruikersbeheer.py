"""Tests voor gebruikersbeheer-admin (story 014).

Dekt: lijst, aanmaken, rol wijzigen, actief wijzigen, wachtwoord-reset,
verwijderen, bescherming laatste beheerder.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app.db import get_engine
from app.features.identiteit_toegang.store import (
    GebruikerNietGevonden,
    GebruikersnaamAlInGebruik,
    LaatsteBeheerder,
    lijst_gebruikers,
    maak_gebruiker,
    maak_gebruiker_admin,
    reset_wachtwoord,
    verwijder_gebruiker,
    wijzig_gebruiker,
)
from app.main import app
from app.shared.auth import GebruikerContext, huidige_beheerder
from conftest import maak_test_engine

TEST_API_TOKEN = "test-token-014"
TEST_BEHEERDER = GebruikerContext(gebruikersnaam="beheerder-test", rol="beheerder")


@pytest.fixture(autouse=True)
def stel_api_token_in(monkeypatch):
    monkeypatch.setattr("app.shared.auth.API_TOKEN", TEST_API_TOKEN)


@pytest.fixture
async def db_engine(tmp_path):
    """Kortlevende engine voor store-laag tests."""
    engine = maak_test_engine(SQLModel.metadata, tmp_path=tmp_path)
    yield engine
    await engine.dispose()


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    """HTTP-client met een dialect-agnostische engine en auth-override."""
    async_engine = maak_test_engine(SQLModel.metadata, tmp_path=tmp_path)
    app.dependency_overrides[get_engine] = lambda: async_engine
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_engine, None)
    app.dependency_overrides.pop(huidige_beheerder, None)


# ---- Store-laag tests -------------------------------------------------------


@pytest.mark.asyncio
async def test_lijst_gebruikers_leeg(db_engine):
    result = await lijst_gebruikers(db_engine)
    assert result == []


@pytest.mark.asyncio
async def test_lijst_gebruikers_na_aanmaken(db_engine):
    await maak_gebruiker(db_engine, "alice", "ww12345678", "analist")
    await maak_gebruiker(db_engine, "bob", "ww12345678", "beheerder")
    result = await lijst_gebruikers(db_engine)
    namen = [g.gebruikersnaam for g in result]
    assert "alice" in namen
    assert "bob" in namen


@pytest.mark.asyncio
async def test_maak_gebruiker_admin_duplicaat(db_engine):
    await maak_gebruiker(db_engine, "alice", "ww12345678", "analist")
    with pytest.raises(GebruikersnaamAlInGebruik):
        await maak_gebruiker_admin(db_engine, "alice", "anderww12345678", "analist")


@pytest.mark.asyncio
async def test_wijzig_rol(db_engine):
    await maak_gebruiker(db_engine, "beheerder1", "ww12345678", "beheerder")
    await maak_gebruiker(db_engine, "analist1", "ww12345678", "analist")
    g = await wijzig_gebruiker(db_engine, "analist1", rol="beheerder", actief=None)
    assert g.rol == "beheerder"


@pytest.mark.asyncio
async def test_wijzig_actief(db_engine):
    await maak_gebruiker(db_engine, "beheerder1", "ww12345678", "beheerder")
    await maak_gebruiker(db_engine, "analist1", "ww12345678", "analist")
    g = await wijzig_gebruiker(db_engine, "analist1", rol=None, actief=False)
    assert g.actief is False


@pytest.mark.asyncio
async def test_wijzig_onbekende_gebruiker_geeft_exception(db_engine):
    with pytest.raises(GebruikerNietGevonden):
        await wijzig_gebruiker(db_engine, "bestaat-niet", rol="analist", actief=None)


@pytest.mark.asyncio
async def test_wijzig_laatste_beheerder_deactiveren_geeft_exception(db_engine):
    await maak_gebruiker(db_engine, "enige-beheerder", "ww12345678", "beheerder")
    with pytest.raises(LaatsteBeheerder):
        await wijzig_gebruiker(db_engine, "enige-beheerder", rol=None, actief=False)


@pytest.mark.asyncio
async def test_wijzig_laatste_beheerder_degraderen_geeft_exception(db_engine):
    await maak_gebruiker(db_engine, "enige-beheerder", "ww12345678", "beheerder")
    with pytest.raises(LaatsteBeheerder):
        await wijzig_gebruiker(db_engine, "enige-beheerder", rol="analist", actief=None)


@pytest.mark.asyncio
async def test_wijzig_beheerder_met_meerdere_beheerders(db_engine):
    await maak_gebruiker(db_engine, "b1", "ww12345678", "beheerder")
    await maak_gebruiker(db_engine, "b2", "ww12345678", "beheerder")
    g = await wijzig_gebruiker(db_engine, "b1", rol="analist", actief=None)
    assert g.rol == "analist"


@pytest.mark.asyncio
async def test_reset_wachtwoord(db_engine):
    await maak_gebruiker(db_engine, "alice", "ww12345678", "analist")
    resultaat = await reset_wachtwoord(db_engine, "alice")
    assert resultaat.gebruikersnaam == "alice"
    assert len(resultaat.tijdelijk_wachtwoord) > 10


@pytest.mark.asyncio
async def test_reset_onbekende_gebruiker(db_engine):
    with pytest.raises(GebruikerNietGevonden):
        await reset_wachtwoord(db_engine, "bestaat-niet")


@pytest.mark.asyncio
async def test_verwijder_gebruiker(db_engine):
    await maak_gebruiker(db_engine, "beheerder1", "ww12345678", "beheerder")
    await maak_gebruiker(db_engine, "analist1", "ww12345678", "analist")
    await verwijder_gebruiker(db_engine, "analist1", ingelogd_als="beheerder1")
    namen = [g.gebruikersnaam for g in await lijst_gebruikers(db_engine)]
    assert "analist1" not in namen


@pytest.mark.asyncio
async def test_verwijder_onbekende_gebruiker(db_engine):
    with pytest.raises(GebruikerNietGevonden):
        await verwijder_gebruiker(db_engine, "bestaat-niet", ingelogd_als="beheerder1")


@pytest.mark.asyncio
async def test_verwijder_laatste_beheerder_gooit_exception(db_engine):
    await maak_gebruiker(db_engine, "enige-beheerder", "ww12345678", "beheerder")
    with pytest.raises(LaatsteBeheerder):
        await verwijder_gebruiker(db_engine, "enige-beheerder", ingelogd_als="enige-beheerder")


# ---- HTTP-laag tests --------------------------------------------------------


def test_get_gebruikers_geeft_lege_lijst(client):
    r = client.get("/v1/admin/gebruikers")
    assert r.status_code == 200
    assert r.json() == []


def test_get_gebruikers_zonder_auth_geeft_401():
    # Geen dependency-override voor huidige_beheerder — de echte auth-check loopt.
    with TestClient(app) as c:
        r = c.get("/v1/admin/gebruikers")
    assert r.status_code == 401


def test_post_gebruiker_maakt_aan(client):
    r = client.post(
        "/v1/admin/gebruikers",
        json={"gebruikersnaam": "nieuwegast", "wachtwoord": "geheim1234", "rol": "analist"},
    )
    assert r.status_code == 201
    assert r.json()["gebruikersnaam"] == "nieuwegast"
    assert r.json()["rol"] == "analist"
    assert r.json()["actief"] is True


def test_post_gebruiker_duplicaat_geeft_409(client):
    client.post(
        "/v1/admin/gebruikers",
        json={"gebruikersnaam": "dubbel", "wachtwoord": "geheim1234", "rol": "analist"},
    )
    r = client.post(
        "/v1/admin/gebruikers",
        json={"gebruikersnaam": "dubbel", "wachtwoord": "geheim1234", "rol": "analist"},
    )
    assert r.status_code == 409


def test_post_gebruiker_ongeldige_rol_geeft_422(client):
    r = client.post(
        "/v1/admin/gebruikers",
        json={"gebruikersnaam": "x", "wachtwoord": "geheim1234", "rol": "superuser"},
    )
    assert r.status_code == 422


def test_patch_wijzigt_rol(client):
    client.post(
        "/v1/admin/gebruikers",
        json={"gebruikersnaam": "alice", "wachtwoord": "geheim1234", "rol": "analist"},
    )
    # Eerste maak een tweede beheerder aan zodat de invariant niet schiet
    client.post(
        "/v1/admin/gebruikers",
        json={"gebruikersnaam": "b2", "wachtwoord": "geheim1234", "rol": "beheerder"},
    )
    r = client.patch("/v1/admin/gebruikers/alice", json={"rol": "beheerder"})
    assert r.status_code == 200
    assert r.json()["rol"] == "beheerder"


def test_patch_onbekende_gebruiker_geeft_404(client):
    r = client.patch("/v1/admin/gebruikers/bestaat-niet", json={"rol": "analist"})
    assert r.status_code == 404


def test_patch_laatste_beheerder_deactiveren_geeft_409(client):
    client.post(
        "/v1/admin/gebruikers",
        json={"gebruikersnaam": "enige-b", "wachtwoord": "geheim1234", "rol": "beheerder"},
    )
    r = client.patch("/v1/admin/gebruikers/enige-b", json={"actief": False})
    assert r.status_code == 409


def test_patch_ongeldige_rol_geeft_422(client):
    r = client.patch("/v1/admin/gebruikers/alice", json={"rol": "superuser"})
    assert r.status_code == 422


def test_patch_lege_body_geeft_422(client):
    r = client.patch("/v1/admin/gebruikers/alice", json={})
    assert r.status_code == 422


def test_reset_wachtwoord_endpoint(client):
    client.post(
        "/v1/admin/gebruikers",
        json={"gebruikersnaam": "resetme", "wachtwoord": "geheim1234", "rol": "analist"},
    )
    r = client.post("/v1/admin/gebruikers/resetme/reset-wachtwoord")
    assert r.status_code == 200
    data = r.json()
    assert data["gebruikersnaam"] == "resetme"
    assert len(data["tijdelijk_wachtwoord"]) > 10


def test_reset_onbekende_gebruiker_geeft_404(client):
    r = client.post("/v1/admin/gebruikers/bestaat-niet/reset-wachtwoord")
    assert r.status_code == 404


def test_delete_verwijdert_gebruiker(client):
    client.post(
        "/v1/admin/gebruikers",
        json={"gebruikersnaam": "weg", "wachtwoord": "geheim1234", "rol": "analist"},
    )
    r = client.delete("/v1/admin/gebruikers/weg")
    assert r.status_code == 204
    lijst = client.get("/v1/admin/gebruikers").json()
    assert all(g["gebruikersnaam"] != "weg" for g in lijst)


def test_delete_onbekende_gebruiker_geeft_404(client):
    r = client.delete("/v1/admin/gebruikers/bestaat-niet")
    assert r.status_code == 404


def test_delete_laatste_beheerder_geeft_409(client):
    client.post(
        "/v1/admin/gebruikers",
        json={"gebruikersnaam": "enige-b", "wachtwoord": "geheim1234", "rol": "beheerder"},
    )
    r = client.delete("/v1/admin/gebruikers/enige-b")
    assert r.status_code == 409


def test_delete_zonder_auth_geeft_401():
    # Geen dependency-override voor huidige_beheerder — de echte auth-check loopt.
    with TestClient(app) as c:
        r = c.delete("/v1/admin/gebruikers/alice")
    assert r.status_code == 401
