# Story 037: Werkplek — echte wetsartikeltekst via GraphDB

**Prioriteit:** middel
**Story points:** 4
**Service:** `api/` + `frontend/`
**Afhankelijkheid:** story 022 (annotatie-backend), story 023 (werkplek-UI, het openstaande
acceptatiecriterium dat deze story sluit), `tools/bwb-import` + `deploy/graphdb` (de kennisgraaf
moet gevuld zijn voor de betreffende wet)

## Verhaal

Als analist wil ik in de werkplek de echte wetsartikeltekst zien (in plaats van de huidige
placeholder), zodat ik een annotatiebeslissing kan nemen zonder de wettekst er ergens anders
bij te moeten zoeken.

## Aanleiding

Story 023's acceptatiecriterium "toont de volledige wetsartikeltekst" was nooit gebouwd — de
oorspronkelijke aanpak (Wettenbank-MCP) bestaat niet meer sinds ADR-0001 (vervangen door
`bwb-import` + GraphDB). `api/app/shared/wettenbank.py` documenteert dit al als openstaand
punt voor een andere functie (`haal_citeertitel_op`); deze story lost het specifiek voor de
werkplek op met een eigen, kleine SPARQL-client — geen hergebruik van `wettenbank.py` (die
module praat nog JSON-RPC tegen een niet-bestaande service en staat gepland voor volledige
vervanging, aparte story, buiten scope hier).

## Acceptatiecriteria

- [x] `GET /v1/annotatie/documenten/{slug}/wetsartikel` geeft de tekst van het artikel (en,
      indien aanwezig, elk lid met nummer + tekst) van het bij het document horende `bwb_id`
      + `artikel`, opgehaald via een SPARQL-query tegen GraphDB.
- [x] Alleen de eigenaar van het document kan dit endpoint bevragen — zelfde 404-op-onbekend/
      andermans-document-gedrag als de bestaande annotatie-endpoints (`_laad_eigen_document`).
- [x] Artikel niet in de graaf gevonden (wet nog niet geïmporteerd, of artikelnummer-mismatch)
      → 404 met een duidelijke detail-message; onderscheiden van "document niet gevonden".
- [x] GraphDB niet bereikbaar (netwerk-/HTTP-fout) → 502; dit blokkeert niet de rest van de
      pagina — de elementenkolom blijft werken ongeacht deze fout (BFF/frontend vangt de fout
      lokaal af, niet de hele documentlaad-flow).
- [x] De frontend (`/werkplek/{slug}`) toont de opgehaalde tekst in de linkerkolom in plaats
      van de huidige placeholder; is er een `lid` op het document gezet, dan is dat lid visueel
      gemarkeerd tussen de overige leden.
- [x] Faalt het ophalen (404/502): de linkerkolom toont een duidelijke melding
      ("Wetsartikeltekst niet beschikbaar: <reden>") in plaats van te crashen; de rechterkolom
      (elementen) blijft functioneren.

## Schemabeslissing

**Nieuw Pydantic-model (`api/app/features/annotatie/models.py`):**

```python
class WetsartikelLid(BaseModel):
    nummer: str | None
    tekst: str

class Wetsartikel(BaseModel):
    bwb_id: str
    artikel: str
    opschrift: str | None
    tekst: str
    leden: list[WetsartikelLid]
```

**Endpoint:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/annotatie/documenten/{slug}/wetsartikel` | GET | Wetsartikeltekst uit GraphDB | `huidige_gebruiker`, client-scoped via het document |

**BFF-route (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/annotatie/documenten/[slug]/wetsartikel/route.ts` | GET | Proxy naar bovenstaand endpoint |

Geen nieuwe database-tabel — dit endpoint leest uitsluitend uit GraphDB, niet uit Postgres.

## IRI/SPARQL-aanpak

`tools/bwb-import/app/rdf_vocab.py`'s `Vocab.by_ref_key` is de canonieke IRI-afleiding
(`urn:bwb:{bwb}:artikel:{nr}`, URN-segmenten `:`-gescheiden, elk segment percent-encoded). Een
directe cross-service-import kan niet (ADR-0002 — geen gedeelde import over een servicegrens).
Deze story herimplementeert alléén het smalle stukje IRI-constructie dat nodig is om een
artikel-IRI te bouwen uit `(bwb_id, artikelnummer)` — geen volledige ontologie-kennis, geen
schrijflogica. Met een commentaar dat expliciet verwijst naar `rdf_vocab.py` als bron van
waarheid voor het schema, zodat een toekomstige wijziging daar zichtbaar is voor wie dit
endpoint onderhoudt.

Query (via SELECT tegen `{GRAPHDB_URL}/repositories/{GRAPHDB_REPOSITORY}`, `Accept:
application/sparql-results+json`, zelfde patroon als `graphdb_writer.py`'s leesquery's):

```sparql
PREFIX bwb: <urn:bwb-ns:>
SELECT ?opschrift ?tekst ?lidNummer ?lidTekst WHERE {
  GRAPH ?g {
    <urn:bwb:{bwb_id}:artikel:{artikel}> a bwb:Artikel .
    OPTIONAL { <urn:bwb:{bwb_id}:artikel:{artikel}> bwb:tekst ?tekst }
    OPTIONAL { <urn:bwb:{bwb_id}:artikel:{artikel}> bwb:opschrift ?opschrift }
    OPTIONAL {
      <urn:bwb:{bwb_id}:artikel:{artikel}> bwb:heeftLid ?lid .
      ?lid bwb:tekst ?lidTekst .
      OPTIONAL { ?lid bwb:nummer ?lidNummer }
    }
  }
}
```

Twee dingen die pas bij handmatige verificatie tegen de live GraphDB naar boven kwamen (beide
verwerkt, zie Implementatieplan):

- De `GRAPH ?g { ... }`-wrapper is niet optioneel: `graphdb_writer.py` schrijft elke wet naar
  zijn eigen named graph (`urn:bwb:graph:{bwb_id}`, idempotente re-import per graaf), nooit naar
  de default graph. Een SELECT zonder `GRAPH ?g` ziet daardoor niets.
- `bwb:tekst` op de Artikel-node zelf is niet gegarandeerd: een artikel met leden heeft zijn
  tekst per lid, niet nogmaals op het artikel (bevestigd tegen de echte Invorderingswet-fixture
  — art. 1 heeft twee leden en geen eigen `bwb:tekst`). Het matchpatroon is daarom
  `<iri> a bwb:Artikel` (bestaat het artikel?), met `?tekst` volledig `OPTIONAL`.

Geen enkele binding (het artikel bestaat niet als `bwb:Artikel`-resource) → niet gevonden → 404.

## Edge cases

- Document bestaat, maar `bwb_id`/`artikel` staan niet (meer) in de graaf → 404,
  "Wetsartikel niet gevonden in de kennisgraaf.".
- GraphDB draait niet (lokale dev zonder `deploy/graphdb`) → 502,
  "GraphDB niet bereikbaar."; ontwikkelaars zonder lokale GraphDB kunnen de rest van de
  werkplek gewoon gebruiken.
- Artikel zonder leden (bv. een enkel-lid-artikel dat inline tekst heeft i.p.v. expliciete
  `Lid`-nodes) → `leden: []`, alleen `tekst` getoond.
- `document_.lid` verwijst naar een nummer dat niet in de opgehaalde `leden`-lijst voorkomt
  (drift tussen annotatie-document en de graaf) → geen crash, gewoon geen markering.

## Auth / rollen

- Zelfde als de bestaande annotatie-endpoints: `huidige_gebruiker` + client-scoping via
  `_laad_eigen_document` (hergebruikt, geen nieuwe autorisatielogica).
- Geen rolbeperking.

## Gedeelde logica

- `_laad_eigen_document` (bestaand, `annotatie/router.py`) — hergebruikt voor de
  ownership-check vóórdat de GraphDB-query gebeurt.
- Nieuwe module `api/app/features/annotatie/graphdb.py` — geen `shared/`-geval (precies één
  consument op dit moment); als een tweede feature dit ooit nodig heeft (bv. wetcatalogus'
  langstaande TODO in `shared/wettenbank.py`), dan is dát het moment om te verplaatsen
  (`feature-bouwen` regel 8).
- Env-vars `GRAPHDB_URL`/`GRAPHDB_REPOSITORY`/`GRAPHDB_USER`/`GRAPHDB_PASSWORD_FILE` — zelfde
  namen en defaults als `tools/bwb-import/app/config.py`, zodat één GraphDB-instance met één
  configuratieset door beide services gelezen kan worden. Wachtwoord volgt werkwijze-ADR-0006
  (`*_FILE`, geen platte env-var).

## UI

- Linkerkolom van `/werkplek/{slug}` (`frontend/app/werkplek/[slug]/page.tsx`): vervangt de
  huidige placeholder-tekst door een `fetch` naar de nieuwe BFF-route; toont opschrift (indien
  aanwezig) + artikeltekst + leden-lijst; het lid dat op het document staat (`document_.lid`)
  krijgt een visuele markering (bv. linker accentrand of achtergrondkleur, zelfde
  aandacht-kleurpatroon als `ElementenKolom.tsx`).
- Laadstatus en foutstatus onafhankelijk van de documentlaad-status (eigen `useState`/`useEffect`
  in dezelfde pagina, geen aparte route/pagina nodig).

## Implementatieplan

**Nieuwe bestanden:**
- `api/app/features/annotatie/graphdb.py` — SPARQL-client: bouwt de artikel-IRI
  (`urn:bwb:{bwb_id}:artikel:{artikel}`, zelfde percent-encoding als
  `tools/bwb-import/app/rdf_vocab.py::Vocab._iri`, met verwijzing daarnaar als bron van
  waarheid), doet de SELECT via `httpx.AsyncClient`, parsed naar `Wetsartikel`. Eigen excepties
  `GraphDbNietBereikbaar`/`WetsartikelNietGevonden` (niet hergebruikt van `wettenbank.py` —
  andere transportlaag, dat module staat gepland voor vervanging). Leest
  `GRAPHDB_URL`/`GRAPHDB_REPOSITORY`/`GRAPHDB_USER`/`GRAPHDB_PASSWORD_FILE` (zelfde
  namen/defaults als `tools/bwb-import/app/config.py`, wachtwoord via `*_FILE` per ADR-0006).
- `api/app/features/annotatie/tests/test_graphdb.py` — IRI-constructie, response-parsing
  (met/zonder leden/opschrift), lege bindings → `WetsartikelNietGevonden`, netwerkfout →
  `GraphDbNietBereikbaar` (gefakete HTTP-laag, geen echte GraphDB).
- `frontend/app/api/annotatie/documenten/[slug]/wetsartikel/route.ts` — BFF-proxy, zelfde
  `requireSession()` + `apiProxy()`-patroon als de bestaande annotatie-BFF-routes.

**Aangepaste bestanden:**
- `api/app/features/annotatie/models.py` — `WetsartikelLid`/`Wetsartikel` toevoegen.
- `api/app/features/annotatie/router.py` — `GET /annotatie/documenten/{slug}/wetsartikel`:
  `_laad_eigen_document` (bestaand, hergebruikt) voor ownership, dan de GraphDB-client;
  `WetsartikelNietGevonden` → 404, `GraphDbNietBereikbaar` → 502.
- `api/app/features/annotatie/tests/test_router.py` — 200 met tekst+leden, 404 (ander
  document), 404 (artikel niet in graaf), 502 (GraphDB onbereikbaar).
- `frontend/app/werkplek/[slug]/page.tsx` — placeholder vervangen door eigen fetch naar de
  nieuwe BFF-route (losse laad-/foutstatus van de documentlaad-status); toont opschrift + tekst
  + leden, met het lid van `document_.lid` visueel gemarkeerd.
- `docs/project/stories/023-werkplek-annotatie-ui.md` — het openstaande criterium afvinken met
  verwijzing naar story 037; `Gebouwd` terug naar volledig `ja`.

**Endpoint:**
- `GET /v1/annotatie/documenten/{slug}/wetsartikel` — wetsartikeltekst uit GraphDB
  (`huidige_gebruiker`, client-scoped via het document).

**Testcases:**
- IRI-vorm correct (incl. percent-encoding, bv. artikelnummer `5a`).
- Volledige response (opschrift + 2 leden) → correcte `Wetsartikel`.
- Geen leden-bindings → `leden == []`.
- Lege bindings → `WetsartikelNietGevonden` → 404.
- Netwerkfout → `GraphDbNietBereikbaar` → 502.
- Ander document (client-scoping) → 404 (regressie, bestaand gedrag).

**Afhankelijkheden en aandachtspunten:**
- Geen `shared/`-plek voor `graphdb.py` — precies één consument nu (`feature-bouwen` regel 8).
- Lokale dev: `GRAPHDB_URL=http://localhost:7200` (poort al gepubliceerd in
  `deploy/graphdb/docker-compose.yml`); geen wijziging aan docker-compose nodig in deze story.
- Alle nieuwe tests met gefakete HTTP-laag, geen `integration`-marker nodig (alleen lezen, geen
  idempotentie-eis); wel één keer handmatig tegen de lokale GraphDB verifiëren
  (BWBR0004770-fixture, al gevuld).
- Story 023's criterium mag pas op `ja` als dit endpoint écht werkt — niet optimistisch vooruit
  afvinken (zie het eerdere vervolgpunt over precies deze valkuil).

**Gebouwd:** nee
