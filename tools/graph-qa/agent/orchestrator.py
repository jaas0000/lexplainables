"""Minimale antwoord-agent-loop (LangGraph) — werkwijze-story 044.

De eerste snede die de drie losse bouwstenen (`ports.py`/story 029, `AnthropicLLM`/story 039,
`MCPClient`/story 040, de toollaag/story 041) daadwerkelijk samenvoegt tot een werkende agent:
vraag in, tools aanroepen, antwoord formuleren, op brongetrouwheid controleren.

Bewust **geen** supervisor, annotatieketen, decompositie, checkpointer/gespreksgeheugen of
streaming — dit is exact de "legacy"-graafvariant die de `wetsanalyse-ai`-referentie zelf nog
aanbiedt (`enable_planning=False, enable_decomposition=False`):

    START → agent_node ⇄ tools_node → verify_node → (correct_node → agent_node
                                                       | finalize_node) → END

Elk van die weggelaten onderdelen is een eigen, latere story — zie
`docs/project/stories/044-graph-qa-antwoord-loop.md` §Afwijkingen voor de reden per punt.
"""

from __future__ import annotations

import logging
import operator
from functools import partial
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from . import prompts
from .config import Settings
from .grounding import check_grounding, curate_sources
from .models import Source
from .ports import GraphPort, LLMPort
from .provenance import collect_sources
from .tools import anthropic_schemas, dispatch

logger = logging.getLogger("graph_qa.orchestrator")

# Vangnet tegen een oneindige tool-lus. Op de laatste toegestane beurt wordt een openstaande
# tool_use genegeerd i.p.v. gepersisteerd — anders belandt een assistant(tool_use)-bericht zonder
# bijbehorend tool_result in de messages-historie, en weigert Anthropic de volgende call (orphan
# tool_use).
MAX_TURNS = 8

# Een los tool-resultaat wordt hierop afgekapt vóór het de trace/messages in gaat, zodat één
# uitgebreide graafquery de prompt niet laat exploderen.
_MAX_TOOL_RESULT_CHARS = 8000

_MAX_TOKENS = 4096


def _truncate(text: str, max_chars: int = _MAX_TOOL_RESULT_CHARS) -> str:
    if len(text) > max_chars:
        return text[:max_chars] + f"\n...[resultaat ingekort op {max_chars} tekens]"
    return text


class State(TypedDict, total=False):
    question: str
    messages: Annotated[list[dict[str, Any]], operator.add]
    source_trace: list[tuple[str, str]]
    answer: str
    pending_tools: list[dict[str, Any]]
    turns: int
    corrected: bool
    grounded: bool
    cited: list[str]
    unsupported: list[str]
    niet_letterlijk: list[str]
    grounding_niveau: str
    sources: list[Source]


def _parse_final(final: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Splits een Anthropic-response in (tool_uses, text_parts)."""
    tool_uses: list[dict[str, Any]] = []
    text_parts: list[str] = []
    for block in final.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_uses.append({"id": block.id, "name": block.name, "input": block.input})
    return tool_uses, text_parts


def agent_node(state: State, *, settings: Settings, llm: LLMPort) -> dict[str, Any]:
    # Eerste beurt: `messages` is nog leeg, dus de vraag wordt hier gezaaid — en die zaai-message
    # gaat ook mee in de return-delta (via de append-reducer), anders bestaat hij alleen lokaal en
    # ontbreekt de user-vraag in de state zodra een volgende node (tools_node) zijn eigen delta
    # toevoegt.
    bestaand = state.get("messages") or []
    zaai = [] if bestaand else [{"role": "user", "content": state["question"]}]
    messages = bestaand + zaai

    final = llm.create(
        model=settings.llm_model,
        max_tokens=_MAX_TOKENS,
        system=prompts.SYSTEM_PROMPT,
        tools=anthropic_schemas(),
        messages=messages,
    )
    tool_uses, text_parts = _parse_final(final)
    turns = state.get("turns", 0) + 1
    if tool_uses and turns >= MAX_TURNS:
        tool_uses = []

    assistant_content: list[dict[str, Any]] = [{"type": "text", "text": t} for t in text_parts if t]
    assistant_content += [
        {"type": "tool_use", "id": t["id"], "name": t["name"], "input": t["input"]}
        for t in tool_uses
    ]

    return {
        "answer": "".join(text_parts),
        "messages": zaai + [{"role": "assistant", "content": assistant_content}],
        "pending_tools": tool_uses,
        "turns": turns,
    }


def tools_node(state: State, *, settings: Settings, graph: GraphPort) -> dict[str, Any]:
    trace = list(state.get("source_trace", []))
    results: list[dict[str, Any]] = []
    for tu in state.get("pending_tools", []):
        result_text = _truncate(dispatch(tu["name"], graph, tu["input"], settings))
        trace.append((tu["name"], result_text))
        results.append({"type": "tool_result", "tool_use_id": tu["id"], "content": result_text})
    return {
        "messages": [{"role": "user", "content": results}],
        "source_trace": trace,
        "pending_tools": [],
    }


def verify_node(state: State) -> dict[str, Any]:
    report = check_grounding(state.get("answer", ""), state.get("source_trace", []))
    return {
        "grounded": report.grounded,
        "cited": report.cited,
        "unsupported": report.unsupported,
        "niet_letterlijk": report.niet_letterlijk,
        "grounding_niveau": report.niveau,
    }


def correct_node(state: State) -> dict[str, Any]:
    """Eén herkansing op wat de groundingcontrole afkeurde.

    Benoemt beide dingen die de controle afkeurt — `unsupported` (verzonnen vindplaatsen) en
    `niet_letterlijk` (een citaat dat niet letterlijk in de bron staat) — met een aparte instructie
    per soort. Alleen het eerste noemen is een bug: een antwoord dat enkel op citaten struikelde
    kreeg dan een correctie-call met een lege opsomming.
    """
    unsupported = state.get("unsupported") or []
    niet_letterlijk = state.get("niet_letterlijk") or []

    opdrachten: list[str] = []
    if unsupported:
        opdrachten.append(
            f"Je noemde verwijzing(en) {', '.join(unsupported)} die niet uit de graaf-resultaten "
            "kwamen. Onderbouw ze met de tools of verwijder ze."
        )
    if niet_letterlijk:
        passages = "; ".join(f'"{c[:120]}…"' if len(c) > 120 else f'"{c}"' for c in niet_letterlijk)
        opdrachten.append(
            f"Deze passages staan tussen aanhalingstekens maar niet letterlijk in de opgehaalde "
            f"tekst: {passages}. Herstel ze woord voor woord zoals ze in de bron staan, of haal "
            "de aanhalingstekens weg en geef het in je eigen woorden weer. Weglatingen met "
            "(...), eigen samenvattingen tussen [ ] en vet of cursief binnen een citaat maken "
            "het een parafrase — die presenteer je niet als citaat."
        )

    return {
        "messages": [{"role": "user", "content": "Let op: " + " ".join(opdrachten)}],
        "corrected": True,
        "answer": "",
    }


def finalize_node(state: State) -> dict[str, Any]:
    """Bouwt de bronnenlijst en vangt een stil leeg antwoord op (bv. na een correctie die niets
    opleverde)."""
    antwoord = state.get("answer", "") or ""
    if not antwoord.strip():
        reden = (
            "grounding-correctie leverde geen antwoord"
            if state.get("corrected")
            else "lege antwoordbeurt"
        )
        logger.warning(
            "leeg antwoord in finalize",
            extra={
                "reden": reden,
                "turns": state.get("turns", 0),
                "grounded": state.get("grounded", True),
                "unsupported": state.get("unsupported", []),
                "bronnen": len(state.get("source_trace", []) or []),
            },
        )
        antwoord = (
            "Ik kon op basis van de geraadpleegde bronnen geen antwoord formuleren. De gevonden "
            "bronnen staan hieronder; stel de vraag eventueel gerichter (bijvoorbeeld met een "
            "specifiek artikel of lid)."
        )

    sources = curate_sources(collect_sources(state.get("source_trace", [])), antwoord)
    return {"answer": antwoord, "sources": sources}


def route_after_agent(state: State) -> str:
    if state.get("pending_tools") and state.get("turns", 0) < MAX_TURNS:
        return "tools"
    return "verify"


def route_after_verify(state: State) -> str:
    if state.get("grounding_niveau") == "ongegrond" and not state.get("corrected"):
        return "correct"
    return "finalize"


def build_graph(settings: Settings, llm: LLMPort, graph: GraphPort) -> Any:
    """Compileert de minimale antwoord-graaf. Geen checkpointer: deze snede kent nog geen
    multi-turn-gespreksgeheugen (dat komt met de story die de API-laag bouwt)."""
    builder = StateGraph(State)
    builder.add_node("agent", partial(agent_node, settings=settings, llm=llm))
    builder.add_node("tools", partial(tools_node, settings=settings, graph=graph))
    builder.add_node("verify", verify_node)
    builder.add_node("correct", correct_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent", route_after_agent, {"tools": "tools", "verify": "verify"}
    )
    builder.add_edge("tools", "agent")
    builder.add_conditional_edges(
        "verify", route_after_verify, {"correct": "correct", "finalize": "finalize"}
    )
    builder.add_edge("correct", "agent")
    builder.add_edge("finalize", END)

    return builder.compile()
