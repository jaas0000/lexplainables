# Story 031: bwb-import — artikel/lid/onderdeel-verrijking

**Prioriteit:** medium
**Story points:** 4
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 027 (RDF-ontologie + GraphDB-writer)

## Verhaal

De parser leest nu alleen de kale tekst en structuur van artikel/lid/onderdeel. De bron-XML draagt
meer: provenance-attributen (wanneer en waardoor een tekstdeel zijn huidige inhoud kreeg),
voetnoten, cursief-gedefinieerde begrippen, illustraties (`<plaatje>/<illustratie>`) en tabellen
(CALS `<table>`, nu stilzwijgend uitgesloten van de lopende tekst). Deze story voegt dat toe zodat
de graaf niet alleen wéét wat een artikel zegt, maar ook wanneer het zo kwam te luiden en met welk
beeldmateriaal het samenhangt.

Referentie: `wetsanalyse-ai/tools/bwb-import/app/parser.py` (provenance-attributen, `_noten`,
`_definities`, `_illustraties`, `_tabel_tekst`/`_tekst_zonder_noot`), `models.py` (`Illustratie`),
`collect.py` (illustratie-relatie), `ontology.py` (reeds volledig: `Illustratie`-klasse,
`bevatIllustratie`, `inwerking`/`terugwerkendTot`/`bron`/`effect`/`status`/`wijzigingsbronnen`/
`voetnoot`/`definieertBegrip`/`naam`/`formaat`/`breedte`/`hoogte`/`alt` — deze story voegt alleen
de termen toe die de writer na deze story daadwerkelijk gebruikt, niet de hele referentie-lijst
(zie Schemabeslissing).

## Acceptatiecriteria

- [x] `models.py`: `Illustratie` (`id`, `naam`, `formaat`, `breedte`, `hoogte`, `alt`, allen
      `str | None` behalve `id`). `Artikel` krijgt `inwerking`/`bron`/`effect`/`status`/
      `terugwerkend_tot: str | None` + `wijzigingsbronnen: list[str]` + `voetnoten: list[str]` +
      `illustraties: list[Illustratie]`. `Lid` krijgt `terugwerkend_tot: str | None` +
      `voetnoten: list[str]` + `definieert_begrippen: list[str]` + `illustraties: list[Illustratie]`.
      `Onderdeel` krijgt `voetnoten: list[str]` + `definieert_begrippen: list[str]` +
      `illustraties: list[Illustratie]`. `ImportSummary` krijgt `illustraties: int = 0`.
- [x] `parser.py`: op `_parse_artikel` en `_parse_lid` de provenance-attributen lezen
      (`element.get("inwerking"/"bron"/"effect"/"status")`), plus nieuwe helpers `_terugwerkend`
      (`./meta-data/brondata/inwerkingtreding/terugwerkend.datum/@isodatum`),
      `_wijzigingsbronnen` (`./meta-data//juncto/publicatie`, formaat `{soort}.{jaar}-{nr}`),
      `_noten`/`_noot_tekst` (`<noot>`-tekst binnen tekstbereik, meta-data uitgesloten),
      `_definities` (`./al/nadruk[@type='cur']/text()` eindigend op `:`, rstrip `:`),
      `_illustraties` (`<illustratie>`-attributen binnen tekstbereik). Alle vier toegepast op
      artikel/lid/onderdeel met dezelfde scope-uitsluitingen als de bestaande tekst-/
      verwijzingen-extractie (nooit binnen een geneste `lid`/`li`).
- [x] `parser.py`: `_lichaamstekst` sluit `<table>`-inhoud niet langer stilzwijgend uit — nieuwe
      `_tabel_tekst(table)` rendert elke rij als `cel | cel | …` (CALS `<row>`/`<entry>`) en wordt
      als extra regel(s) ná de lopende tekst toegevoegd (`\n`-gescheiden), zodat niets verdwijnt
      en de tekst full-text-doorzoekbaar blijft. Lege tabellen (geen niet-lege rijen) leveren
      niets op.
- [x] `collect.py`: provenance-velden + `voetnoot`/`definieert_begrip` als node-props op
      Artikel/Lid/Onderdeel (lijst-props waar van toepassing — de generieke schrijflus in
      `graphdb_writer.py` handelt lijst-waarden al af). Nieuwe `_illustraties(ouder_ent, ouder_id,
      illustraties)`-helper: eigen `Illustratie`-node per illustratie + `BEVAT_ILLUSTRATIE`-relatie
      vanaf de ouder (artikel/lid/onderdeel); `ImportSummary.illustraties` wordt opgehoogd.
- [x] `ontology.py`: klasse `Illustratie` (geen superklasse); object-property `bevatIllustratie`
      (Citeerbaar-generiek → Illustratie, geen ELI-alignment); data-properties `inwerking`
      (`XSD.date`), `terugwerkendTot` (`XSD.date`), `bron`, `effect`, `status`,
      `wijzigingsbronnen`, `voetnoot`, `definieertBegrip`, `naam` (hergebruikt, WTI's
      Organisatie-naam en nu ook illustratie-bestandsnaam delen dezelfde term — beide zijn "naam
      van iets", geen betekenisconflict), `formaat`, `breedte`, `hoogte`, `alt`.
- [x] `graphdb_writer.py`: geen wijziging aan de publieke signatuur nodig — de nieuwe node-props
      en de illustratie-relatie lopen mee via de al bestaande generieke node-/rel-schrijflus in
      `build_graph`. Wél: `predicaat_rel("BEVAT_ILLUSTRATIE")` moet naar `bevatIllustratie`
      camelCasen (bestaand `_camel`-mechanisme in `rdf_vocab.py`, geen wijziging nodig — alleen
      verifiëren via een test).

## Buiten scope van deze story

- Divisies (circulaires), bijlagen, ondertekenaars — eigen stories (032/033/034), wachten op hun
  parser-onderdeel.
- Lucene-FTS-connector — losse story, ongewijzigd vervolgpunt uit story 027.
- Tekstuele fallback-verwijzingsdetectie (`afkortingen.py`) — ongewijzigd vervolgpunt uit story
  026/027.
- Wet-brondata/aanhef/considerans (`_wet_brondata`/`_wet_aanhef` in de referentie) — regeling-
  niveau metadata, hoort natuurlijker bij story 032 (samen met ondertekenaars, beide
  regeling-niveau verrijking) dan bij deze artikel/lid/onderdeel-story.

## Schemabeslissing

`Illustratie` als `dataclass` (zelfde stijl als `Onderdeel`/`Lid`). Ontologie neemt alleen de
termen op die deze story's writer daadwerkelijk emit — niet de volledige referentie-`_DATA_PROPS`/
`_KLASSEN`-lijst (die bevat ook termen voor divisies/bijlagen/ondertekenaars/WTI-rechtsgebieden die
pas in latere stories relevant worden). Geen SQL-schema (ongewijzigd — RDF-ontologie in
`ontology.py` blijft de schemabeslissing van dit domein).

## Edge cases

- Artikel/lid zonder provenance-attributen (bv. mijn handgeschreven test-XML) → alle nieuwe velden
  blijven `None`/lege lijst, geen crash, geen lege props in de graaf (bestaande
  `skip_prop`/`value is None or value == ""`-filtering in `graphdb_writer.py` dekt dit al).
- Tabel zonder niet-lege rijen (bv. alleen opmaak-cellen) → `_tabel_tekst` geeft `""`, wordt niet
  aan de lopende tekst toegevoegd (geen loze `\n` aan het eind).
- Nadruk-element dat niet op `:` eindigt (gewone cursivering, geen definitie) → niet opgenomen in
  `definieert_begrippen` — voorkomt vals-positieve "definieert een begrip"-relaties.
- Illustratie zonder `id`- én zonder `naam`-attribuut → lege `id`-string (matcht referentiegedrag;
  geen crash, wel een makkelijk te herkennen edge case in de tests).
- Voetnoot binnen een genest lid/onderdeel → hoort bij dát lid/onderdeel, niet bij het artikel
  erboven (zelfde scope-exclusiepatroon als de bestaande lichaamstekst-extractie).

## Test-plan

- `test_parser.py`: provenance-attributen op artikel/lid, `_terugwerkend`/`_wijzigingsbronnen`
  tegen de bestaande fixture (artikel 2 heeft al `bron="Stb.2016-163" effect="wijziging"` in
  `sample_toestand.xml`), voetnoten/definities/illustraties op elk niveau, tabelweergave
  (nieuwe fixture-XML-fragment met een kleine CALS-tabel).
- `test_collect.py`: illustratie-node + `BEVAT_ILLUSTRATIE`-relatie, provenance-props op de
  Artikel/Lid-node-rijen, `ImportSummary.illustraties`-telling.
- `test_graphdb_writer.py`: `predicaat_rel("BEVAT_ILLUSTRATIE")` → `bwb:bevatIllustratie`;
  volledige triple-check voor een artikel met illustratie + provenance-velden.

## Implementatieplan

**Aangepaste bestanden:**
- `app/models.py` — nieuwe `Illustratie`-dataclass; provenance/voetnoten/definities/illustraties
  op `Artikel`/`Lid`/`Onderdeel`; `ImportSummary.illustraties`.
- `app/parser.py` — provenance-attributen op artikel/lid; nieuwe `_terugwerkend`,
  `_wijzigingsbronnen`, `_noten`/`_noot_tekst`, `_definities`, `_illustraties`; `_lichaamstekst`
  neemt tabellen mee via nieuwe `_tabel_tekst`.
- `app/collect.py` — provenance/voetnoot/definieert_begrip als node-props; nieuwe
  `_illustraties()`-helper (eigen node + `BEVAT_ILLUSTRATIE`-relatie).
- `app/ontology.py` — klasse `Illustratie`; object-property `bevatIllustratie`; data-properties
  `inwerking`/`terugwerkendTot`/`bron`/`effect`/`status`/`wijzigingsbronnen`/`voetnoot`/
  `definieertBegrip`/`naam`/`formaat`/`breedte`/`hoogte`/`alt`.
- `app/graphdb_writer.py` — geen codewijziging (generieke node-/rel-schrijflus dekt dit al).

**Testcases:**
- Parser: provenance/voetnoten/definities/illustraties per niveau, tabelweergave, edge cases
  (geen `:` op nadruk, illustratie zonder id/naam).
- Collect: illustratie-node + relatie, provenance-props, tellingen.
- GraphDB-writer: `BEVAT_ILLUSTRATIE` → `bevatIllustratie`-camelCase; volledige triple-check.

**Verificatie:** `uv run pytest -q` + ruff + handmatige her-import tegen lokale GraphDB.
