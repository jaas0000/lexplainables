# Story 052 — graph-qa: run/stop (`stop_check`/`BeurtGestopt`)

## Verhaal

Als jurist wil ik een lopende beurt kunnen afbreken (van gesprek wisselen, een verkeerde vraag
gesteld), zonder dat de agent stiekem op de achtergrond doorwerkt en zonder dat de state van het
gesprek in een inconsistente tussentoestand blijft steken.

## Aanleiding

Tweede story ná de checkpointer, expliciet uitgesteld in zowel story 050 als 051 (§Afwijkingen):
raakt in principe alle node-registraties in `build_graph`, dus een eigen, afgebakende snede.
Bewust **smal**: alleen het stop-mechanisme zelf (een `stop_check`-callback + een
node-grens-bewaking die de graaf netjes laat uitstappen). Er is nog **geen aanroeper** die 'm
daadwerkelijk gebruikt — dat is het runs-model (`POST /v1/runs`, `POST /v1/runs/{id}/cancel`),
dat een beslissing over `tools/graph-qa/api/` vraagt en dus een latere story blijft. Deze story
levert de primitief, unit-getest met een fake `stop_check`, zodat die latere story 'm alleen nog
hoeft aan te sluiten.

## lexplainables-specifieke afwijkingen

1. **Stoppen op een nodegrens, geen taak-annulering.** 1:1 met de referentie
   (`agent_common.BeurtGestopt`): de node-functies zijn synchroon, en een lopende LLM-/MCP-call
   afbreken zou de MCP-verbinding in een inconsistente staat achterlaten. `stopbaar()` checkt
   `stop_check()` **vóór** elke node start; is die `True`, dan gooit hij `BeurtGestopt` in plaats
   van de node uit te voeren. De prijs: stoppen kost tijd, want de lopende stap maakt zichzelf af
   — dat is een bewuste keuze, geen tekortkoming.
2. **Geen `run_sync`/`agent_common.py`-losse module.** De referentie zet `BeurtGestopt` in een
   eigen `agent_common.py` omdat `agent.py` en `orchestrator.py` hem allebei nodig hebben zonder
   elkaar te importeren (cirkel-risico). lexplainables heeft dezelfde twee bestanden, dus dezelfde
   reden geldt — `BeurtGestopt` komt in een nieuw, klein `agent/agent_common.py`. `run_sync` (de
   andere helper daar in de referentie) blijft weg: niets in lexplainables' `agent.py` doet nu een
   blocking call die een threadpool-wrapper nodig heeft (providers bouwen is puur synchrone
   object-constructie, geen I/O).
3. **Geen HTTP-endpoint, geen runs-model, geen 409-botsingscontrole.** `POST /v1/runs` +
   `/cancel` + het achtergrondtaak-eventlog zijn een aparte, grotere story die eerst een keuze
   vraagt over `tools/graph-qa/api/` (nu een leeg skelet) — zie ook story 051 §Afwijkingen punt 3.
   `answer_stream(..., stop_check=...)` is hier puur een parameter; wie 'm aanroept en hoe de
   vlag gezet wordt, is die latere story.
4. **`BeurtGestopt` in `answer_stream` is geen foutpad.** Zoals de referentie: geen
   `error`-event, gewoon `done` (en `conversation_id` indien gegeven) — wat er tot dat punt al
   geëmit is (tokens) blijft geldig, maar `sources`/`grounding` worden **niet** ge-yield (de
   beurt is nooit bij `finalize`/`emit` aangekomen, dus die velden zijn niets toe te voegen aan
   wat de client al kreeg).

## Wijzigingen

- `agent/agent_common.py` (nieuw) — `BeurtGestopt(Exception)`, met dezelfde uitleg als de
  referentie (nodegrens, geen taak-annulering, prijs = latency).
- `agent/orchestrator.py`:
  - `build_graph(..., stop_check: Callable[[], bool] | None = None)`: nieuwe lokale `stopbaar(fn)`
    + `add(naam, fn)`-helpers; alle 16 bestaande `builder.add_node(...)`-aanroepen (beide
    topologieën + de annotatieketen) lopen voortaan via `add(...)`. Zonder `stop_check` (default)
    is het gedrag byte voor byte gelijk aan stories 044-051 — `stopbaar()` checkt dan simpelweg
    niets (de `is not None`-guard).
- `agent/agent.py`:
  - `answer_stream(..., stop_check: Callable[[], bool] | None = None)`: geeft 'm door aan
    `build_graph`. Nieuwe `except BeurtGestopt:`-tak (vóór de generieke `except Exception`, zie
    §Afwijkingen punt 4).

## Acceptatiecriteria

- [x] Een `stop_check` die meteen `True` teruggeeft: de graaf voert **geen enkele node** uit
      (`.invoke()` gooit `BeurtGestopt` vóór de eerste node) — unit-geverifieerd.
- [x] Een `stop_check` die pas na N aanroepen `True` wordt: de graaf stopt op de eerstvolgende
      nodegrens ná dat punt, niet halverwege een node — unit-geverifieerd (aantal LLM-calls klopt
      exact met het aantal nodes dat vóór de stop draaide).
- [x] Zonder `stop_check` (of `stop_check=None`): bestaande 227 tests blijven groen zonder
      aanpassing — het stopmechanisme is een no-op default.
- [x] `answer_stream(..., stop_check=...)` eindigt op `BeurtGestopt` met `done` (en
      `conversation_id` indien gegeven), zonder `error`-event en zonder `sources`/`grounding`.
- [x] `graph.close()` loopt ook bij een gestopte beurt (de bestaande `finally` in `answer_stream`
      dekt dit al — geverifieerd, niet apart gebouwd).

## Buiten scope

Het runs-model (`POST /v1/runs`/`/cancel`, eventlog, 409-botsingscontrole), een echte aanroeper
van `stop_check` (HTTP-laag), `agent_common.run_sync`. Zie §Afwijkingen.

## Prioriteit / story points

Prioriteit: **medium** (infrastructuur zonder aanroeper — waardevol als bouwsteen, maar levert nu
nog geen zichtbaar gedrag op). Story points: **2** (één nieuwe, kleine module, een
wrapper-functie om bestaande node-registraties, één nieuwe parameter + één nieuwe except-tak in
de wrapper — geen graaf-topologiewijziging).

## Verificatie

- `pytest -q -m "not integration"`: 231 passed (227 bestaand + 3 in `test_orchestrator.py` + 1 in
  `test_agent.py`, geen enkele bestaande test aangepast).
- `ruff check . && ruff format --check .`: schoon.
- `pytest -q -m integration`: 11 passed, ongewijzigd (bewijst dat `build_graph(...)` zonder
  `stop_check` byte voor byte hetzelfde gedrag houdt tegen de echte GraphDB + Foundry).

## Gebouwd:

Ja (PR #90).
