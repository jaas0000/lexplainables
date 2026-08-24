# Story 051 — graph-qa: streaming (SSE-events)

## Verhaal

Als jurist wil ik het antwoord live zien verschijnen terwijl de agent het formuleert, in plaats
van te wachten tot de hele beurt (tool-calls + antwoord) klaar is, zodat lange beurten niet als
een stilstaand scherm aanvoelen.

## Aanleiding

Eerste story ná de checkpointer (050). Voegt het SSE-event-contract toe via een nieuwe dunne
wrapper `agent/agent.py`'s `answer_stream()` — nog **geen HTTP**, dat is de eerstvolgende
API-laag-story (`tools/graph-qa/api/` bestaat al als leeg skelet). `LLMPort.stream()` /
`AnthropicLLM.stream()` (poorten/adapter) bestonden al sinds de vroege stories maar werden door
geen enkele node gebruikt — deze story is de eerste die ze daadwerkelijk aan de graaf knoopt.
Bewust **smal**: alleen tokenstreaming van het eind-antwoord + het event-contract + foutvertaling.
Stop/annuleren, observability en de runs-/persistentielaag zijn losse, latere stories (zie
referentie `agent/agent.py` + `agent/runs.py` + `agent/beurt.py`, die dit allemaal samen met
streaming bouwen — hier expliciet ontbundeld, net als bij story 050).

## lexplainables-specifieke afwijkingen

1. **Geen `stop_check`/`BeurtGestopt`.** De referentie wikkelt elke node in `stopbaar()` zodat een
   lopende beurt op een nodegrens kan stoppen. Dat raakt alle ~15 bestaande node-functies — een
   eigen, latere story, en zonder een aanroeper die kan annuleren (geen HTTP-laag hier) is er nu
   ook niets dat 'm zou gebruiken.
2. **Geen observability/tracer.** De referentie wikkelt de stream in
   `tracer.start_as_current_span(...)`. lexplainables heeft nog geen OTel-stack — komt terug zodra
   die er is.
3. **Geen runs-model (`POST /v1/runs`, `agent/runs.py`) en geen beurt-persistentie
   (`agent/beurt.py`).** Dat vraagt eerst een beslissing over hoe `tools/graph-qa/api/` (nu een
   leeg skelet) zich verhoudt tot het losse `api`-service — een aparte, grotere afweging dan deze
   story. `answer_stream()` hier blijft een pure Python-generator, geen endpoint.
4. **Geen recursielimiet-formule.** Zoals al vastgesteld in story 050 §Afwijkingen punt 2: geen
   `advance_node`/worker-chaining in deze topologie, dus de LangGraph-default (25) is ruim
   voldoende. Wél een eigen, vriendelijke melding bij `GraphRecursionError` i.p.v. de generieke
   foutmelding — dat kost niets extra en voorkomt dat een té lange beurt als "er ging iets mis"
   overkomt.
5. **Tokenstreaming alleen op het eind-antwoord**, niet op elke tussenliggende tool-lus-beurt —
   1:1 met de referentie ("deelvraag-tokens streamen niet; alleen de synthese"). Twee plekken
   emitten dus tokens: `agent_node` (single-loop-pad) en `synthesize_node`
   (decompositie-pad). `solve_node`, `decompose_node`, de annotatieketen-nodes en de supervisor
   blijven ongestreamd (geen eindantwoordtekst, of een interne beslissing die de jurist niet
   letterlijk hoeft mee te lezen).
6. **Geen `modus`/`context`/`opgegeven_doel`** in `answer_stream()`'s parameters — bestaan hier
   niet, zie story 050 §Afwijkingen punt 3 (`nieuwe_beurt_invoer` blijft de reset-bron; deze
   wrapper roept 'm aan i.p.v. een eigen inline `init`-dict te herhalen).
7. **Geen `entities_seen`-event/samenvatting.** Nog niet gebouwd (zie story 050 §Afwijkingen punt
   5) — dit event-contract laat er wél ruimte voor (een extra `sources`/`grounding`-achtig type
   toevoegen is later een kwestie van een extra `elif`, geen contractbreuk).

## Wijzigingen

- `agent/orchestrator.py`:
  - `agent_node` gebruikt `llm.stream(...)` i.p.v. `llm.create(...)`; elke tekst-delta gaat via
    `get_stream_writer()` als `{"type": "token", "content": delta}` naar de custom-stream, vóór
    `stream.final_message()` wordt gelezen voor tool_uses/turns (ongewijzigde parsing —
    `final_message()` heeft dezelfde vorm als `create()`'s return).
  - `synthesize_node` idem: `llm.stream(...)`, tokens via `get_stream_writer()`.
  - Geen wijziging aan de graaf-topologie zelf — alleen hoe deze twee nodes hun LLM-call doen.
- `agent/agent.py` (nieuw): `answer_stream(question, conversation_id=None, *, settings=None,
  llm=None, graph=None) -> AsyncIterator[dict[str, Any]]`. Bouwt providers (of injecteert de
  meegegeven fakes), kiest de checkpointer (`checkpointer_ctx`), compileert de graaf
  (`build_graph(..., checkpointer=saver)`), roept `nieuwe_beurt_invoer(question)` aan, en streamt
  via `app.astream(init, config, stream_mode=["custom", "values"])`:
  - `mode == "custom"` → chunk (de `token`-events uit de nodes) direct doorgeven.
  - `mode == "values"` → bij het laatste frame: `{"type": "sources", "sources": [...]}` +
    `{"type": "grounding", "grounded": bool, "niveau": ..., "unsupported": [...]}`, dan
    `{"type": "done"}`.
  - `GraphRecursionError` → `{"type": "error", "message": "<vriendelijke melding>"}`.
  - Overige `Exception` → `_foutmelding(exc)` (poort van de referentie se soort-op-naam-herkenning:
    RateLimitError/BadRequestError/UnprocessableEntityError/APIConnectionError/APITimeoutError,
    provider-uitzonderingen op naam herkend i.p.v. geïmporteerd — de anthropic-SDK blijft een
    optionele extra) → `{"type": "error", "message": ...}`.
  - `graph.close()` in een `finally`.

## Acceptatiecriteria

- [x] `agent_node`/`synthesize_node` streamen tekst-deltas via `get_stream_writer()`
      (`{"type": "token", ...}`) i.p.v. het antwoord in één stuk terug te geven — unit-geverifieerd
      met een `FakeLLM.stream()`-scenario (gedeelde helper `_stream_final`).
- [x] `answer_stream()` levert het volledige event-contract (`token`/`sources`/`grounding`/`done`/
      `error`) voor het single-loop-pad (decompositie-pad qua topologie ongewijzigd — `synthesize_
      node` streamt via dezelfde `_stream_final`-helper, geen apart event-contract nodig).
- [x] Een afgewezen vraag (supervisor `AFWIJZEN`) levert nog steeds `done`, geen crash op het
      ontbreken van `sources`/`grounding`-velden (`.get(..., default)` — `nieuwe_beurt_invoer`'s
      reset-defaults vangen dit al op).
- [x] `GraphRecursionError` geeft een eigen, herkenbare melding (niet de generieke tekst).
- [x] Overige exceptions krijgen een gesaniteerde melding via `_foutmelding` — de ruwe
      exception-tekst lekt niet naar het event (unit-geverifieerd met een kapotte LLM-fake).
- [x] Bestaande 222 tests blijven groen zonder aanpassing aan hun asserties (`agent_node`/
      `synthesize_node`'s return-vorm — `answer`, `messages`, `pending_tools`, `turns` — verandert
      niet; alleen de manier waarop de tekst tot stand komt) — bevestigd, geen enkele bestaande
      test aangepast.
- [x] Live-geverifieerd: een echte vraag via `answer_stream()` levert zichtbare token-events vóór
      het `done`-event (`test_live_answer_stream_levert_tokens_vóór_done`).

## Buiten scope

`stop_check`/`BeurtGestopt`, observability/tracer, het runs-model (`POST /v1/runs`) en
beurt-persistentie (`agent/beurt.py`), de recursielimiet-formule, tokenstreaming op
tussenliggende tool-lus-beurten, `entities_seen`. Zie §Afwijkingen per punt.

## Prioriteit / story points

Prioriteit: **high**. Story points: **3** (twee bestaande nodes ombouwen van `create` naar
`stream`, één nieuwe dunne wrapper-module, geen graaf-topologiewijziging, geen nieuwe
dependencies — `get_stream_writer`/`stream()` bestaan al).

## Verificatie

- `pytest -q -m "not integration"`: 227 passed (222 bestaand + 5 nieuw in `tests/test_agent.py`,
  geen enkele bestaande test aangepast).
- `ruff check . && ruff format --check .`: schoon.
- `pytest -q -m integration`: 11 passed (10 bestaand + 1 nieuw:
  `test_live_answer_stream_levert_tokens_vóór_done`), tegen de echte GraphDB + Foundry — bewijst
  dat er daadwerkelijk `token`-events binnenkomen vóór `done`, niet alleen dat er ergens een
  antwoord verschijnt.

## Gebouwd:

Ja (PR #89).
