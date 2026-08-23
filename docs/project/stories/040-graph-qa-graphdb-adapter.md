# Story 040: graph-qa — GraphDB-adapter (MCP-client)

**Prioriteit:** hoog
**Story points:** 3
**Service:** `tools/graph-qa/`
**Afhankelijkheid:** story 029 (poorten/config-skelet), story 039 (patroon: poort van de
`wetsanalyse-ai`-referentie, live geverifieerd). `deploy/graphdb` moet lokaal draaien
(`lex-graphdb` + `lex-mcp-auth-proxy`, al aanwezig in dit project).

## Verhaal

Als tweede poort-implementatie van `tools/graph-qa` wil ik een werkende `GraphPort` tegen de
GraphDB MCP-server, zodat latere stories (toollaag, supervisor, annotatieketen) tegen de échte
kennisgraaf kunnen draaien i.p.v. alleen `FakeGraph`. Met deze én de LLM-adapter (story 039) zijn
beide poorten van story 029 ingevuld.

## Aanleiding

Story 029 markeerde de GraphDB-adapter expliciet buiten scope. `deploy/graphdb` draait al lokaal
(GraphDB ≥ 11.2's ingebouwde MCP-server op `/mcp`, met `lex-mcp-auth-proxy` als bearer-token-gate
ervoor — poort 8004, dev-default-token `lex-dev-mcp-token`, repository `inning`), dus deze
adapter kan direct tegen een levende server gebouwd én getest worden.

## Acceptatiecriteria

- [x] `agent/mcp_client.py`: `MCPClient` (voldoet aan `GraphPort`) — synchrone MCP Streamable
      HTTP-client (JSON-RPC over POST, met SSE-response-parsing), `sparql()`,
      `semantic_search()`, `close()`.
- [x] Read-only-vangnet: `sparql()` weigert een query die er als een SPARQL-update uitziet
      (INSERT/DELETE/LOAD/CLEAR/DROP/...), óók als het update-sleutelwoord niet aan het begin van
      de string staat (bv. na een `PREFIX`-declaratie op dezelfde regel). Allowlist-gebaseerd
      (moet met een leesvorm beginnen: SELECT/ASK/CONSTRUCT/DESCRIBE), niet blocklist — een
      blocklist die alleen het regelbegin checkt is te omzeilen.
      `semantic_search()` (natuurlijke taal, geen SPARQL) valt niet onder deze guard.
- [x] `agent/config.py`: nieuwe velden `graphdb_sparql_tool: str = "sparql_query"` en
      `similarity_index: str = ""` (env `GRAPHDB_SPARQL_TOOL`/`SIMILARITY_INDEX`).
- [x] `agent/adapters/graphdb_graph.py`: `make_graph(settings) -> GraphPort`-factory, roept
      `settings.require_graph()`.
- [x] Unit-tests (geen netwerk, gemockte `httpx`-responses/`_rpc`): de read-only-guard (poort van
      `wetsanalyse-ai/tools/graph-qa/tests/test_mcp_guard.py` — bewuste bypass-gevallen die een
      regelbegin-blocklist zou missen), `semantic_search`-argumentopbouw en een non-2xx-zonder-
      `result`-fout (poort van `test_mcp_client.py`).
- [x] Protocol-conformance: `isinstance(MCPClient(...), GraphPort)` (zelfde patroon als
      `test_ports.py`/story 039's `test_anthropic_llm_voldoet_aan_llmport`).
- [x] Eén `@pytest.mark.integration`-test tegen de lokaal draaiende GraphDB-MCP (standaard
      geskipt tenzij `GRAPHDB_MCP_URL`/`GRAPHDB_TOKEN` in de omgeving staan): een echte
      `sparql()`-aanroep (bv. `SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }`) geeft een niet-lege
      tekst terug.

## Buiten scope van deze story

De toollaag, de orkestrator, het run-model, de API-laag — zelfde lijst als story 029/039
§Buiten scope. `semantic_search` vereist een bestaande GraphDB-similarity-index; die bestaat nog
niet in dit project (`SIMILARITY_INDEX` blijft leeg) — de methode zelf wordt wel gebouwd en
getest (tegen een gemockte `call_tool`), een live similarity-index-aanmaak is een aparte,
latere stap (zie de referentie se `docs/embeddings-runbook.md`, nog niet overgezet).

## Ontwerp

Grotendeels 1:1 poort van `wetsanalyse-ai/tools/graph-qa/agent/mcp_client.py` +
`agent/adapters/graphdb_graph.py`. Kern van de read-only-guard: strip commentaar/string-
literals/IRI's, strip herhaald voorkomende `PREFIX`-/`BASE`-declaraties, en wat overblijft moet
met een leesvorm beginnen — anders geweigerd. Allowlist, niet blocklist (zie de
referentie-toelichting in `mcp_client.py` over waarom een regelbegin-blocklist te omzeilen was).

**Eén afwijking, gevonden tijdens live-verificatie (niet vooraf voorzien).** De referentie roept
`initialize()` nergens expliciet aan vóór een tool-call. Tegen de lokale GraphDB 11.4.0 gaf dat
een `502` (mcp-auth-proxy kon de GraphDB-container niet bereiken — een lokaal podman-netwerk-
probleem, opgelost met een proxy-restart) gevolgd door een `400 McpError` van GraphDB zelf zodra
de proxy wél doorkwam: deze GraphDB-versie weigert `tools/call` zonder eerst een MCP-sessie te
openen via `initialize` (`Mcp-Session-Id`-header). `_rpc()` doet dat nu **lazy**: vóór de eerste
niet-`initialize`-aanroep, één keer per client-instantie — `sparql()`/`semantic_search()` zelf
weten nergens van sessies. Bevestigd via `_rpc("tools/call", ...)` direct (zonder handmatige
`initialize()`-aanroep vooraf) tegen de echte lokale server: pas met deze fix slaagt de
integratietest.

## Testcases

- **Guard** (poort van `test_mcp_guard.py`): alle `UPDATES`/`BYPASS`/`BENIGN`-gevallen uit de
  referentie, inclusief de expliciete bypass-regressie (`PREFIX x: <http://a/> LOAD <...>` op één
  regel) en de valse-positieven-check (`"nr. #3 DROP GRAPH <http://g>"` als string-literal-inhoud
  mag niet als update herkend worden; een Lucene-connector-IRI die op `#` eindigt mag niet als
  commentaar worden gestript).
- **MCP-client** (poort van `test_mcp_client.py`): `semantic_search` bouwt de juiste
  `similarity_search`-argumenten; een non-2xx-response zonder `result`/`error` gooit `MCPError`
  i.p.v. stil een leeg resultaat; een gewone 200-met-`result` blijft werken.
- **Lazy-initialize** (nieuw, niet in de referentie): de eerste `call_tool()` op een verse
  `MCPClient` doet eerst een `initialize`-RPC en pas dan de eigenlijke `tools/call`; een tweede
  aanroep op dezelfde instantie doet dat niet nogmaals (sessie staat al).
- **Protocol**: `isinstance(MCPClient(...), GraphPort)`, plus `make_graph()`-tests
  (`require_graph()`-foutpad, en dat de teruggegeven client `GraphPort`-conform is).
- **Integration** (geskipt zonder env): een echte `sparql()`-call tegen `localhost:8004/mcp`
  (`lex-dev-mcp-token`, repository `inning`) geeft een SPARQL-resultaat terug.

## Verificatie

- `cd tools/graph-qa && uv run --extra dev pytest -q` — 69 passed, 2 skipped (integration).
- Handmatig met de lokale GraphDB-stack draaiend: `GRAPHDB_MCP_URL=http://localhost:8004/mcp
  GRAPHDB_TOKEN=lex-dev-mcp-token uv run --extra dev pytest -q -m integration` — 1 passed
  (echte `sparql()`-call, `SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }` → `1343` triples in de
  lokale `inning`-repository).
- `uv run ruff check .` + `ruff format --check .` schoon.

**Gebouwd:** ja (PR volgt). `agent/mcp_client.py` (nieuw), `agent/adapters/graphdb_graph.py`
(nieuw), `agent/config.py` (+ `graphdb_sparql_tool`/`similarity_index`), `httpx` toegevoegd aan
`pyproject.toml`. Nieuwe tests: `test_mcp_client.py`, `test_mcp_guard.py` (poorten van de
referentie, 1:1), `test_graphdb_graph.py`, `test_mcp_client_integration.py`. Tijdens
live-verificatie een echte GraphDB-11.4.0-gedragsafwijking gevonden en gefixt (lazy
`initialize`-handshake, zie §Ontwerp) — precies waarom deze story een integratietest eiste in
plaats van alleen unit-tests tegen fakes.
