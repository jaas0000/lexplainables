"""Gedragstests voor de GraphDB-SPARQL-client (story 037).

Geen echte GraphDB nodig: `httpx.MockTransport` injecteert de HTTP-laag (DI-punt in
`haal_wetsartikel_op`, zelfde patroon als bwb-import's injecteerbare `requests.Session`).
"""

from __future__ import annotations

import httpx
import pytest

from app.features.annotatie.graphdb import (
    GraphDbNietBereikbaar,
    WetsartikelNietGevonden,
    _artikel_iri,
    haal_wetsartikel_op,
)


def _binding(**velden: str) -> dict:
    return {sleutel: {"value": waarde} for sleutel, waarde in velden.items()}


def _sparql_response(bindings: list[dict]) -> httpx.Response:
    return httpx.Response(200, json={"results": {"bindings": bindings}})


def test_artikel_iri_percent_encodeert_segmenten() -> None:
    assert _artikel_iri("BWBR0004770", "5a") == "urn:bwb:BWBR0004770:artikel:5a"
    assert _artikel_iri("BWBR0004770", "5:a") == "urn:bwb:BWBR0004770:artikel:5%3Aa"


async def test_haal_wetsartikel_op_met_opschrift_en_leden() -> None:
    bindings = [
        _binding(
            opschrift="Definities",
            tekst="In dit besluit wordt verstaan onder:",
            lidNummer="1",
            lidTekst="a. begrip een;",
        ),
        _binding(
            opschrift="Definities",
            tekst="In dit besluit wordt verstaan onder:",
            lidNummer="2",
            lidTekst="b. begrip twee;",
        ),
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        return _sparql_response(bindings)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        artikel = await haal_wetsartikel_op("BWBR0004770", "1", client=client)

    assert artikel.bwb_id == "BWBR0004770"
    assert artikel.artikel == "1"
    assert artikel.opschrift == "Definities"
    assert artikel.tekst == "In dit besluit wordt verstaan onder:"
    assert [lid.nummer for lid in artikel.leden] == ["1", "2"]
    assert artikel.leden[0].tekst == "a. begrip een;"


async def test_haal_wetsartikel_op_zonder_leden() -> None:
    bindings = [_binding(tekst="Enkele artikeltekst zonder leden.")]

    async def handler(request: httpx.Request) -> httpx.Response:
        return _sparql_response(bindings)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        artikel = await haal_wetsartikel_op("BWBR0004770", "2", client=client)

    assert artikel.opschrift is None
    assert artikel.leden == []


async def test_haal_wetsartikel_op_lege_bindings_geeft_niet_gevonden() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return _sparql_response([])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(WetsartikelNietGevonden):
            await haal_wetsartikel_op("BWBR0004770", "999", client=client)


async def test_haal_wetsartikel_op_netwerkfout_geeft_niet_bereikbaar() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connectie geweigerd", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GraphDbNietBereikbaar):
            await haal_wetsartikel_op("BWBR0004770", "1", client=client)


async def test_haal_wetsartikel_op_http_fout_geeft_niet_bereikbaar() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="interne GraphDB-fout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(GraphDbNietBereikbaar):
            await haal_wetsartikel_op("BWBR0004770", "1", client=client)
