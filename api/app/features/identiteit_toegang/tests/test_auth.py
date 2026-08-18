"""Auth-grenzen: API_TOKEN-verificatie en credential-verificatie.

Negatieve paden voor `huidige_beheerder` (geen override — test de echte auth-grens).
Gelukkige paden lopen via de berichten-tests met dependency-override.
Positieve en negatieve paden voor /v1/auth/verify.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future import select
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_engine
from app.features.identiteit_toegang.models import Gebruiker
from app.features.identiteit_toegang.store import (
    maak_gebruiker,
    maak_gebruiker_indien_ontbreekt,
    verifieer_credentials,
)
from app.main import app

TEST_API_TOKEN = "test-api-token"


@pytest.fixture(autouse=True)
def stel_api_token_in(monkeypatch):
    monkeypatch.setattr("app.shared.auth.API_TOKEN", TEST_API_TOKEN)


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    """HTTP-client met in-memory SQLite zodat CI geen echte DB hoeft.

    De get_engine-override zorgt dat alle endpoints (incl. berichten) een schone
    in-memory database zien in plaats van de productie-wetsanalyse.db.
    """
    db_pad = tmp_path / "auth_test.db"
    sync_engine = create_engine(f"sqlite:///{db_pad}")
    SQLModel.metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    app.dependency_overrides[get_engine] = lambda: async_engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_engine, None)


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


# --- huidige_beheerder grenzen ---


def test_admin_bericht_zonder_token_geeft_401(client):
    response = client.get("/v1/admin/berichten")
    assert response.status_code == 401
    assert response.json()["detail"] == "Niet geautoriseerd."


def test_admin_bericht_met_fout_token_geeft_401(client):
    response = client.get(
        "/v1/admin/berichten",
        headers={"Authorization": "Bearer fout-token", "X-User-Id": "beheerder"},
    )
    assert response.status_code == 401


def test_admin_bericht_zonder_user_id_geeft_401(client):
    response = client.get(
        "/v1/admin/berichten",
        headers={"Authorization": f"Bearer {TEST_API_TOKEN}"},
    )
    assert response.status_code == 401


def test_admin_bericht_met_geldig_token_en_user_id_geeft_200(client):
    response = client.get(
        "/v1/admin/berichten",
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
