"""Client naar lexplainables' eigen `api`-service — schrijft een afgeronde annotatiebeurt weg
(document + elementen), zodat de jurist het resultaat in de werkplek terugziet.

Poort van `wetsanalyse-ai/tools/graph-qa/agent/wetsanalyse_api.py`, met één architectuur-
aanpassing: de contractgrens hier is `api/app/features/annotatie/`, niet de referentie se eigen
`/v1/annotatie/*`-vorm — velden komen dus 1:1 overeen qua betekenis maar zijn hier tegen
lexplainables' eigen Pydantic-modellen (`api/app/features/annotatie/models.py`) getoetst.

**Contractgrens**: `naar_contract()` vertaalt graph-qa's voorstel-vorm (plain dicts, uit
`AnnotatieVoorstel.model_dump()`) naar wat `api` verwacht. Twee concrete verschillen:
- `aandacht`/`critic` (top-level): hier `str = ""` als "geen oordeel"; `api` gebruikt
  `Aandacht | None` (`None` = "geen oordeel"). Lege string → `None`.
- Alternatieven: hier `{"klasse", "motivatie"}`; `api` verwacht `{"klasse", "tekst", "toelichting"}`
  (geen los `tekst`-veld op een alternatief in graph-qa's eigen model — hetzelfde fragment als het
  hoofdvoorstel, dus die vullen we hier bij).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import Settings

logger = logging.getLogger("graph_qa.wetsanalyse_api")

_TIMEOUT = 30.0

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Proces-brede lazy singleton — zelfde patroon als `api/app/shared/wettenbank.py` en
    lexplainables' eigen `chat_proxy/client.py`. Tests monkeypatchen deze module-globale."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_TIMEOUT)
    return _client


class WetsanalyseApiFout(RuntimeError):
    """De api antwoordde niet, of niet zoals verwacht — de beurt gaat door, het schrijven niet."""


def naar_contract(voorstel: dict[str, Any]) -> dict[str, Any]:
    """Vertaal één graph-qa-voorstel naar `api`'s `ElementInvoer`-vorm."""
    hoofdtekst = voorstel.get("tekst", "")
    return {
        "id": voorstel.get("id", ""),
        "klasse": voorstel.get("klasse", ""),
        "tekst": hoofdtekst,
        "lid": voorstel.get("lid", ""),
        "toelichting": voorstel.get("toelichting", ""),
        "vindplaats": voorstel.get("vindplaats", ""),
        "alternatieven": [
            {
                "klasse": a.get("klasse", ""),
                "tekst": hoofdtekst,
                "toelichting": a.get("motivatie", ""),
            }
            for a in voorstel.get("alternatieven") or []
        ],
        "aandacht": voorstel.get("aandacht") or None,
        "critic": voorstel.get("critic") or None,
        "critic_rondes": voorstel.get("critic_rondes") or [],
    }


def _headers(settings: Settings, gebruiker: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.wetsanalyse_api_token or ''}",
        "X-User-Id": gebruiker,
    }


async def maak_document(
    settings: Settings,
    *,
    werkgebied: str,
    bwb_id: str,
    artikel: str,
    lid: str,
    gebruiker: str,
) -> str:
    """Maak een nieuw annotatiedocument aan en geef de `slug` terug."""
    body = {"werkgebied": werkgebied, "bwb_id": bwb_id, "artikel": artikel, "lid": lid or None}
    url = f"{settings.wetsanalyse_api_url}/v1/annotatie/documenten"
    try:
        resp = await _get_client().post(url, json=body, headers=_headers(settings, gebruiker))
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
        raise WetsanalyseApiFout(f"api niet bereikbaar voor maak_document: {exc}") from exc
    if not resp.is_success:
        raise WetsanalyseApiFout(f"api HTTP {resp.status_code} voor maak_document: {resp.text}")
    return resp.json()["slug"]


async def zet_elementen(
    settings: Settings,
    *,
    slug: str,
    voorstellen: list[dict[str, Any]],
    run_info: dict[str, Any],
    gebruiker: str,
) -> tuple[int, int]:
    """Schrijf de voorstellen van deze beurt weg. Geeft `(aanvaard, verworpen)` terug."""
    body = {
        "elementen": [naar_contract(v) for v in voorstellen if not v.get("van_jurist")],
        "run": run_info,
    }
    url = f"{settings.wetsanalyse_api_url}/v1/annotatie/documenten/{slug}/elementen"
    try:
        resp = await _get_client().put(url, json=body, headers=_headers(settings, gebruiker))
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
        raise WetsanalyseApiFout(f"api niet bereikbaar voor zet_elementen: {exc}") from exc
    if not resp.is_success:
        raise WetsanalyseApiFout(f"api HTTP {resp.status_code} voor zet_elementen: {resp.text}")
    data = resp.json()
    return data["aanvaard"], data["verworpen"]
