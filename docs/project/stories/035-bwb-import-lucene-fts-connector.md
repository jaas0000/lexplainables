# Story 035: bwb-import — Lucene-FTS-connector

**Prioriteit:** laag
**Story points:** 3
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 034 (circulaires — de FTS-connector indexeert o.a. `Divisie`/`Bijlage`,
die pas sinds 033/034 bestaan)

## Verhaal

De graaf is nu compleet qua structuur en tekst, maar zonder full-text-index moet elke
tekstzoekopdracht van `graph-qa` (nog te bouwen) een `FILTER(CONTAINS(...))`-scan over alle
`tekst`/`titel`/… literals doen — traag op een graaf van deze omvang. GraphDB's ingebouwde
Lucene-connector maakt dat een geïndexeerde full-text-zoekopdracht. Deze story waarborgt die
connector als onderdeel van de bestaande `prepare()`-stap (naast repo + ontologie), zelfherstellend
en idempotent.

**Prestatie/zoek-UX, niet correctheids-kritiek** — vandaar prioriteit laag, zoals al vastgelegd in
story 027 §Buiten scope.

Referentie: `wetsanalyse-ai/tools/bwb-import/app/graphdb_writer.py` (`ensure_fts_connector`,
`_fts_connector_config`, `_config_omvat`, `_fts_bestaande_config`, `_sparql_update` — allemaal
compleet en getest, `tests/test_graphdb_writer.py` §FTS-connector, incident-gedreven edge case
gedocumenteerd in de code zelf).

## Acceptatiecriteria

- [x] `graphdb_writer.py`: nieuwe module-constanten `_LUC`/`_LUC_INST` (Ontotext Lucene-connector-
      namespaces), `_FTS_CONNECTOR_NAAM = "bwb_tekst"`, `_FTS_TYPES` (alle citeerbare/tekstdragende
      entiteiten die dit project kent: Regeling, Hoofdstuk, Titeldeel, Afdeling, Paragraaf,
      Artikel, Lid, Onderdeel, Divisie, Bijlage — **niet** de subtypes Wet/AMvB/… of Illustratie/
      Organisatie/Ondertekenaar, die dragen geen doorzoekbare tekst), `_FTS_VELDEN` (`tekst`,
      `titel`, `citeertitel`, `opschrift`, `aanhef`, `considerans`, `voetnoot`,
      `definieertBegrip` — bestaan allemaal al in de ontologie sinds stories 030-034, geen
      nieuwe termen nodig).
- [x] `graphdb_writer.py`: nieuwe functie `_fts_connector_config(vocab) -> dict` (createConnector-
      JSON: `types`, `fields` (incl. `rdfs:label`), `languages: ["nl", ""]`,
      `analyzer: "org.apache.lucene.analysis.nl.DutchAnalyzer"`), `_config_omvat(gewenst,
      bestaand) -> bool` (recursieve subset-check — GraphDB vult de opgeslagen config aan met
      defaults, dus een letterlijke gelijkheidscheck zou altijd falen).
- [x] `GraphDbWriter.ensure_fts_connector(self) -> None`: zelfherstellend en idempotent —
      bestaat de connector niet → aanmaken; bestaat hij met een actuele config (subset-check) →
      niets doen; bestaat hij met een verouderde/onleesbare config → drop + opnieuw aanmaken
      (volledige herindexering, gelogd als waarschuwing). Een onleesbare config (sommige
      GraphDB-versies geven via `listConnectors` geen JSON terug maar alleen de connectornaam)
      wordt behandeld als "onbekend, dus opnieuw bouwen" — nooit als "waarschijnlijk actueel",
      want dat leidde in de referentie tot een incident (stille nul-treffers na een
      namespace-wijziging). Nieuwe helper `_fts_bestaande_config(self) -> dict | None` en
      `_sparql_update(self, update: str) -> None`.
- [x] `main.py`: `prepare()` roept ná `write_ontology()` ook `writer.ensure_fts_connector()` aan.

## Buiten scope van deze story

- Daadwerkelijk full-text zoeken vanuit `graph-qa` — dat is aan die service zodra hij gebouwd
  wordt; deze story waarborgt alleen de index zelf.
- Tekstuele fallback-verwijzingsdetectie — losse story (036), inhoudelijk ongerelateerd aan FTS.

## Schemabeslissing

Geen wijziging aan de RDF-ontologie (alle geïndexeerde velden bestaan al) en geen SQL-schema. De
FTS-connector-config zelf is GraphDB-interne staat (geen RDF), opgeslagen via een
`INSERT DATA`-SPARQL-update naar de Lucene-connector-namespace — geen nieuw opslagpatroon in dit
project, wel een nieuw protocol (GraphDB-specifieke connector-API i.p.v. reguliere RDF-writes).

## Edge cases

- Connector bestaat nog niet → aanmaken, één `createConnector`-update.
- Connector bestaat met exact de gewenste config (eventueel aangevuld met GraphDB-defaults) →
  geen update (idempotent, geen onnodige herindexering).
- Connector bestaat met een config die een subset mist (bv. minder velden dan gewenst) → drop +
  create (twee updates).
- `listConnectors` geeft een niet-JSON-waarde terug (bv. alleen de naam) → behandeld als
  onleesbaar → drop + create, nooit stilzwijgend aangenomen dat de config klopt.

**Bevestigd tegen de echte lokale GraphDB (11.4)**: deze installatie valt zelf in het
"onleesbare config"-geval — `listConnectors` geeft voor een bestaande connector alleen de naam
terug (`"bwb_tekst"`), geen JSON. `ensure_fts_connector()` herbouwt de connector daardoor bij
*elke* aanroep, niet alleen de eerste (elke `prepare()`-run reindexeert dus volledig — geen bug,
maar bewust gekozen gedrag, zie hierboven). Op de dataset van dit project (één wet, 133
artikelen) kost dat verwaarloosbaar; bij een veel grotere corpus is dit een reëel
aandachtspunt voor een latere story.

## Test-plan

- `test_graphdb_writer.py`: `_fts_connector_config` dekt de juiste types/velden/taal/analyzer;
  `ensure_fts_connector` — connector afwezig → aanmaken; actuele config (met GraphDB-defaults
  erbij) → geen update; verouderde config → drop+create; onleesbare config → drop+create. Alle
  vier met een stub-`requests.Session` (geen netwerk, zelfde patroon als de referentie).

## Implementatieplan

**Aangepaste bestanden:**
- `app/graphdb_writer.py` — `_LUC`/`_LUC_INST`/`_FTS_CONNECTOR_NAAM`/`_FTS_TYPES`/`_FTS_VELDEN`
  constanten; `_fts_connector_config`/`_config_omvat` functies; `ensure_fts_connector`/
  `_fts_bestaande_config`/`_sparql_update` methoden; `import json` toevoegen.
- `app/main.py` — `prepare()` roept `writer.ensure_fts_connector()` aan.

**Testcases:** config-inhoud, aanmaken/idempotent/hermaken-bij-verouderd/hermaken-bij-onleesbaar,
allemaal met een stub-Session (geen netwerk).

**Aandachtspunt:** `test_main.py`'s `FakeWriter` heeft een no-op `ensure_fts_connector` nodig.

**Verificatie:** `uv run pytest -q` + ruff + handmatig tegen lokale GraphDB (connector-aanmaak +
idempotentie bevestigen).
