# Story 041: graph-qa — toollaag (SPARQL-bouwers + tool-registry)

**Prioriteit:** hoog
**Story points:** 5
**Service:** `tools/graph-qa/`
**Afhankelijkheid:** story 040 (`GraphPort`/`MCPClient`, `deploy/graphdb` lokaal draaiend, gevuld
via `tools/bwb-import` — Invorderingswet-fixture BWBR0004770 al aanwezig).

## Verhaal

Als volgende stap na de twee poorten (story 039/040) wil ik een getypeerde domein-toollaag over
de kennisgraaf, zodat het LLM straks kiest uit een vaste set deterministische bewerkingen
(zoeken, artikel/lid ophalen, verwijzingen volgen, ...) in plaats van vrije SPARQL te schrijven.
De correctheid zit in geteste code, niet in prompt-proza.

## Aanleiding

Story 029 markeerde de toollaag expliciet buiten scope. Met beide poorten nu ingevuld (story
039/040) en een gevulde lokale kennisgraaf (`tools/bwb-import`, Invorderingswet-fixture) kan de
toollaag gebouwd én tegen echte data geverifieerd worden.

## Acceptatiecriteria

- [x] `agent/namespace.py`: `BASIS`/`ONTOLOGIE`-IRI-ruimte (env `GRAPHDB_BASE_IRI`/
      `GRAPHDB_ONTOLOGY_IRI`, defaults `urn:bwb:`/`urn:bwb-ns:` — moeten gelijk zijn aan
      `tools/bwb-import/app/rdf_vocab.py`'s `DEFAULT_BASE_IRI`/`DEFAULT_ONTOLOGY_IRI`, anders
      matchen de `STRSTARTS`-filters stilzwijgend niets). Eén bron voor wat drie eerdere plekken
      in de referentie los overtypten.
- [x] Drift-guard-test: vergelijkt de default-IRI's in `agent/namespace.py` letterlijk met die in
      `tools/bwb-import/app/rdf_vocab.py` (bestand-als-tekst, geen import over de servicegrens —
      ADR-0002). Faalgedrag zonder deze guard is stil: geen foutmelding, een leeg antwoord.
- [x] `agent/graph/queries.py`: geparametriseerde SPARQL-bouwers — `fts` (Lucene-full-text),
      `list_regelingen`, `get_artikel` (incl. leden én directe onderdelen), `get_lid` (incl.
      onderdelen, `GROUP_CONCAT`), `get_bepaling` (decimale/beleidsregel-nummers), `get_regeling_info`,
      `follow_verwijzingen`, `referenced_by`, `resolve_begrip` (SKOS), `count_by_type`, `context`
      (GraphRAG-subgraaf in één UNION-query). Invoervalidatie (BWB-id/artikelnummer/bepaling-
      nummer-regex) + SPARQL-string-escaping — geen injectie via een tool-argument mogelijk.
- [x] `agent/graph/schema.py`: `graph_schema(graph)` — live schema-introspectie (aantallen per
      type + regelingenlijst), in-proces gecached (`reset_cache()` voor tests).
- [x] `agent/tools/__init__.py`: `TOOLS`-registry (13 tool-declaraties, model-facing
      naam/beschrijving/JSON-schema), `anthropic_schemas(only=...)`, `dispatch(name, graph, args,
      settings=None)` — vangt `ValueError`/`MCPError`/`KeyError` (ongeldig argument/MCP-fout) en
      `httpx.HTTPError` (transportfout naar de graaf) af als tekstueel tool-resultaat, breekt nooit
      de agent-beurt. `semantic_search` degradeert netjes naar een uitleg-tekst als er geen
      similarity-index geconfigureerd is (`Settings.similarity_index`).
- [x] Unit-tests (poort van `test_namespace_drift.py`/`test_queries.py`/`test_schema.py`/
      `test_tools.py`, 1:1 waar mogelijk): query-vorm-assertions, invoervalidatie-afwijzingen,
      schema-cache-gedrag, registry-volledigheid, dispatch-foutafhandeling (validatie- én
      transportfout), `semantic_search`-limit-clamping.
- [x] Eén handmatige live-verificatie (geen nieuwe `@pytest.mark.integration`-test — de bestaande
      story-040-integratietest dekt de MCP-laag al; dit is een sanity-check dat de query's tegen
      échte data kloppen): `get_artikel`/`get_lid` tegen de lokale Invorderingswet-fixture
      (BWBR0004770) via `MCPClient`, handmatig via een script, geen automatische test (zou de
      fixture-inhoud hardcoderen in de suite — bewust vermeden, zelfde reden als story 037's
      keuze om alleen unit- en integratietests te scheiden).

## Buiten scope van deze story

De orkestrator, de supervisor, de annotatieketen, de API-laag, `agent/graph/results.py` (SPARQL-
TSV-parser — alleen gebruikt door de referentie's `artikel.py`/`orchestrator.py`, geen consument
in deze story, dus nog niet porten — voorkomt dode code). Zie story 029/039/040 §Buiten scope
voor de volledige resterende lijst.

## Ontwerp

Grotendeels 1:1 poort van `wetsanalyse-ai/tools/graph-qa/agent/{namespace.py,graph/queries.py,
graph/schema.py,tools/__init__.py}` — geen afwijking verwácht (in tegenstelling tot story 039),
maar wél gevonden: de referentie se query's zijn geschreven tegen háár eigen importer-schema, en
dat schema wijkt op twee punten af van wat dit project se `tools/bwb-import` daadwerkelijk
schrijft. Beide gevonden via live-verificatie tegen de lokale Invorderingswet-fixture (art. 2,
niet art. 9 — dat artikel zit niet in deze fixture, alleen 2 `Artikel`-nodes zijn geïmporteerd).

1. **Geen `bwb:jci`-predicaat.** Dit project se importer schrijft de wetten.overheid.nl-
   vindplaats als `owl:sameAs` (een IRI), niet als een los `bwb:jci`-stringliteral. Elke
   `?jci`-binding in `queries.py` leest daarom `owl:sameAs` i.p.v. `bwb:jci`.
2. **Geen generiek `bwb:bevat`-predicaat.** `get_lid`'s geneste-onderdelen-subquery gebruikt nu
   `bwb:heeftOnderdeel+` (property-path, matcht `api/app/features/annotatie/graphdb.py`, die dit
   al eerder tegen dezelfde data verifieerde); `context()`'s "wat bevat deze node"-tak gebruikt nu
   `eli:has_part` (omgekeerd) — dit project se importer schrijft per structuurniveau een eigen
   predicaat (`heeftArtikel`/`heeftLid`/`heeftOnderdeel`) plus, generiek over alle niveaus heen,
   de ELI-ontologie se `has_part`. Dat laatste is precies waar de reverse "bevat-door"-lookup
   `bwb:bevat` voor nodig had — `eli:has_part` is het generieke equivalent in dit project se data.
3. **`STR()` ontbrak om een IRI in `CONCAT()` te gebruiken** — een subtielere derde bug, ontstaan
   dóór fix 1: `get_lid`'s onderdelen-`GROUP_CONCAT` bouwt per onderdeel een regel met
   `CONCAT(..., ?ojk, ...)`, waarbij `?ojk` was afgeleid van `?oj` (nu een `owl:sameAs`-IRI, was
   voorheen een `bwb:jci`-literal in de referentie). `CONCAT()` eist stringliteralen; een IRI
   erin geven laat de `BIND` **stil falen** voor élke rij (geen foutmelding — SPARQL-type-errors
   in een `BIND` maken de binding alleen onbound), waardoor de hele `GROUP_CONCAT` leeg bleef.
   Gevonden door de query stap voor stap te isoleren tegen de live server tot het exacte punt
   boven water kwam; opgelost met `STR(?oj)` op elke plek waar de IRI als tekst gebruikt wordt.

Zonder de story se eigen eis van een echte live-verificatie (i.p.v. alleen unit-tests tegen
fakes) waren alle drie onopgemerkt gebleven: elke fout geeft geen crash, alleen een stilzwijgend
leeg of onvolledig resultaat — precies het faalpatroon dat `agent/namespace.py`'s eigen docstring
al waarschuwt te verwachten bij een schema-mismatch.

## Testcases

- **Namespace-drift**: `agent/namespace.py`'s default-IRI's == `tools/bwb-import/app/
  rdf_vocab.py`'s defaults (bestandsvergelijking, geen import).
- **Queries** (poort van `test_queries.py`): FTS-Lucene-vorm + limit-clamping, eigen-IRI-ruimte-
  filter op `list_regelingen`, artikel-/lid-IRI-opbouw, `get_lid`'s onderdelen-`GROUP_CONCAT` +
  volgorde + jci-zonder-datumstaart, `get_artikel`'s directe-onderdelen-tak, verwijzingen met/
  zonder lid, `context`'s volledige UNION-dekking, `resolve_begrip`'s escaping, en de
  invoervalidatie-afwijzingen (ongeldig BWB-id/artikelnummer → `ValueError`).
- **Schema** (poort van `test_schema.py`): bevat tellingen + regelingenlijst, wordt gecached
  (tweede aanroep raakt de graaf niet nogmaals).
- **Tools** (poort van `test_tools.py`): registry compleet/welgevormd, filter-optie, dispatch voor
  een onbekende tool, een geslaagde query, een validatiefout (query nooit uitgevoerd), een
  transportfout (`httpx.ConnectError` → nette foutmelding, geen crash), `raw_sparql` stuurt de
  query onveranderd door, `get_context` raakt alle relatiesoorten, `semantic_search` zonder/met
  index + limit-clamping (1–50, niet-int → default 10).

## Verificatie

- `cd tools/graph-qa && uv run --extra dev pytest -q` — 105 passed, 2 skipped (integration).
- Handmatig tegen de lokale, gevulde GraphDB: `get_artikel`/`get_lid`/`context`/
  `follow_verwijzingen`/`graph_schema` op de Invorderingswet-fixture (BWBR0004770, art. 2 — art.
  9 zit niet in deze fixture) via zowel `MCPClient` rechtstreeks als via `tools.dispatch()` (de
  echte aanroep-route) — echte tekst/leden/25 onderdelen/verwijzingen/tellingen terug.
- `uv run ruff check .` + `ruff format --check .` schoon.

**Gebouwd:** ja (PR volgt). `agent/namespace.py`, `agent/graph/{__init__.py,queries.py,
schema.py}`, `agent/tools/__init__.py` (nieuw). Drie schemacorrecties t.o.v. de referentie
gevonden tijdens live-verificatie, zie §Ontwerp: `owl:sameAs` i.p.v. `bwb:jci`,
`bwb:heeftOnderdeel+`/`eli:has_part` i.p.v. `bwb:bevat`, en een `STR()`-fix voor een SPARQL-
`CONCAT()`-typefout die de eerste correctie zelf introduceerde. Nieuwe tests:
`test_namespace_drift.py`, `test_queries.py`, `test_schema.py`, `test_tools.py` (poorten van de
referentie, aangepast aan de gecorrigeerde queries).
