"""Gedragstests voor GET /v1/projecten/{id}/llm-calls (story 021).

Dekt:
- 200 met lege lijst als er geen calls zijn vastgelegd
- 200 met lege lijst als het analyse-id onbekend is (geen 404)
- 200 met calls nadat de store een call heeft opgeslagen
- 401/503 zonder authenticatie (endpoint vereist huidige_beheerder)

Seeding van llm_calls-rijen gaat via een synchrone engine (vermijdt event-loop-conflicten
tussen de TestClient en asyncio.run()).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.ext.asyncio import create_async_engine

from app.features.llm_calls.dependencies import get_llm_calls_store
from app.features.llm_calls.models import llm_calls
from app.features.llm_calls.models import metadata as llm_calls_metadata
from app.features.llm_calls.store import SqlAlchemyLlmCallsStore
from app.features.projecten.models import metadata as projecten_metadata
from app.features.projecten.router import get_store
from app.features.projecten.store import SqlAlchemyAnalyseStore
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER

GELDIGE_BRON = {"bwb_id": "BWBR0011823", "artikel": "9", "lid": "1"}


def _llm_call_rij(analyse_id: str, activiteit: str = "act2", **overrides) -> dict:
    """Minimale LLM-call rij voor directe INSERT in de sync engine."""
    return {
        "analyse_id": analyse_id,
        "activiteit": activiteit,
        "bron_id": None,
        "system_prompt": "sys",
        "user_prompt": "usr",
        "ruwe_respons": "resp",
        "model": "gpt-4o",
        "tokens_in": 10,
        "tokens_out": 20,
        "aangemaakt": datetime.now(UTC),
        **overrides,
    }


def _maak_engines(db_pad):
    """Geeft (sync_engine, store, llm_store) na aanmaken van het schema."""
    sync_engine = create_engine(f"sqlite:///{db_pad}")
    projecten_metadata.create_all(sync_engine)
    llm_calls_metadata.create_all(sync_engine)

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    return sync_engine, SqlAlchemyAnalyseStore(async_engine), SqlAlchemyLlmCallsStore(async_engine)


@pytest.fixture
def client_en_sync(tmp_path) -> Iterator[tuple[TestClient, object]]:
    """Fixture met TestClient + synchrone engine voor seeding van llm_calls."""
    sync_engine, store, llm_store = _maak_engines(tmp_path / "test_llm.db")

    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_llm_calls_store] = lambda: llm_store
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    with TestClient(app) as test_client:
        yield test_client, sync_engine

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(get_llm_calls_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)
    sync_engine.dispose()


@pytest.fixture
def client_zonder_auth(tmp_path) -> Iterator[TestClient]:
    """Fixture zonder auth-override — gebruikt voor de beveiligingstest."""
    sync_engine, store, llm_store = _maak_engines(tmp_path / "test_noauth.db")
    sync_engine.dispose()  # alleen nodig voor schema-aanmaak, niet voor seeding

    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_llm_calls_store] = lambda: llm_store
    # huidige_beheerder NIET overridden — echte auth-check actief

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(get_llm_calls_store, None)


# ─── Tests ─────────────────────────────────────────────────────────────────────


def test_lege_lijst_onbekend_analyse_id(client_en_sync):
    """Onbekend analyse-id → 200 met lege lijst (geen 404)."""
    client, _ = client_en_sync
    resp = client.get("/v1/projecten/00000000-0000-0000-0000-000000000000/llm-calls")
    assert resp.status_code == 200
    assert resp.json() == []


def test_lege_lijst_analyse_zonder_calls(client_en_sync):
    """Bekende analyse zonder vastgelegde calls → 200 met lege lijst."""
    client, _ = client_en_sync
    analyse = client.post(
        "/v1/projecten",
        json={"naam": "Test", "bronnen": [GELDIGE_BRON]},
    ).json()
    resp = client.get(f"/v1/projecten/{analyse['id']}/llm-calls")
    assert resp.status_code == 200
    assert resp.json() == []


def test_lijst_met_calls_na_opslaan(client_en_sync):
    """Na een directe INSERT geeft het endpoint de call terug (200)."""
    client, sync_engine = client_en_sync
    analyse = client.post(
        "/v1/projecten",
        json={"naam": "Test capture", "bronnen": [GELDIGE_BRON]},
    ).json()
    analyse_id = analyse["id"]

    with sync_engine.begin() as conn:
        conn.execute(
            insert(llm_calls).values(
                _llm_call_rij(
                    analyse_id,
                    activiteit="act2",
                    bron_id="BWBR0011823_9_1",
                    system_prompt="Jij bent een juridisch analist.",
                    user_prompt="Analyseer artikel 9.",
                    ruwe_respons="Artikel 9 stelt dat...",
                    model="gpt-4o",
                    tokens_in=150,
                    tokens_out=300,
                )
            )
        )

    resp = client.get(f"/v1/projecten/{analyse_id}/llm-calls")
    assert resp.status_code == 200
    calls = resp.json()
    assert len(calls) == 1
    call = calls[0]
    assert call["activiteit"] == "act2"
    assert call["bron_id"] == "BWBR0011823_9_1"
    assert call["model"] == "gpt-4o"
    assert call["tokens_in"] == 150
    assert call["tokens_out"] == 300
    assert call["system_prompt"] == "Jij bent een juridisch analist."
    assert call["ruwe_respons"] == "Artikel 9 stelt dat..."
    assert "aangemaakt" in call


def test_volgorde_op_aangemaakt_asc(client_en_sync):
    """Meerdere calls worden gesorteerd op aangemaakt oplopend teruggegeven."""
    from datetime import timedelta

    client, sync_engine = client_en_sync
    analyse = client.post(
        "/v1/projecten",
        json={"naam": "Volgorde-test", "bronnen": [GELDIGE_BRON]},
    ).json()
    analyse_id = analyse["id"]

    basis = datetime.now(UTC)
    activiteiten = ["act2", "act3a", "act3b"]
    with sync_engine.begin() as conn:
        for i, activiteit in enumerate(activiteiten):
            conn.execute(
                insert(llm_calls).values(
                    _llm_call_rij(
                        analyse_id,
                        activiteit=activiteit,
                        aangemaakt=basis + timedelta(seconds=i),
                    )
                )
            )

    resp = client.get(f"/v1/projecten/{analyse_id}/llm-calls")
    assert resp.status_code == 200
    teruggegeven = [c["activiteit"] for c in resp.json()]
    assert teruggegeven == activiteiten


def test_endpoint_beveiligd_zonder_auth(client_zonder_auth):
    """Endpoint geeft een foutrespons (401 of 503) zonder geldig auth-token."""
    resp = client_zonder_auth.get("/v1/projecten/00000000-0000-0000-0000-000000000000/llm-calls")
    assert resp.status_code in (401, 503)
