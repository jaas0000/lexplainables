# Story 026: bwb-import — onderdelen (lijsten) + gestructureerde verwijzingen

**Prioriteit:** hoog
**Story points:** 3
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 025 (XSD-validatie + kernparser)

## Verhaal

Als vervolg op story 025 wil ik genestelde `<lijst>/<li>`-onderdelen (definities, opsommingen)
en gestructureerde `<intref>`/`<extref>`-verwijzingen kunnen parsen, zodat een artikel/lid zijn
volledige inhoud draagt (niet alleen de lopende tekst) en de latere GraphDB-writer relaties
tussen bepalingen kan leggen.

Referentie: `wetsanalyse-ai/tools/bwb-import/app/parser.py` (`_parse_onderdelen`/
`_parse_onderdeel`) + `app/references.py` (`extract_references`). Niet 1:1 gekopieerd: de
jci-parsing-helpers (`jci_doel`/`jci_to_ref_key`/`jci_doel_ref_key`) en de tekstuele
fallback-detectie (regex + wetsafkortingen-lookup) horen bij het moment dat een `Verwijzing`
een graafrelatie wordt — dat is een taak voor de GraphDB-writer-story, niet voor de parser. Deze
story levert alleen de rauwe, gestructureerde `Verwijzing`-objecten.

## Acceptatiecriteria

- [x] `Onderdeel` (id, nummer, tekst, verwijzingen, subonderdelen) wordt geparsed uit direct
      geneste `<lijst>/<li>`, recursief voor sub-lijsten (bv. "aa." met een genest "1°./2°./…").
- [x] `Verwijzing` (soort, tekst, doel_bwb_id, doel_pad, doc, verwijzing_id) wordt geparsed uit
      `<intref>`/`<extref>`-elementen. Een `extref` naar de eigen wet (`bwb-id` == de wet die
      geparsed wordt) telt als `INTERN`, niet `EXTERN`.
- [x] Verwijzingen komen nooit uit `<meta-data>`-subtrees (zelfde brongetrouwheidsregel als
      story 025's tekst-extractie).
- [x] Scoping voorkomt dubbeling: de `verwijzingen` van een artikel bevatten niet de
      verwijzingen die al bij een `<lid>` of onderdeel (`<li>`) horen; de `verwijzingen` van een
      lid bevatten niet die van een genest onderdeel; de `verwijzingen` van een onderdeel komen
      alleen uit zijn eigen directe `<al>`-kinderen, niet uit geneste sub-onderdelen.
- [x] `Artikel` en `Lid` krijgen een `onderdelen: list[Onderdeel]`-veld.
- [x] Getest tegen `tests/fixtures/sample_toestand.xml` artikel 2 lid 1, dat een geneste
      lijststructuur + meerdere `extref`'s draagt (echte overheid.nl-tekst).

## Buiten scope van deze story

- jci-parsing (`jci_doel`, `jci_to_ref_key`, `jci_doel_ref_key`) — nodig zodra de GraphDB-writer
  een `Verwijzing` naar een graafrelatie vertaalt.
- Tekstuele fallback-detectie van ongetagde verwijzingen ("artikel 4", "artikel 6:162 BW") +
  `app/afkortingen.py` (wetsafkortingen-lookup) — apart, kleiner stukje functionaliteit, eigen
  story omdat het een ander soort risico draagt (regex-gebaseerde detectie, fout-positieven
  mogelijk) dan de gestructureerde extractie hier.
- Illustraties, voetnoten, definities, tabellen binnen onderdelen (`Onderdeel`-velden daarvoor
  bestaan in de referentie maar worden hier niet toegevoegd — YAGNI totdat een story ze nodig
  heeft).

## Schemabeslissing

`VerwijzingSoort` als `StrEnum` (`INTERN = "intref"`, `EXTERN = "extref"`) — de string-waarde is
de brontag, handig bij debuggen/logging. `Onderdeel` en `Verwijzing` als `dataclass`, zelfde
patroon als de rest van het model.

## Edge cases

- `<intref>` (interne verwijzing, geen `bwb-id`-attribuut) → `soort=INTERN`, `doel_bwb_id=None`.
- `<extref bwb-id="{eigen bwb_id}">` (verwijst naar de eigen wet maar getagd als extern) →
  `soort=INTERN` (de brontag zegt "extern", maar het doel is de eigen wet).
- Onderdeel zonder `<li.nr>` → `nummer=""`, geen crash.
- Diep geneste sub-onderdelen (2+ niveaus, zoals "aa." → "1°./2°./3°./4°." in de fixture) →
  `subonderdelen` recursief gevuld, elk niveau met zijn eigen `verwijzingen`.

## Test-plan

- Tegen `sample_toestand.xml` artikel 2 lid 1: aantal onderdelen, nummers (`a.`, `aa.`, `b.`,
  …), geneste sub-onderdelen onder `aa.` (`1°.`…`4°.`), verwijzingen per onderdeel.
- Kleine inline XML-snippets voor: `intref` (niet in de fixture aanwezig), extref-naar-eigen-wet,
  scoping (artikel met een verwijzing binnen een lid mag die niet op artikel-niveau tonen).
