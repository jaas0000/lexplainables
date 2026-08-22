# Story 032: bwb-import — wet-brondata, aanhef/considerans, ondertekenaars

**Prioriteit:** medium
**Story points:** 3
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 027 (RDF-ontologie + GraphDB-writer)

## Verhaal

Naast de wettekst zelf draagt de bron-XML regeling-niveau metadata die nu nog niet gelezen wordt:
de oorspronkelijke publicatiebron (Staatsblad-jaar/nummer, ondertekenings-/uitgiftedatum,
Kamerdossier), de aanhef/considerans (de formele inleidende tekst vóór de artikelen), de
toestand-identiteit op wetten.overheid.nl (`bwb-ng-vast-deel`), en de ondertekenaars (wie de
regeling namens de Kroon/minister heeft ondertekend). Deze story voegt dat toe als
regeling-niveau verrijking, los van de artikel/lid/onderdeel-verrijking uit story 031.

Referentie: `wetsanalyse-ai/tools/bwb-import/app/parser.py` (`_wet_brondata`, `_wet_aanhef`,
`_parse_ondertekenaars`), `models.py` (`Ondertekenaar`, de brondata-/aanhef-velden op `Wet`),
`ontology.py` (reeds volledig: `Ondertekenaar`-klasse, `ondertekendDoor`, `toestandUrl`,
`publicatiejaar`/`publicatienr`/`ondertekeningsdatum`/`uitgiftedatum`/`dossier`/`aanhef`/
`considerans`/`functie`/`voornaam`/`achternaam`/`plaats` — deze story voegt alleen de termen toe
die de writer na deze story daadwerkelijk gebruikt).

## Acceptatiecriteria

- [x] `models.py`: `Ondertekenaar` (`functie`, `naam`, `voornaam`, `achternaam`, `plaats`, `datum`,
      allen `str | None`). `Wet` krijgt `vast_deel_url`, `aanhef`, `considerans`,
      `publicatiejaar`, `publicatienr`, `ondertekeningsdatum`, `uitgiftedatum`,
      `dossier: str | None` + `ondertekenaars: list[Ondertekenaar]`.
- [x] `parser.py`: `parse()` vult `vast_deel_url=root.get("bwb-ng-vast-deel")` en roept twee
      nieuwe helpers aan: `_wet_aanhef(wetgeving)` (`aanhef` = `<wij>`/`<wie>` + `<afkondiging>`
      samengevoegd; `considerans` = `<considerans>/<considerans.al>`-tekst, meta-data/noten
      uitgesloten) en `_wet_brondata(wetgeving)` (uit `wetgeving/meta-data/brondata/
      oorspronkelijk/publicatie`: `publicatiejaar`/`publicatienr`/`ondertekeningsdatum`
      (`ondertekeningsdatum/@isodatum`)/`uitgiftedatum` (`uitgiftedatum/@isodatum`)/`dossier`
      (`dossierref/@dossier`)). Beide defensief: ontbrekende bron-elementen geven `None`, geen
      crash. Nieuwe `_parse_ondertekenaars(wetgeving)`: itereert `<ondertekening>`-blokken
      (`<functie>`, `<naam>` met `<voornaam>`/`<achternaam>`, `<plaats>`), ontdubbelt op
      `(functie, naam, achternaam)`, slaat een ondertekening zonder functie én zonder naam over.
      Aangeroepen aan het eind van `parse()`, ongeacht wettekst/circulaire-pad (circulaires
      blijven een `ParseError` — zie Buiten scope — maar de aanroep staat al op de juiste plek
      voor als dat wegvalt).
- [x] `ontology.py`: klasse `Ondertekenaar` (superklasse `FOAF.Agent`, zelfde patroon als
      `Organisatie`); object-property `ondertekendDoor` (Regeling → Ondertekenaar,
      `ELI.passed_by`); data-properties `toestandUrl` (geen datatype — vrije string/URL),
      `publicatiejaar` (`XSD.gYear`), `publicatienr`, `ondertekeningsdatum` (`XSD.date`,
      `ELI.date_document`), `uitgiftedatum` (`XSD.date`, `ELI.date_publication`), `dossier`,
      `aanhef`, `considerans`, `functie`, `voornaam`, `achternaam`, `plaats`.
- [x] `collect.py`: de Regeling-node-props in `_Collector.run` breiden uit met `aanhef`/
      `considerans`/`publicatiejaar`/`publicatienr`/`ondertekeningsdatum`/`uitgiftedatum`/
      `dossier` (net als `citeertitel`/`opschrift` al deden) — zonder deze regel had de
      bestaande generieke node-prop-schrijflus in `graphdb_writer.py` niets om te schrijven,
      want die leest uit de `Batch`, niet rechtstreeks van `Wet`.
- [x] `graphdb_writer.py`: `build_graph` zet, ná de bestaande node-loop, twee wet-niveau
      toevoegingen: (1) als `wet.vast_deel_url`, een `toestandUrl`-triple op de wet-IRI (eigen
      property, geen `owl:sameAs` — een toestand-URL is een ánder FRBR-niveau dan de wet zelf,
      zie Schemabeslissing); (2) `_ondertekenaars(g, wet_iri, wet.ondertekenaars)`: per
      ondertekenaar een wet-overstijgende node via `v.entiteit("ondertekenaar", f"{functie}|
      {naam}")` (zelfde open-world-dedup-patroon als de WTI-Organisatie-node uit story 030) +
      `ondertekendDoor`-edge vanaf de wet.

## Buiten scope van deze story

- Circulaires (divisies) en bijlagen — eigen stories (033/034), `parse()` blijft een
  `ParseError` gooien voor circulaires zoals nu.
- `wet.geldig_tot` vullen vanuit de SRU-toestand-ref in `main.py`'s `run_import` (zoals de
  referentie doet) — orkestratie-detail, geen parser-verrijking; apart vervolgpunt indien nodig.
- Een admin/UI-weergave van de nieuwe velden — aan `graph-qa`/`api` zodra die de graaf bevragen.

## Schemabeslissing

`Ondertekenaar` als `dataclass` (zelfde stijl als `Illustratie`). `toestandUrl` krijgt bewust geen
`owl:sameAs` (dat is gereserveerd voor de canonieke wet-identiteit via `ref_key`/`canonieke_url`)
maar een eigen datatype-property — een toestand-URL identificeert een specifieke *versie*, een
ander FRBR-niveau dan de wet als geheel. Geen SQL-schema (ongewijzigd — RDF-ontologie blijft de
schemabeslissing van dit domein).

## Edge cases

- `wetgeving/meta-data/brondata` ontbreekt volledig (bv. handgeschreven test-XML) → alle
  brondata-velden `None`, geen crash.
- `<ondertekening>` zonder `<functie>` én zonder `<naam>` → overgeslagen (geen lege
  Ondertekenaar-node).
- Twee identieke ondertekeningen (functie+naam+achternaam) in dezelfde wet → ontdubbeld tot één
  `Ondertekenaar`-entry.
- Twee verschillende wetten met dezelfde ondertekenaar (bv. "De Staatssecretaris van Financiën" /
  "Wiebes") → vallen open-world samen op dezelfde slug-IRI (zelfde patroon als WTI-Organisatie).
- `root.get("bwb-ng-vast-deel")` ontbreekt → geen `toestandUrl`-triple, geen crash (bestaande
  `skip_prop`/lege-waarde-filtering elders dekt dit al waar van toepassing; hier expliciet een
  `if`-guard omdat het geen generieke node-prop is).

## Test-plan

- `test_parser.py`: `_wet_brondata`/`_wet_aanhef` tegen de bestaande fixture (`wetgeving/meta-data/
  brondata/oorspronkelijk/publicatie`: publicatiejaar 2018, nr 75, dossier 34753,
  ondertekeningsdatum 2018-02-21); ontbrekende brondata → alle velden `None`; de fixture heeft al
  drie `<ondertekening>`-blokken (functie + alleen `<achternaam>`, geen `<voornaam>`) — parsen +
  ontdubbelen + lege ondertekening overslaan.
- `test_graphdb_writer.py`: `toestandUrl`-triple aanwezig/afwezig, `Ondertekenaar`-node +
  `ondertekendDoor`-edge, twee wetten met dezelfde ondertekenaar vallen samen op één IRI.

## Implementatieplan

**Aangepaste bestanden:**
- `app/models.py` — `Ondertekenaar`-dataclass; brondata/aanhef/considerans/vast_deel_url/
  ondertekenaars op `Wet`.
- `app/parser.py` — `vast_deel_url` in `parse()`; nieuwe `_wet_aanhef`, `_wet_brondata`,
  `_parse_ondertekenaars`.
- `app/collect.py` — Regeling-node-props uitgebreid met de brondata-/aanhef-velden (bleek tijdens
  het bouwen alsnog nodig: zonder deze regel had de generieke schrijflus niets om te schrijven,
  correctie op de oorspronkelijke aanname in dit plan).
- `app/ontology.py` — klasse `Ondertekenaar`; object-property `ondertekendDoor`; data-properties
  `toestandUrl`/`publicatiejaar`/`publicatienr`/`ondertekeningsdatum`/`uitgiftedatum`/`dossier`/
  `aanhef`/`considerans`/`functie`/`voornaam`/`achternaam`/`plaats`.
- `app/graphdb_writer.py` — `toestandUrl`-triple + nieuwe `_ondertekenaars()`-methode in
  `build_graph`.

**Testcases:** brondata/aanhef tegen fixture + hand-geschreven fragment zonder brondata,
ondertekenaars parsen/dedup/lege-overslaan, toestandUrl-triple, Ondertekenaar-node + edge,
open-world-dedup over twee wetten.

**Verificatie:** `uv run pytest -q` + ruff + handmatige her-import tegen lokale GraphDB.
