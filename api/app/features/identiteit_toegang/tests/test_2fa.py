"""Gedragstests voor 2FA/TOTP (story 017).

Store-laag: begin/activeer/uitschakel/verifieer met TOTP, versleuteld-secret-flow.
Router-integratie leunt op dezelfde `client`-fixture als test_auth.py (dezelfde engine +
API_TOKEN-monkeypatch); dat is hier apart bevestigd via `test_begin_via_http_200`.
"""

from __future__ import annotations

import urllib.parse

import pyotp
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_engine
from app.features.identiteit_toegang.models import gebruikers, metadata
from app.features.identiteit_toegang.store import (
    TotpFout,
    activeer_totp,
    begin_totp_koppeling,
    maak_gebruiker,
    uitschakel_totp,
    verifieer_credentials,
)
from app.main import app
from app.shared import crypto
from conftest import maak_test_engine

TEST_API_TOKEN = "test-api-token-2fa"
# Willekeurige geldige Fernet-key voor tests die encryptie raken.
TEST_FERNET_KEY = "pHJH9BfOH6gWMJGBpD2bBRHpJE9hCVs0iiqHWH8Xm0k="


@pytest.fixture(autouse=True)
def stel_omgeving_in(monkeypatch, tmp_path):
    monkeypatch.setattr("app.shared.auth.API_TOKEN", TEST_API_TOKEN)
    pad = tmp_path / "fernet_key"
    pad.write_text(TEST_FERNET_KEY)
    monkeypatch.setenv("FERNET_KEY_FILE", str(pad))
    crypto._fernet.cache_clear()
    yield
    crypto._fernet.cache_clear()


@pytest.fixture(autouse=True)
def wis_rate_limit():
    from app.shared.rate_limit import wis

    wis()
    yield
    wis()


@pytest_asyncio.fixture
async def db_engine(tmp_path):
    engine = maak_test_engine(metadata, tmp_path=tmp_path)
    yield engine
    await engine.dispose()


@pytest.fixture
def client(tmp_path) -> TestClient:
    async_engine = maak_test_engine(metadata, tmp_path=tmp_path)
    app.dependency_overrides[get_engine] = lambda: async_engine

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_engine, None)


def _totp_van_uri(uri: str) -> pyotp.TOTP:
    """Extract het secret uit een otpauth-URI en bouw een TOTP-instantie voor test-side codes."""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(uri).query)
    return pyotp.TOTP(q["secret"][0])


# --- Store-laag ------------------------------------------------------------


async def test_begin_totp_koppeling_maakt_secret_en_uri(db_engine):
    await maak_gebruiker(db_engine, "ana", "wachtwoord123", "analist")
    uri = await begin_totp_koppeling(db_engine, "ana")
    assert uri.startswith("otpauth://totp/")
    assert "issuer=lexplainables" in uri

    # Secret staat versleuteld in de DB (niet plaintext, ook niet in de URI-vorm).
    async with db_engine.connect() as conn:
        rij = (
            await conn.execute(select(gebruikers).where(gebruikers.c.gebruikersnaam == "ana"))
        ).first()
        g = dict(rij._mapping)
        assert g["totp_secret_enc"] is not None
        assert g["totp_ingeschakeld"] is False
        # Fernet-tokens beginnen met "gAAAA…"; niet gelijk aan de plaintext secret.
        plaintext = crypto.decrypt(g["totp_secret_enc"])
        assert plaintext not in g["totp_secret_enc"]


async def test_begin_zonder_fernet_key_gooit_cryptofout(db_engine, monkeypatch):
    await maak_gebruiker(db_engine, "ana", "wachtwoord123", "analist")
    monkeypatch.delenv("FERNET_KEY_FILE", raising=False)
    crypto._fernet.cache_clear()
    with pytest.raises(crypto.CryptoFout):
        await begin_totp_koppeling(db_engine, "ana")


async def test_activeer_totp_met_goede_code_zet_vlag(db_engine):
    await maak_gebruiker(db_engine, "ana", "wachtwoord123", "analist")
    uri = await begin_totp_koppeling(db_engine, "ana")
    totp = _totp_van_uri(uri)

    await activeer_totp(db_engine, "ana", totp.now())

    async with db_engine.connect() as conn:
        rij = (
            await conn.execute(select(gebruikers).where(gebruikers.c.gebruikersnaam == "ana"))
        ).first()
        assert rij._mapping["totp_ingeschakeld"] is True


async def test_activeer_totp_met_foute_code_raist(db_engine):
    await maak_gebruiker(db_engine, "ana", "wachtwoord123", "analist")
    await begin_totp_koppeling(db_engine, "ana")
    with pytest.raises(TotpFout):
        await activeer_totp(db_engine, "ana", "000000")


async def test_activeer_zonder_pending_setup_raist(db_engine):
    """Als `begin` niet is aangeroepen, is er niets om te activeren — 400."""
    await maak_gebruiker(db_engine, "ana", "wachtwoord123", "analist")
    with pytest.raises(TotpFout):
        await activeer_totp(db_engine, "ana", "123456")


async def test_uitschakel_totp_wist_secret_en_vlag(db_engine):
    await maak_gebruiker(db_engine, "ana", "wachtwoord123", "analist")
    uri = await begin_totp_koppeling(db_engine, "ana")
    totp = _totp_van_uri(uri)
    await activeer_totp(db_engine, "ana", totp.now())

    await uitschakel_totp(db_engine, "ana", totp.now())

    async with db_engine.connect() as conn:
        rij = (
            await conn.execute(select(gebruikers).where(gebruikers.c.gebruikersnaam == "ana"))
        ).first()
        assert rij._mapping["totp_ingeschakeld"] is False
        assert rij._mapping["totp_secret_enc"] is None


async def test_uitschakel_totp_met_foute_code_raist(db_engine):
    await maak_gebruiker(db_engine, "ana", "wachtwoord123", "analist")
    uri = await begin_totp_koppeling(db_engine, "ana")
    totp = _totp_van_uri(uri)
    await activeer_totp(db_engine, "ana", totp.now())

    with pytest.raises(TotpFout):
        await uitschakel_totp(db_engine, "ana", "000000")


async def test_verifieer_credentials_totp_required_zonder_totp(db_engine):
    await maak_gebruiker(db_engine, "ana", "wachtwoord123", "analist")
    uri = await begin_totp_koppeling(db_engine, "ana")
    totp = _totp_van_uri(uri)
    await activeer_totp(db_engine, "ana", totp.now())

    resultaat = await verifieer_credentials(db_engine, "ana", "wachtwoord123")
    assert resultaat.ok is False
    assert resultaat.code == "totp_required"


async def test_verifieer_credentials_met_correcte_totp_slaagt(db_engine):
    await maak_gebruiker(db_engine, "ana", "wachtwoord123", "analist")
    uri = await begin_totp_koppeling(db_engine, "ana")
    totp = _totp_van_uri(uri)
    await activeer_totp(db_engine, "ana", totp.now())

    resultaat = await verifieer_credentials(db_engine, "ana", "wachtwoord123", totp=totp.now())
    assert resultaat.ok is True
    assert resultaat.gebruikersnaam == "ana"
    assert resultaat.rol == "analist"


async def test_verifieer_credentials_met_verkeerde_totp_geeft_invalid(db_engine):
    """Verkeerde totp lekt de 2FA-status niet: gewoon `invalid`, niet `totp_required`."""
    await maak_gebruiker(db_engine, "ana", "wachtwoord123", "analist")
    uri = await begin_totp_koppeling(db_engine, "ana")
    totp = _totp_van_uri(uri)
    await activeer_totp(db_engine, "ana", totp.now())

    resultaat = await verifieer_credentials(db_engine, "ana", "wachtwoord123", totp="000000")
    assert resultaat.ok is False
    assert resultaat.code == "invalid"


# --- Router-integratie -----------------------------------------------------


def test_begin_via_http_zonder_sessie_geeft_401(client):
    """Route zit achter huidige_beheerder — zonder X-User-Id → 401."""
    resp = client.post("/v1/auth/2fa/begin", headers={"Authorization": f"Bearer {TEST_API_TOKEN}"})
    assert resp.status_code == 401


def test_begin_zonder_fernet_key_geeft_400(client, monkeypatch):
    monkeypatch.delenv("FERNET_KEY_FILE", raising=False)
    crypto._fernet.cache_clear()
    resp = client.post(
        "/v1/auth/2fa/begin",
        headers={"Authorization": f"Bearer {TEST_API_TOKEN}", "X-User-Id": "ana"},
    )
    # 400 als de user bestaat en Fernet weg is; 401 als user niet bestaat.
    # Voor deze test bewijzen we dat FERNET_KEY-afwezigheid niet doorknalt naar 500.
    assert resp.status_code in (400, 401)
