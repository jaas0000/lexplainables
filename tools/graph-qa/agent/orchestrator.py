"""Antwoord-agent-loop (LangGraph) — werkwijze-stories 044-048.

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

Story 047 begint de **annotatieketen**: `annoteer_node` is de kleinste zelfstandig bewijsbare
snede daarvan — één LLM-call die een aangeleverde bepaling classificeert volgens het Juridisch
Analyseschema (JAS), brongetrouw en ontdubbeld. Story 048 voegt `critic_node` toe: één LLM-call
die diezelfde voorstellen beoordeelt (aandacht-niveau groen/geel/rood + actie
behoud/vervang/verwijder per element, plus waarschijnlijk gemiste elementen). Beide bewust
**losstaand**, niet in `build_graph` gewired (geen supervisor-routing naar een annotatie-worker)
— patch/herzie/emit/advance en de graaf-wiring zijn stuk voor stuk latere stories, zie
`docs/project/stories/047-graph-qa-annotatie-enkele-ronde.md` en `docs/project/stories/
048-graph-qa-annotatie-critic.md` §Afwijkingen. Bewust nog **geen** checkpointer/gespreksgeheugen
of streaming — zie de story-docs' §Afwijkingen voor de reden per punt.
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
    sources: list[Source]
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


def supervisor_node(state: State, *, settings: Settings, llm: LLMPort) -> dict[str, Any]:
    """Kiest een specialist voor de vraag, of wijst hem af als hij buiten de wetgeving valt.

    Geen tools: de supervisor kijkt niet in de graaf, hij beslist alleen wíé (welke specialist)
    of dát er niemand aan te pas komt (afwijzen)."""
    resp = llm.create(
        model=settings.llm_model,
        max_tokens=_MAX_SUPERVISOR_TOKENS,
        system=supervisor.SUPERVISOR_SYSTEM,
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
    upd: dict[str, Any] = {"answer": antwoord, "sources": sources}
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


def build_graph(settings: Settings, llm: LLMPort, graph: GraphPort) -> Any:
    """Compileert de antwoord-graaf. Geen checkpointer: deze snede kent nog geen
    multi-turn-gespreksgeheugen (dat komt met de story die de API-laag bouwt).

    `settings.enable_decomposition=True` vertakt naar de multi-hop-topologie (story 046) i.p.v.
    de agent⇄tools-lus; de toggel-uit-stand hieronder blijft byte voor byte gelijk aan
    stories 044-045."""
    builder = StateGraph(State)
    builder.add_node("supervisor", partial(supervisor_node, settings=settings, llm=llm))
    builder.add_node("afwijzen", afwijs_node)
    builder.add_node("verify", verify_node)
    builder.add_node("finalize", finalize_node)

    if settings.enable_decomposition:
        builder.add_node("decompose", partial(decompose_node, settings=settings, llm=llm))
        builder.add_node("solve", partial(solve_node, settings=settings, llm=llm, graph=graph))
        builder.add_node("synthesize", partial(synthesize_node, settings=settings, llm=llm))
        builder.add_node("resynth", resynth_node)

        builder.add_edge(START, "supervisor")
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
        return builder.compile()

    builder.add_node("agent", partial(agent_node, settings=settings, llm=llm))
    builder.add_node("tools", partial(tools_node, settings=settings, graph=graph))
    builder.add_node("correct", correct_node)

    builder.add_edge(START, "supervisor")
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

    return builder.compile()
