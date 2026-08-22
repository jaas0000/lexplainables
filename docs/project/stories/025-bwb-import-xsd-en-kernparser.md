# Story 025: bwb-import — XSD-validatie + kernparser (wet-besluit)

**Prioriteit:** hoog
**Story points:** 3
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 024 (project-setup + download)

## Verhaal

Als vervolg op story 024 wil ik de gedownloade toestand-XML kunnen valideren tegen het officiële
BWB-XSD en de kernstructuur van een `wet-besluit`-document (wet/besluit, niet ministeriële
regeling of circulaire — zie Buiten scope) kunnen parsen naar een intern model: wet →
hoofdstuk/afdeling/paragraaf (generiek genest) → artikel → lid, met de leesbare lopende tekst per
artikel/lid.

Referentie-architectuur: `wetsanalyse-ai/tools/bwb-import/app/parser.py` (niet 1:1 gekopieerd —
de referentie is 592 regels en dekt ook onderdelen/lijsten, verwijzingen, illustraties,
voetnoten, tabellen, ondertekenaars, bijlagen en circulaires; deze story dekt bewust alleen de
kernstructuur, zie Buiten scope).

De XSD-schema's (`schemas/*.xsd`) zijn 1:1 gekopieerd van de referentie — dit zijn de officiële,
publieke schema's van `repository.officiele-overheidspublicaties.nl`, geen projectcode.

## Acceptatiecriteria

- [x] `ToestandParser.validate(xml_path)` valideert tegen `schemas/toestand_2016-1.xsd` en geeft
      `True`/`False` terug — **niet-blokkerend**: een ontbrekend of onleesbaar schema geeft `False`
      + een waarschuwing, gooit geen exception (matcht de referentie: validatie is een
      kwaliteitssignaal, geen harde poort — de parse zelf gaat door).
- [x] `ToestandParser.parse(xml_path)` geeft een `Wet` terug met `bwb_id`, `citeertitel`,
      `opschrift`, `soort`, `geldig_vanaf`.
- [x] Structuurdelen (`hoofdstuk`/`afdeling`/`paragraaf`/`titeldeel`) worden generiek recursief
      geparsed (`Structuurdeel.subdelen`) — geen aparte code per nestingdiepte.
- [x] `Artikel` (nummer, label, tekst, leden) en `Lid` (nummer, tekst) worden geparsed; tekst is
      de lopende `<al>`-tekst, **exclusief** `<meta-data>` (jci/brondata) en, voor een artikel met
      leden, exclusief de tekst die al bij een `<lid>` hoort (geen dubbeling).
- [x] Getest tegen `tests/fixtures/sample_toestand.xml` — een echt fragment van de
      Invorderingswet 1990 (BWBR0004770, publieke wettekst), gekopieerd van de referentie-app.
- [x] `parse()` gooit `ParseError` met een duidelijke boodschap als root niet `<toestand>` is,
      `<wetgeving>` ontbreekt, of geen `<wet-besluit>/<wettekst>`/`<regeling>/<regeling-tekst>`
      gevonden wordt — **geen** stille lege `Wet` teruggeven (brongetrouwheid: een niet-ondersteund
      documenttype is een fout, geen leeg-maar-geslaagd resultaat).

## Buiten scope van deze story (latere stories)

- Onderdelen/lijsten (`<lijst>/<li>`), verwijzingen (`intref`/`extref`-extractie), illustraties,
  voetnoten, definities, tabellen, ondertekenaars, bijlagen.
- Ministeriële regelingen: `<regeling>/<regeling-tekst>` wordt wél als wettekst-equivalent
  herkend (zelfde structuur als wet-besluit), maar ongeteste velden (bv. `regeling-sluiting`)
  zijn niet gedekt.
- Circulaires/beleidsregels (`<circulaire>/<circulaire-tekst>`, recursieve
  `<circulaire.divisie>`-boom) — ander documentmodel, eigen story.
- WTI-verrijking, collect/Batch, RDF-ontologie, GraphDB-writer.

## Schemabeslissing

`Wet`/`Structuurdeel`/`Artikel`/`Lid` als `dataclass` (intern domeinmodel, geen API-contract).
`_knoop_id` (stabiele sleutel uit `bwb-ng-variabel-deel`, valt terug op `{bwb_id}/{tag}`) volgt
de referentie 1:1 — dat patroon is nodig zodra de GraphDB-writer stabiele IRI's per node moet
genereren, en afwijken zou een latere story dwingen dit alsnog zo te doen.

## Edge cases

- Root-tag ≠ `toestand`, of geen `<wetgeving>` → `ParseError`.
- Geen `<wet-besluit>/<wettekst>` én geen `<regeling>/<regeling-tekst>` → `ParseError` (zie
  hierboven — dit dekt zowel circulaires als een echt kapot bestand; de foutmelding maakt het
  onderscheid niet, dat is acceptabel voor deze story).
- Artikel zonder leden (losse tekst direct in het artikel, geen `<lid>`-kinderen) → `tekst` bevat
  de artikeltekst, `leden` is leeg.
- `validate()` zonder `schema_path` (geen XSD meegegeven) → `False` + waarschuwing, geen crash.

## Test-plan

- `tests/fixtures/sample_toestand.xml` (gekopieerd van de referentie-app — een echt fragment van
  BWBR0004770) voor de parse-tests: structuur, artikel-tekst, lid-tekst, geen meta-data-lekkage.
- Losse, kleine XML-strings (inline in de tests, geen fixture-bestand) voor de edge cases
  (verkeerde root-tag, ontbrekende wetgeving, ontbrekende wettekst).
- `validate()` tegen het echte gevendorde schema (geen mock) — bevestigt dat de gekopieerde
  XSD's daadwerkelijk laden en een geldig document accepteren.
