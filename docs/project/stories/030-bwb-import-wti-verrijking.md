# Story 030: bwb-import — WTI-verrijking

**Prioriteit:** medium
**Story points:** 5
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 027 (RDF-ontologie + GraphDB-writer), service 1 (`deploy/graphdb`)

## Verhaal

De toestand-XML (huidige pijplijn) levert de wettekst zelf, maar niet de wetstechnische
verrijking: officiële citeertitel(s)/afkortingen, rechtsgebieden/overheidsdomeinen
(thesaurustermen), grondslag-relaties naar andere regelingen en de verantwoordelijke organisatie.
Die informatie staat in een los WTI-document (`wetstechnische-informatie`), waarvan de SRU-
discovery al een locatie meelevert (`locatie_wti`, nog ongebruikt). Deze story haalt dat document
op, parset het en verrijkt de wet-node ermee, zodat `graph-qa` straks op citeertitel/rechtsgebied
kan filteren en grondslag-relaties kan volgen.

Referentie: `wetsanalyse-ai/tools/bwb-import/app/wti_parser.py` (compleet, getest,
`tests/test_wti.py` + `tests/fixtures/sample_wti.xml`) en de WTI-secties in `downloader.py`,
`config.py`, `main.py`, `graphdb_writer.py`, `ontology.py`, `rdf_vocab.py` (`Vocab.entiteit`).
Dit project heeft een eenvoudiger `collect.py`/`graphdb_writer.py` dan de referentie (geen
`iri_soort`/`iri_sleutel`-schema op nodes — dat dient daar andere, nog niet gebouwde entiteiten
zoals ondertekenaars); deze story neemt daarom alleen de WTI-relevante delen over: `label_id` als
join-sleutel op `Wet`/`Structuurdeel`/`Artikel`, en `Vocab.entiteit()` losstaand voor de
organisatie-node.

## Acceptatiecriteria

- [x] `models.py`: `ToestandRef.locatie_wti: str | None` (SRU levert 'm al, alleen nog niet
      gelezen). `Wet`, `Structuurdeel`, `Artikel` krijgen elk `label_id: str | None` (WTI-
      join-sleutel; `Lid`/`Onderdeel` niet — de referentie kent daar geen WTI-relaties aan toe).
- [x] `parser.py`: `label_id=element.get("label-id")` op dezelfde drie plekken waar nu al
      `jci=self._element_jci(element)` gebeurt (`wetgeving`, structuurdeel, artikel).
- [x] `downloader.py`: `download_wti(ref: ToestandRef) -> Path | None` — `None` zonder
      netwerkcall als `ref.locatie_wti` leeg is; anders cache + download zoals
      `download_toestand`.
- [x] Nieuw `wti_parser.py`: `WtiElementRel` (`grondslag_voor`/`bevoegdheid_voor`/
      `verwijzing_door`, elk `list[str]` van BWB-id's), `WtiInfo` (`citeertitels`,
      `afkortingen`, `niet_officiele_titels`, `eerstverantwoordelijke`, `rechtsgebieden`
      (`list[tuple[hoofdgebied, specifiekgebied | None]]`), `overheidsdomeinen`, `grondslagen`
      (BWB-id's), `authority`, `wetsfamilie` (BWB-id's, ontdubbeld, zonder zichzelf),
      `element_relaties: dict[label_id, WtiElementRel]`), `WtiParser.parse(xml_path) -> WtiInfo`
      — 1:1 de parse-logica van de referentie (defensief: elk veld optioneel, geen enkel
      ontbrekend element is een fout).
- [x] `config.py`: `Settings.import_wti: bool` uit `BWB_IMPORT_WTI` (default `false` — zelfde
      patroon als `validate_xsd`).
- [x] `main.py`: als `settings.import_wti`, download + parse de WTI **best-effort** (nooit
      blokkerend — een mislukte WTI-download/parse logt een warning en de import gaat door
      zonder verrijking, want de kernwettekst is altijd waardevoller dan de verrijking).
- [x] `rdf_vocab.py` (`Vocab`): `entiteit(soort: str, sleutel: str) -> URIRef` — deterministische,
      wet-overstijgende slug-IRI (bv. dezelfde organisatie valt over wetten heen samen tot één
      node), 1:1 uit de referentie. `begrip(label: str) -> URIRef` — slug-IRI voor een
      thesaurusterm (rechtsgebied/overheidsdomein), 1:1 uit de referentie.
- [x] `ontology.py`: nieuwe klasse `Organisatie` (superklasse `FOAF.Agent`); nieuwe
      object-properties `heeftGrondslag` (Regeling→Regeling, `ELI.based_on`), `uitgegevenDoor`
      (Regeling→Organisatie, `ELI.responsibility_of`), `inFamilie` (Regeling→Regeling,
      wetsfamilie), en op `Citeerbaar`-niveau `grondslagVoor`/`bevoegdheidVoor`/`verwijzingDoor`
      (tekstdeel → Regeling); nieuwe data-properties `afkorting`, `alternatieveTitel`
      (`ELI.title_alternative`), `eerstverantwoordelijke`, `naam` (generiek, ook voor
      Organisatie). Rechtsgebieden/overheidsdomeinen worden `skos:Concept`s (via `_begrip()` in
      de writer — SKOS is een extern vocabulaire, geen ontology-toevoeging nodig). `citeertitel`
      bestaat al (hergebruikt: WTI voegt er extra waarden aan toe).
- [x] `graphdb_writer.py`: `build_graph(wet, wti: WtiInfo | None = None)` en
      `write_wet(wet, wti: WtiInfo | None = None)` — WTI-triples in dezelfde named graph als de
      wet zelf (atomair mee-vervangen bij her-import). `_wti_verrijking` zet de wet-node-triples
      (titels, thesaurustermen, grondslagen, organisatie); `_wti_element_relaties` koppelt via de
      `label_id → IRI`-map (opgebouwd tijdens de node-loop) de per-tekstdeel-relaties
      (`grondslagVoor`/`bevoegdheidVoor`/`verwijzingDoor`) — een `label_id` uit de WTI zonder
      match in de geïmporteerde wet wordt overgeslagen (geen crash, geen stub-node).

## Buiten scope van deze story

- Divisies (circulaires), bijlagen, illustraties, ondertekenaars — wachten op hun
  parser-onderdeel (ongewijzigd vervolgpunt uit story 027).
- `locatie_manifest`/manifest-download — geen WTI-gebruik hiervan; aparte story indien nodig.
- WTI voor `Lid`/`Onderdeel` — de referentie kent op dat niveau geen `label-id`-relaties toe;
  als dat later blijkt te bestaan, is dat een aanvulling op deze story, geen breuk.
- Een admin/UI-weergave van de nieuwe velden (citeertitel etc.) — dat is aan `graph-qa`/`api`
  zodra die de graaf bevragen.

## Schemabeslissing

`WtiInfo`/`WtiElementRel` als `dataclass` (zelfde stijl als `models.py`), 1:1 uit de referentie.
Geen SQL-schema (ongewijzigd t.o.v. story 027 — de RDF-ontologie in `ontology.py` blijft de
schemabeslissing van dit domein).

## Edge cases

- `ref.locatie_wti` ontbreekt (SRU levert 'm niet voor elke regeling) → `download_wti` geeft
  `None`, import gaat door zonder verrijking, geen warning-spam (dit is een normale toestand,
  geen fout).
- WTI-document aanwezig maar (deels) leeg/onvolledig (bv. geen `rechtsgebieden`) → elk veld op
  `WtiInfo` heeft een leeg-default, geen crash.
- `element_relaties` bevat een `label_id` die niet voorkomt in de geïmporteerde wet (WTI en
  toestand-XML kunnen qua toestand-datum licht uiteenlopen) → relatie wordt overgeslagen, niet
  gegokt.
- Her-import van dezelfde wet met WTI aan → WTI-triples zitten in dezelfde named graph als de
  wet, dus de PUT vervangt ze atomair mee (geen dubbele/verouderde WTI-triples na een tweede
  import).
- `BWB_IMPORT_WTI` niet gezet → gedrag identiek aan vóór deze story (geen download, geen
  verrijking) — bestaande tests/imports blijven ongewijzigd werken.

## Test-plan

- `test_wti.py`: geport van de referentie (`WtiParser.parse` tegen `sample_wti.xml`-fixture,
  1:1 overgenomen) — elk veld correct gevuld, ontdubbeling van `wetsfamilie`/`grondslagen`,
  `element_relaties` opgeschoond tot alleen entries met minstens één relatie.
- `test_downloader.py`: `download_wti` — met/zonder `locatie_wti`, caching-gedrag identiek aan
  `download_toestand`.
- `test_config.py`: `import_wti`-default (`false`) + override via `BWB_IMPORT_WTI`.
- `test_graphdb_writer.py`: `build_graph(wet, wti=...)` op een kleine, met de hand gebouwde
  `Wet` + `WtiInfo` (geen netwerk) — juiste triples voor titels/thesaurustermen/grondslagen/
  organisatie-node/element-relaties; label_id-mismatch wordt stilzwijgend overgeslagen.
- `test_main.py`: `import_wti=True` met een WTI-download die faalt → import van de wet zelf
  slaagt alsnog (best-effort, warning gelogd).

## Implementatieplan

**Nieuwe bestanden:**
- `app/wti_parser.py` — 1:1 poort van de referentie: `WtiElementRel`, `WtiInfo`, `WtiParser.parse`.
- `tests/test_wti.py` — 4 tests: parser-velden, authority/wetsfamilie/element-relaties,
  WTI-verrijking-in-graaf, zonder-WTI-geen-verrijking.
- `tests/fixtures/sample_wti.xml` — 1:1 kopie van de referentie-fixture.

**Aangepaste bestanden:**
- `app/models.py` — `ToestandRef.locatie_wti`; `label_id` op `Wet`/`Structuurdeel`/`Artikel`.
- `app/parser.py` — `label_id=element.get("label-id")` op de drie jci-plekken.
- `app/downloader.py` — `_parse_record` leest `locatie_wti`; nieuwe `download_wti()`.
- `app/config.py` — `Settings.import_wti` uit `BWB_IMPORT_WTI` (default false).
- `app/collect.py` — `label_id` mee in de node-props van Regeling/Structuurdeel/Artikel.
- `app/rdf_vocab.py` — `Vocab.begrip()` + `Vocab.entiteit()`.
- `app/ontology.py` — klasse `Organisatie`; object-properties `heeftGrondslag`/`uitgegevenDoor`/
  `inFamilie`/`grondslagVoor`/`bevoegdheidVoor`/`verwijzingDoor`; data-properties `afkorting`/
  `alternatieveTitel`/`eerstverantwoordelijke`/`naam`.
- `app/graphdb_writer.py` — module-level `DCTERMS`/`SKOS`; `build_graph`/`write_wet` krijgen
  `wti: WtiInfo | None = None`; nieuwe `_wti_verrijking`/`_wti_element_relaties`/`_begrip`.
- `app/main.py` — `run_import` bepaalt eerst `latest_toestand`, dan `_laad_wti` (best-effort) als
  `settings.import_wti`.

**Testcases:**
- WTI-parser: alle velden uit `sample_wti.xml`, authority/wetsfamilie-ontdubbeling,
  element_relaties per label-id.
- Writer: volledige WTI-triple-set in de graaf; geen WTI-triples zonder `wti`-param.
- Downloader: met/zonder `locatie_wti` (geen netwerkcall in het zonder-geval).
- Config: `import_wti`-default + override.
- Main: WTI-downloadfout breekt de wet-import niet (best-effort).

**Afhankelijkheden en aandachtspunten:**
- `run_import` gaat expliciet `latest_toestand` ophalen vóór `download_toestand` (nodig voor
  `locatie_wti`); bestaande fake-downloader-tests op aanroepvolgorde/-aantal checken en zo nodig
  bijwerken.
- Nieuwe `FOAF`-namespace-import in `ontology.py`, alleen voor `Organisatie`.
- Predicaatnamen in dit plan zijn geverifieerd tegen de referentie-implementatie (zie
  `wetsanalyse-ai/tools/bwb-import/app/{ontology,graphdb_writer,rdf_vocab}.py`), niet vrij
  gekozen.

**Verificatie:**
- `cd tools/bwb-import && uv run pytest -q` + `uv run ruff check . && uv run ruff format --check .`
- Handmatig: `BWB_IMPORT_WTI=true uv run python -m app.main BWBR0004770` tegen de lokale
  GraphDB, SPARQL-check op de nieuwe WTI-triples.
