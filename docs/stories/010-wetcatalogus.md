# Story 010: Wetcatalogus

**Prioriteit:** hoog
**Story points:** 3
**Service:** `api/` + `frontend/`

## Verhaal

Als analist wil ik een lijst van beschikbare wetten kunnen opvragen en de artikel-structuur van een wet kunnen inzien, zodat ik bij het aanmaken van een analyse de juiste bronnen kan selecteren.

## Acceptatiecriteria

- [ ] Een ingelogde gebruiker kan een lijst van beschikbare wetten opvragen (bwb-id + naam).
- [ ] Een ingelogde gebruiker kan de artikel-structuur van een specifieke wet opvragen (bwb-id → genummerde artikelen met padnotatie).
- [ ] De frontend biedt een herbruikbaar `WetSelector`-component dat wetten laadt, een wet laat kiezen, en vervolgens de artikel-structuur toont zodat de gebruiker één of meer artikelen kan selecteren.
- [ ] De wetcatalogus levert statische data voor de eerste PoC: wetten zijn geseed in de database of hardcoded in de router.
- [ ] Bij een onbekend `bwb_id` geeft de API een 404 terug; de frontend toont een foutmelding.
- [ ] Bij een lege wettenlijst toont de frontend "Geen wetten beschikbaar."

## Schemabeslissing

**Python-models (`api/app/features/wetcatalogus/models.py`):**

- `WetKeuze` — `bwb_id: str`, `naam: str`
- `ArtikelKeuze` — `artikel: str`, `pad: str`
- `WetStructuur` — `bwb_id: str`, `artikelen: list[ArtikelKeuze]`

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/wetten` | GET | Lijst beschikbare wetten | ingelogd |
| `/v1/wetten/{bwb_id}/structuur` | GET | Artikel-structuur van een wet | ingelogd |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/wetten/route.ts` | GET | Proxy → `/v1/wetten` |
| `app/api/wetten/[bwbId]/structuur/route.ts` | GET | Proxy → `/v1/wetten/{bwb_id}/structuur` |

## Edge cases

- Onbekend `bwb_id` → API 404; frontend toont foutmelding in het selectieformulier.
- Lege wettenlijst → toon "Geen wetten beschikbaar."
- Wet zonder artikelen → lege lijst, geen crash.
- Netwerk-fout bij laden → foutmelding; selector blijft bruikbaar.

## Auth / rollen

- Beide endpoints vereisen een ingelogde gebruiker (bearer-token via BFF-sessie).
- Geen rolbeperking — zowel analisten als beheerders mogen de catalogus raadplegen.

## Gedeelde logica

- `requireSession()` uit `lib/bff-auth.ts` — bestaat ✓
- `apiProxy()` uit `lib/api-client.ts` — bestaat ✓
- `WetSelector`-component wordt hergebruikt in het analyse-aanmaken-formulier (story 012).

## Implementatienoot

Cataloguslogica kopiëren en aanpassen vanuit `wetsanalyse-ai/api/app/routers/catalog.py` → herindelen als `api/app/features/wetcatalogus/router.py` (feature-map patroon).

## UI

- **`WetSelector`-component** (Client Component): dropdown voor wet-keuze, laadt artikel-structuur on change, checkboxes of multi-select voor artikelkeuze. Wordt hergebruikt in het analyse-aanmaken-formulier (story 012).
- Mockup-varianten: leeg (geen wet gekozen), wet gekozen + artikelen zichtbaar, één artikel geselecteerd.

**Gebouwd:** nee
