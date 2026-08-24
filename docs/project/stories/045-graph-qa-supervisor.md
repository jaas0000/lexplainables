# Story 045 — graph-qa: supervisor (specialist-routing + afwijzen)

## Verhaal

Als jurist wil ik dat de agent een vraag over een juridisch begrip anders aanpakt dan een vraag
over de samenhang tussen bepalingen, en dat een vraag die niets met wetgeving te maken heeft
meteen en zonder graafbevraging wordt afgewezen — in plaats van dat elke vraag met dezelfde brede
toolset en dezelfde generieke aanpak wordt behandeld.

## Aanleiding

Vervolg op story 044 (minimale antwoord-agent-loop). Dat verhaal bouwde bewust de kleinste
snede: één vaste systeemprompt, alle tools, geen keuze. Dit is de tweede snede: de supervisor die
per vraag een **specialist** kiest (`definitie`/`duiding`/`algemeen`, elk met een eigen
prompt-addendum en een beperkte toolset) en vaststelt of een vraag helemaal **buiten de wetgeving**
valt (`afwijzen`).

De referentie se supervisor kiest ook tussen een `antwoord`-worker en een `annotatie`-worker (en
kan ze ketenen). Dat vervalt hier volledig — lexplainables heeft nog geen annotatieketen (dat is
een eigen, veel grotere latere story, zie story 044 §Buiten scope), dus er is maar één worker om
naar te routeren. Een supervisor die tussen twee dingen kiest waarvan er één niet bestaat, is geen
supervisor maar overhead.

## Referentie-architectuur (relevante deel)

`agent/supervisor.py`: `SUPERVISOR_SYSTEM`-prompt, drieregelig antwoordformaat (`WORKERS:`/
`SPECIALIST:`/`PLAN:`), `parse_supervisor(text) -> (worker_plan, plan, afwijzen)`.
`agent/specialists.py`: `Specialist(system, tools)`-registry — `definitie`/`duiding`/`algemeen`
(+ `retrieval` voor de annotatie-ophaal-agent, hier niet relevant). `orchestrator.py`:
`supervisor_node` (één `llm.create`-call, `max_tokens=300`, geen tools), `_entry_node` routeert
naar `afwijzen` of de gekozen worker, `afwijs_node` (terminale beleefde weigering, geen tools/LLM),
`agent_node` bouwt het systeemblok uit `SYSTEM_PROMPT` + het specialist-addendum en de toolset uit
`anthropic_schemas(only=spec.tools)`.

## lexplainables-specifieke afwijkingen (bewust, met reden)

1. **Geen `WORKERS:`-regel, geen `antwoord`/`annotatie`-keuze.** `parse_supervisor` levert hier
   `(specialist: str, plan: str, afwijzen: bool)` — twee velden i.p.v. drie, en geen
   worker-keten/`_MAX_WORKERS`-plafond (dat bestond om ketenen van workers te begrenzen; met één
   worker is er niets om te ketenen). `SUPERVISOR_SYSTEM` is ingekort tot een `SPECIALIST:`/
   `PLAN:`-formaat.
2. **Geen `retrieval`-specialist.** Die hoort bij de annotatie-ophaal-agent, die hier niet bestaat.
   `agent/specialists.py` bevat alleen `definitie`/`duiding`/`algemeen`.
3. **Geen `worker_plan`/`worker_idx`/`advance_node`.** Die machinerie bestaat om tussen meerdere
   workers te schakelen (bv. eerst annoteren, dan samenvatten) — met één worker is er niets om
   tussen te schakelen. `State` krijgt alleen `specialist: str`, `plan: str`, `afwijzen: bool`.
4. **Geen `_heeft_opgegeven_doel`/`modus: "advies"`-kortsluitingen.** Die slaan de supervisor-call
   over voor de annotatieketen resp. adviesvragen bij een bestaande markering — geen van beide
   bestaat hier.
5. **Geen apart `model_voor("router")`.** De referentie kan de supervisor op een goedkoper/sneller
   model laten draaien dan de specialisten. lexplainables' `Settings` heeft dat knop-concept niet
   en deze story voegt het niet toe — de supervisor-call gebruikt gewoon `settings.llm_model`. Een
   apart routermodel is een losse, latere optimalisatie-story als de kosten dat rechtvaardigen,
   geen aanname om hier vooruit te bouwen.
6. **`afwijs_node`'s tekst mist de annotatie-uitnodiging.** De referentie se weigering eindigt met
   "...of laat me een artikel annoteren volgens het JAS" — die mogelijkheid bestaat hier niet, dus
   die zin vervalt.
7. **Geen prompt-caching-split (`[stabiel, variabel]`) op het antwoord-systeemblok.** Story 044
   koos al voor één platte string i.p.v. de gesplitste vorm — caching heeft pas zin bij herhaalde
   calls binnen één sessie, en die sessie-laag (checkpointer/API) bestaat nog niet. Deze story
   volgt dezelfde keuze voor het specialist-addendum.

## Wijzigingen

- `agent/specialists.py` (nieuw) — `Specialist`-dataclass + registry (3 specialisten), `get(naam)`
  met terugval op `"algemeen"`.
- `agent/supervisor.py` (nieuw) — ingekorte `SUPERVISOR_SYSTEM` + `parse_supervisor`.
- `agent/orchestrator.py` (aangepast) —
  - `State`: `specialist: str`, `plan: str`, `afwijzen: bool` erbij.
  - Nieuwe nodes: `supervisor_node` (roept de LLM aan, `max_tokens=300`, `tools=[]`), `afwijs_node`
    (terminaal, geen LLM/tools).
  - `agent_node`: systeemblok wordt `prompts.SYSTEM_PROMPT + "\n\n" + specialist.system` (indien
    niet leeg), toolset wordt `anthropic_schemas(only=specialist.tools)` (`None` = alle tools, voor
    `algemeen`).
  - Graafwiring: `START → supervisor → (afwijzen | agent) ⇄ tools → verify → (correct → agent |
    finalize) → END`.

## Acceptatiecriteria

- [x] Een begripsvraag ("wat is een belastingschuldige?") routeert naar de `definitie`-specialist
      (aantoonbaar via de toolset/systeemprompt die de daaropvolgende `agent_node`-call krijgt).
      Geverifieerd zowel unit (`test_supervisor_routeert_naar_specialist_en_beperkt_de_toolset`)
      als live (zie §Verificatie).
- [x] Een vraag buiten de wetgeving ("wat is het weer vandaag?") wordt afgewezen: geen
      `agent_node`/`tools_node`-aanroep, geen graafbevraging, een vast beleefd weigeringsantwoord.
      Geverifieerd unit (`test_afwijzen_pad_raakt_de_graaf_niet`) en live.
- [x] Een onbekende/lege specialist-waarde uit een malvormd LLM-antwoord valt terug op `algemeen`
      (nooit een crash op een onverwacht antwoordformaat). Unit-geverifieerd
      (`test_onbekende_specialist_valt_terug_op_algemeen_volledige_toolset`,
      `test_onbekende_specialist_valt_terug_op_algemeen` in `test_supervisor.py`).
- [x] Live-geverifieerd: een definitievraag en een duidingsvraag tegen de lokale GraphDB + Foundry
      routeren zichtbaar naar verschillende specialisten, en een evident-buiten-de-wetgeving-vraag
      wordt afgewezen zonder de graaf te raken. Zie §Verificatie voor de drie handmatig
      doorgelichte responsen.
- [x] Unit-tests dekken: routing naar elk van de 3 specialisten, afwijzen-pad, terugval op
      `algemeen` bij een malvormd supervisor-antwoord. 136 unit-tests groen (incl. de nieuwe
      `test_specialists.py`/`test_supervisor.py` en de 3 aanvullingen op `test_orchestrator.py`),
      plus 5 live-tests groen.

## Buiten scope

Worker-keten (antwoord+annotatie), annotatieketen zelf, `modus: "advies"`, apart routermodel,
prompt-caching-split, checkpointer/streaming/API-laag — zie §Afwijkingen voor de reden per punt.

## Prioriteit / story points

Prioriteit: **high** (tweede story van de agent-loop-werkstroom, direct vervolg op 044).
Story points: **4** — twee nieuwe, kleine modules + wiziging aan de bestaande graafwiring uit
story 044, geen nieuwe dependency, minder omvangrijk dan 044 (geen nieuwe grounding/provenance-laag).

## Implementatieplan

**Nieuwe bestanden:**
- `agent/specialists.py` — `Specialist`-dataclass + registry (definitie/duiding/algemeen), `get()`.
- `agent/supervisor.py` — ingekorte `SUPERVISOR_SYSTEM` + `parse_supervisor() -> (specialist, plan, afwijzen)`.
- `tests/test_specialists.py`, `tests/test_supervisor.py` — nieuw.

**Aangepaste bestanden:**
- `agent/orchestrator.py` — `State` (+specialist/plan/afwijzen), nieuwe nodes `supervisor_node`/`afwijs_node`, `agent_node` gebruikt specialist-scoped system/tools, nieuwe routing `route_after_supervisor`, `build_graph` wiring: `START → supervisor → (afwijzen → END) → agent ⇄ tools → verify → (correct → agent | finalize) → END`.
- `tests/test_orchestrator.py` — 4 bestaande tests krijgen een supervisor-respons vooraan hun `FakeLLM`-lijst (regel 9 uit `feature-bouwen`: bewuste wijziging van bestaand gedrag, expliciet vastgelegd); 3 nieuwe tests (specialist-routing, afwijzen-pad, onbekende-specialist-terugval).
- `tests/test_orchestrator_integration.py` — tweede live test (specialist-routing + afwijzen zonder graafbevraging).

**Testcases:** zie story §Acceptatiecriteria.

**Aandachtspunten:**
- Geen worker-keten/annotatie-routing, geen apart routermodel, geen prompt-caching-split — zie §Afwijkingen.
- `afwijs_node` zet ook `sources: []` zodat de State-vorm consistent blijft met het normale pad.

## Verificatie

- `uv run --extra dev pytest -q -m "not integration"` — **136 passed, 5 deselected**.
- `uv run ruff check . && uv run ruff format --check .` — schoon (2 regels E501 onderweg
  gefixt, 2 bestanden door `ruff format` herschikt).
- `uv run --extra dev pytest -q -m integration` (tegen de lokale `deploy/graphdb`-stack +
  Azure Foundry) — **5 passed** (de bestaande story-044-test, plus de 2 nieuwe uit deze story).
- Handmatig doorgelicht, drie live vragen tegen de echte Invorderingswet-fixture:
  - *"Wat betekent het begrip belastingschuldige volgens de Invorderingswet 1990?"* → routeerde
    naar `definitie`, `resolve_begrip`/`search_wetgeving`/`get_lid` gebruikt, antwoord citeert
    letterlijk artikel 2 lid 1 onderdeel k ("belastingschuldige: degene te wiens naam de
    belastingaanslag is gesteld;"), `grounding_niveau: gegrond`.
  - *"Hoe verhoudt artikel 2 zich tot artikel 3 van de Invorderingswet 1990?"* → routeerde naar
    `duiding`, gebruikte `get_context`/`get_artikel`/`search_wetgeving`, en rapporteerde eerlijk
    dat artikel 3 niet als zelfstandig artikel in de graaf voorkomt (de Invorderingswet-fixture
    heeft dat artikel niet) — geen verzonnen inhoud.
  - *"Wat is het weer vandaag in Amsterdam?"* → `afwijzen: True`, `source_trace: []` (geen
    enkele tool aangeroepen), vaste weigeringstekst.

## Gebouwd:

Ja (PR #82).
