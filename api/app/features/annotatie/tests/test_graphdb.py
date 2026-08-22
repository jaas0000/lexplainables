"""Gedragstests voor de GraphDB-SPARQL-client (story 037, uitgebreid met onderdelen/bepaling-
fallback na vergelijking met wetsanalyse-ai's `graph-qa`-agent).

Geen echte GraphDB nodig: `httpx.MockTransport` injecteert de HTTP-laag (DI-punt in
`haal_wetsartikel_op`, zelfde patroon als bwb-import's injecteerbare `requests.Session`).
"""

from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest

from app.features.annotatie.graphdb import (
    GraphDbNietBereikbaar,
    WetsartikelNietGevonden,
    _artikel_iri,
    _sorteersleutel,
    haal_wetsartikel_op,
)


def _binding(**velden: str) -> dict:
    return {sleutel: {"value": waarde} for sleutel, waarde in velden.items()}


def _sparql_response(bindings: list[dict]) -> httpx.Response:
    return httpx.Response(200, json={"results": {"bindings": bindings}})


def _query_uit(request: httpx.Request) -> str:
    """De verzonden SPARQL-tekst uit een form-urlencoded POST-body (`data={"query": ...}`)."""
    return parse_qs(request.content.decode())["query"][0]


def test_artikel_iri_percent_encodeert_segmenten() -> None:
    assert _artikel_iri("BWBR0004770", "5a") == "urn:bwb:BWBR0004770:artikel:5a"
    assert _artikel_iri("BWBR0004770", "5:a") == "urn:bwb:BWBR0004770:artikel:5%3Aa"


def test_sorteersleutel_numeriek_niet_lexicaal() -> None:
    genummerd = sorted(["10", "2", "1"], key=_sorteersleutel)
    assert genummerd == ["1", "2", "10"]


async def test_haal_wetsartikel_op_met_opschrift_en_leden() -> None:
    bindings = [
        _binding(
            opschrift="Definities",
            tekst="In dit besluit wordt verstaan onder:",
            lid="urn:bwb:BWBR0004770:artikel:1:lid:1",
            lidNummer="1",
            lidTekst="a. begrip een;",
        ),
        _binding(
            opschrift="Definities",
            tekst="In dit besluit wordt verstaan onder:",
            lid="urn:bwb:BWBR0004770:artikel:1:lid:2",
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
    assert artikel.leden[0].onderdelen == []


async def test_haal_wetsartikel_op_leden_numeriek_gesorteerd() -> None:
    """Tien leden — lexicale sortering zou lid 10 vóór lid 2 zetten (regressietest)."""
    bindings = [
        _binding(
            lid=f"urn:bwb:BWBR0004770:artikel:1:lid:{n}", lidNummer=str(n), lidTekst=f"Lid {n}."
        )
        for n in (10, 2, 1)
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        return _sparql_response(bindings)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        artikel = await haal_wetsartikel_op("BWBR0004770", "1", client=client)

    assert [lid.nummer for lid in artikel.leden] == ["1", "2", "10"]


async def test_haal_wetsartikel_op_onderdelen_onder_lid() -> None:
    """Definitieartikel: lid 1 heeft nauwelijks eigen tekst, de definities zitten in de
    onderdelen (zie Invorderingswet art. 2 lid 1 — het gat dat deze uitbreiding dichtte)."""
    bindings = [
        _binding(
            tekst="",
            lid="urn:bwb:BWBR0004770:artikel:2:lid:1",
            lidNummer="1",
            lidTekst="Deze wet verstaat onder:",
            onderdeel="urn:bwb:BWBR0004770:artikel:2:lid:1:o:b",
            onderdeelNummer="b.",
            onderdeelTekst="belastingrente: de rente, bedoeld in hoofdstuk VA.",
        ),
        _binding(
            tekst="",
            lid="urn:bwb:BWBR0004770:artikel:2:lid:1",
            lidNummer="1",
            lidTekst="Deze wet verstaat onder:",
            onderdeel="urn:bwb:BWBR0004770:artikel:2:lid:1:o:a",
            onderdeelNummer="a.",
            onderdeelTekst="rijksbelastingen: belastingen als bedoeld in artikel 1.",
        ),
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        return _sparql_response(bindings)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        artikel = await haal_wetsartikel_op("BWBR0004770", "2", client=client)

    assert len(artikel.leden) == 1
    onderdelen = artikel.leden[0].onderdelen
    assert [o.nummer for o in onderdelen] == ["a.", "b."]
    assert onderdelen[0].tekst.startswith("rijksbelastingen")


async def test_haal_wetsartikel_op_onderdelen_direct_onder_artikel_zonder_leden() -> None:
    """Eerste call (leden-query) levert alleen een `?onderdeel`-rij zonder `?lid` — geen leden,
    dus de client valt terug op de aparte artikel-onderdelen-query."""
    hoofdbindings = [_binding(tekst="")]
    onderdelen_bindings = [
        _binding(
            onderdeel="urn:bwb:BWBR0004770:artikel:9:o:a",
            onderdeelNummer="a",
            onderdeelTekst="eerste onderdeel",
        ),
        _binding(
            onderdeel="urn:bwb:BWBR0004770:artikel:9:o:b",
            onderdeelNummer="b",
            onderdeelTekst="tweede onderdeel",
        ),
    ]
    aanroepen = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal aanroepen
        aanroepen += 1
        return _sparql_response(hoofdbindings if aanroepen == 1 else onderdelen_bindings)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        artikel = await haal_wetsartikel_op("BWBR0004770", "9", client=client)

    assert artikel.leden == []
    assert [o.nummer for o in artikel.onderdelen] == ["a", "b"]
    assert aanroepen == 2


async def test_haal_wetsartikel_op_zonder_leden_en_zonder_onderdelen() -> None:
    hoofdbindings = [_binding(tekst="Enkele artikeltekst zonder leden.")]

    async def handler(request: httpx.Request) -> httpx.Response:
        return _sparql_response(hoofdbindings if "heeftLid" in _query_uit(request) else [])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        artikel = await haal_wetsartikel_op("BWBR0004770", "2", client=client)

    assert artikel.opschrift is None
    assert artikel.leden == []
    assert artikel.onderdelen == []


async def test_haal_wetsartikel_op_valt_terug_op_bepaling_bij_decimaal_nummer() -> None:
    """Een circulaire/beleidsregel-bepaling ('9.1') heeft geen `bwb:Artikel`-node op het
    artikel-IRI-patroon — de eerste query levert niets, de bepaling-fallback zoekt op nummer."""

    async def handler(request: httpx.Request) -> httpx.Response:
        query = _query_uit(request)
        if "a bwb:Artikel" in query:
            return _sparql_response([])
        assert '"9.1"' in query
        return _sparql_response(
            [_binding(tekst="Tekst van bepaling 9.1.", opschrift="Toelichting")]
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        artikel = await haal_wetsartikel_op("BWBR0004770", "9.1", client=client)

    assert artikel.tekst == "Tekst van bepaling 9.1."
    assert artikel.opschrift == "Toelichting"
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
