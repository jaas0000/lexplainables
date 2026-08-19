"""Wettenbank-MCP client — deterministisch ophalen via HTTP JSON-RPC.

Gedeelde JSON-RPC-boilerplate (`_jsonrpc_call`) + publieke ophaal-functies:

- `haal_artikel_op` (story 024) — tool `wettenbank_artikel`, gebruikt door de analyse-engine.
- `haal_citeertitel_op` (story 020) — tool `wettenbank_structuur`, gebruikt door de
  wetcatalogus-router om de officiële naam van een wet op te halen.

Lege of fout-respons → `WettenbankFout` (of een subklasse): doorgaan met lege context is
verboden (brongetrouwheidseis). Twee subklassen zodat callers netwerk/HTTP-fouten van
niet-gevonden kunnen onderscheiden (router → 502 vs. 404):

- `WettenbankNietBereikbaar` — netwerk-/HTTP-probleem, de MCP zelf antwoordt niet.
- `WettenbankNietGevonden` — MCP antwoordt, maar de gevraagde entiteit is er niet
  (JSON-RPC `error`-veld, `is_error`-blok, of geen bruikbare content).

Gedeelde module (feature-bouwen regel 8): geen eigenaar-feature — meerdere features hebben
wettenbank-ophalingen nodig.
"""

from __future__ import annotations

import json
import os

import httpx

WETTENBANK_MCP_URL = os.getenv("WETTENBANK_MCP_URL", "http://localhost:8000")
_TIMEOUT = 30.0


class WettenbankFout(RuntimeError):
    """Ophalen mislukte of leverde niets bruikbaars — analyse moet stoppen."""


class WettenbankNietBereikbaar(WettenbankFout):
    """Netwerk- of HTTP-fout — de Wettenbank-MCP zelf antwoordt niet (correct)."""


class WettenbankNietGevonden(WettenbankFout):
    """Wettenbank antwoordt, maar de gevraagde entiteit is er niet."""


async def _jsonrpc_call(method: str, arguments: dict, *, foutcontext: str) -> list[dict]:
    """Doe een JSON-RPC-`tools/call` op de Wettenbank-MCP en geef de content-blokken terug.

    Werpt `WettenbankNietBereikbaar` bij netwerk- of HTTP-fouten, en `WettenbankNietGevonden`
    bij een JSON-RPC-`error`-veld. Het parsen van de content-blokken zelf is aan de aanroeper
    — dat is per tool anders.
    """
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": method, "arguments": arguments},
        "id": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{WETTENBANK_MCP_URL}/",
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
        raise WettenbankNietBereikbaar(
            f"Wettenbank niet bereikbaar voor {foutcontext}: {exc}"
        ) from exc

    if not resp.is_success:
        raise WettenbankNietBereikbaar(f"Wettenbank HTTP {resp.status_code} voor {foutcontext}")

    data = resp.json()

    if "error" in data:
        raise WettenbankNietGevonden(f"Wettenbank-fout voor {foutcontext}: {data['error']}")

    result = data.get("result", {})
    return result.get("content", []) if isinstance(result, dict) else []


def _tekstblokken(content: list[dict]):
    """Yield de JSON-payloads uit alle content-blokken van type `text`."""
    for blok in content:
        if not isinstance(blok, dict) or blok.get("type") != "text":
            continue
        try:
            data = json.loads(blok["text"])
        except (json.JSONDecodeError, KeyError):
            continue
        if isinstance(data, dict):
            yield data


async def haal_artikel_op(bwb_id: str, artikel: str, lid: str | None) -> dict:
    """Haal de tekst van één artikel op via de Wettenbank-MCP.

    Geeft een dict terug met (minimaal):
      bwbId, artikel, lid, wet, versiedatum, bronreferentie, leden: [{lid, tekst}]

    Werpt `WettenbankFout` (of subklasse) bij netwerk-/MCP-/parseerfout of lege leden-lijst.
    """
    args: dict = {"bwbId": bwb_id, "artikel": artikel}
    if lid:
        args["lid"] = lid

    foutcontext = f"{bwb_id} art. {artikel}"
    content = await _jsonrpc_call("wettenbank_artikel", args, foutcontext=foutcontext)

    for artikel_data in _tekstblokken(content):
        if artikel_data.get("is_error"):
            raise WettenbankNietGevonden(f"Artikel {foutcontext} niet gevonden in de Wettenbank.")
        leden = artikel_data.get("leden", [])
        if not leden:
            raise WettenbankFout(f"Artikel {foutcontext}: geen leden in de Wettenbank-respons.")
        return artikel_data

    raise WettenbankFout(
        f"Kan geen bruikbare data parsen uit de Wettenbank-respons voor {foutcontext}."
    )


async def haal_citeertitel_op(bwb_id: str) -> str:
    """Haal de officiële citeertitel van een wet op via de Wettenbank-MCP.

    Werpt `WettenbankNietBereikbaar` bij netwerk-/HTTP-fouten (router → 502) en
    `WettenbankNietGevonden` als de wet niet in de Wettenbank staat of de respons niets
    bruikbaars bevat (router → 404).
    """
    content = await _jsonrpc_call("wettenbank_structuur", {"bwbId": bwb_id}, foutcontext=bwb_id)

    for payload_data in _tekstblokken(content):
        if payload_data.get("is_error"):
            raise WettenbankNietGevonden(f"Wet {bwb_id} niet gevonden in de Wettenbank.")
        citeertitel = (
            payload_data.get("citeertitel") or payload_data.get("titel") or payload_data.get("naam")
        )
        if citeertitel:
            return str(citeertitel)

    raise WettenbankNietGevonden(f"Wet {bwb_id} niet gevonden in de Wettenbank.")
