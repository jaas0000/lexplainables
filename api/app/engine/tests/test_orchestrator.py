"""Tests voor de orchestrator + router-integratie (story 024, feature-bouwen regel 6).

Tests draaien via de echte HTTP-laag (TestClient) met gemockte LLM-client en gemockte
Wettenbank-MCP. De background-job wordt gepatcht naar no-op voor router-tests;
de orchestrator zelf wordt direct getest via asyncio.run().
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from app.features.projecten.models import metadata
from app.features.projecten.router import get_store
from app.features.projecten.store import SqlAlchemyAnalyseStore
from app.main import app
from app.shared.auth import huidige_beheerder
from conftest import TEST_BEHEERDER

GELDIGE_BRON = {"bwb_id": "BWBR0011823", "artikel": "9", "lid": "1"}


async def _noop_bg(*args, **kwargs):
    """No-op achtergrond-job voor router-tests."""


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    db_pad = tmp_path / "test.db"
    sync_engine = create_engine(f"sqlite:///{db_pad}")
    metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    store = SqlAlchemyAnalyseStore(async_engine)
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[huidige_beheerder] = lambda: TEST_BEHEERDER

    # Patcheer de background-job naar no-op zodat de router-tests niet afhangen van
    # het beschikbaar zijn van de llm_profielen-tabel of MCP.
    with patch("app.features.projecten.router._voer_analyse_uit", new=_noop_bg):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.pop(get_store, None)
    app.dependency_overrides.pop(huidige_beheerder, None)


def _maak(client, *, naam="Test", human_in_the_loop=False, **extra):
    body = {
        "naam": naam,
        "bronnen": [GELDIGE_BRON],
        "human_in_the_loop": human_in_the_loop,
        **extra,
    }
    resp = client.post("/v1/projecten", json=body)
    assert resp.status_code == 202, resp.json()
    return resp.json()


def _run(coro):
    """Voer een coroutine synchroon uit via asyncio.run()."""
    return asyncio.run(coro)


# ─── Akkoord/Afwijzen endpoints ────────────────────────────────────────────


def test_akkoord_alleen_in_review(client):
    """POST /akkoord geeft 409 als de analyse niet in review-status staat."""
    data = _maak(client)
    resp = client.post(f"/v1/projecten/{data['id']}/akkoord")
    assert resp.status_code == 409


def test_afwijzen_alleen_in_review(client):
    """POST /afwijzen geeft 409 als de analyse niet in review-status staat."""
    data = _maak(client)
    resp = client.post(f"/v1/projecten/{data['id']}/afwijzen")
    assert resp.status_code == 409


def test_akkoord_na_review(client):
    """POST /akkoord zet status van 'review' naar 'actief'."""
    data = _maak(client, human_in_the_loop=True)
    store = app.dependency_overrides[get_store]()
    _run(store.zet_status(data["id"], "review", "Wacht op goedkeuring"))

    resp = client.post(f"/v1/projecten/{data['id']}/akkoord")
    assert resp.status_code == 204

    detail = client.get(f"/v1/projecten/{data['id']}").json()
    assert detail["status"] == "actief"


def test_afwijzen_na_review(client):
    """POST /afwijzen zet status van 'review' naar 'fout'."""
    data = _maak(client, human_in_the_loop=True)
    store = app.dependency_overrides[get_store]()
    _run(store.zet_status(data["id"], "review", "Wacht op goedkeuring"))

    resp = client.post(f"/v1/projecten/{data['id']}/afwijzen")
    assert resp.status_code == 204

    detail = client.get(f"/v1/projecten/{data['id']}").json()
    assert detail["status"] == "fout"
    assert "afgewezen" in (detail["foutmelding"] or "").lower()


def test_akkoord_onbekend_id(client):
    resp = client.post("/v1/projecten/00000000-0000-0000-0000-000000000000/akkoord")
    assert resp.status_code == 404


def test_afwijzen_onbekend_id(client):
    resp = client.post("/v1/projecten/00000000-0000-0000-0000-000000000000/afwijzen")
    assert resp.status_code == 404


# ─── Rapport in AnalyseDetail ─────────────────────────────────────────────


def test_rapport_initieel_none(client):
    """Rapport is None zolang de analyse niet klaar is."""
    data = _maak(client)
    detail = client.get(f"/v1/projecten/{data['id']}").json()
    assert "rapport" in detail
    assert detail["rapport"] is None


def test_rapport_opgeslagen_na_klaar(client):
    """Rapport wordt opgeslagen via store.sla_rapport_op en is daarna leesbaar."""
    data = _maak(client)
    store = app.dependency_overrides[get_store]()
    test_rapport = {"naam": "Test", "bronnen": [], "begrippen": [], "afleidingsregels": []}
    _run(store.sla_rapport_op(data["id"], test_rapport))

    detail = client.get(f"/v1/projecten/{data['id']}").json()
    assert detail["rapport"] == test_rapport


# ─── haal_status store-methode ────────────────────────────────────────────


def test_haal_status(client):
    """store.haal_status geeft de huidige status terug."""
    data = _maak(client)
    store = app.dependency_overrides[get_store]()
    status = _run(store.haal_status(data["id"]))
    assert status == "wachtrij"


def test_haal_status_onbekend_id(client):
    """store.haal_status geeft None voor onbekend id."""
    store = app.dependency_overrides[get_store]()
    status = _run(store.haal_status("00000000-0000-0000-0000-000000000000"))
    assert status is None


# ─── Orchestrator directe tests (asyncio.run, gemockte engine) ─────────────


@pytest.fixture
def orch_env(tmp_path):
    """Geeft (store, engine) terug voor directe orchestrator-tests."""
    db_pad = tmp_path / "orch.db"
    from app.features.llm_profielen.models import metadata as profiel_metadata

    sync_engine = create_engine(f"sqlite:///{db_pad}")
    metadata.create_all(sync_engine)
    profiel_metadata.create_all(sync_engine)
    sync_engine.dispose()

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_pad}")
    store = SqlAlchemyAnalyseStore(async_engine)
    return store, async_engine


def test_volledige_flow_zonder_hitl(orch_env):
    """Orchestrator doorloopt act2 + act3 en zet status op 'klaar'."""
    store, engine = orch_env

    from app.features.projecten.models import BronKeuze

    analyse = _run(
        store.maak(
            gebruiker_id="test",
            naam="Test-analyse",
            bronnen=[BronKeuze(bwb_id="BWBR0011823", artikel="9", lid="1")],
            omschrijving=None,
            analysefocus=None,
            begrippenlijst=None,
            model_profiel=None,
            human_in_the_loop=False,
        )
    )

    mcp_data = {
        "bwbId": "BWBR0011823",
        "wet": "Algemene wet inzake rijksbelastingen",
        "artikel": "9",
        "versiedatum": "2024-01-01",
        "bronreferentie": "jci1.3:c:BWBR0011823&artikel=9",
        "leden": [{"lid": "1", "tekst": "De belastingplichtige heeft recht op aftrek."}],
    }

    act2_out = {
        "markeringen": [
            {
                "id": "m1",
                "formulering": "heeft recht op aftrek",
                "klasse": "Rechtsbetrekking",
                "vindplaats": "lid 1",
                "toelichting": "kern",
            }
        ],
        "samenhang": "Belastingplichtige heeft recht op aftrek.",
    }
    act3a_out = {
        "begrippen": [
            {
                "id": "b1",
                "naam": "aftrek",
                "klasse": "Rechtsbetrekking",
                "definitie": "een aftrek",
                "is_interpretatie": False,
                "vindplaatsen": [{"bron_id": "br1", "lid": "1"}],
                "markering_ids": ["m1"],
            }
        ]
    }
    act3b_out = {"afleidingsregels": [], "nieuwe_begrippen": []}

    call_count = {"n": 0}

    async def fake_complete(self, system, user):
        from app.shared.llm.base import LLMResult

        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            return LLMResult(data=act2_out, ruwe_tekst="{}")
        if n == 1:
            return LLMResult(data=act3a_out, ruwe_tekst="{}")
        return LLMResult(data=act3b_out, ruwe_tekst="{}")

    fake_llm = type("FakeLLM", (), {"complete": fake_complete})()

    from app.engine import orchestrator as orch_mod
    from app.shared.llm.base import LlmConfig

    async def fake_lees(model_profiel, eng):
        return LlmConfig(provider="openai", model="gpt-test")

    with (
        patch("app.engine.orchestrator.haal_artikel_op", new=AsyncMock(return_value=mcp_data)),
        patch.object(orch_mod, "_lees_llm_config", new=fake_lees),
        patch("app.engine.orchestrator.bouw_llm_client", return_value=fake_llm),
    ):
        _run(orch_mod.voer_analyse_uit(analyse.id, store, engine))

    detail_rij = _run(store.haal_rij_op_id(analyse.id))
    assert detail_rij.status == "klaar"
    assert detail_rij.rapport is not None
    assert "bronnen" in detail_rij.rapport


def test_flow_mcp_fout_zet_status_fout(orch_env):
    """Als de MCP een fout geeft, wordt de status op 'fout' gezet."""
    store, engine = orch_env

    from app.features.projecten.models import BronKeuze

    analyse = _run(
        store.maak(
            gebruiker_id="test",
            naam="Test",
            bronnen=[BronKeuze(bwb_id="BWBR0011823", artikel="9")],
            omschrijving=None,
            analysefocus=None,
            begrippenlijst=None,
            model_profiel=None,
            human_in_the_loop=False,
        )
    )

    from app.engine import orchestrator as orch_mod
    from app.shared.llm.base import LlmConfig
    from app.shared.wettenbank import WettenbankFout

    async def fake_lees(model_profiel, eng):
        return LlmConfig(provider="openai", model="gpt-test")

    with (
        patch(
            "app.engine.orchestrator.haal_artikel_op",
            new=AsyncMock(side_effect=WettenbankFout("test")),
        ),
        patch.object(orch_mod, "_lees_llm_config", new=fake_lees),
    ):
        _run(orch_mod.voer_analyse_uit(analyse.id, store, engine))

    rij = _run(store.haal_rij_op_id(analyse.id))
    assert rij.status == "fout"
    assert "wettekst" in (rij.foutmelding or "").lower()


def test_flow_brongetrouwheid_mismatch_zet_fout(orch_env):
    """Als het LLM een niet-letterlijk citaat geeft, wordt de status op 'fout' gezet."""
    store, engine = orch_env

    from app.features.projecten.models import BronKeuze

    analyse = _run(
        store.maak(
            gebruiker_id="test",
            naam="Test",
            bronnen=[BronKeuze(bwb_id="BWBR0011823", artikel="9")],
            omschrijving=None,
            analysefocus=None,
            begrippenlijst=None,
            model_profiel=None,
            human_in_the_loop=False,
        )
    )

    mcp_data = {
        "bwbId": "BWBR0011823",
        "wet": "Test wet",
        "artikel": "9",
        "versiedatum": "2024-01-01",
        "bronreferentie": "jci1.3:c:BWBR0011823&artikel=9",
        "leden": [{"lid": "1", "tekst": "Werkelijke wettekst hier."}],
    }

    # LLM geeft een verzonnen citaat terug
    act2_verzonnen = {
        "markeringen": [
            {
                "id": "m1",
                "formulering": "verzonnen tekst die niet in de wet staat",
                "klasse": "Rechtsbetrekking",
                "vindplaats": "lid 1",
                "toelichting": "test",
            }
        ],
        "samenhang": "test",
    }

    async def fake_complete(self, system, user):
        from app.shared.llm.base import LLMResult

        return LLMResult(data=act2_verzonnen, ruwe_tekst="{}")

    fake_llm = type("FakeLLM", (), {"complete": fake_complete})()

    from app.engine import orchestrator as orch_mod
    from app.shared.llm.base import LlmConfig

    async def fake_lees(model_profiel, eng):
        return LlmConfig(provider="openai", model="gpt-test")

    with (
        patch("app.engine.orchestrator.haal_artikel_op", new=AsyncMock(return_value=mcp_data)),
        patch.object(orch_mod, "_lees_llm_config", new=fake_lees),
        patch("app.engine.orchestrator.bouw_llm_client", return_value=fake_llm),
    ):
        _run(orch_mod.voer_analyse_uit(analyse.id, store, engine))

    rij = _run(store.haal_rij_op_id(analyse.id))
    assert rij.status == "fout"
    assert "brongetrouwheid" in (rij.foutmelding or "").lower()
