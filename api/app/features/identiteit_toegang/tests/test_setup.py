"""Setup-flow: GET /v1/auth/setup-status en POST /v1/auth/setup.

Gedrag getest:
- setup-status bij lege tabel → needs_setup: true
- setup aanmaken → 201 + GebruikerInfo
- setup-status ná aanmaken → needs_setup: false
- dubbele setup aanroep → 409
- gebruikersnaam al in gebruik → 409
- wachtwoord te kort → 422 (Pydantic-validatie)
- ongeldige gebruikersnaam → 422 (Pydantic-validatie)
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel

from app.db import get_engine
from app.features.identiteit_toegang.store import maak_gebruiker, tabel_leeg
from app.main import app

TEST_API_TOKEN = "test-api-token"
HEADERS = {"Authorization": f"Bearer {TEST_API_TOKEN}"}


@pytest.fixture(autouse=True)
def stel_api_token_in(monkeypatch):
    monkeypatch.setattr("app.shared.auth.API_TOKEN", TEST_API_TOKEN)


@pytest.fixture
def db_pad(tmp_path) -> Path:
    return tmp_path / "test.db"


@pytest_asyncio.fixture
async def async_engine(db_pad) -> AsyncIterator[AsyncEngine]:
    """Kortlevende async SQLite-engine met het volledige schema aangemaakt."""
    sync_engine = create_engine(f"sqlite:///{db_pad}")
    SQLModel.metadata.create_all(sync_engine)
    sync_engine.dispose()
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    yield engine
    await engine.dispose()


@pytest.fixture
def client(db_pad) -> Iterator[TestClient]:
    """Elke test krijgt een eigen, lege SQLite-database."""
    sync_engine = create_engine(f"sqlite:///{db_pad}")
    SQLModel.metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_eng: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    app.dependency_overrides[get_engine] = lambda: async_eng

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_engine, None)


# --- store: tabel_leeg ---


@pytest.mark.asyncio
async def test_tabel_leeg_bij_lege_db(async_engine):
    assert await tabel_leeg(async_engine) is True


@pytest.mark.asyncio
async def test_tabel_leeg_na_gebruiker(async_engine):
    await maak_gebruiker(async_engine, "beheerder", "wachtwoord123")
    assert await tabel_leeg(async_engine) is False


# --- GET /v1/auth/setup-status ---


def test_setup_status_zonder_token_geeft_401(client):
    resp = client.get("/v1/auth/setup-status")
    assert resp.status_code == 401


def test_setup_status_leeg_geeft_needs_setup_true(client):
    resp = client.get("/v1/auth/setup-status", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["needs_setup"] is True


# --- POST /v1/auth/setup ---


def test_setup_maakt_eerste_beheerder(client):
    resp = client.post(
        "/v1/auth/setup",
        json={
            "gebruikersnaam": "admin",
            "email": "admin@example.com",
            "wachtwoord": "veiligww123",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["gebruikersnaam"] == "admin"
    assert data["email"] == "admin@example.com"
    assert data["rol"] == "beheerder"


def test_setup_daarna_needs_setup_false(client):
    client.post(
        "/v1/auth/setup",
        json={
            "gebruikersnaam": "admin",
            "email": "admin@example.com",
            "wachtwoord": "veiligww123",
        },
        headers=HEADERS,
    )
    resp = client.get("/v1/auth/setup-status", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["needs_setup"] is False


def test_setup_twee_keer_geeft_409(client):
    payload = {
        "gebruikersnaam": "admin",
        "email": "admin@example.com",
        "wachtwoord": "veiligww123",
    }
    client.post("/v1/auth/setup", json=payload, headers=HEADERS)
    resp = client.post("/v1/auth/setup", json=payload, headers=HEADERS)
    assert resp.status_code == 409
    assert "Setup al voltooid" in resp.json()["detail"]


def test_setup_wachtwoord_te_kort_geeft_422(client):
    resp = client.post(
        "/v1/auth/setup",
        json={
            "gebruikersnaam": "admin",
            "email": "admin@example.com",
            "wachtwoord": "kort",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 422


def test_setup_ongeldige_gebruikersnaam_geeft_422(client):
    resp = client.post(
        "/v1/auth/setup",
        json={
            "gebruikersnaam": "Ad Min!",  # hoofdletters + spatie verboden
            "email": "admin@example.com",
            "wachtwoord": "veiligww123",
        },
        headers=HEADERS,
    )
    assert resp.status_code == 422


def test_setup_zonder_token_geeft_401(client):
    resp = client.post(
        "/v1/auth/setup",
        json={
            "gebruikersnaam": "admin",
            "email": "admin@example.com",
            "wachtwoord": "veiligww123",
        },
    )
    assert resp.status_code == 401
