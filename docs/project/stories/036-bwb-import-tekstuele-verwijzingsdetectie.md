# Story 036: bwb-import — tekstuele fallback-verwijzingsdetectie

**Prioriteit:** laag
**Story points:** 4
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 027 (collect.py/graphdb_writer.py-basis)

## Verhaal

Gestructureerde verwijzingen (`<intref>`/`<extref>`) missen soms een expliciete tag, terwijl de
lopende tekst wél een verwijzing bevat ("zie artikel 4", "artikel 6:162 BW"). Deze story voegt een
**conservatieve, expliciet laag-betrouwbare** fallback-detectie toe — akkoord met de gebruiker
vastgelegd na review van de referentie-aanpak (zie gesprek bij deze story): geen brede gok, maar
een kleine hardcoded afkortingentabel + één regex, met elke treffer zichtbaar gelabeld als
`soort=tekstueel`/`betrouwbaarheid=laag` in de graaf, zodat een consument dit desgewenst volledig
kan uitfilteren. Dit blijft binnen het brongetrouwheidsprincipe: er wordt niets *verzonnen*, alleen
een expliciet als onzeker gemarkeerde extra signaal toegevoegd, nooit vermengd met de
brongetrouwe structured refs.

Referentie: `wetsanalyse-ai/tools/bwb-import/app/afkortingen.py` (compleet, 1:1 over te nemen),
`app/references.py` (`detect_textual_references`, `_TEXT_REF`-regex), `app/collect.py`
(`_verwijzingen` — dedup tegen al-gestructureerde artikelnummers, `betrouwbaarheid=laag`-prop),
`app/config.py` (`detect_tekstuele_refs`-toggle), `app/graphdb_writer.py`
(`tekstuele_refs`-constructor-param).

## Acceptatiecriteria

- [x] Nieuw `app/afkortingen.py`: `AFKORTING_BWB` (10 bekende afkortingen: Awb, AWR/Awr, IW, Sr,
      Sv, Rv, Fw, Awir, Gw), `_BW_BOEKEN` (Burgerlijk Wetboek per boeknummer), `zoek_bwb_id
      (afkorting, artikelnummer) -> str | None` — 1:1 uit de referentie, bewust niet uitgebreid
      ("geen poging tot volledigheid").
- [x] `models.py`: `VerwijzingSoort.TEKSTUEEL = "tekstueel"` (naast bestaande `INTERN`/`EXTERN`).
      `Verwijzing` krijgt `doel_artikel: str | None = None` (artikelnummer bij tekstuele
      detectie, vóórdat het een jci-doc heeft).
- [x] `references.py`: nieuwe `_TEXT_REF`-regex (`artikel(en) <nummer>[ <AFKORTING>]`,
      hoofdlettergevoelig op de afkorting zodat losse woorden als "en"/"van" niet meetellen) en
      `detect_textual_references(tekst, *, eigen_bwb_id) -> list[Verwijzing]` — 1:1 uit de
      referentie: onbekende afkorting → overgeslagen (nooit gegokt), geen afkorting → interne
      verwijzing (eigen wet). Module-docstring bijgewerkt (de huidige tekst kondigt dit al aan
      als "eigen story zodra dat nodig is").
- [x] `config.py`: `Settings.detect_tekstuele_refs: bool` uit `BWB_DETECT_TEKSTUELE_REFS`
      (default `true`, zelfde patroon als `validate_xsd`).
- [x] `collect.py`: `_Collector.__init__` + module-`collect()` krijgen een `tekstuele_refs: bool
      = True`-parameter. `_verwijzingen(bron_ref_key, verwijzingen, tekst: str | None = None)`
      uitgebreid: (1) houdt een `artikelnummers`-set bij van alle via jci gevonden
      doel-artikelnummers tijdens het verwerken van de gestructureerde verwijzingen; (2) ná die
      loop, als `tekstuele_refs` aan staat en `tekst` niet leeg is, roept
      `detect_textual_references(tekst, eigen_bwb_id=self._bwb)` aan en voegt elke treffer toe
      **behalve** als het artikelnummer al in `artikelnummers` zit (voorkomt een dubbele/
      onterechte edge naast een al-getagde verwijzing naar hetzelfde artikel) — elke toegevoegde
      rij draagt `"betrouwbaarheid": "laag"`. Alle vijf aanroeppunten (`_artikelen`/`_leden`/
      `_onderdelen`/`_bijlagen`/`_divisies`) geven voortaan ook de eigen `.tekst` mee.
- [x] `graphdb_writer.py`: `GraphDbWriter.__init__` krijgt `tekstuele_refs: bool = True`,
      opgeslagen als `self._tekstuele_refs`; `build_graph` roept `collect(wet,
      tekstuele_refs=self._tekstuele_refs)` aan (was `collect(wet)`). De verwijzingen-schrijflus
      krijgt `("betrouwbaarheid", v.ns.betrouwbaarheid)` toegevoegd aan de bestaande
      `(key, prop)`-tuple, zodat het veld meeschrijft wanneer aanwezig (leeg voor structured
      refs, `"laag"` voor tekstuele).
- [x] `ontology.py`: nieuwe data-property `betrouwbaarheid` ("Betrouwbaarheid van een
      gedetecteerde (tekstuele) verwijzing.").
- [x] `main.py`: `maak_writer(settings)` geeft `tekstuele_refs=settings.detect_tekstuele_refs`
      door aan `GraphDbWriter(...)`.

## Buiten scope van deze story

- Uitbreiding van de afkortingentabel — bewust minimaal gehouden, uit te breiden in een losse,
  kleine PR zodra een concrete behoefte blijkt.
- Detectie van verwijzingen naar leden/onderdelen in lopende tekst ("het tweede lid") — de regex
  dekt alleen artikelniveau, zelfde scope als de referentie.
- Een UI-weergave die tekstuele van structured verwijzingen onderscheidt — aan `graph-qa`/`api`.

## Schemabeslissing

`VerwijzingSoort.TEKSTUEEL` als derde enum-waarde (niet een aparte klasse) — een tekstuele
verwijzing is qua vorm identiek aan een structured verwijzing, alleen de herkomst/betrouwbaarheid
verschilt, dus geen nieuwe RDF-klasse nodig (de bestaande `Verwijzing`-klasse + `soort`/
`betrouwbaarheid`-props volstaan). Geen SQL-schema (ongewijzigd).

## Edge cases

- Onbekende afkorting (bv. "artikel 5 XYZ") → geen treffer, niets toegevoegd (nooit gegokt).
- Geen afkorting (bv. "artikel 12") → geldt als interne verwijzing (eigen wet).
- Hetzelfde artikelnummer al aanwezig als gestructureerde verwijzing → tekstuele match
  overgeslagen (geen dubbele edge).
- `BWB_DETECT_TEKSTUELE_REFS=false` → gedrag identiek aan vóór deze story (geen enkele tekstuele
  detectie, ook niet als de tekst er wel op lijkt).
- Lege tekst (`onderdeel.tekst == ""`) → geen regex-scan, geen crash.
- "BW" met een artikelnummer zonder boeknummer-prefix (bv. "artikel 5 BW" zonder `:`) → geen
  boek te bepalen → `zoek_bwb_id` geeft `None` → overgeslagen.

## Test-plan

- `test_afkortingen.py` (nieuw): `zoek_bwb_id` voor bekende afkortingen, BW per boeknummer,
  onbekende afkorting → `None`.
- `test_references.py`: `detect_textual_references` — met afkorting, zonder afkorting (intern),
  onbekende afkorting (overgeslagen), meerdere treffers in één tekst.
- `test_collect.py`: tekstuele match met een reeds-gestructureerd artikelnummer wordt
  overgeslagen; nieuwe tekstuele match krijgt `betrouwbaarheid=laag` + `soort=tekstueel`;
  `tekstuele_refs=False` onderdrukt detectie volledig.
- `test_config.py`: `detect_tekstuele_refs`-default + override.
- `test_graphdb_writer.py`: `betrouwbaarheid`-triple aanwezig op een tekstuele verwijzing,
  afwezig op een structured verwijzing.

**Bevestigd tegen de echte Invorderingswet-fixture en de live GraphDB**: de tekstuele fallback
vindt 22 echte, laag-betrouwbare verwijzingen in de al aanwezige fixture-tekst (bv. "artikel 114"
in een onderdeel-tekst), elk correct opgelost naar een bestaande, geldige artikel-IRI binnen
dezelfde wet — geen enkele naar een niet-bestaand artikel. Relatie-telling ging van 1284 naar
1311 na een her-import tegen de lokale GraphDB.

## Implementatieplan

**Nieuwe bestanden:**
- `app/afkortingen.py` — 1:1 poort: `AFKORTING_BWB`, `_BW_BOEKEN`, `zoek_bwb_id`.
- `tests/test_afkortingen.py`.

**Aangepaste bestanden:**
- `app/models.py` — `VerwijzingSoort.TEKSTUEEL`; `Verwijzing.doel_artikel`.
- `app/references.py` — `_TEXT_REF` + `detect_textual_references`.
- `app/config.py` — `detect_tekstuele_refs`.
- `app/collect.py` — `tekstuele_refs`-parameter door `_Collector`/`collect()`; `_verwijzingen`
  krijgt `tekst`-param + dedup-set + tekstuele-detectie-aanroep; alle vijf call-sites bijgewerkt.
- `app/graphdb_writer.py` — `tekstuele_refs`-constructor-param; `betrouwbaarheid` in de
  verwijzingen-schrijflus.
- `app/ontology.py` — data-property `betrouwbaarheid`.
- `app/main.py` — `maak_writer` geeft `tekstuele_refs` door.

**Testcases:** afkortingen-lookup, detect_textual_references-varianten, collect-dedup +
betrouwbaarheid-label + toggle, config-default/override, writer-triple-assertie.

**Verificatie:** `uv run pytest -q` + ruff + handmatige her-import tegen lokale GraphDB.
