"""`agent/wetsanalyse_api.py`: de client naar lexplainables' `api`-annotatiedomein.

`httpx.MockTransport` injecteert de HTTP-laag op de proces-brede client — zelfde patroon als
`api/app/shared/tests/test_wettenbank.py`.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest

import agent.wetsanalyse_api as wetsanalyse_api
from agent.wetsanalyse_api import (
    WetsanalyseApiFout,
    maak_document,
    naar_contract,
    zet_elementen,
)
from tests.fakes import make_settings


@pytest.fixture(autouse=True)
def _reset_client(monkeypatch):
    monkeypatch.setattr(wetsanalyse_api, "_client", None)
    yield
    monkeypatch.setattr(wetsanalyse_api, "_client", None)


def _monkeypatch_transport(monkeypatch, handler) -> None:
    monkeypatch.setattr(
        wetsanalyse_api, "_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


def test_naar_contract_vertaalt_lege_aandacht_naar_none() -> None:
    voorstel = {
        "id": "abc",
        "klasse": "Rechtssubject",
        "tekst": "de belastingplichtige",
        "lid": "1",
        "toelichting": "",
        "vindplaats": "art. 2",
        "alternatieven": [{"klasse": "Rechtsobject", "motivatie": "twijfel"}],
        "aandacht": "",
        "critic": "",
        "critic_rondes": [],
    }

    contract = naar_contract(voorstel)

    assert contract["aandacht"] is None
    assert contract["critic"] is None
    assert contract["alternatieven"] == [
        {"klasse": "Rechtsobject", "tekst": "de belastingplichtige", "toelichting": "twijfel"}
    ]


def test_naar_contract_behoudt_gezette_aandacht() -> None:
    voorstel = {"id": "x", "klasse": "K", "tekst": "t", "aandacht": "rood", "critic": "waarom"}
    contract = naar_contract(voorstel)
    assert contract["aandacht"] == "rood"
    assert contract["critic"] == "waarom"


def test_maak_document_geeft_slug_terug(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-user-id"] == "jurist-1"
        return httpx.Response(201, json={"slug": "abc123"})

    _monkeypatch_transport(monkeypatch, handler)
    settings = make_settings(wetsanalyse_api_url="http://api.local", wetsanalyse_api_token="tok")

    async def _run() -> None:
        slug = await maak_document(
            settings,
            werkgebied="sociaal",
            bwb_id="BWBR0004770",
            artikel="1",
            lid="",
            gebruiker="jurist-1",
        )
        assert slug == "abc123"

    asyncio.run(_run())


def test_zet_elementen_geeft_aanvaard_verworpen_terug(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"aanvaard": 2, "verworpen": 1})

    _monkeypatch_transport(monkeypatch, handler)
    settings = make_settings(wetsanalyse_api_url="http://api.local")

    async def _run() -> None:
        aanvaard, verworpen = await zet_elementen(
            settings,
            slug="abc123",
            voorstellen=[{"id": "1", "klasse": "K", "tekst": "t"}],
            run_info={"model": "x"},
            gebruiker="jurist-1",
        )
        assert (aanvaard, verworpen) == (2, 1)

    asyncio.run(_run())


def test_zet_elementen_slaat_van_jurist_voorstellen_over(monkeypatch) -> None:
    ontvangen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        import json

        ontvangen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"aanvaard": 1, "verworpen": 0})

    _monkeypatch_transport(monkeypatch, handler)
    settings = make_settings(wetsanalyse_api_url="http://api.local")

    async def _run() -> None:
        await zet_elementen(
            settings,
            slug="abc",
            voorstellen=[
                {"id": "1", "klasse": "K", "tekst": "agent-voorstel"},
                {"id": "2", "klasse": "K", "tekst": "jurist-markering", "van_jurist": True},
            ],
            run_info={},
            gebruiker="jurist-1",
        )

    asyncio.run(_run())
    teksten = [e["tekst"] for e in ontvangen["body"]["elementen"]]
    assert teksten == ["agent-voorstel"]


def test_onbereikbare_api_geeft_wetsanalyseapifout(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _monkeypatch_transport(monkeypatch, handler)
    settings = make_settings(wetsanalyse_api_url="http://api.local")

    async def _run() -> None:
        with pytest.raises(WetsanalyseApiFout):
            await maak_document(
                settings, werkgebied="x", bwb_id="y", artikel="1", lid="", gebruiker="jurist-1"
            )

    asyncio.run(_run())
