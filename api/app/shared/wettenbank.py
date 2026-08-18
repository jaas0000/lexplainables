"""Wettenbank-MCP client — deterministisch ophalen via HTTP JSON-RPC (story 024).

Dezelfde HTTP-aanroep als wetcatalogus/router.py (JSON-RPC POST naar WETTENBANK_MCP_URL),
maar dan voor `wettenbank_artikel`. Lege of fout-respons → WettenbankFout: doorgaan met
lege context is verboden (brongetrouwheidseis).

Gedeelde module (feature-bouwen regel 8): geen eigenaar-feature — meerdere features kunnen
wettenbank-ophalingen nodig hebben.
"""

from __future__ import annotations

import json
import os

import httpx

WETTENBANK_MCP_URL = os.getenv("WETTENBANK_MCP_URL", "http://localhost:8000")
_TIMEOUT = 30.0


class WettenbankFout(RuntimeError):
    """Ophalen mislukte of leverde niets bruikbaars — analyse moet stoppen."""


async def haal_artikel_op(bwb_id: str, artikel: str, lid: str | None) -> dict:
    """Haal de tekst van één artikel op via de Wettenbank-MCP.

    Geeft een dict terug met (minimaal):
      bwbId, artikel, lid, wet, versiedatum, bronreferentie, leden: [{lid, tekst}]

    Werpt WettenbankFout bij netwerk-/MCP-/parseerfout of lege leden-lijst.
    """
    args: dict = {"bwbId": bwb_id, "artikel": artikel}
    if lid:
        args["lid"] = lid

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "wettenbank_artikel", "arguments": args},
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
        raise WettenbankFout(
            f"Wettenbank niet bereikbaar voor {bwb_id} art. {artikel}: {exc}"
        ) from exc

    if not resp.is_success:
        raise WettenbankFout(f"Wettenbank HTTP {resp.status_code} voor {bwb_id} art. {artikel}")

    data = resp.json()

    if "error" in data:
        raise WettenbankFout(f"Wettenbank-fout voor {bwb_id} art. {artikel}: {data['error']}")

    # Parseer MCP-tool-result: content-blokken met type=text bevatten JSON.
    result = data.get("result", {})
    content = result.get("content", []) if isinstance(result, dict) else []
    for blok in content:
        if not isinstance(blok, dict) or blok.get("type") != "text":
            continue
        try:
            artikel_data = json.loads(blok["text"])
        except (json.JSONDecodeError, KeyError):
            continue
        if isinstance(artikel_data, dict) and artikel_data.get("is_error"):
            raise WettenbankFout(f"Artikel {bwb_id} art. {artikel} niet gevonden in de Wettenbank.")
        if isinstance(artikel_data, dict):
            leden = artikel_data.get("leden", [])
            if not leden:
                raise WettenbankFout(
                    f"Artikel {bwb_id} art. {artikel}: geen leden in de Wettenbank-respons."
                )
            return artikel_data

    raise WettenbankFout(
        f"Kan geen bruikbare data parsen uit de Wettenbank-respons voor {bwb_id} art. {artikel}."
    )
