# Story 012: Analyse aanmaken en volgen

**Prioriteit:** hoog
**Story points:** 5
**Service:** `api/` + `frontend/`
**Afhankelijkheid:** story 010 (WetSelector-component), story 011 (LLM-profiel aanwezig als standaard)

## Verhaal

Als analist wil ik een analyse kunnen starten door een werkgebied-naam, één of meer bronartikelen, en optioneel een analysefocus op te geven, en vervolgens de voortgang live kunnen volgen, zodat ik weet wanneer de analyse klaar is en ik het rapport kan bekijken.

## Acceptatiecriteria

- [ ] Een ingelogde gebruiker kan een nieuwe analyse aanmaken met naam (optioneel), bronartikelen (wet-dropdown + artikel-input + lid-input), omschrijving/context (optioneel), hoofdvraag/analysefocus (optioneel), en een bestaande begrippenlijst (optioneel, inklapbaar blok).
- [ ] Het model-profiel is te kiezen via een dropdown; bij ontbreken van profielen valt het formulier terug op een vrij tekstveld.
- [ ] Human-in-the-loop review is instelbaar via een checkbox (default aangevinkt); uit = volautomatisch tot het rapport.
- [ ] Na aanmaken geeft de API direct 202 terug met het job-id; de analyse draait asynchroon op de achtergrond.
- [ ] De frontend navigeert direct naar de detailpagina van de nieuwe analyse.
- [ ] De detailpagina toont de huidige status live via SSE (`GET /v1/projecten/{id}/events`).
- [ ] De analyselijst (`/projecten`) toont alle analyses van de ingelogde gebruiker met naam, bronnen-samenvatting, status (dot + tekst) en datum.
- [ ] De analyselijst heeft een zoekbalk (naam/BWB-id/artikel), status-dropdown en wet-dropdown als filters.
- [ ] Een ingelogde gebruiker kan een analyse verwijderen vanuit de lijst of de detailpagina.
- [ ] Statussen: `wachtrij`, `actief`, `review`, `klaar`, `fout`.
- [ ] Bij status `klaar` verschijnt een knop "Bekijk rapport →" die linkt naar `/projecten/{id}/rapport` (story 013).
- [ ] Bij status `fout` wordt een foutmelding getoond op de detailpagina.
- [ ] Minimaal 1 bronartikel is verplicht (wet + artikel); het aanmaken-formulier blokkeert verzenden bij lege bronnenlijst (client-side).

## Schemabeslissing

**Python-models (`api/app/features/projecten/models.py`):**

- `BronKeuze` — `bwb_id: str`, `artikel: str`, `lid: str | None = None`
- `BegripInvoer` — `naam: str`, `definitie: str | None = None`
- `AnalyseAanmaken` — `naam: str | None = None`, `bronnen: list[BronKeuze]` (min 1, max 50), `omschrijving: str | None = None`, `analysefocus: str | None = None`, `begrippenlijst: list[BegripInvoer] | None = None`, `model_profiel: str | None = None`, `human_in_the_loop: bool = True`
- `AnalyseStatus` (str enum) — `wachtrij`, `actief`, `review`, `klaar`, `fout`
- `AangemaaktAcceptatie` — `id: str`, `status: AnalyseStatus`
- `AnalyseOverzicht` — `id: str`, `naam: str`, `bronnen: list[BronKeuze]`, `status: AnalyseStatus`, `bijgewerkt: str`
- `AnalyseDetail` — extends `AnalyseOverzicht` + `omschrijving: str | None`, `analysefocus: str | None`, `model_profiel: str | None`, `human_in_the_loop: bool`, `begrippenlijst: list[BegripInvoer] | None`, `huidige_fase: str | None`

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

**Frontend-routes:**
- `/projecten` — analyselijst
- `/projecten/nieuw` — aanmaakformulier
- `/projecten/{id}` — analyse-detail (status + voortgang)
- `/projecten/{id}/rapport` — rapport-weergave (story 013)

## Edge cases

- Geen standaard LLM-profiel → API 422 met uitleg; frontend toont foutmelding in het formulier.
- Geen bronnen opgegeven → client-side validatie blokkeert verzenden.
- Analyse al verwijderd (race condition bij delete) → API 404 → frontend navigeert naar de lijst.
- SSE-verbinding verbroken → frontend herverbindt automatisch met exponentiële backoff (max 3 pogingen).
- Engine-fout tijdens analyse → status `fout`; foutbericht zichtbaar op de detailpagina.
- Analyse nog actief bij refresh → SSE hervat live updates.
- Begrippenlijst bevat parse-fouten → frontend toont per-fout melding, blokkeert verzenden.

## Auth / rollen

- Alle endpoints vereisen ingelogde gebruiker.
- Een analist ziet en verwijdert alleen eigen analyses; een beheerder ziet alle analyses.
- Rolfilter staat in `store.py`, niet in `router.py`.

## Gedeelde logica

- `WetSelector`-component uit story 010 — als grondslag voor de wet-dropdown in de bron-rijen (de mockup gebruikt een simplere select; de echte implementatie hergebruikt de WetSelector + artikel-autocomplete).
- `requireSession()` + `apiProxy()` — bestaan ✓
- Engine-logica kopiëren vanuit `wetsanalyse-ai/api/app/engine/` → `api/app/features/projecten/engine/`.
- Router-logica kopiëren vanuit `wetsanalyse-ai/api/app/routers/projects.py` → `api/app/features/projecten/router.py`.
- Job-orkestratie (`orchestrator.py`) wordt meegekopieerd en aangepast aan de nieuwe structuur.

## UI

- **`/projecten`**: donkerblauwe hero-banner (label "JURIDISCH ANALYSESCHEMA", titel "Analyses", beschrijving, knop "Nieuwe analyse"). Filterbar met zoekbalk, status-dropdown, wet-dropdown en sorteerdropdown (nieuwste/oudste). Tabel: checkbox | NAAM (+ id eronder) | BRON (samenvatting eerste bron + +N) | STATUS (dot + volledige tekst) | BIJGEWERKT | acties.
- **`/projecten/nieuw`**: formulier met:
  - Sectie "Bronnen in het werkgebied" met teller rechts — per bron een rij met wet-dropdown, artikel-autocomplete (dropdown-suggesties bij typen) en lid-keuze (select als leden bekend, vrij veld als fallback); ×-knop; "+ Bron toevoegen"-knop.
  - Model-profiel: dropdown (geladen via BFF) met "beheer via /beheer"-link rechts.
  - Naam werkgebied: tekstveld, optioneel, hint "anders afgeleid".
  - Omschrijving / context: textarea, optioneel.
  - Hoofdvraag / analysefocus: textarea, optioneel.
  - Bestaande begrippenlijst: `<details>`-element (inklapbaar), optioneel; textarea + `<input type="file" accept=".csv,.json,.txt">` voor uploaden; JSON/CSV/vrij formaat.
  - Human-in-the-loop review: checkbox (default aangevinkt) + uitlegtekst.
  - "Analyse starten"-knop (primair) + "Annuleer"-knop.
- **`/projecten/{id}`**: status-scherm met live SSE-updates; toont huidige fase als tekst + voortgangsbalk. Bij `klaar`: "Bekijk rapport →". Bij `fout`: foutmelding. Verwijderknop met bevestigingsstap.
- Mockup-varianten: lijst, aanmaken-formulier, status-wachtrij, status-lopend, status-klaar, status-fout.

**Gebouwd:** ja (PR #11) — nep-engine; echte LLM-orkestratie volgt
