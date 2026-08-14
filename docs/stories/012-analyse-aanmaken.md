# Story 012: Analyse aanmaken en volgen

**Prioriteit:** hoog
**Story points:** 5
**Service:** `api/` + `frontend/`
**Afhankelijkheid:** story 010 (WetSelector-component), story 011 (LLM-profiel aanwezig als standaard)

## Verhaal

Als analist wil ik een analyse kunnen starten door een werkgebied-naam, één of meer bronartikelen, en optioneel een analysefocus op te geven, en vervolgens de voortgang live kunnen volgen, zodat ik weet wanneer de analyse klaar is en ik het rapport kan bekijken.

## Acceptatiecriteria

- [ ] Een ingelogde gebruiker kan een nieuwe analyse aanmaken met naam, bronartikelen (uit de wetcatalogus), en optioneel een analysefocus.
- [ ] Het standaard LLM-profiel wordt automatisch gebruikt — de analist hoeft geen profiel te kiezen.
- [ ] Na aanmaken geeft de API direct 202 terug met het job-id; de analyse draait asynchroon op de achtergrond.
- [ ] De frontend navigeert direct naar de detailpagina van de nieuwe analyse.
- [ ] De detailpagina toont de huidige status live via SSE (`GET /v1/projecten/{id}/events`).
- [ ] De analyselijst (`/analyse`) toont alle analyses van de ingelogde gebruiker met naam, status-badge en datum.
- [ ] Een ingelogde gebruiker kan een analyse verwijderen vanuit de lijst of de detailpagina.
- [ ] Statussen: `wachtrij`, `actief`, `review`, `klaar`, `fout`.
- [ ] Bij status `klaar` verschijnt een knop "Bekijk rapport →" die linkt naar `/analyse/{id}/rapport` (story 013).
- [ ] Bij status `fout` wordt een foutmelding getoond op de detailpagina.
- [ ] Minimaal 1 bronartikel is verplicht; het aanmaken-formulier blokkeert verzenden bij lege bronnenlijst (client-side).

## Schemabeslissing

**Python-models (`api/app/features/projecten/models.py`):**

- `BronKeuze` — `bwb_id: str`, `artikel: str`, `lid: str | None = None`
- `AnalyseAanmaken` — `naam: str`, `bronnen: list[BronKeuze]` (min 1, max 50), `analysefocus: str | None = None`
- `AnalyseStatus` (str enum) — `wachtrij`, `actief`, `review`, `klaar`, `fout`
- `AangemaaktAcceptatie` — `id: str`, `status: AnalyseStatus`
- `AnalyseOverzicht` — `id: str`, `naam: str`, `status: AnalyseStatus`, `bijgewerkt: str`
- `AnalyseDetail` — extends `AnalyseOverzicht` + `bronnen: list[BronKeuze]`, `analysefocus: str | None`, `huidige_fase: str | None`

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/projecten` | POST | Analyse aanmaken (202) | ingelogd |
| `/v1/projecten` | GET | Lijst analyses (gepagineerd) | ingelogd |
| `/v1/projecten/{id}` | GET | Analyse-detail | ingelogd |
| `/v1/projecten/{id}` | DELETE | Analyse verwijderen | ingelogd |
| `/v1/projecten/{id}/events` | GET | SSE-stroom (status + fase) | ingelogd |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/projecten/route.ts` | GET, POST | Lijst + aanmaken |
| `app/api/projecten/[id]/route.ts` | GET, DELETE | Detail + verwijderen |
| `app/api/projecten/[id]/events/route.ts` | GET | SSE-proxy (streaming) |

## Edge cases

- Geen standaard LLM-profiel → API 422 met uitleg; frontend toont foutmelding in het formulier.
- Geen bronnen opgegeven → client-side validatie blokkeert verzenden.
- Analyse al verwijderd (race condition bij delete) → API 404 → frontend navigeert naar de lijst.
- SSE-verbinding verbroken → frontend herverbindt automatisch met exponentiële backoff (max 3 pogingen).
- Engine-fout tijdens analyse → status `fout`; foutbericht zichtbaar op de detailpagina.
- Analyse nog actief bij refresh → SSE hervat live updates.

## Auth / rollen

- Alle endpoints vereisen ingelogde gebruiker.
- Een analist ziet en verwijdert alleen eigen analyses; een beheerder ziet alle analyses.
- Rolfilter staat in `store.py`, niet in `router.py`.

## Gedeelde logica

- `WetSelector`-component uit story 010 — hergebruikt in het aanmaken-formulier.
- `requireSession()` + `apiProxy()` — bestaan ✓
- Engine-logica kopiëren vanuit `wetsanalyse-ai/api/app/engine/` → `api/app/features/projecten/engine/`.
- Router-logica kopiëren vanuit `wetsanalyse-ai/api/app/routers/projects.py` → `api/app/features/projecten/router.py`.
- Job-orkestratie (`orchestrator.py`) wordt meegekopieerd en aangepast aan de nieuwe structuur.

## UI

- **`/analyse`**: analyselijst met naam, status-badge, datum, "Bekijk →"-knop per rij, en een "Nieuwe analyse →"-knop bovenaan.
- **`/analyse/nieuw`**: formulier met werkgebied-naam (tekstveld), `WetSelector` (bronnen kiezen), analysefocus (optioneel tekstgebied), verzendknop.
- **`/analyse/{id}`**: status-scherm met live SSE-updates; toont huidige fase als tekst ("Analyse loopt — act 2/3..."), voortgangsindicator. Bij `klaar`: "Bekijk rapport →". Bij `fout`: foutmelding. Opnieuw-proberen valt buiten scope van deze story.
- Mockup-varianten: aanmaken-formulier (leeg), status-lopend, status-klaar, status-fout, analyselijst.

**Gebouwd:** nee
