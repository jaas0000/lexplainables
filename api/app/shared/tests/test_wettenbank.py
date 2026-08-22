"""Gedragstests voor de Wettenbank-JSON-RPC-client (had nog geen dekking).

Geen echte Wettenbank-MCP nodig: `httpx.MockTransport` injecteert de HTTP-laag op de
proces-brede client (`_get_client()`) via monkeypatch van de module-globale `_client`.
"""

from __future__ import annotations

import httpx
import pytest

import app.shared.wettenbank as wettenbank
from app.shared.wettenbank import (
    WettenbankNietBereikbaar,
    WettenbankNietGevonden,
    haal_citeertitel_op,
)


def _jsonrpc_result(content: list[dict]) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {"content": content}})


def _tekstblok(payload: dict) -> dict:
    import json

    return {"type": "text", "text": json.dumps(payload)}


@pytest.fixture(autouse=True)
def _reset_client(monkeypatch):
    """Elke test krijgt een schone `_client`-singleton, anders lekt de mock-transport van de
    vorige test door (module-globaal, net als `db.py::get_engine`)."""
    monkeypatch.setattr(wettenbank, "_client", None)
    yield
    monkeypatch.setattr(wettenbank, "_client", None)


def _monkeypatch_transport(monkeypatch, handler) -> None:
    monkeypatch.setattr(
        wettenbank, "_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )


async def test_haal_citeertitel_op_gelukkig_pad(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return _jsonrpc_result([_tekstblok({"citeertitel": "Invorderingswet 1990"})])

    _monkeypatch_transport(monkeypatch, handler)

    assert await haal_citeertitel_op("BWBR0004770") == "Invorderingswet 1990"


async def test_haal_citeertitel_op_valt_terug_op_titel_of_naam(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return _jsonrpc_result([_tekstblok({"naam": "Algemene wet inzake rijksbelastingen"})])

    _monkeypatch_transport(monkeypatch, handler)

    assert await haal_citeertitel_op("BWBR0002320") == "Algemene wet inzake rijksbelastingen"


async def test_haal_citeertitel_op_netwerkfout_geeft_niet_bereikbaar(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connectie geweigerd", request=request)

    _monkeypatch_transport(monkeypatch, handler)

    with pytest.raises(WettenbankNietBereikbaar):
        await haal_citeertitel_op("BWBR0004770")


async def test_haal_citeertitel_op_http_fout_geeft_niet_bereikbaar(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="interne MCP-fout")

    _monkeypatch_transport(monkeypatch, handler)

    with pytest.raises(WettenbankNietBereikbaar):
        await haal_citeertitel_op("BWBR0004770")


async def test_haal_citeertitel_op_jsonrpc_error_geeft_niet_gevonden(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "onbekend"}}
        )

    _monkeypatch_transport(monkeypatch, handler)

    with pytest.raises(WettenbankNietGevonden):
        await haal_citeertitel_op("BWBR9999999")


async def test_haal_citeertitel_op_is_error_blok_geeft_niet_gevonden(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return _jsonrpc_result([_tekstblok({"is_error": True})])

    _monkeypatch_transport(monkeypatch, handler)

    with pytest.raises(WettenbankNietGevonden):
        await haal_citeertitel_op("BWBR9999999")


async def test_haal_citeertitel_op_lege_content_geeft_niet_gevonden(monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return _jsonrpc_result([])

    _monkeypatch_transport(monkeypatch, handler)

    with pytest.raises(WettenbankNietGevonden):
        await haal_citeertitel_op("BWBR9999999")
