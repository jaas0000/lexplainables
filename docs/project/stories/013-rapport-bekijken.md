# Story 013: Rapport bekijken

**Prioriteit:** hoog
**Story points:** 3
**Service:** `api/` + `frontend/`
**Afhankelijkheid:** story 012 (analyse met status `klaar`)

## Verhaal

Als analist wil ik het analyserapport kunnen inzien nadat de analyse klaar is, zodat ik de resultaten — werkgebied, bronnen, begrippen en afleidingsregels — overzichtelijk kan lezen en eventueel als Markdown kan downloaden.

## Acceptatiecriteria

- [ ] Een ingelogde gebruiker kan het rapport opvragen van een afgesloten analyse (status `klaar`).
- [ ] Het rapport toont: werkgebied (naam, hoofdvraag, omschrijving, analysefocus), bronnen (per bron: metadata + samenvatting), begrippen (naam, definitie, klasse, synoniemen), en afleidingsregels.
- [ ] Bij een analyse die nog niet klaar is (status ≠ `klaar`) geeft de API 409; de frontend toont "Rapport nog niet beschikbaar" en biedt een link terug naar de statuspagina.
- [ ] Het rapport is ook te downloaden als Markdown-bestand via een download-knop.
- [ ] De rapportpagina bevat een "← Terug naar analyse"-link naar `/analyse/{id}`.
- [ ] Lege secties (geen begrippen, geen regels) worden niet weergegeven of tonen "geen resultaten".

## Schemabeslissing

**Python-models (uitbreiding `api/app/features/projecten/models.py`):**

- `Rapport` — `werkgebied: dict`, `bronnen: list`, `begrippen: list`, `afleidingsregels: list`

(Velden zijn `dict`/`list` om de complexe geneste structuur uit de engine direct door te geven zonder extra re-mapping; `extra = "allow"` op het model om forward-compatible te blijven met engine-uitbreidingen.)

**Verwachte top-level sleutels per veld** (op basis van de engine-uitvoer; de renderer vertrouwt hierop):

| Veld | Verwachte sleutels |
|---|---|
| `werkgebied` | `naam`, `hoofdvraag`, `omschrijving`, `scoping`, `analysefocus` |
| `bronnen[i]` | `bron_id`, `label`, `wet`, `bwbId`, `artikel`, `lid`, `versiedatum`, plus engine-uitvoer per bron |
| `begrippen[i]` | `id`, `naam`, `definitie`, `klasse`, `synoniemen`, `voorbeeld` |
| `afleidingsregels[i]` | `id`, `naam`, `omschrijving` (exacte structuur volgt engine-uitvoer) |

De frontend-renderer werkt met defensive access (ontbrekende sleutels worden leeg weergegeven, niet als error).

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/projecten/{id}/rapport` | GET | Rapport als JSON | ingelogd |
| `/v1/projecten/{id}/rapport.md` | GET | Rapport als Markdown-download | ingelogd |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/projecten/[id]/rapport/route.ts` | GET | JSON-proxy |
| `app/api/projecten/[id]/rapport.md/route.ts` | GET | Markdown-download (doorstuurt `Content-Disposition`) |

## Edge cases

- Rapport opvragen van een niet-afgesloten analyse → API 409; frontend toont melding + link terug.
- Analyse niet gevonden → API 404; frontend navigeert naar de lijst.
- Lege rapport-secties → secties niet weergeven of "geen resultaten" per sectie.
- Markdown-download: `Content-Disposition: attachment; filename="rapport-{id}.md"` doorgeven vanuit de BFF.

## Auth / rollen

- Vereist ingelogde gebruiker; rolfilter identiek aan story 012 (analist ziet alleen eigen analyses).

## Gedeelde logica

- `requireSession()` + `apiProxy()` — bestaan ✓
- Rapport-endpoint kopiëren vanuit `wetsanalyse-ai/api/app/routers/projects.py` (rapport- en rapport.md-handlers).
- Markdown-renderlogica kopiëren vanuit `wetsanalyse-ai/api/app/engine/render_regelspraak.py` (waar van toepassing).

## UI

- **`/analyse/{id}/rapport`**: sectie-gebaseerde lay-out. Werkgebied bovenaan (naam + hoofdvraag als kop, omschrijving + analysefocus als tekst), daarna bronnen (per bron een kaart of collapsible), begrippen (tabel of kaartenoverzicht), afleidingsregels (genummerd).
- **Download-knop**: directe link naar `/api/projecten/{id}/rapport.md` — browser triggert download.
- Mockup-varianten: rapport volledig gevuld, rapport met lege secties, rapport-niet-beschikbaar-melding.

**Gebouwd:** nee
