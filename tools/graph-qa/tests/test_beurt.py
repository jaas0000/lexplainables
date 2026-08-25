"""`agent/beurt.py`: één `doel`-gedreven annotatiebeurt, inclusief het wegschrijven naar `api`.

Herbruikt de FakeLLM-sequentie van `test_orchestrator.py::test_build_graph_volledige_
annotatieketen_met_doel` (annoteer → critic rood+vervang → critic eindbeoordeling groen).
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

import agent.wetsanalyse_api as wetsanalyse_api
from agent.beurt import voer_annotatie_beurt_uit
from tests.fakes import FakeGraph, FakeLLM, make_settings, response, text_block


def _annotatieketen_llm() -> FakeLLM:
    return FakeLLM(
        [
            response(
                [
                    text_block(
                        json.dumps(
                            {
                                "elementen": [
                                    {"klasse": "Rechtssubject", "tekst": "Degene die aangifte doet"}
                                ]
                            }
                        )
                    )
                ],
                "end_turn",
            ),
            response(
                [
                    text_block(
                        json.dumps(
                            {
                                "oordelen": [
                                    {
                                        "index": 0,
                                        "aandacht": "rood",
                                        "actie": "vervang",
                                        "voorstel_klasse": "Rechtsfeit",
                                        "motivatie": "beter zo",
                                    }
                                ],
                                "ontbrekend": [],
                            }
                        )
                    )
                ],
                "end_turn",
            ),
            response(
                [
                    text_block(
                        json.dumps(
                            {"oordelen": [{"index": 0, "aandacht": "groen"}], "ontbrekend": []}
                        )
                    )
                ],
                "end_turn",
            ),
        ]
    )


_CORPUS_TSV = (
    "?tekst\t?jci\t?lid\t?lidnummer\t?lidtekst\t?onderdeel\t?onderdeeltekst\n"
    '\t\t\t"1"\t"Degene die aangifte doet, is verplicht de gegevens waarheidsgetrouw te '
    'verstrekken."@nl\t\t'
)


@pytest.fixture(autouse=True)
def _reset_client(monkeypatch):
    monkeypatch.setattr(wetsanalyse_api, "_client", None)
    yield
    monkeypatch.setattr(wetsanalyse_api, "_client", None)


def test_zonder_wetsanalyse_api_url_is_de_beurt_een_doorgeefluik() -> None:
    """`settings.legt_zelf_vast` is False (geen URL) — de annotatieketen draait, niets wordt
    weggeschreven, geen `opgeslagen`-event."""
    settings = make_settings()  # geen wetsanalyse_api_url
    llm = _annotatieketen_llm()
    graph = FakeGraph(result=_CORPUS_TSV)

    async def _run() -> list[dict]:
        return [
            e
            async for e in voer_annotatie_beurt_uit(
                settings=settings,
                llm=llm,
                graph=graph,
                doel={"bwbId": "BWBR0004770", "artikel": "1"},
                werkgebied="sociaal",
                gebruiker="jurist-1",
            )
        ]

    events = asyncio.run(_run())

    types = [e["type"] for e in events]
    assert types[0] == "doel"
    assert "element" in types
    assert "opgeslagen" not in types
    assert types[-1] == "done"
    elementen = [e for e in events if e["type"] == "element"]
    assert elementen[0]["klasse"] == "Rechtsfeit"  # gepatcht door de Critic


def test_met_wetsanalyse_api_url_wordt_het_resultaat_weggeschreven(monkeypatch) -> None:
    aangeroepen: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        aangeroepen.append(request.url.path)
        if request.url.path.endswith("/documenten"):
            return httpx.Response(201, json={"slug": "doc-1"})
        return httpx.Response(200, json={"aanvaard": 1, "verworpen": 0})

    monkeypatch.setattr(
        wetsanalyse_api, "_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    settings = make_settings(wetsanalyse_api_url="http://api.local")
    llm = _annotatieketen_llm()
    graph = FakeGraph(result=_CORPUS_TSV)

    async def _run() -> list[dict]:
        return [
            e
            async for e in voer_annotatie_beurt_uit(
                settings=settings,
                llm=llm,
                graph=graph,
                doel={"bwbId": "BWBR0004770", "artikel": "1"},
                werkgebied="sociaal",
                gebruiker="jurist-1",
            )
        ]

    events = asyncio.run(_run())

    opgeslagen = next(e for e in events if e["type"] == "opgeslagen")
    assert opgeslagen["slug"] == "doc-1"
    assert opgeslagen["aanvaard"] == 1
    assert any(p.endswith("/documenten") for p in aangeroepen)
    assert any(p.endswith("/documenten/doc-1/elementen") for p in aangeroepen)
    assert events[-1]["type"] == "done"


def test_wegschrijffout_geeft_waarschuwing_geen_error(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(
        wetsanalyse_api, "_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    settings = make_settings(wetsanalyse_api_url="http://api.local")
    llm = _annotatieketen_llm()
    graph = FakeGraph(result=_CORPUS_TSV)

    async def _run() -> list[dict]:
        return [
            e
            async for e in voer_annotatie_beurt_uit(
                settings=settings,
                llm=llm,
                graph=graph,
                doel={"bwbId": "BWBR0004770", "artikel": "1"},
                werkgebied="sociaal",
                gebruiker="jurist-1",
            )
        ]

    events = asyncio.run(_run())

    types = [e["type"] for e in events]
    assert "waarschuwing" in types
    assert "error" not in types
    assert types[-1] == "done"
