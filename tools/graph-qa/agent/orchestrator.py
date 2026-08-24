"""Antwoord-/annotatie-agent-loop (LangGraph) — werkwijze-stories 044-050.

Story 044 bouwde de kleinste snede die de drie losse bouwstenen (`ports.py`/story 029,
`AnthropicLLM`/story 039, `MCPClient`/story 040, de toollaag/story 041) daadwerkelijk samenvoegt
tot een werkende agent: vraag in, tools aanroepen, antwoord formuleren, op brongetrouwheid
controleren — zonder keuze, één vaste systeemprompt, alle tools. Story 045 zet daar een
**supervisor** vóór: kiest een specialist (`definitie`/`duiding`/`algemeen`, elk met een eigen
prompt-addendum en beperkte toolset) en wijst een vraag buiten de wetgeving direct af, zonder
tool-call. Story 046 voegt een **tweede graaf-topologie** toe (`settings.enable_decomposition`,
standaard uit): een samengestelde vraag wordt eerst in deelvragen gesplitst, elke deelvraag krijgt
een eigen agent⇄tools-lus, en de bevindingen worden samengevoegd tot één antwoord. Staat de toggle
uit, dan is de graaf-opbouw byte voor byte gelijk aan stories 044-045.

    START → supervisor_node → (afwijs_node → END)
                             → agent_node ⇄ tools_node → verify_node
                               → (correct_node → agent_node | finalize_node) → END

    Met enable_decomposition=True vervangt dit de agent/tools/correct-tak:
    START → supervisor_node → (afwijs_node → END)
                             → decompose_node → solve_node
                               → (verify_node, 1 deelvraag)
                               → (synthesize_node → verify_node, >1 deelvraag)
                             → verify_node → (resynth_node → synthesize_node | finalize_node) → END

Stories 047-049 bouwen de **annotatieketen**: `annoteer_node` (047) classificeert een bepaling
volgens het JAS; `critic_node` (048) beoordeelt de voorstellen (aandacht-niveau groen/geel/rood +
actie per element); story 049 rondt af met `patch_node` (voert rood+vervang-instructies
code-only uit), `herzie_node` (één LLM-call: herstelt verworpen fragmenten, voegt gemiste
elementen toe) en `emit_node` (finale structuur, geen SSE — geen streaming-laag), plus de
graaf-wiring: `state["doel"]` routeert (via `_heeft_doel`) om de supervisor heen recht naar
`annoteer`, onafhankelijk van `enable_decomposition`.

    START → _heeft_doel → (annoteer → critic → (patch → (herzie|critic|emit) | emit)
                            → herzie → critic → emit → END)
                         → supervisor_node → (afwijs_node → END) → (antwoord-tak, zie hierboven)

Bewust nog **geen** `advance_node`/worker-chaining (één worker per beurt), geen streaming, geen
API-laag, geen NL-vraag-gebaseerde annotatie-routing via de supervisor. Story 050 voegt
**gespreksgeheugen** toe: `build_graph(..., checkpointer=...)` (`agent/checkpointer.py`, Postgres
→ SQLite → in-memory) + `nieuwe_beurt_invoer()` (zaait de nieuwe vraag, reset alle ephemere
velden) — zie `docs/project/stories/050-graph-qa-checkpointer.md` §Afwijkingen voor de reden per
punt.
"""

from __future__ import annotations

import logging
import operator
import re
from functools import partial
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from . import annotatie, annotatie_prompt, artikel, prompts, specialists, supervisor
from .config import Settings
from .grounding import check_grounding, curate_sources
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

# De supervisor levert een kort, gestructureerd antwoord (twee regels) — geen ruimte nodig voor
# een lang antwoord, en een kleine cap houdt de routeringsbeurt snel en goedkoop.
_MAX_SUPERVISOR_TOKENS = 300

# Dezelfde weigeringstekst als de referentie, minus de annotatie-uitnodiging (die mogelijkheid
# bestaat hier nog niet — werkwijze-story 045 §Afwijkingen).
_AFWIJS_MELDING = (
    "Deze vraag gaat niet over Nederlandse wet- en regelgeving, dus daar kan ik je niet mee "
    "helpen. Vraag me gerust naar een bepaling, een begrip of de samenhang tussen artikelen."
)

_MAX_DECOMPOSE_TOKENS = 400

# Een volledig artikel met veel JAS-elementen kan een lange JSON-respons opleveren — ruim boven de
# 4096 van de antwoord-loop, matcht de referentie.
_MAX_ANNOTATIE_TOKENS = 8192

# De Critic levert een compacter oordeel per element dan de annotator een heel artikel.
_MAX_CRITIC_TOKENS = 2048

_DECOMPOSE_SYSTEM = (
    "Je splitst een juridische vraag over de kennisgraaf op in de deelvragen die je apart moet "
    "beantwoorden om de hele vraag te dekken. Geef ELKE deelvraag op een eigen regel, genummerd "
    "(1., 2., …), in logische volgorde (een deelvraag mag voortbouwen op een eerdere). Splits "
    "ALLEEN als de vraag echt meerdere losse onderdelen heeft; een enkelvoudige vraag geef je als "
    "één regel terug (de vraag zelf). Verzin geen deelvragen die niet in de oorspronkelijke vraag "
    "liggen. Geen inleiding of uitleg — alleen de genummerde regels."
)

_SYNTHESE_SYSTEM = (
    "Je stelt één samenhangend eindantwoord samen uit de per-deelvraag verzamelde bevindingen. "
    "Steun UITSLUITEND op die bevindingen — voeg geen nieuwe feiten toe en verzin geen "
    "vindplaatsen. Behoud de vindplaatsen (regeling/artikel/lid) letterlijk zoals ze in de "
    "bevindingen staan. "
    "Antwoord bondig en goed gestructureerd; adresseer elk onderdeel van de oorspronkelijke vraag."
)

_SUBQUESTION_RE = re.compile(r"^\s*\d+[.)]\s*(.+)$")


def _truncate(text: str, max_chars: int = _MAX_TOOL_RESULT_CHARS) -> str:
    if len(text) > max_chars:
        return text[:max_chars] + f"\n...[resultaat ingekort op {max_chars} tekens]"
    return text


def parse_subquestions(text: str, cap: int) -> list[str]:
    """Genummerde regels (`1. …`) naar een lijst deelvragen; geen match → geen fallback hier (de
    aanroeper geeft de oorspronkelijke vraag mee als terugval, zodat deze functie zuiver blijft)."""
    subs = [m.group(1).strip() for line in text.splitlines() if (m := _SUBQUESTION_RE.match(line))]
    return subs[:cap]


class State(TypedDict, total=False):
    question: str
    messages: Annotated[list[dict[str, Any]], operator.add]
    specialist: str
    plan: str
    afwijzen: bool
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
    sources: list[dict[str, Any]]  # plain dicts (net als voorstellen), checkpointer-safe
    sub_questions: list[str]
    sub_findings: list[dict[str, str]]
    doel: dict[str, str]
    corpus: str
    voorstellen: list[dict[str, Any]]
    verworpen_fragmenten: list[dict[str, Any]]
    critic_feedback: list[dict[str, Any]]
    critic_ontbrekend: list[dict[str, Any]]
    critic_gefaald: bool
    critic_ronde: int
    nieuw_ontbrekend: list[dict[str, Any]]
    gemeld_ontbrekend: list[str]
    patch_toegepast: int
    suggesties: list[dict[str, Any]]


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


def _recent_context(state: State) -> str:
    """Korte samenvatting van eerdere berichten in dit gesprek — puur als aanknopingspunt voor
    verwijzingen als "dat begrip"/"dat artikel", nooit als vervanging van de eigen vraag.

    Zonder dit ziet de supervisor (story 050: `messages` persisteert nu over beurten heen via de
    checkpointer) een vervolgvraag als "en welk artikel regelt dat begrip precies?" volledig
    los van het gesprek — en zo'n contextloze, pronomenrijke vraag kan dan onterecht als
    "niet over de wetgeving" worden afgewezen. Zelf gevonden tijdens de live-verificatie van deze
    story: exact dit gebeurde bij een tweede vraag in hetzelfde gesprek.
    """
    berichten = state.get("messages") or []
    if not berichten:
        return ""
    regels: list[str] = []
    for m in berichten[-6:]:
        content = m.get("content")
        if isinstance(content, str):
            tekst = content
        elif isinstance(content, list):
            tekst = " ".join(
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            tekst = ""
        tekst = tekst.strip()
        if tekst:
            rol = "jurist" if m.get("role") == "user" else "jij"
            regels.append(f"- {rol}: {tekst[:200]}")
    if not regels:
        return ""
    return (
        "\n\nGESPREKSCONTEXT — eerder in dit gesprek (alléén als aanknopingspunt voor "
        "verwijzingen, de huidige vraag blijft leidend):\n" + "\n".join(regels)
    )


def supervisor_node(state: State, *, settings: Settings, llm: LLMPort) -> dict[str, Any]:
    """Kiest een specialist voor de vraag, of wijst hem af als hij buiten de wetgeving valt.

    Geen tools: de supervisor kijkt niet in de graaf, hij beslist alleen wíé (welke specialist)
    of dát er niemand aan te pas komt (afwijzen)."""
    resp = llm.create(
        model=settings.llm_model,
        max_tokens=_MAX_SUPERVISOR_TOKENS,
        system=supervisor.SUPERVISOR_SYSTEM + _recent_context(state),
        tools=[],
        messages=[{"role": "user", "content": state["question"]}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    specialist, plan, afwijzen = supervisor.parse_supervisor(text)
    return {"specialist": specialist, "plan": plan, "afwijzen": afwijzen}


def afwijs_node(state: State) -> dict[str, Any]:
    """De supervisor plaatste de vraag buiten de wetgeving: hier eindigt de beurt — geen tools,
    geen tweede LLM-call, geen graafbevraging."""
    return {
        "answer": _AFWIJS_MELDING,
        "messages": [{"role": "assistant", "content": _AFWIJS_MELDING}],
        # Expliciet meegeven: het normale pad (tools_node/finalize_node) zet deze ook altijd, en
        # zonder dit ontbreken ze in de eindstate na een afwijzing — een aanroeper die `result
        # ["sources"]`/`result["source_trace"]` rechtstreeks leest (zoals de integratietests)
        # zou dan een KeyError krijgen i.p.v. een lege lijst.
        "source_trace": [],
        "sources": [],
    }


def agent_node(state: State, *, settings: Settings, llm: LLMPort) -> dict[str, Any]:
    # Eerste beurt: `messages` is nog leeg, dus de vraag wordt hier gezaaid — en die zaai-message
    # gaat ook mee in de return-delta (via de append-reducer), anders bestaat hij alleen lokaal en
    # ontbreekt de user-vraag in de state zodra een volgende node (tools_node) zijn eigen delta
    # toevoegt.
    bestaand = state.get("messages") or []
    zaai = [] if bestaand else [{"role": "user", "content": state["question"]}]
    messages = bestaand + zaai

    spec = specialists.get(state.get("specialist"))
    system = (
        prompts.SYSTEM_PROMPT if not spec.system else f"{prompts.SYSTEM_PROMPT}\n\n{spec.system}"
    )

    final = llm.create(
        model=settings.llm_model,
        max_tokens=_MAX_TOKENS,
        system=system,
        tools=anthropic_schemas(only=spec.tools),
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
    # `.model_dump()`: state moet plain-dict-serialiseerbaar blijven zodra een checkpointer 'm
    # opslaat (story 050) — een Pydantic-object in de state gaf een msgpack-deserialisatie-
    # waarschuwing ("unregistered type"), zelf gevonden tijdens de live-verificatie van die story.
    upd: dict[str, Any] = {"answer": antwoord, "sources": [s.model_dump() for s in sources]}
    # In de decompositie-stroom komt het eind-antwoord uit synthesize_node/solve_node en is het
    # nog niet in het messages-kanaal beland (agent_node doet dat wél, via de zaai-message). Zet
    # het hier één keer zodat een latere checkpointer-story het gespreksgeheugen kan lezen zonder
    # deze functie opnieuw aan te passen — en zodat de State-vorm gelijk blijft aan het legacy-pad.
    if state.get("sub_questions") is not None:
        upd["messages"] = [{"role": "assistant", "content": [{"type": "text", "text": antwoord}]}]
    return upd


# ---- Decompositie-nodes (multi-hop; alleen actief bij settings.enable_decomposition) ---------


def decompose_node(state: State, *, settings: Settings, llm: LLMPort) -> dict[str, Any]:
    """Splitst de vraag in geordende deelvragen (één LLM-call). Enkelvoudig → één deelvraag."""
    resp = llm.create(
        model=settings.llm_model,
        max_tokens=_MAX_DECOMPOSE_TOKENS,
        system=_DECOMPOSE_SYSTEM,
        tools=[],
        messages=[{"role": "user", "content": state["question"]}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    subs = parse_subquestions(text, settings.max_subquestions) or [state["question"]]
    return {"sub_questions": subs}


def solve_node(
    state: State, *, settings: Settings, llm: LLMPort, graph: GraphPort
) -> dict[str, Any]:
    """Beantwoordt elke deelvraag met een eigen agent⇄tools-lus (lokale scratch-messages).

    De gedeelde `source_trace` accumuleert over alle deelvragen zodat grounding/provenance op het
    eind-antwoord ongewijzigd werken. Bij precies één deelvraag is er geen synthese nodig: de
    tool-loze eindbeurt ís het eindantwoord (`route_after_solve` slaat `synthesize` dan over).
    """
    spec = specialists.get(state.get("specialist"))
    subs = state.get("sub_questions") or [state["question"]]
    enkelvoudig = len(subs) == 1
    base_system = (
        prompts.SYSTEM_PROMPT if not spec.system else f"{prompts.SYSTEM_PROMPT}\n\n{spec.system}"
    )
    schemas = anthropic_schemas(only=spec.tools)
    trace = list(state.get("source_trace", []))
    findings: list[dict[str, str]] = []

    for sub in subs:
        # base_system is stabiel over alle deelvragen heen (identiteit + specialist-addendum);
        # variabel groeit per deelvraag met de bevindingen tot dan toe. Dit is de eerste plek in
        # de orkestrator die herhaalde calls met hetzelfde stabiele systeemblok doet binnen één
        # graafinvocatie — de cachingsplit (`ports.Systeem`, story 039) heeft hier voor het eerst
        # iets om op te herhalen.
        variabel = ""
        if findings:
            ctx = "\n".join(f"- {f['vraag']} → {f['antwoord'][:300]}" for f in findings)
            variabel += (
                "EERDERE DEELBEVINDINGEN (context; verifieer elk feit opnieuw via de tools):\n"
                + ctx
            )
        msgs: list[dict[str, Any]] = [{"role": "user", "content": sub}]
        antwoord = ""
        for turn in range(settings.sub_max_turns):
            # Op de laatste toegestane beurt geen tools meer aanbieden — anders kan het model
            # blijven zoeken tot de lus afloopt en `antwoord` leeg blijft (zelfde vangnet als
            # `agent_node`'s MAX_TURNS, maar hier per deelvraag i.p.v. per hele beurt).
            laatste_beurt = turn == settings.sub_max_turns - 1
            final = llm.create(
                model=settings.llm_model,
                max_tokens=_MAX_TOKENS,
                system=[base_system, variabel],
                tools=[] if laatste_beurt else schemas,
                messages=msgs,
            )
            tool_uses, text_parts = _parse_final(final)
            assistant_content: list[dict[str, Any]] = [
                {"type": "text", "text": t} for t in text_parts if t
            ]
            assistant_content += [
                {"type": "tool_use", "id": t["id"], "name": t["name"], "input": t["input"]}
                for t in tool_uses
            ]
            msgs.append({"role": "assistant", "content": assistant_content})
            if not tool_uses:
                antwoord = "".join(text_parts)
                break
            results = []
            for tu in tool_uses:
                result_text = _truncate(dispatch(tu["name"], graph, tu["input"], settings))
                trace.append((tu["name"], result_text))
                results.append(
                    {"type": "tool_result", "tool_use_id": tu["id"], "content": result_text}
                )
            msgs.append({"role": "user", "content": results})
        if not antwoord.strip():
            logger.warning(
                "deelvraag zonder antwoord",
                extra={
                    "deelvraag": sub[:120],
                    "beurten": settings.sub_max_turns,
                    "specialist": state.get("specialist"),
                    "bronnen": len(trace),
                },
            )
        findings.append({"vraag": sub, "antwoord": antwoord})

    upd: dict[str, Any] = {"sub_findings": findings, "source_trace": trace}
    if enkelvoudig:
        upd["answer"] = findings[0]["antwoord"] if findings else ""
    return upd


def route_after_solve(state: State) -> str:
    return "verify" if len(state.get("sub_questions") or []) <= 1 else "synthesize"


def synthesize_node(state: State, *, settings: Settings, llm: LLMPort) -> dict[str, Any]:
    """Stelt het eind-antwoord samen uit de deelbevindingen (één LLM-call)."""
    findings = state.get("sub_findings") or []
    bevindingen = "\n\n".join(
        f"DEELVRAAG: {f['vraag']}\nBEVINDING: {f['antwoord']}" for f in findings
    )
    system = _SYNTHESE_SYSTEM
    # Beide categorieën benoemen, niet alleen `unsupported` — zelfde bugklasse-fix als
    # `correct_node` al toepast op het legacy-pad (werkwijze-story 046 §Afwijkingen punt 5): een
    # synthese die alleen op een citaat struikelde kreeg anders een herkansing met een lege
    # opsomming.
    if state.get("corrected"):
        opdrachten: list[str] = []
        if state.get("unsupported"):
            opdrachten.append(
                "Verwijder of onderbouw deze eerder niet-gegronde verwijzingen: "
                + ", ".join(state["unsupported"])
                + "."
            )
        if state.get("niet_letterlijk"):
            passages = "; ".join(
                f'"{c[:120]}…"' if len(c) > 120 else f'"{c}"' for c in state["niet_letterlijk"]
            )
            opdrachten.append(
                "Deze passages stonden tussen aanhalingstekens maar niet letterlijk in de "
                f"bevindingen: {passages}. Herstel ze woord voor woord of haal de "
                "aanhalingstekens weg."
            )
        if opdrachten:
            system += "\n\n" + " ".join(opdrachten)
    user = (
        f"OORSPRONKELIJKE VRAAG:\n{state['question']}\n\nBEVINDINGEN PER DEELVRAAG:\n{bevindingen}"
    )
    final = llm.create(
        model=settings.llm_model,
        max_tokens=_MAX_TOKENS,
        system=system,
        tools=[],
        messages=[{"role": "user", "content": user}],
    )
    _, text_parts = _parse_final(final)
    return {"answer": "".join(text_parts).strip()}


def resynth_node(state: State) -> dict[str, Any]:
    """Ongegronde synthese → markeer voor één her-synthese (synthesize_node leest `corrected`)."""
    return {"corrected": True, "answer": ""}


# ---- Annotatie (stories 047-048) — losstaand, niet in build_graph gewired -----------------


def annoteer_node(
    state: State, *, settings: Settings, llm: LLMPort, graph: GraphPort
) -> dict[str, Any]:
    """Classificeert één bepaling (`state["doel"]`) volgens het JAS in één LLM-call.

    Geen ophaal-agent, geen graaf-routing: `doel` (bwbId/artikel/lid) is al bekend. Geen patch/
    herzie — dat zijn latere stories die op deze ruwe, gegronde voorstellen voortbouwen."""
    doel = state["doel"]
    corpus = artikel.artikel_corpus(doel["bwbId"], doel["artikel"], graph, doel.get("lid"))
    resp = llm.create(
        model=settings.llm_model,
        max_tokens=_MAX_ANNOTATIE_TOKENS,
        system=annotatie_prompt.annotatie_systeemprompt(),
        tools=[],
        messages=[
            {
                "role": "user",
                "content": annotatie_prompt.annotatie_userprompt(
                    doel["bwbId"], doel["artikel"], corpus, doel.get("lid")
                ),
            }
        ],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    voorstellen, verworpen = annotatie._verwerk(
        text, corpus, doel["bwbId"], doel["artikel"], doel.get("lid")
    )
    return {
        "corpus": corpus,
        "voorstellen": [v.model_dump() for v in voorstellen],
        "verworpen_fragmenten": [v.model_dump() for v in verworpen],
    }


def _ontbrekend_sleutel(item: dict[str, Any]) -> str:
    """Identiteit van een gemeld gemist element: klasse + het genoemde fragment."""
    klasse = str(item.get("klasse", "")).strip()
    fragment = " ".join(str(item.get("tekst", "")).split()).lower()
    return f"{klasse}|{fragment}"


def critic_node(state: State, *, settings: Settings, llm: LLMPort) -> dict[str, Any]:
    """Critic-pas: beoordeelt de gegronde voorstellen en zet per element een aandacht-niveau
    (groen/geel/rood) + motivatie, plus een lijst waarschijnlijk ontbrekende elementen. Eén
    LLM-call (geen tools).

    Faalt de Critic → `critic_gefaald`, elementen komen door met lege aandacht (nooit de
    annotatie breken)."""
    voorstellen = list(state.get("voorstellen") or [])
    if not voorstellen:
        return {}

    corpus = state.get("corpus", "")
    try:
        resp = llm.create(
            model=settings.llm_model,
            max_tokens=_MAX_CRITIC_TOKENS,
            system=annotatie_prompt.critic_systeemprompt(),
            tools=[],
            messages=[
                {
                    "role": "user",
                    "content": annotatie_prompt.critic_userprompt(
                        voorstellen, corpus, list(state.get("gemeld_ontbrekend") or [])
                    ),
                }
            ],
        )
        crit_text = "".join(b.text for b in resp.content if b.type == "text")
        oordelen, ontbrekend = annotatie._verwerk_critic(
            crit_text, [str(v.get("id", "")) for v in voorstellen]
        )
    except Exception:  # noqa: BLE001 — de Critic mag de annotatie nooit breken
        logger.warning(
            "critic: beoordeling mislukt; elementen zonder aandacht doorgelaten", exc_info=True
        )
        # Laat de voorstellen ONGEMOEID. In een tweede ronde staat er al een oordeel van de
        # eerste pas op; dat overschrijven met lege waarden zou een geslaagde beoordeling
        # ongedaan maken omdat een latere poging mislukte.
        return {"voorstellen": voorstellen, "critic_feedback": [], "critic_gefaald": True}

    # Rondenummer voor het spoor: 1 = het eerste oordeel, 2 = de eindbeoordeling na correctie.
    ronde = int(state.get("critic_ronde") or 0) + 1

    feedback: list[dict[str, Any]] = []
    for v in voorstellen:
        oordeel = oordelen.get(str(v.get("id", "")))
        aandacht = oordeel.aandacht if oordeel else ""
        # De motivatie gaat één-op-één naar de reviewkaart. Interne ids horen daar niet: de
        # Critic gebruikt ze om naar buurelementen te verwijzen, de jurist leest een hexcode.
        motivatie = (
            annotatie.vervang_ids_door_citaat(oordeel.motivatie, voorstellen) if oordeel else ""
        )
        v["aandacht"] = aandacht
        v["critic"] = motivatie
        if oordeel is not None:
            feedback.append({"id": v.get("id", ""), **oordeel.model_dump()})
            v.setdefault("critic_rondes", []).append(
                {
                    "ronde": ronde,
                    "aandacht": aandacht,
                    "motivatie": motivatie,
                    "actie": oordeel.actie,
                    "toegepast": False,
                    "voorstel_klasse": oordeel.voorstel_klasse,
                    "voorstel_tekst": oordeel.voorstel_tekst,
                }
            )

    al_gemeld = set(state.get("gemeld_ontbrekend") or [])
    huidig = {_ontbrekend_sleutel(o.model_dump()) for o in ontbrekend}
    nieuw_ontbrekend = [
        o.model_dump() for o in ontbrekend if _ontbrekend_sleutel(o.model_dump()) not in al_gemeld
    ]

    # De eindbeoordeling gaat rechtstreeks naar de jurist; er komt geen patcher meer overheen die
    # haar kan wegen. Dus hier, en alleen hier, dempen we een oordeel dat de eigen uitgevoerde
    # correctie terugdraait.
    if ronde >= 2:
        annotatie.demp_zelfweerspreking(voorstellen)

    return {
        "voorstellen": voorstellen,
        "critic_feedback": feedback,
        "critic_ontbrekend": [o.model_dump() for o in ontbrekend],
        "critic_gefaald": False,
        "critic_ronde": ronde,
        "nieuw_ontbrekend": nieuw_ontbrekend,
        "gemeld_ontbrekend": sorted(al_gemeld | huidig),
    }


def route_na_critic(state: State, *, settings: Settings) -> str:
    """Naar de correctiestap, of naar de jurist? De keten is lineair: `critic₁ → patch → [herzie]
    → [critic₂] → emit` — er valt hier niets te kiezen behalve of er nog een correctieronde ís."""
    if settings.critic_max_rondes <= 0:
        return "emit"
    if state.get("critic_gefaald"):
        return "emit"
    if int(state.get("critic_ronde") or 0) >= 2:
        return "emit"
    return "patch"


def patch_node(state: State) -> dict[str, Any]:
    """Voer de correcties van de Critic uit — in code, niet via een tweede taalmodel. Geen
    LLM-call, geen graafverkeer."""
    voorstellen, telling, rest = annotatie.pas_critic_toe(
        list(state.get("voorstellen") or []),
        list(state.get("critic_feedback") or []),
        state.get("corpus", ""),
    )
    return {
        "voorstellen": voorstellen,
        "patch_toegepast": telling.toegepast,
        # Teruggebracht tot wat de patcher NIET heeft afgehandeld — anders krijgt de herziener
        # dezelfde instructies opnieuw voorgelegd.
        "critic_feedback": rest,
    }


def _open_werk(state: State) -> bool:
    """Ligt er werk dat alléén het model kan doen: een gemeld ontbrekend element, of een eerder
    verworpen fragment? Correctie-instructies (vervang/verwijder) staan hier niet meer bij — die
    voert de patcher al exact uit."""
    return bool(state.get("nieuw_ontbrekend")) or bool(state.get("verworpen_fragmenten"))


def route_na_patch(state: State) -> str:
    """Restant voor het model → `herzie`. Alleen gepatcht (geen open werk) → nog een
    Critic-beoordeling over de gecorrigeerde versie. Niets veranderd → klaar."""
    if _open_werk(state):
        return "herzie"
    return "critic" if state.get("patch_toegepast") else "emit"


def herzie_node(state: State, *, settings: Settings, llm: LLMPort) -> dict[str, Any]:
    """Laat de annoteerder de resterende Critic-instructies verwerken (een bijna-goed citaat
    repareren, een gemeld ontbrekend element toevoegen). Eén LLM-call, geen tools.

    Conservatief samenvoegen: wat de herziening niet noemt blijft staan. Alleen een expliciete
    `verwijder`-instructie laat een element verdwijnen."""
    alle = list(state.get("voorstellen") or [])
    # Markeringen van de jurist gaan de herziening niet in: de agent herschrijft ze niet.
    van_jurist = [v for v in alle if v.get("van_jurist")]
    voorstellen = [v for v in alle if not v.get("van_jurist")]
    if not voorstellen:
        return {}

    doel = state["doel"]
    corpus = state.get("corpus", "")
    feedback = [
        f
        for f in (state.get("critic_feedback") or [])
        if f.get("id") not in {v.get("id") for v in van_jurist}
    ]
    try:
        resp = llm.create(
            model=settings.llm_model,
            max_tokens=_MAX_ANNOTATIE_TOKENS,
            system=annotatie_prompt.herziening_systeemprompt(),
            tools=[],
            messages=[
                {
                    "role": "user",
                    "content": annotatie_prompt.herziening_userprompt(
                        voorstellen,
                        feedback,
                        state.get("critic_ontbrekend") or [],
                        state.get("verworpen_fragmenten") or [],
                        corpus,
                    ),
                }
            ],
        )
        llm_text = "".join(b.text for b in resp.content if b.type == "text")
        herzien, verworpen = annotatie._verwerk(
            llm_text,
            corpus,
            doel.get("bwbId", ""),
            doel.get("artikel", ""),
            doel.get("lid"),
            geldige_ids={str(v.get("id", "")) for v in voorstellen if v.get("id")},
        )
    except Exception:  # noqa: BLE001 — een mislukte herziening mag de annotatie niet breken
        logger.warning("herziening: mislukt; vorige voorstellen behouden", exc_info=True)
        return {"critic_feedback": []}

    if not herzien:
        logger.warning("herziening: leverde niets gegronds op; vorige voorstellen behouden")
        return {"critic_feedback": []}

    te_verwijderen = {f.get("id") for f in feedback if f.get("actie") == "verwijder"}
    samengevoegd = {v["id"]: v for v in voorstellen if v.get("id") not in te_verwijderen}
    op_inhoud = {
        annotatie.sleutel_van(v.get("tekst", ""), v.get("lid", "")): v["id"]
        for v in samengevoegd.values()
    }
    for nieuw_v in herzien:
        bestaand_id = op_inhoud.get(annotatie.sleutel_van(nieuw_v.tekst, nieuw_v.lid))
        if bestaand_id and bestaand_id != nieuw_v.id:
            # Het OUDSTE id wint: daar hangen de beslissingen van de jurist aan.
            nieuw_v = nieuw_v.model_copy(update={"id": bestaand_id})
        nieuw_dict = nieuw_v.model_dump()
        vorig = samengevoegd.get(nieuw_v.id)
        if vorig:
            nieuw_dict["critic_rondes"] = list(vorig.get("critic_rondes") or [])
            bestaand = list(vorig.get("alternatieven") or [])
            gezien_alt = {str(a.get("klasse")) for a in bestaand}
            nieuw_dict["alternatieven"] = bestaand + [
                a
                for a in (nieuw_dict.get("alternatieven") or [])
                if str(a.get("klasse")) not in gezien_alt
            ]
        # Inhoudelijk ongewijzigd → het vorige oordeel geldt nog. Echt gewijzigd → aandacht leeg,
        # die versie is nog niet beoordeeld.
        if vorig and all(vorig.get(k) == nieuw_dict.get(k) for k in ("klasse", "tekst", "lid")):
            nieuw_dict["aandacht"] = vorig.get("aandacht", "")
            nieuw_dict["critic"] = vorig.get("critic", "")
        samengevoegd[nieuw_v.id] = nieuw_dict

    uit = list(samengevoegd.values())
    voor_op_id = {v.get("id"): v for v in voorstellen}
    gewijzigd = {
        v.get("id")
        for v in uit
        if v.get("id") not in voor_op_id
        or any(voor_op_id[v["id"]].get(k) != v.get(k) for k in ("klasse", "tekst", "lid"))
    }
    for v in uit:
        v["aangepast_na_kritiek"] = v.get("id") in gewijzigd

    return {
        "voorstellen": uit + van_jurist,
        "critic_feedback": [],
        "nieuw_ontbrekend": [],
        "verworpen_fragmenten": [x.model_dump() for x in verworpen] if gewijzigd else [],
    }


def emit_node(state: State) -> dict[str, Any]:
    """Bouwt de finale annotatiestructuur. Geen SSE-events (geen streaming-laag) — de referentie
    stuurt hier `run`/`element`/`suggestie`/`ontbrekend`/`token`-events; hier komt in plaats
    daarvan één finale structuur terug in de state."""
    voorstellen = list(state.get("voorstellen") or [])
    if not voorstellen:
        return {}
    corpus = state.get("corpus", "")
    ontbrekend = state.get("critic_ontbrekend") or []

    suggesties: list[dict[str, Any]] = []
    met_aandacht = 0
    for v in voorstellen:
        if v.get("van_jurist"):
            continue
        if v.get("aandacht") in ("geel", "rood"):
            met_aandacht += 1
        klasse, tekst, waarom = annotatie.openstaand_voorstel(v, corpus)
        if klasse or tekst:
            suggesties.append(
                {
                    "element_id": v.get("id", ""),
                    "aandacht": v.get("aandacht", ""),
                    "motivatie": waarom,
                    "voorstel_klasse": klasse,
                    "voorstel_tekst": tekst,
                }
            )

    eigen = [v for v in voorstellen if v.get("van_jurist")]
    voorstellen_zonder_jurist = [v for v in voorstellen if not v.get("van_jurist")]
    delen = [f"Ik heb {len(voorstellen_zonder_jurist)} JAS-elementen voorgesteld"]
    if met_aandacht:
        delen.append(f"{met_aandacht} met aandacht")
    if ontbrekend:
        delen.append(f"{len(ontbrekend)} mogelijk ontbrekend")
    if eigen:
        delen.append(f"{len(eigen)} eigen markering(en) beoordeeld")
    samenvatting = "; ".join(delen) + "."

    return {"voorstellen": voorstellen, "suggesties": suggesties, "answer": samenvatting}


def _heeft_doel(state: State) -> str:
    """Is de bepaling al bekend (`state["doel"]`)? Dan valt er niets te routeren — recht naar
    `annoteer`, geen supervisor-LLM-call nodig. Zonder `doel` werkt de bestaande QA-routing
    ongewijzigd."""
    return "annoteer" if state.get("doel") else "supervisor"


def route_after_supervisor(state: State) -> str:
    return "afwijzen" if state.get("afwijzen") else "agent"


def route_after_agent(state: State) -> str:
    if state.get("pending_tools") and state.get("turns", 0) < MAX_TURNS:
        return "tools"
    return "verify"


def route_after_verify(state: State) -> str:
    if state.get("grounding_niveau") == "ongegrond" and not state.get("corrected"):
        return "correct"
    return "finalize"


def nieuwe_beurt_invoer(
    question: str | None = None, doel: dict[str, str] | None = None
) -> dict[str, Any]:
    """Bouwt de `.ainvoke()`/`.invoke()`-input voor één nieuwe beurt: zaait de vraag (via de
    `messages`-append-reducer) en reset alle ephemere velden.

    Zonder deze reset draagt een tweede beurt in hetzelfde gesprek (checkpointer, story 050) de
    staat van de eerste mee — een vervolgvraag zou annoteren tegen de vórige bepaling, of een
    nieuwe kritiekronde zou beginnen met de oude `critic_ronde`. `messages` zelf reset NIET: dat
    is de bewaarde gespreksgeschiedenis, en de append-reducer plakt de nieuwe vraag erachteraan.

    Een `doel`-gedreven annotatiebeurt zaait geen `messages`-entry — matcht hoe `_heeft_doel` de
    supervisor al overslaat zonder een user-bericht toe te voegen.
    """
    invoer: dict[str, Any] = {
        "question": question or "",
        "specialist": "",
        "plan": "",
        "afwijzen": False,
        "source_trace": [],
        "answer": "",
        "pending_tools": [],
        "turns": 0,
        "corrected": False,
        "grounded": True,
        "cited": [],
        "unsupported": [],
        "niet_letterlijk": [],
        "grounding_niveau": "",
        "sources": [],
        "sub_questions": [],
        "sub_findings": [],
        "doel": doel or {},
        "corpus": "",
        "voorstellen": [],
        "verworpen_fragmenten": [],
        "critic_feedback": [],
        "critic_ontbrekend": [],
        "critic_gefaald": False,
        "critic_ronde": 0,
        "nieuw_ontbrekend": [],
        "gemeld_ontbrekend": [],
        "patch_toegepast": 0,
        "suggesties": [],
    }
    if question:
        invoer["messages"] = [{"role": "user", "content": question}]
    return invoer


def build_graph(
    settings: Settings, llm: LLMPort, graph: GraphPort, *, checkpointer: Any = None
) -> Any:
    """Compileert de antwoord-/annotatiegraaf. `checkpointer=None` (default) compileert zonder
    gespreksgeheugen — identiek aan stories 044-049; geef een checkpointer (`agent/
    checkpointer.py`, story 050) mee voor multi-turn-persistentie via `thread_id`. Een
    async-only checkpointer (Postgres/SQLite) vereist `.ainvoke()`/`.astream()` i.p.v. `.invoke()`
    — de node-functies zelf blijven synchroon.

    `settings.enable_decomposition=True` vertakt de antwoord-tak naar de multi-hop-topologie
    (story 046) i.p.v. de agent⇄tools-lus; de toggle-uit-stand blijft byte voor byte gelijk aan
    stories 044-045. `state["doel"]` routeert (via `_heeft_doel`) om de supervisor heen recht naar
    de annotatieketen (story 049) — onafhankelijk van die toggle."""
    builder = StateGraph(State)
    builder.add_node("supervisor", partial(supervisor_node, settings=settings, llm=llm))
    builder.add_node("afwijzen", afwijs_node)
    builder.add_node("verify", verify_node)
    builder.add_node("finalize", finalize_node)

    # Annotatieketen — zelfde nodes voor beide antwoord-topologieën hieronder.
    builder.add_node("annoteer", partial(annoteer_node, settings=settings, llm=llm, graph=graph))
    builder.add_node("critic", partial(critic_node, settings=settings, llm=llm))
    builder.add_node("patch", patch_node)
    builder.add_node("herzie", partial(herzie_node, settings=settings, llm=llm))
    builder.add_node("emit", emit_node)

    builder.add_conditional_edges(
        START, _heeft_doel, {"annoteer": "annoteer", "supervisor": "supervisor"}
    )
    builder.add_edge("annoteer", "critic")
    builder.add_conditional_edges(
        "critic", partial(route_na_critic, settings=settings), {"patch": "patch", "emit": "emit"}
    )
    builder.add_conditional_edges(
        "patch", route_na_patch, {"herzie": "herzie", "critic": "critic", "emit": "emit"}
    )
    builder.add_edge("herzie", "critic")
    builder.add_edge("emit", END)

    if settings.enable_decomposition:
        builder.add_node("decompose", partial(decompose_node, settings=settings, llm=llm))
        builder.add_node("solve", partial(solve_node, settings=settings, llm=llm, graph=graph))
        builder.add_node("synthesize", partial(synthesize_node, settings=settings, llm=llm))
        builder.add_node("resynth", resynth_node)

        builder.add_conditional_edges(
            "supervisor", route_after_supervisor, {"afwijzen": "afwijzen", "agent": "decompose"}
        )
        builder.add_edge("afwijzen", END)
        builder.add_edge("decompose", "solve")
        builder.add_conditional_edges(
            "solve", route_after_solve, {"verify": "verify", "synthesize": "synthesize"}
        )
        builder.add_edge("synthesize", "verify")
        builder.add_conditional_edges(
            "verify", route_after_verify, {"correct": "resynth", "finalize": "finalize"}
        )
        builder.add_edge("resynth", "synthesize")
        builder.add_edge("finalize", END)
        return builder.compile(checkpointer=checkpointer)

    builder.add_node("agent", partial(agent_node, settings=settings, llm=llm))
    builder.add_node("tools", partial(tools_node, settings=settings, graph=graph))
    builder.add_node("correct", correct_node)

    builder.add_conditional_edges(
        "supervisor", route_after_supervisor, {"afwijzen": "afwijzen", "agent": "agent"}
    )
    builder.add_edge("afwijzen", END)
    builder.add_conditional_edges(
        "agent", route_after_agent, {"tools": "tools", "verify": "verify"}
    )
    builder.add_edge("tools", "agent")
    builder.add_conditional_edges(
        "verify", route_after_verify, {"correct": "correct", "finalize": "finalize"}
    )
    builder.add_edge("correct", "agent")
    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)
