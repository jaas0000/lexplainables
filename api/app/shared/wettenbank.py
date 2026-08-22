"""Wettenbank-lookup client — deterministisch ophalen via HTTP JSON-RPC.

**Architectuur-correctie (2026-08-22, zie ADR-0001 §Consequenties):** deze module praat nu met
een JSON-RPC-service (`WETTENBANK_MCP_URL`) die nooit gebouwd gaat worden — `tools/wettenbank-mcp`
is geschrapt vóórdat dit project ermee begon (zie het fase-4-plan). De referentie-app
(wetsanalyse-ai) heeft de vergelijkbare functionaliteit inmiddels zelfs uit de API-laag
verwijderd; wettekst komt daar rechtstreeks uit een GraphDB-kennisgraaf. Voor lexplainables is de
vastgelegde vervolgrichting: zodra `deploy/graphdb` + `tools/bwb-import` bestaan en gevuld zijn,
wordt `haal_citeertitel_op` een directe (read-only) SPARQL-query tegen de graaf i.p.v. dit
JSON-RPC-protocol. Nog niet omgebouwd — dat is een aparte story zodra er een graaf is om tegen te
bevragen; tot die tijd faalt deze functie in de praktijk altijd (`WettenbankNietBereikbaar`, geen
service luistert op `WETTENBANK_MCP_URL`).

Publieke functie:

- `haal_citeertitel_op` (story 020) — gebruikt door de wetcatalogus-router om de officiële naam
  van een wet op te halen.

Lege of fout-respons → `WettenbankFout` (of een subklasse): doorgaan met lege context is
verboden (brongetrouwheidseis). Twee subklassen zodat callers netwerk/HTTP-fouten van
niet-gevonden kunnen onderscheiden (router → 502 vs. 404):

- `WettenbankNietBereikbaar` — netwerk-/HTTP-probleem, de bron zelf antwoordt niet.
- `WettenbankNietGevonden` — de bron antwoordt, maar de gevraagde entiteit is er niet
  (JSON-RPC `error`-veld, `is_error`-blok, of geen bruikbare content).

Gedeelde module (feature-bouwen regel 8): geen eigenaar-feature.
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
