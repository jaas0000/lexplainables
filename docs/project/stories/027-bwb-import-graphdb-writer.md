# Story 027: bwb-import — jci-ref_key + RDF-ontologie + GraphDB-writer

**Prioriteit:** hoog
**Story points:** 5
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 026 (onderdelen + verwijzingen), service 1 (`deploy/graphdb`)

## Verhaal

Het model kan nu een wet-besluit volledig parsen (structuur, artikelen, leden, onderdelen,
verwijzingen). Deze story maakt het bruikbaar: het model naar RDF-triples vertalen en als named
graph naar GraphDB schrijven, zodat `graph-qa` (service 3) er straks iets aan heeft.

Referentie: `wetsanalyse-ai/tools/bwb-import/app/rdf_vocab.py` + `ontology.py` + `collect.py` +
`graphdb_writer.py` (samen ~1717 regels). Deze story dekt het IRI-schema, de ontologie en de
writer **volledig qua mechanisme**, maar **scoped tot de entiteiten die dit project al parset**
(Regeling, Structuurdeel, Artikel, Lid, Onderdeel, Verwijzing) — WTI-verrijking, divisies,
bijlagen, illustraties, ondertekenaars en de Lucene-FTS-connector volgen pas zodra hun
parser-onderdeel bestaat.

**Waarom dit géén losstaand herontwerp is**: de IRI-/ref_key-conventies (URN-basis, disjuncte
ontologie-namespace, ref_key afgeleid van jci met een nummer/id-fallback) zijn niet arbitrair —
`graph-qa` (nog te bouwen) zal ditzelfde patroon verwachten (provenance-detectie prefixt op de
documentbasis). Afwijken hier zou dat later dwingen tot een incompatibele herbouw. Vandaar: op
dit punt wél op de referentie-architectuur leunen, niet er los van ontwerpen.

## Acceptatiecriteria

- [x] `references.py`: `jci_doel`/`jci_to_ref_key`/`jci_doel_ref_key` (pure functies, jci-string
      → (bwb_id, artikel, lid) resp. een stabiele ref_key-string).
- [x] `parser.py`: elk knooppunt met een JuriConnect-identiteit (structuurdeel, artikel, lid,
      onderdeel) draagt nu ook zijn ruwe `jci`-string (`_element_jci`, uit `meta-data/jcis/jci`).
- [x] `rdf_vocab.py` (`Vocab`): IRI-fabriek — `urn:bwb:` voor resources, disjuncte `urn:bwb-ns:`
      voor de ontologie, `by_ref_key`/`by_id`/`canonieke_url`/`verwijzing`, camelCase-predicaten.
- [x] `ontology.py` (`build_ontology`): T-Box met ELI-alignment, scoped tot Regeling (+ Wet/AMvB/
      KoninklijkBesluit/MinisterieleRegeling/Beleidsregel/Circulaire), Citeerbaar, Structuurdeel
      (+Hoofdstuk/Titeldeel/Afdeling/Paragraaf), Artikel, Lid, Onderdeel, Verwijzing.
- [x] `collect.py`: platte `Batch`-traversal van `Wet` → nodes/rels/verwijzingen, met
      ref_key-berekening (jci eerst, dan nummer/id-fallback — zelfde volgorde als de referentie).
- [x] `graphdb_writer.py` (`GraphDbWriter`): `ensure_constraints` (repo aanmaken indien nodig),
      `build_graph` (Batch → rdflib `Graph`, geen HTTP), `write_ontology` + `write_wet` (RDF4J
      Graph Store PUT — idempotente named-graph-vervanging).
- [x] Cross-referenties (`verwijstNaar`) wijzen naar de ref_key-afgeleide doel-IRI, ook als de
      doelwet nog niet geïmporteerd is (open-world; geen stub-nodes nodig) — getest door een
      `Verwijzing` naar een niet-geïmporteerde wet en te controleren dat de doel-IRI toch
      deterministisch en consistent is.
- [x] Unit-tests voor `build_graph` gebruiken géén live GraphDB (rdflib `Graph`-assertions,
      dezelfde DI-aanpak als `downloader.py`). Eén `integration`-marked test (standaard geskipt)
      schrijft daadwerkelijk naar de lokale `deploy/graphdb`-stack en leest terug.

## Buiten scope van deze story

- WTI-verrijking (citeertitels, thesaurustermen, grondslagen) — eigen story, wacht op
  `wti_parser.py`.
- Divisies (circulaires), bijlagen, illustraties, ondertekenaars — wachten op hun
  parser-onderdeel.
- Lucene-FTS-connector (`ensure_fts_connector`) — prestatie/zoek-UX, niet correctheids-kritiek;
  losse story.
- `main.py`-orkestratie (download → parse → collect → write in één CLI-commando),
  FastAPI-service-wrapper, Dockerfile.
- Tekstuele fallback-verwijzingsdetectie (`detect_textual_references` + `afkortingen.py`) — blijft
  buiten scope zoals al vastgelegd in story 026.

## Schemabeslissing

`Vocab`, `Batch` als `dataclass`; `build_ontology`/`GraphDbWriter` als in de referentie. Geen
eigen SQL-schema (zie stack-profiel.md §Migraties) — de RDF-ontologie in `ontology.py` **is** de
schemabeslissing van dit domein.

## Edge cases

- Structuurdeel/artikel zonder jci (bv. mijn eigen inline-test-XML zonder `meta-data`) → ref_key
  valt terug op `{bwb}#{soort}={nummer}` resp. `{bwb}#id={id}` — geen crash, geen lege ref_key.
- Verwijzing naar een niet-geïmporteerde wet → doel-IRI wordt toch gegenereerd (open-world);
  krijgt een leesbaar fallback-label (`_doel_label`) zodat 'ie niet als kaal IRI in de viewer
  verschijnt.
- Her-import van dezelfde wet (PUT) → de named graph wordt integraal vervangen, geen dubbele
  triples (getest via de `integration`-test: twee keer schrijven, triple-count blijft gelijk).

## Test-plan

- `test_references.py`: jci-parsing-functies op geldige/onvolledige/lege jci-strings.
- `test_collect.py`: `Wet` (uit de bestaande fixture) → `Batch`, ref_key per entiteitstype,
  fallback zonder jci.
- `test_graphdb_writer.py`: `build_graph` op een kleine, met de hand gebouwde `Wet` (geen
  netwerk) — juiste triples voor klasse/label/props/structuurrelaties/verwijzingen;
  `@pytest.mark.integration` voor de echte PUT + terug-SPARQL-query tegen `deploy/graphdb`.
