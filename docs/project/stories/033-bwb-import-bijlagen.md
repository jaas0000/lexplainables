# Story 033: bwb-import — bijlagen

**Prioriteit:** medium
**Story points:** 4
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 031 (artikel-verrijking — hergebruikt provenance/voetnoten/illustraties)

## Verhaal

Een regeling kan naast de wettekst zelf bijlagen dragen (`<bijlage>`, kind van `<wet-besluit>`/
`<regeling>`, ná de wettekst): tabellen, formulieren, lijsten die bij de wet horen maar buiten de
artikelstructuur staan. Een bijlage is tegelijk *container* (kan eigen artikelen en onderdelen
bevatten) én *tekstdrager* (eigen alinea's), en is — net als een artikel — citeerbaar op een
JuriConnect-sleutel. Deze story voegt bijlagen toe als eigen entiteit in de graaf.

Referentie: `wetsanalyse-ai/tools/bwb-import/app/parser.py` (`_parse_bijlage`, `_bijlage_tekst`),
`models.py` (`Bijlage`), `collect.py` (`_bijlagen`), `ontology.py` (reeds volledig: `Bijlage`-
klasse, `heeftBijlage`, `volgtOp` — deze story voegt alleen die twee toe, de rest van de
ontologie (provenance/voetnoot/illustratie-termen) bestaat al sinds story 031).

## Acceptatiecriteria

- [x] `models.py`: `Bijlage` (`id`, `nummer`, `label`, `titel`, `tekst`, `jci`, `inwerking`,
      `bron`, `effect`, `status`, `terugwerkend_tot`, `wijzigingsbronnen: list[str]`,
      `verwijzingen: list[Verwijzing]`, `artikelen: list[Artikel]`, `onderdelen: list[Onderdeel]`,
      `voetnoten: list[str]`, `illustraties: list[Illustratie]` — zelfde velden als `Artikel` plus
      `titel` en een eigen `artikelen`-lijst). `Wet` krijgt `bijlagen: list[Bijlage]`.
      `ImportSummary` krijgt `bijlagen: int = 0` (consistent met de `illustraties`-teller uit
      story 031).
- [x] `parser.py`: nieuwe `_parse_bijlage(element, bwb_id) -> Bijlage` (kop → nummer/titel/label
      met fallback op `element.get("label")`; provenance-attributen en `_terugwerkend`/
      `_wijzigingsbronnen`/`_noten`/`_illustraties` hergebruikt van story 031, scope-exclusie
      `not(ancestor::artikel) and not(ancestor::lid) and not(ancestor::li)`; eigen `<artikel>`-
      kinderen via `_parse_artikel`). Nieuwe module-functie `_bijlage_tekst(element)`: lopende
      tekst van de bijlage zelf, exclusief geneste artikel/lid/onderdeel-tekst en exclusief tabel-
      inhoud in de exclusie-scope (tabellen wél gerenderd, net als `_lichaamstekst` sinds story
      031). `parse()`: ná de bestaande structuurdeel/artikel-opbouw, `houder = wettekst.
      getparent()` en `for bijlage_el in houder.iterfind("bijlage"): wet.bijlagen.append(...)`
      (blijft veilig als `houder` `None` is — kan bij een losstaand wettekst-fragment in een
      test, vandaar een `if houder is not None`-guard).
- [x] `collect.py`: nieuwe `_bijlagen(bijlagen, ouder_id, ouder_ent)`: per bijlage een node
      (ref_key uit jci met `#id=`-fallback net als artikel), `HEEFT_BIJLAGE`-relatie vanaf de
      Regeling, en — als er een vorige bijlage was — een `VOLGT_OP`-relatie naar die vorige
      (documentvolgorde tussen bijlagen onderling). Roept de bestaande `_verwijzingen`/
      `_illustraties`/`_onderdelen` aan voor de bijlage zelf, en `_artikelen(bijlage.artikelen,
      bijlage.id, "Bijlage")` voor de geneste artikelen (hergebruik, geen duplicatie van de
      artikel-traversal-logica). Aangeroepen vanuit `_Collector.run` ná de bestaande structuur-
      /artikel-opbouw.
- [x] `ontology.py`: klasse `Bijlage` (superklassen `Citeerbaar` + `ELI.LegalResourceSubdivision`,
      zelfde patroon als `Artikel`); object-properties `heeftBijlage` (Regeling → Bijlage,
      `ELI.has_part`) en `volgtOp` (Bijlage → Bijlage, geen ELI-alignment — documentvolgorde is
      geen ELI-begrip).
- [x] `graphdb_writer.py`: geen wijziging nodig — `Bijlage`-nodes/-relaties lopen mee via de
      bestaande generieke node-/rel-schrijflus in `build_graph` (zelfde patroon als Illustratie
      in story 031).

## Buiten scope van deze story

- Divisies/circulaires — eigen story (034), grootste resterende stuk (vereist de
  `parse()`-tak voor circulaires te vervangen, nu nog een `ParseError`).
- Tekstuele fallback-verwijzingsdetectie binnen bijlagen — ongewijzigd vervolgpunt uit story
  026/027, geldt hier net zo min als bij artikelen.
- Een admin/UI-weergave van bijlagen — aan `graph-qa`/`api` zodra die de graaf bevragen.

## Schemabeslissing

`Bijlage` als `dataclass`, zelfde stijl als `Artikel`/`Divisie`(later). Geen SQL-schema
(ongewijzigd). `VOLGT_OP`/`volgtOp` is de eerste documentvolgorde-relatie in dit project — bewust
alleen tussen bijlagen onderling (niet ook tussen artikelen: die hebben al een ondubbelzinnige
volgorde via hun structuurpositie/nummer, bijlagen niet per se).

## Edge cases

- Bijlage zonder `<kop>` → `nummer`/`titel` leeg, `label` valt terug op `element.get("label")`
  (bijlagen dragen soms een label-attribuut zonder kop-element, zie referentie).
- Bijlage zonder eigen artikelen → `artikelen` blijft leeg, geen crash.
- Eén bijlage (geen "vorige") → geen `VOLGT_OP`-relatie (niets om naar te verwijzen).
- `houder` is `None` (test-XML met een losstaand `<wettekst>` zonder ouder) → geen bijlagen-scan,
  geen crash.
- Bijlage zonder jci → ref_key valt terug op `#id=`, net als een artikel zonder jci (zie story
  027 §Edge cases, zelfde patroon).

## Test-plan

- `test_parser.py`: `_parse_bijlage` op een hand-geschreven fragment (kop, provenance,
  voetnoot, illustratie, eigen `<artikel>`-kind, tabel-in-tekst), bijlage zonder kop → label uit
  attribuut, bijlage zonder eigen artikelen.
- `test_collect.py`: `Bijlage`-node + `HEEFT_BIJLAGE`-relatie, `VOLGT_OP` tussen twee bijlagen
  (geen relatie bij één bijlage), geneste artikelen als aparte `Artikel`-nodes met
  `HEEFT_ARTIKEL`-relatie vanaf de bijlage, `ImportSummary`-tellingen (indien een `bijlagen`-
  teller wordt toegevoegd — zie Acceptatiecriteria `models.py`, `ImportSummary.bijlagen: int = 0`
  toevoegen naast de nieuwe node zelf, consistent met `illustraties`-teller uit story 031).
- `test_graphdb_writer.py`: `Bijlage`-node krijgt `Citeerbaar`-type + `owl:sameAs` als jci-
  adresseerbaar; `heeftBijlage`/`volgtOp`-predicaten correct camelCaset.

## Implementatieplan

**Aangepaste bestanden:**
- `app/models.py` — `Bijlage`-dataclass; `Wet.bijlagen`; `ImportSummary.bijlagen`.
- `app/parser.py` — `_parse_bijlage`, `_bijlage_tekst`; `parse()` scant `houder.iterfind("bijlage")`
  ná de structuurdeel/artikel-opbouw.
- `app/collect.py` — nieuwe `_bijlagen()`: node + `HEEFT_BIJLAGE` + `VOLGT_OP`, hergebruikt
  `_verwijzingen`/`_illustraties`/`_onderdelen`/`_artikelen`.
- `app/ontology.py` — klasse `Bijlage`; object-properties `heeftBijlage`/`volgtOp`.
- `app/graphdb_writer.py` — geen wijziging.

**Testcases:** parser (kop/provenance/voetnoot/illustratie/eigen artikel/tabel, label-fallback,
lege artikelenlijst, houder-None-guard), collect (node/relatie/volgt-op/telling), writer
(Citeerbaar-type + camelCase-predicaten).

**Verificatie:** `uv run pytest -q` + ruff + handmatige check tegen lokale GraphDB (met een
BWB-id dat een bijlage heeft, of anders expliciet vermelden dat dit ontbreekt).
