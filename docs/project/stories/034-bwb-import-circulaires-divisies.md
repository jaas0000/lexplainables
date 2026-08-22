# Story 034: bwb-import — circulaires (divisies)

**Prioriteit:** medium
**Story points:** 5
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 033 (bijlagen — hergebruikt de `VOLGT_OP`-documentvolgorde en de
provenance/voetnoten/illustraties/onderdelen-logica)

## Verhaal

Circulaires en beleidsregels dragen geen wettekst (`<wet-besluit>`/`<regeling>`) maar een
recursieve boom van `<circulaire.divisie>`-elementen. Tot nu toe gooit `parse()` hiervoor een
`ParseError` (zie story 025 §Buiten scope). Deze story maakt circulaires daadwerkelijk
parseerbaar: een divisie is — net als een bijlage — tegelijk *container* (kan subdivisies
bevatten) én *tekstdrager* (eigen alinea's/onderdelen), en doet mee in het citatienetwerk op
JuriConnect-sleutel.

Referentie: `wetsanalyse-ai/tools/bwb-import/app/parser.py` (`_parse_divisie`, `_divisie_tekst`,
de `parse()`-tak voor circulaires), `models.py` (`Divisie`), `collect.py` (`_divisies`),
`ontology.py` (reeds volledig: `Divisie`-klasse, `heeftDivisie` — `volgtOp` bestaat al sinds
story 033, hergebruikt voor divisie-volgorde).

**Bewuste afwijking van de referentie**: als na deze story *nog steeds* geen `<wettekst>`,
`<regeling-tekst>` **en** geen `<circulaire>` gevonden wordt, blijft `parse()` een `ParseError`
gooien — de referentie logt in dat geval alleen een waarschuwing en geeft een lege `Wet` terug.
Dit project houdt vast aan zijn eigen, strengere brongetrouwheidsprincipe (zie
`tools/bwb-import/CLAUDE.md` §Architectuurbeslissingen: "doorgaan met 'niets gevonden' alsof dat
een geldig antwoord is, is verboden"): een onherkend documenttype moet luid falen, niet stil een
inhoudsloos object opleveren. Circulaires zelf zijn na deze story wél een herkend, geldig
documenttype — dit raakt alleen het restgeval waarin *helemaal niets* herkend wordt.

## Acceptatiecriteria

- [x] `models.py`: `Divisie` (`id`, `nummer`, `label`, `titel`, `tekst`, `jci`, `inwerking`,
      `bron`, `effect`, `status`, `terugwerkend_tot`, `wijzigingsbronnen: list[str]`,
      `verwijzingen: list[Verwijzing]`, `onderdelen: list[Onderdeel]`,
      `subdivisies: list[Divisie]`, `voetnoten: list[str]`, `illustraties: list[Illustratie]`).
      `Wet` krijgt `divisies: list[Divisie]`. `ImportSummary` krijgt `divisies: int = 0`.
- [x] `parser.py`: nieuwe `_parse_divisie(element, bwb_id) -> Divisie` (kop → nummer/titel,
      `label` uit `element.get("label")`; eigen tekst uit `./tekst//al` via nieuwe
      `_divisie_tekst(element)`; onderdelen uit `./tekst` via `_parse_onderdelen`; provenance/
      voetnoten/illustraties hergebruikt van story 031, scope beperkt tot `./tekst` resp.
      `not(ancestor::li)`; recursief voor geneste `<circulaire.divisie>`-kinderen). Nieuwe
      module-functie `_divisie_tekst(element)`: analoog aan `_bijlage_tekst`, inclusief
      tabelweergave via de bestaande `_tabel_tekst` (bewuste aanvulling t.o.v. de referentie, die
      hier geen tabellen rendert — inconsistent met `_lichaamstekst`/`_bijlage_tekst` sinds story
      031/033; deze story trekt dat gelijk zodat geen enkele tekstdrager stilzwijgend
      tabelinhoud verliest).
      `parse()` herstructureren: als `wettekst` gevonden is, ongewijzigd gedrag (structuurdelen/
      artikelen/bijlagen); **anders** (geen `wettekst`/`regeling-tekst`) een `<circulaire>/
      <circulaire-tekst>` proberen — gevonden → `wet.divisies` vullen via
      `circulaire_tekst.iterfind("circulaire.divisie")`; **niet** gevonden → `ParseError`
      (bewuste afwijking van de referentie, zie Verhaal). `wet.ondertekenaars` wordt in beide
      paden gevuld (circulaires hebben ook een `<ondertekening>`-blok).
- [x] `collect.py`: nieuwe `_divisies(divisies, ouder_id, ouder_ent)`, recursief voor
      subdivisies, met dezelfde `VOLGT_OP`-documentvolgorde-relatie tussen opeenvolgende
      (sub)divisies op hetzelfde niveau als bijlagen in story 033. Roept de bestaande
      `_verwijzingen`/`_illustraties`/`_onderdelen` aan. Aangeroepen vanuit `_Collector.run`.
- [x] `ontology.py`: klasse `Divisie` (superklassen `Citeerbaar` + `ELI.LegalResourceSubdivision`,
      zelfde patroon als `Bijlage`); object-property `heeftDivisie` (Regeling → Divisie,
      `ELI.has_part`). Geen nieuwe data-properties nodig (alles bestaat al sinds eerdere
      stories).
- [x] `graphdb_writer.py`: geen wijziging nodig (generieke node-/rel-schrijflus).
- [x] Bestaande test `test_parse_zonder_wettekst_geeft_parse_error` (in `test_parser.py`, sinds
      story 025) vervangen: het scenario "circulaire zonder wettekst" is vanaf nu een geldig,
      succesvol parse-pad, geen foutpad meer. Nieuwe test dekt het écht-onherkende restgeval
      (geen wettekst/regeling-tekst/circulaire) als `ParseError`.

## Buiten scope van deze story

- Lucene-FTS-connector — losse story (035), ongewijzigd vervolgpunt uit story 027.
- Tekstuele fallback-verwijzingsdetectie — losse story (036), ongewijzigd vervolgpunt uit story
  026/027.
- Een admin/UI-weergave van circulaires — aan `graph-qa`/`api` zodra die de graaf bevragen.
- `wet.geldig_tot`/manifest-download — al eerder als vervolgpunt genoteerd (story 032 §Buiten
  scope), ongewijzigd.

## Schemabeslissing

`Divisie` als `dataclass`, zelfde stijl als `Bijlage` (beide container + tekstdrager,
citeerbaar). `_divisie_tekst` rendert tabellen (bewuste aanvulling t.o.v. de referentie, zie
Acceptatiecriteria). Geen SQL-schema (ongewijzigd). Het restgeval "niets herkend" blijft een
harde `ParseError` — zie Verhaal voor de motivatie.

## Edge cases

- Circulaire met geneste subdivisies (`<circulaire.divisie>` in `<circulaire.divisie>`) →
  recursief geparset, elk niveau eigen `VOLGT_OP`-keten (subdivisies van verschillende ouders
  volgen elkaar niet op).
- Divisie zonder jci → ref_key valt terug op `#id=`, zelfde patroon als artikel/bijlage zonder
  jci.
- Divisie met tabel in `./tekst` → tabel wordt gerenderd (niet meer stilzwijgend uitgesloten,
  zie Acceptatiecriteria).
- Eén divisie op een niveau → geen `VOLGT_OP`-relatie.
- Toestand-XML met noch `<wettekst>`/`<regeling-tekst>` noch `<circulaire>/<circulaire-tekst>`
  → `ParseError` (bewuste afwijking van de referentie).
- Circulaire mét `<ondertekening>`-blokken → ondertekenaars alsnog geparset (dat pad staat na de
  wettekst/circulaire-vertakking, ongeacht welke tak genomen is).

## Test-plan

- `test_parser.py`: `_parse_divisie` op een hand-geschreven circulaire-fragment (kop, tekst,
  provenance, tabel, geneste subdivisie, onderdelen); circulaire zonder wettekst parseert nu
  succesvol (vervangt `test_parse_zonder_wettekst_geeft_parse_error`); écht onherkend document
  (geen van beide) geeft nog steeds `ParseError`; ondertekenaars ook gevuld op het
  circulaire-pad.
- `test_collect.py`: `Divisie`-node + `HEEFT_DIVISIE`-relatie, `VOLGT_OP` tussen twee divisies op
  hetzelfde niveau, subdivisies als geneste `Divisie`-nodes met eigen relatie naar hun ouder,
  `ImportSummary.divisies`-telling.
- `test_graphdb_writer.py`: `Divisie`-node krijgt `Citeerbaar`-type + `owl:sameAs` bij jci;
  `heeftDivisie`-predicaat correct camelCaset (echte triple-assertie).

## Implementatieplan

**Aangepaste bestanden:**
- `app/models.py` — `Divisie`-dataclass; `Wet.divisies`; `ImportSummary.divisies`.
- `app/parser.py` — `_parse_divisie`, `_divisie_tekst` (incl. tabelweergave); `parse()`
  herstructureren naar wettekst-pad / circulaire-pad / `ParseError`-restgeval.
- `app/collect.py` — nieuwe `_divisies()`, recursief, met `HEEFT_DIVISIE` + `VOLGT_OP`.
- `app/ontology.py` — klasse `Divisie`; object-property `heeftDivisie`.
- `app/graphdb_writer.py` — geen wijziging.
- `test_parser.py::test_parse_zonder_wettekst_geeft_parse_error` vervangen door een succesvol
  circulaire-parse-pad + een nieuwe test voor het écht-onherkende restgeval.

**Testcases:** parser (divisie-parsing, circulaire-pad, restgeval-ParseError, ondertekenaars op
circulaire-pad), collect (node/relatie/volgt-op/subdivisies/telling), writer (Citeerbaar-type +
camelCase-predicaat).

**Verificatie:** `uv run pytest -q` + ruff + handmatige check tegen lokale GraphDB (echte
circulaire indien snel te vinden, anders synthetische Wet zoals bij story 033).
