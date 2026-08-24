# Story 050 — graph-qa: checkpointer (gespreksgeheugen)

## Verhaal

Als jurist wil ik dat een vervolgvraag in hetzelfde gesprek de context van eerdere vragen kent
(en een vervolg-annotatie niet per ongeluk de vorige bepaling opnieuw pakt), zodat ik niet elke
vraag als een geïsoleerd, geheugenloos verzoek hoef te stellen.

## Aanleiding

Eerste story ná de annotatieketen-werkstroom (044-049, afgerond). Voegt LangGraph-checkpointing
toe: `messages` (al een append-reducer sinds story 044) persisteert nu daadwerkelijk over
losse `.ainvoke()`-aanroepen heen via `thread_id = conversation_id`. Bewust **smal**: alleen de
checkpointer-selectie + het per-beurt-reset-patroon. Streaming, observability, foutvertaling,
het run-/stop-model en de API-laag zelf zijn losse, latere stories (zie referentie `agent/
agent.py`'s `answer_stream`, die dit allemaal in één functie bundelt — hier expliciet ontbundeld).

## lexplainables-specifieke afwijkingen

1. **Geen SSE/streaming, geen observability-tracer, geen foutvertaling naar de gebruiker, geen
   `stop_check`/`BeurtGestopt`, geen `delete_conversation`.** Allemaal onderdeel van de referentie
   se `answer_stream`, maar horen bij de streaming- resp. API-laag-stories.
2. **Geen `_recursielimiet`-topologieformule.** Die bestaat om een lange annotatie+antwoord-keten
   niet tegen LangGraph's default recursielimiet te laten lopen — met de huidige, kleinere
   topologie (geen worker-chaining) is de default limiet ruim voldoende; een aparte formule zou
   hier vooruitlopen op complexiteit die nog niet bestaat.
3. **`nieuwe_beurt_invoer(question=None, doel=None)`** vervangt de referentie se inline `init`-dict
   in `answer_stream` — een eigen, testbare functie i.p.v. inline in een streaming-wrapper die hier
   nog niet bestaat. Resetvelden 1:1 afgeleid van lexplainables' (getrimde) `State` — geen
   `modus`/`context`/`opgegeven_doel` (advies-modus/jurist-context bestaan hier niet).
4. **`build_graph` blijft de enige graaf-bouwer**, met een nieuwe optionele
   `checkpointer`-parameter (default `None` → ongewijzigd gedrag, `builder.compile()` zoals nu).
   Geen aparte `build_graph_met_checkpointer`-variant.
5. **`_recent_context(state)` i.p.v. de referentie se `entities_seen`-laag +
   `_memory_context()`.** De referentie houdt een gededupliceerde lijst geraadpleegde BWB-IRI's
   bij (`entities_seen`, een apart State-veld + accumulatielogica in `finalize_node`/
   `emit_node`) en injecteert die als beknopte context in `supervisor_node`/`decompose_node`/
   `solve_node`. Dat is een eigen, grotere feature. Deze story bouwt in plaats daarvan een
   kleinere, alleen-in-`supervisor_node` variant: de laatste paar `messages`-berichten zelf, plat
   samengevat. Reden: zonder enige vorm van gesprekscontext bij de supervisor faalt een
   pronomenrijke vervolgvraag zichtbaar (zelf live gevonden, zie §Acceptatiecriteria) — een
   volledige `entities_seen`-laag oplossen is meer dan deze smalle story aankan, maar niets doen
   laat de kernbelofte van "gespreksgeheugen" half af. `decompose_node`/`solve_node` krijgen dit
   niet — een vervolgvraag die via decompositie loopt, is al door de supervisor heen (die wél
   context had) tegen die tijd.

## Wijzigingen

- `pyproject.toml` — `langgraph-checkpoint-sqlite`, `langgraph-checkpoint-postgres` toegevoegd.
- `agent/config.py` — `checkpoint_db_url: str | None`, `checkpoint_db_path: str | None` (env
  `CHECKPOINT_DB_URL`/`CHECKPOINT_DB_PATH`).
- `agent/checkpointer.py` (nieuw) — `checkpointer_ctx(settings) -> AsyncContextManager`: 1:1 poort
  van `_checkpointer_ctx` (Postgres → SQLite-bestand → `MemorySaver`), minus
  `delete_conversation`/observability.
- `agent/orchestrator.py` —
  - `build_graph(settings, llm, graph, *, checkpointer=None)`: `builder.compile(checkpointer=
    checkpointer)` i.p.v. `builder.compile()`. Zonder `checkpointer` (default) blijft het gedrag
    byte voor byte gelijk aan stories 044-049.
  - Nieuwe functie `nieuwe_beurt_invoer(question=None, doel=None) -> dict[str, Any]`: reset alle
    ephemere `State`-velden (zie §Afwijkingen punt 3) en zaait `messages` met de nieuwe
    user-vraag (alleen bij `question`; een `doel`-gedreven annotatiebeurt zaait geen bericht,
    matcht `_heeft_doel`'s bestaande bypass).
  - `State.sources` van `list[Source]` naar `list[dict[str, Any]]`; `finalize_node` doet nu
    `.model_dump()` vóór het de state in gaat (zelf gevonden bugfix, zie §Acceptatiecriteria).
  - Nieuwe functie `_recent_context(state) -> str` + `supervisor_node` gebruikt
    `supervisor.SUPERVISOR_SYSTEM + _recent_context(state)` i.p.v. de kale systeemprompt (zelf
    gevonden bugfix, zie §Afwijkingen punt 5 en §Acceptatiecriteria).

## Acceptatiecriteria

- [x] `checkpointer_ctx` kiest Postgres bij `checkpoint_db_url`, SQLite-bestand bij
      `checkpoint_db_path`, anders `MemorySaver` — alle drie unit-geverifieerd.
- [x] Twee losse `.ainvoke()`-aanroepen met hetzelfde `thread_id` (via `nieuwe_beurt_invoer`)
      tonen dat de tweede aanroep de `messages`-historie van de eerste heeft. Unit + live.
- [x] Ephemere velden resetten bij elke nieuwe beurt. Unit-geverifieerd.
- [x] Twee verschillende `thread_id`'s delen geen state. Unit-geverifieerd.
- [x] `build_graph(...)` zonder `checkpointer`-argument blijft byte voor byte werken (222
      bestaande tests ongewijzigd groen, plus 2 die vanaf deze story wijzigden qua *systeem*-
      inhoud door de memory-context-fix hieronder — zie §Verificatie).
- [x] Live-geverifieerd: een echte tweede vraag in hetzelfde gesprek toont gespreksgeheugen.

**Twee bugs zelf gevonden tijdens live-verificatie, binnen deze PR opgelost (niet vóóraf
gepland, wel binnen scope — beide zijn state-vorm-problemen die pas zichtbaar worden zodra state
daadwerkelijk over beurten heen blijft bestaan, precies wat deze story toevoegt):**
- `finalize_node` zette `Source`-Pydantic-objecten rechtstreeks in de state — de checkpointer gaf
  een msgpack-deserialisatiewaarschuwing ("unregistered type", wordt in een toekomstige
  langgraph-versie geblokkeerd). Gefixt: `.model_dump()` vóór het de state in gaat, zoals overal
  elders in de codebase al gebeurde.
- `supervisor_node` bouwde zijn routeringsprompt uitsluitend uit `state["question"]`, zonder de nu
  persisterende `messages`-historie te lezen. Een vervolgvraag met een pronomen ("en welk artikel
  regelt dát begrip precies?") werd daardoor ten onrechte als "niet over de wetgeving" afgewezen.
  Gefixt met een nieuwe, kleine `_recent_context(state)`-helper die de laatste berichten als
  aanknopingspunt in de systeemprompt zet (losse, geen 1:1 poort van de referentie se volledige
  `entities_seen`-laag — zie §Afwijkingen punt 5).

## Buiten scope

Streaming/SSE, observability, foutvertaling, `stop_check`/`BeurtGestopt`/run-model,
`delete_conversation`, de topologie-afgeleide recursielimiet, API-laag — zie §Afwijkingen.

## Prioriteit / story points

Prioriteit: **high**. Story points: **5** (nieuwe dependency, nieuwe module, ~20 State-velden
met expliciete resetsemantiek, `build_graph`-signatuurwijziging, async testinfrastructuur).

## Verificatie

- `pytest -q -m "not integration"`: 222 passed (220 bestaand + 2 nieuw voor de
  memory-context-fix, bovenop de eerdere 7 checkpointer-tests — alle oorspronkelijke tests
  ongewijzigd).
- `ruff check . && ruff format --check .`: schoon.
- `pytest -q -m integration`: 10 passed.
- Live sanity-check (twee `ainvoke()`-aanroepen, zelfde `thread_id`, `MemorySaver`): de
  vervolgvraag "En welk artikel regelt dat begrip precies?" (zonder het woord
  "belastingschuldige" te herhalen) kreeg vóór de fix `afwijzen=True`; ná de fix `afwijzen=False`
  en een correct antwoord dat teruggreep op "artikel 2, lid 1, onderdeel k" uit de eerste beurt.
  Geen msgpack-waarschuwing meer.

## Gebouwd:

Ja (PR #88).
