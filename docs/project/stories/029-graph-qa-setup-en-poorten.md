# Story 029: graph-qa — project-setup + poorten (GraphPort/LLMPort)

**Prioriteit:** hoog
**Story points:** 3
**Service:** `tools/graph-qa/` (nieuw)
**Afhankelijkheid:** service 1 (`deploy/graphdb`), service 2 (`tools/bwb-import` — levert straks
de gevulde graaf; deze story heeft dat nog niet nodig)

## Verhaal

Als eerste stap van service 3 (`tools/graph-qa`, de Juridische Assistent — zie
`ai-notes/fase-4-aparte-services-plan.md` §Service 3) wil ik het projectskelet en de
poorten-abstractie (`GraphPort`/`LLMPort`) die de agent-loop scheidt van concrete providers
(GraphDB-MCP, Anthropic via Azure AI Foundry), zodat latere stories (toollaag, supervisor,
annotatieketen) tegen fakes getest kunnen worden zonder netwerk of echte credentials.

Referentie: `wetsanalyse-ai/tools/graph-qa/agent/ports.py` + `agent/config.py` +
`tests/fakes.py`. **Bewust niet 1:1 gekopieerd op één punt: `Settings` in deze story bevat alleen
de velden die de poorten zelf nodig hebben** (GraphDB-MCP-verbinding, LLM-verbinding) — de
referentie's `Settings` (agent/config.py, ~150 regels) is het resultaat van vele stories/
productie-iteraties (orkestrator-knoppen, annotatieketen-tuning, rate-limiting, OTel, …) die in
dit project nog niet bestaan. Velden komen erbij zodra de story die ze nodig heeft er is — zelfde
patroon als `tools/bwb-import`'s `Settings` (stories 024/027/028).

**Belangrijke beperking van deze story**: zonder een echte GraphDB-MCP-endpoint en Anthropic/
Azure-AI-Foundry-credentials kan niets hiervan end-to-end getest worden tegen een levende
provider. Dat is niet uitstelbaar tot een latere story — het is de reden dat de poorten-abstractie
en de fakes (`tests/fakes.py`) de allereerste stap zijn: alle latere agent-logica (toollaag,
supervisor, annotatieketen) test tegen de fakes, nooit tegen een live LLM/graaf, tenzij expliciet
`@pytest.mark.integration` (zelfde conventie als `tools/bwb-import`).

## Acceptatiecriteria

- [x] `tools/graph-qa/` is een zelfstandig Python-project (`pyproject.toml`, `uv`), pakketten
      `agent/` + `api/` (geen `graph_qa/`-map, matcht de referentie — hatchling moet dat expliciet
      weten).
- [x] `agent/ports.py`: `GraphPort` (Protocol — `sparql`, `semantic_search`, `close`) en `LLMPort`
      + `LLMStream` (Protocol — `create`, `stream`, met een `Systeem = str | list[str]`-type voor
      het systeemblok, zie referentie-toelichting over prompt-caching-scope).
- [x] `agent/config.py` (`Settings`, gewone `pydantic.BaseModel` + `from_env()`, geen
      `pydantic-settings`-dependency): alleen `graphdb_mcp_url`/`graphdb_token`/`repository_id` +
      `azure_foundry_api_key`/`azure_foundry_base_url`/`llm_model`. Secrets via `_read_secret`
      (`<NAAM>_FILE` eerst, ADR-0006).
- [x] `Settings.require_graph()`/`require_llm()`: expliciete, vroege configuratiefout (`ValueError`)
      in plaats van een cryptische fout dieper in de agent-loop.
- [x] `tests/fakes.py`: `FakeGraph` (onthoudt uitgevoerde SPARQL, geeft canned tekst terug),
      `FakeLLM` + `_FakeStream` (speelt een vaste reeks responses af via `create()`/`stream()`,
      gedeelde index), `make_settings()`-testhelper.
- [x] CI (`graph-qa-ci.yml`): pytest + ruff, path-filtered op `tools/graph-qa/**`. Geen
      `integration`-tests in deze story (die komen zodra er iets is dat een echte provider nodig
      heeft).

## Buiten scope van deze story

Letterlijk alles inhoudelijks: de LLM-/GraphDB-adapters zelf (`adapters/anthropic_llm.py`,
`adapters/graphdb_graph.py`, `mcp_client.py`), de toollaag, de orkestrator (supervisor +
antwoord-worker + annotatieketen), het run-model, de API-laag. Zie
`ai-notes/fase-4-aparte-services-plan.md` §Service 3 voor de volledige story-lijst (~25-35
stories geschat) en de reden waarom dat aantal zo hoog ligt.

## Test-plan

- `test_ports.py`: `FakeGraph`/`FakeLLM` voldoen aan de `GraphPort`/`LLMPort`-Protocols
  (`isinstance`-check via `@runtime_checkable`); `FakeLLM.create()`/`.stream()` spelen responses
  af in volgorde en onthouden de aanroepen.
- `test_config.py`: `Settings.from_env()` met/zonder env-vars, `_read_secret`-precedentie
  (`*_FILE` boven platte waarde), `require_graph()`/`require_llm()` gooien bij ontbrekende config.
