"""Agent-instap: dunne wrapper rond de LangGraph-orkestrator (`agent/orchestrator.py`).

`answer_stream()` levert het SSE-event-contract (werkwijze-story 051) als Python-generator — nog
**geen HTTP**, dat is de eerstvolgende API-laag-story (`tools/graph-qa/api/` is nu een leeg
skelet). Poort van `wetsanalyse-ai/tools/graph-qa/agent/agent.py`, bewust smal: geen
observability/runs-model — zie `docs/project/stories/051-graph-qa-streaming.md` §Afwijkingen.
Story 052 voegt `stop_check` door: een aanroeper kan een lopende beurt op een nodegrens laten
stoppen (`BeurtGestopt`) — er is hier nog geen aanroeper die 'm daadwerkelijk zet, dat wacht op
het latere runs-model, zie `docs/project/stories/052-graph-qa-stop-check.md`.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any

from langgraph.errors import GraphRecursionError

from .agent_common import BeurtGestopt
from .checkpointer import checkpointer_ctx
from .config import Settings
from .orchestrator import State, build_graph, nieuwe_beurt_invoer
from .ports import GraphPort, LLMPort

logger = logging.getLogger("graph_qa.agent")


def _foutmelding(exc: Exception) -> str:
    """Wat de jurist te zien krijgt als een beurt sneuvelt — per soort fout iets anders.

    De provider-uitzonderingen worden op naam herkend i.p.v. geïmporteerd: de anthropic-SDK is
    een optionele extra (`--extra llm`), en deze module hoort ook te draaien in een omgeving die
    hem niet heeft.
    """
    soort = type(exc).__name__
    if soort == "RateLimitError":
        return (
            "De modelprovider is momenteel overbelast. Probeer het over een halve minuut "
            "opnieuw — je vraag is niet verloren, hij is alleen niet uitgevoerd."
        )
    if soort in ("BadRequestError", "UnprocessableEntityError"):
        return (
            "Deze beurt paste niet binnen de grenzen van het model — meestal is het gesprek te "
            "lang geworden. Begin een nieuw gesprek of stel de vraag gerichter."
        )
    if soort in ("APIConnectionError", "APITimeoutError"):
        return (
            "Ik kon de modelprovider niet bereiken. Probeer het zo opnieuw; blijft het "
            "misgaan, dan staat de oorzaak in het server-log."
        )
    return (
        "Er ging iets mis bij het beantwoorden. Probeer het opnieuw; blijft het misgaan, dan "
        "staat de oorzaak in het server-log."
    )


async def answer_stream(
    question: str,
    conversation_id: str | None = None,
    *,
    settings: Settings | None = None,
    llm: LLMPort | None = None,
    graph: GraphPort | None = None,
    stop_check: Callable[[], bool] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Async generator die SSE-events yield:
    {"type": "token", "content": "..."}
    {"type": "sources", "sources": [...]}
    {"type": "grounding", "grounded": bool, "niveau": "...", "unsupported": [...]}
    {"type": "conversation_id", "conversation_id": "..."}
    {"type": "done"}
    {"type": "error", "message": "..."}
    """
    settings = settings or Settings.from_env()

    try:
        if graph is None:
            from .adapters.graphdb_graph import make_graph

            graph = make_graph(settings)
        if llm is None:
            from .adapters.anthropic_llm import AnthropicLLM

            llm = AnthropicLLM(settings)
    except Exception as exc:
        logger.warning("providers konden niet gebouwd worden", exc_info=True)
        yield {"type": "error", "message": f"Verbinding mislukt: {exc}"}
        return

    thread_id = conversation_id or uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}
    invoer = nieuwe_beurt_invoer(question=question)

    laatste_state: State = {}
    try:
        async with checkpointer_ctx(settings) as saver:
            app = build_graph(settings, llm, graph, checkpointer=saver, stop_check=stop_check)
            async for mode, chunk in app.astream(
                invoer, config=config, stream_mode=["custom", "values"]
            ):
                if mode == "custom":
                    yield chunk
                elif mode == "values":
                    laatste_state = chunk

            yield {"type": "sources", "sources": laatste_state.get("sources", [])}
            yield {
                "type": "grounding",
                "grounded": laatste_state.get("grounded", True),
                "niveau": laatste_state.get("grounding_niveau", ""),
                "unsupported": laatste_state.get("unsupported", []),
            }
            if conversation_id:
                yield {"type": "conversation_id", "conversation_id": conversation_id}
            yield {"type": "done"}

    except BeurtGestopt:
        # Geen fout: de jurist vroeg om te stoppen en de graaf is op een nodegrens uitgestapt.
        # Wat er tot hier geëmit is (tokens) blijft geldig; `sources`/`grounding` slaan we over —
        # de beurt kwam nooit bij `finalize`/`emit`, dus die velden voegen niets toe.
        logger.info(
            "beurt gestopt op verzoek",
            extra={"chat_session_id": conversation_id or ""},
        )
        if conversation_id:
            yield {"type": "conversation_id", "conversation_id": conversation_id}
        yield {"type": "done"}
    except GraphRecursionError:
        logger.warning(
            "beurt raakte de stappenlimiet",
            extra={"chat_session_id": conversation_id or ""},
        )
        yield {
            "type": "error",
            "message": "Deze beurt werd te lang en is afgebroken. Stel de vraag gerichter — "
            "bijvoorbeeld met een specifiek artikel of lid.",
        }
    except Exception as exc:
        logger.error("agent-fout", exc_info=True)
        yield {"type": "error", "message": _foutmelding(exc)}
    finally:
        graph.close()
