"""Voert één `doel`-gedreven annotatiebeurt uit en schrijft het resultaat naar `api` weg.

Poort van `wetsanalyse-ai/tools/graph-qa/agent/beurt.py`, sterk versmald: geen SSE-narratie
(`status`/`reason`-events — die bestaan hier nog niet, zie story 051 §Afwijkingen), geen
`GesprekVerdwenen`-afhandeling (lexplainables heeft geen `/v1/gesprekken`-domein), geen
`X-Verworpen`-header-uitlezing (`agent/wetsanalyse_api.py::zet_elementen` leest het al uit de
JSON-body). Wat overblijft is de kern: de annotatieketen draait volledig in-memory (LangGraph),
en **pas aan het eind** — als `emit_node` een finale structuur heeft — wordt er geschreven. Een
document dat al bij de start ontstond, bleef bij een afgebroken beurt eerder als leeg skelet
achter; dat risico bestaat hier niet, want er is nog geen tussentijds schrijfmoment.

Zonder `settings.legt_zelf_vast` (geen `WETSANALYSE_API_URL`) is dit een doorgeefluik: de
annotatieketen draait, maar er wordt niets weggeschreven — dezelfde graceful-degradation als de
referentie.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from .agent_common import BeurtGestopt
from .config import Settings
from .orchestrator import State, build_graph, nieuwe_beurt_invoer
from .ports import GraphPort, LLMPort
from .wetsanalyse_api import WetsanalyseApiFout, maak_document, zet_elementen

logger = logging.getLogger("graph_qa.beurt")


async def voer_annotatie_beurt_uit(
    *,
    settings: Settings,
    llm: LLMPort,
    graph: GraphPort,
    doel: dict[str, str],
    werkgebied: str,
    gebruiker: str,
    stop_check: Any = None,
) -> AsyncIterator[dict[str, Any]]:
    """Draait de annotatieketen voor `doel` (`{bwbId, artikel, lid?}`) en schrijft het resultaat
    weg naar `api` (tenzij `settings.legt_zelf_vast` False is). Yields SSE-events:
      {"type": "doel", "doel": {...}}
      {"type": "element", ...}  (per voorgesteld JAS-element)
      {"type": "opgeslagen", "slug": "...", "aanvaard": int, "verworpen": int}
      {"type": "waarschuwing", "message": "..."}  (schrijven mislukte — de beurt zelf slaagde wel)
      {"type": "done"}
      {"type": "error", "message": "..."}
    """
    yield {"type": "doel", "doel": doel}

    try:
        app = build_graph(settings, llm, graph, stop_check=stop_check)
        eindstate: State = await app.ainvoke(nieuwe_beurt_invoer(doel=doel))
    except BeurtGestopt:
        logger.info("annotatiebeurt gestopt op verzoek")
        yield {"type": "done"}
        return
    except Exception:
        logger.error("annotatiebeurt mislukt", exc_info=True)
        yield {
            "type": "error",
            "message": "Er ging iets mis bij het annoteren. Probeer het opnieuw.",
        }
        return

    voorstellen = eindstate.get("voorstellen") or []
    for voorstel in voorstellen:
        yield {"type": "element", **voorstel}

    if not voorstellen:
        yield {"type": "done"}
        return

    if not settings.legt_zelf_vast:
        yield {"type": "done"}
        return

    run_info = {
        "model": settings.llm_model,
        "provider": "azure-foundry",
        "agent_versie": settings.agent_versie,
        "critic_rondes": int(eindstate.get("critic_ronde") or 0),
        "stop_reden": "",
    }
    try:
        slug = await maak_document(
            settings,
            werkgebied=werkgebied,
            bwb_id=doel.get("bwbId", ""),
            artikel=doel.get("artikel", ""),
            lid=doel.get("lid", ""),
            gebruiker=gebruiker,
        )
        aanvaard, verworpen = await zet_elementen(
            settings,
            slug=slug,
            voorstellen=voorstellen,
            run_info=run_info,
            gebruiker=gebruiker,
        )
    except WetsanalyseApiFout as exc:
        logger.warning("wegschrijven naar api mislukt", exc_info=True)
        yield {"type": "waarschuwing", "message": str(exc)}
        yield {"type": "done"}
        return

    yield {"type": "opgeslagen", "slug": slug, "aanvaard": aanvaard, "verworpen": verworpen}
    yield {"type": "done"}
