# Story 044 — graph-qa: minimale antwoord-agent-loop (LangGraph)

## Verhaal

Als ontwikkelaar wil ik dat de drie losse bouwstenen van `tools/graph-qa` (LLM-adapter,
GraphDB-adapter, toollaag — stories 039-041) daadwerkelijk samenwerken tot een agent die een vraag
over de wetgeving beantwoordt: tools aanroepen, een antwoord formuleren, en dat antwoord op
brongetrouwheid controleren vóór het teruggaat.

## Aanleiding

Eerste story van de "agent-loop"-werkstroom (CLAUDE.md §Volgende stap, ~25-35 stories geschat).
Vooronderzoek: een Explore-agent las de volledige `wetsanalyse-ai/tools/graph-qa/agent/`-map
(orchestrator.py 1769 regels, plus 15 kleinere modules) en de reeds bestaande sessie-kennis van
`grounding.py`/`provenance.py`/`models.py`. Aanbeveling, overgenomen: begin met de kleinste
zelfstandige snede — de **antwoord-worker zonder supervisor, zonder annotatie-keten, zonder
decompositie** (dit is exact de "legacy"-graafvariant die de referentie zelf nog aanbiedt als
`enable_planning=False, enable_decomposition=False` uitvalt). Reden om niet met de supervisor of de
annotatieketen te beginnen:
- De **supervisor** kiest alleen tussen workers die nog niet bestaan — routeringstests zouden tegen
  denkbeeldige bestemmingen moeten schrijven.
- De **annotatieketen** (ophaal → annoteer → Critic → patch → herzie) is met afstand het grootste en
  meest beproefde deel van de referentie (`test_critic_lus.py` alleen al 769 regels) — geen goede
  eerste snede om vanaf nul te bouwen.
- De antwoord-loop is **nu al volledig zelfstandig te bouwen en te bewijzen**: hij heeft alleen de
  al-bestaande poorten (`ports.py`) en toollaag (`agent/tools/`) nodig, plus twee kleine
  deterministische modules (`grounding.py`, `provenance.py`) zonder eigen LLM-afhankelijkheden.

## Referentie-architectuur (relevante deel)

`orchestrator.py`'s `State` (`TypedDict`) — hier alleen het antwoord-deel:
`question`, `messages` (`operator.add`), `source_trace: list[tuple[str,str]]`, `answer`,
`pending_tools`, `turns`, `corrected`, `grounded`, `cited`, `unsupported`, `niet_letterlijk`,
`grounding_niveau`, `sources`.

Graaf (legacy-variant): `START → agent_node ⇄ tools_node → verify_node → (correct_node → agent_node
| finalize_node) → END`.

- **`agent_node`** — één specialist-systeemprompt (`SYSTEM_PROMPT` uit `prompts.py`) +
  `anthropic_schemas()` (alle 13 tools — geen specialistenregistratie in deze snede, zie
  §Afwijkingen), roept `llm.create(...)`, leest `stop_reason`/tool_use-blokken.
- **`tools_node`** — `dispatch(name, graph, args, settings)` per pending tool-call, resultaat in
  `source_trace`.
- **`verify_node`** — `check_grounding(answer, source_trace)` (`grounding.py`, deterministisch, geen
  LLM): controleert vindplaatsen (BWB-id moet uit de trace komen) én citaten (tekst tussen
  aanhalingstekens moet letterlijk in de trace staan). Levert `niveau: gegrond|onbepaald|ongegrond`.
- **`correct_node`** — bij `ongegrond` één corrigerende her-vraag (max. 1 ronde via `corrected`).
- **`finalize_node`** — `collect_sources` (`provenance.py`, regex over de trace, nooit over
  modeltekst) → `curate_sources` (beperkt tot in het antwoord genoemde regelingen).

## lexplainables-specifieke afwijkingen (bewust, met reden)

1. **Geen supervisor, geen specialistenregistratie (`specialists.py`).** Deze snede gebruikt één
   vaste systeemprompt met alle tools, exact de referentie se legacy-graafvariant. De supervisor +
   specialisten-routing is een aparte, latere story zodra er meerdere workers zijn om tussen te
   routeren (zie §Aanleiding).
2. **Geen supervisor betekent ook: geen "AFWIJZEN"-pad.** Een vraag buiten de wetgeving belandt nu
   gewoon bij de agent-node, die met de tools niets zinnigs vindt en dat zegt. Acceptabel voor deze
   snede; de supervisor-story voegt de vroege afwijzing toe.
3. **Geen annotatie-worker, geen `modus: "advies"`.** Buiten scope; komt met de annotatieketen-story.
4. **Geen checkpointer, geen multi-turn gespreksgeheugen, geen streaming/SSE.** Er is nog geen
   API-laag die dit consumeert (`tools/graph-qa/api/` is leeg). `build_graph()` compileert zonder
   checkpointer; een aanroep is één synchrone `.invoke(state)` per vraag. Streaming
   (`llm.stream()`/`get_stream_writer()`) en de checkpointer-keuze (Postgres/SQLite/memory) komen
   met de story die de FastAPI-laag + `/v1/runs`-achtige endpoints bouwt.
5. **Geen decompositie (`enable_decomposition`).** Multi-hop-vragen zijn een latere uitbreiding op
   een werkende single-hop-loop, niet een dag-1-feature.
6. **`SYSTEM_PROMPT` zonder naam/identiteit-framing.** De referentie se prompt opent met "Je heet
   Lex" + een uitgebreid identiteitsblok. lexplainables heeft nog geen chat-UI die een agentnaam zou
   tonen (`frontend-chat` staat nog niet gebouwd) en nergens in dit project is een naam voor de
   agent vastgelegd. De inhoudelijke regels (onderwerp-afbakening, onderbouwing, citeren,
   toolkeuze, antwoordvorm — de regels die het gedrag bepalen) worden **wel** 1:1 geport; alleen de
   naam/persona-zin vervalt. Naamgeving is een productbeslissing voor wanneer er een UI is om hem in
   te tonen — vervolgpunt, geen aanname om hier stilzwijgend te maken.
7. **`komt_letterlijk_voor`/`_normaliseer` (nodig voor `grounding.py`'s citaatcontrole) leven in de
   referentie in `annotatie.py`, dat hier nog niet bestaat.** Rechtstreeks in `grounding.py` gezet
   (de enige consument in deze snede) i.p.v. een `annotatie.py`-stub vooruit te bouwen — opportunistisch
   verwijzen geldt pas ná een tweede consument (`feature-bouwen` regel 8); de annotatieketen-story
   verhuist de functie dan naar een gedeelde plek.
8. **`namespace.py` krijgt `vindplaats_patroon()` terug.** Story 041 liet die helper bewust weg
   ("geen consument nu"); `provenance.py` is nu de eerste echte consument.
9. **`langgraph` wordt een nieuwe dependency** (`pyproject.toml`), zonder de checkpointer-extra's
   (`langgraph-checkpoint-sqlite`/`-postgres` — die horen bij de story die de checkpointer echt
   gebruikt, zie punt 4).

## Nieuwe/aangepaste bestanden

- `agent/namespace.py` — `vindplaats_patroon()` + `import re` toevoegen.
- `agent/models.py` (nieuw) — getrimd: `Source`, `TokenEvent`, `SourcesEvent`, `GroundingEvent`,
  `DoneEvent`, `ErrorEvent`. Geen `ChatRequest`/`AgentDoel`/`ChatContext`/annotatie-modellen/
  `ArtikelResult` — die horen bij stories die ze daadwerkelijk gebruiken.
- `agent/provenance.py` (nieuw) — 1:1 poort (`iter_refs`, `citations_in`, `collect_sources`,
  `first_bwb`, `_BWB_RE`).
- `agent/grounding.py` (nieuw) — 1:1 poort van `GroundingReport`/`check_grounding`/`curate_sources`,
  plus `komt_letterlijk_voor`/`_normaliseer` (zie afwijking 7).
- `agent/prompts.py` (nieuw) — `SYSTEM_PROMPT`, inhoudelijk 1:1 minus de naam-framing (afwijking 6).
- `agent/orchestrator.py` (nieuw) — `State`, `build_graph(settings, llm, graph) -> CompiledGraph`
  met de vijf nodes hierboven.
- `pyproject.toml` — `langgraph` toevoegen.
- Tests: `tests/test_grounding.py`, `tests/test_provenance.py`, `tests/test_orchestrator.py`
  (poorten van de gelijknamige referentie-bestanden, getrimd tot wat hier bestaat), plus een
  `@pytest.mark.integration`-test die de gecompileerde graaf één keer echt laat draaien tegen de
  lokale GraphDB + Foundry (verplicht live-verificatie-principe, zoals bij elke eerdere graph-qa-story).

## Acceptatiecriteria

- [x] `build_graph(settings, llm, graph).invoke({"question": "..."})` levert een `answer` op die
      via tools uit de graaf is opgehaald (niet uit LLM-parametrische kennis).
- [x] Een antwoord met een vindplaats die niet in de tool-trace voorkomt, of een citaat dat niet
      letterlijk in de trace staat, krijgt `grounding_niveau: "ongegrond"` en doorloopt
      `correct_node` (precies één corrigerende ronde, niet meer).
- [x] Een antwoord zonder enige vindplaats/citaat krijgt `grounding_niveau: "onbepaald"` (niet
      stilzwijgend "gegrond").
- [x] `sources` in de eindstate bevat alleen regelingen die het antwoord daadwerkelijk noemt
      (`curate_sources`).
- [x] Live-geverifieerd: een echte vraag ("Wat staat er in artikel 2 van de Invorderingswet 1990
      over belastingschuldigen?") tegen de lokale, gevulde GraphDB + Foundry levert een grounded
      antwoord op met een correct, letterlijk citaat van de definitie ("belastingschuldige: degene
      te wiens naam de belastingaanslag is gesteld", art. 2 lid 1 onderdeel k) en 40 bronnen
      (alle jci/IRI-vindplaatsen die het antwoord noemt); 4 turns (search_wetgeving → get_artikel →
      get_lid × 2).
- [x] Unit-tests dekken: gelukkig pad (tool-call → antwoord → gegrond), ongegrond-pad → correctie,
      onbepaald-pad (geen citaat/vindplaats), max-turns-vangnet (geen oneindige tool-lus).

## Buiten scope

Supervisor/specialisten-routing, annotatieketen, decompositie, checkpointer/gespreksgeheugen,
streaming/SSE, FastAPI-laag (`api/main.py`), agentnaam/identiteit — zie §Afwijkingen voor de reden
per punt. Elk hiervan is een eigen, latere story.

## Prioriteit / story points

Prioriteit: **high** (eerste story van de eerstvolgende grote werkstroom, expliciet gekozen door de
gebruiker). Story points: **5** — meerdere nieuwe modules, een nieuwe dependency, een echte
architecturale beslissing (welke laag van de referentie wél/niet meekomt), en raakt de bestaande
poorten/toollaag uit stories 029/039-041.

## Implementatieplan

**Nieuwe bestanden:**
- `agent/models.py` — `Source`, `TokenEvent`, `SourcesEvent`, `GroundingEvent`, `DoneEvent`, `ErrorEvent`.
- `agent/provenance.py` — `iter_refs`/`citations_in`/`collect_sources`/`first_bwb` + de IRI/jci/BWB-regexes.
- `agent/grounding.py` — `GroundingReport`/`check_grounding`/`curate_sources` + `komt_letterlijk_voor`/`_normaliseer`.
- `agent/prompts.py` — `SYSTEM_PROMPT` (identiteit-opening neutraal, rest 1:1).
- `agent/orchestrator.py` — `State`, `MAX_TURNS=8`, nodes `agent_node`/`tools_node`/`verify_node`/`correct_node`/`finalize_node`, `build_graph(settings, llm, graph)`.
- `tests/test_provenance.py`, `tests/test_grounding.py`, `tests/test_orchestrator.py` (+ 1 `@pytest.mark.integration`-test).

**Aangepaste bestanden:**
- `agent/namespace.py` — `vindplaats_patroon()` + `import re` toevoegen.
- `pyproject.toml` — `langgraph>=1.2` toevoegen (geen checkpointer-extra's).

**Graafwiring:** `START → agent_node ⇄ tools_node → verify_node → (correct_node → agent_node | finalize_node) → END`, `.compile()` zonder checkpointer.

**Testcases:** zie story §Acceptatiecriteria — gelukkig pad (gegrond), ongegrond-pad → precies 1 correctieronde, onbepaald-pad (geen vindplaats/citaat), max-turns-vangnet, live-integratietest tegen de Invorderingswet-fixture.

**Aandachtspunten:**
- `komt_letterlijk_voor`/`_normaliseer` tijdelijk in `grounding.py` (enige consument nu) i.p.v. vooruitlopend een `annotatie.py`-stub te bouwen.
- Geen supervisor/annotatieketen/decompositie/checkpointer/streaming/API-laag/agentnaam — allemaal expliciet latere stories, zie §Afwijkingen.

## Verificatie

- `uv run --extra dev pytest -q -m "not integration"` — 122 tests groen (o.a. de nieuwe
  `test_provenance.py`/`test_grounding.py`/`test_orchestrator.py`).
- `uv run ruff check . && uv run ruff format --check .` — schoon.
- Live: `GRAPHDB_MCP_URL=... GRAPHDB_TOKEN=... AZURE_FOUNDRY_API_KEY_FILE=... AZURE_FOUNDRY_
  RESOURCE=... uv run --extra dev pytest -q -m integration` — 3 tests groen (incl. de nieuwe
  `test_orchestrator_integration.py`). Handmatig doorgelicht: het antwoord citeert de echte
  definitie van "belastingschuldige" (art. 2 lid 1 onderdeel k) letterlijk en correct, met
  40 reële bronnen — geen placeholder- of hallucinatie-uitkomst.

## Gebouwd:

Ja (PR #81). Eerste werkende graph-qa-agent: vraag → tools → antwoord → brongetrouwheidscontrole,
live bewezen tegen de Invorderingswet-fixture. Alle drie eerdere bouwstenen (poorten/adapters/
toollaag, stories 029/039-041) werken nu daadwerkelijk samen. Geen enkele live-gevonden bug deze
keer — het gedegen vooronderzoek (volledige referentie-orchestrator gelezen vóór het bouwen) betaalde
zich hier uit, in tegenstelling tot stories 040/041.
