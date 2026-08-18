# Story 021: LLM-calls log

**Prioriteit:** laag
**Story points:** 3
**Service:** `api/` + `frontend/`
**Afhankelijkheid:** story 012 (analyses aanmaken), story 019 (capture-toggle)

## Verhaal

Als beheerder wil ik de LLM-aanroepen van een analyse kunnen inzien — inclusief de gebruikte prompts, het model, en het token-verbruik — zodat ik inzicht heb in het verbruik, eventuele kwaliteitsproblemen kan opsporen, en de kosten per analyse kan inschatten.

## Acceptatiecriteria

- [ ] Wanneer de `capture_llm_calls`-instelling (story 019) is ingeschakeld, legt de engine elke LLM-aanroep vast in de database (systeem-prompt, gebruikersprompt, ruwe respons, model, tokens, tijdstip, analyse-slug).
- [ ] `GET /v1/admin/analyses/{slug}/llm-calls` geeft alle vastgelegde aanroepen van één analyse terug, gesorteerd op tijdstip.
- [ ] Het vastleggen faalt nooit de analyse: schrijffouten worden gelogd maar niet naar de aanroeper gepropageerd.
- [ ] Frontend: een beheerder ziet op de rapport-pagina (`/analyse/{id}/rapport`, story 013) een uitklapbare sectie "LLM-calls" die de tabel toont; of een aparte pagina `/beheer/llm-log/` met een overzicht per analyse.
- [ ] De capture is standaard uitgeschakeld; de beheerder schakelt hem in via story 019.
- [ ] De response-inhoud en de prompts kunnen gevoelige (wets)tekst bevatten — toegang is bewust beperkt tot beheerders.

## Schemabeslissing

**Alembic-migratie:** maak tabel `llm_calls` aan (migrations/0009_*).

**Tabel `llm_calls`:**

| Kolom | Type | Opmerking |
|---|---|---|
| `id` | BIGINT PK | autoincrement |
| `analyse_slug` | TEXT NOT NULL | Verwijzing naar de analyse (geen FK-constraint — analyses mogen verwijderd worden) |
| `activiteit` | TEXT NOT NULL DEFAULT '' | bijv. `act2`, `act3a`, `act3b` |
| `ronde` | INTEGER NOT NULL DEFAULT 0 | Rondenummer binnen de analyse |
| `poging` | INTEGER NOT NULL DEFAULT 1 | Herhalingen bij auto-correctie |
| `fase` | TEXT NOT NULL DEFAULT '' | Verfijnde stap binnen de activiteit |
| `model` | TEXT NOT NULL DEFAULT '' | Model-identifier zoals teruggegeven door de provider |
| `provider` | TEXT NOT NULL DEFAULT '' | bijv. `azure_ai`, `anthropic` |
| `system_prompt` | TEXT NOT NULL DEFAULT '' | Volledige systeemprompt |
| `user_prompt` | TEXT NOT NULL DEFAULT '' | Volledige gebruikersprompt |
| `response_text` | TEXT NOT NULL DEFAULT '' | Ruwe tekstrespons van het model |
| `tokens_in` | INTEGER NOT NULL DEFAULT 0 | |
| `tokens_out` | INTEGER NOT NULL DEFAULT 0 | |
| `ok` | BOOLEAN NOT NULL DEFAULT TRUE | `FALSE` als de aanroep een fout opleverde |
| `fout` | TEXT | Nullable; foutomschrijving bij `ok = FALSE` |
| `tijdstip` | TIMESTAMP NOT NULL | |

**Python-models (`api/app/features/llm_log/models.py`):**

- `LlmCallRead` — alle kolommen als Pydantic-velden; `tijdstip: str`, `fout: str | None`

**Endpoints:**

| Endpoint | Methode | Doel | Auth |
|---|---|---|---|
| `/v1/admin/analyses/{slug}/llm-calls` | GET | Vastgelegde LLM-calls van één analyse | beheerder |

**BFF-routes (`frontend/app/api/`):**

| Route | Methode | Doel |
|---|---|---|
| `app/api/admin/analyses/[slug]/llm-calls/route.ts` | GET | Proxy → `/v1/admin/analyses/{slug}/llm-calls` |

## Edge cases

- Analyse bestaat niet (al verwijderd) → lege lijst teruggeven (geen 404, het log is losstaand van de analyse-levenscyclus).
- `capture_llm_calls` is uitgeschakeld → engine schrijft niet; GET geeft een lege lijst terug.
- Schrijffout bij capture → engine logt de fout (`logger.warning`) en vervolgt de analyse; de analyse mag niet mislukken door een log-schrijffout.
- Grote responses (lange prompts, lange outputs) → geen limiet per rij; de tabel gebruikt TEXT-kolommen.
- Gelijktijdige analyses met capture aan → elke call krijgt zijn eigen rij; `analyse_slug` disambigueert.

## Auth / rollen

- `GET /v1/admin/analyses/{slug}/llm-calls` — alleen beheerder (`huidige_beheerder`).
- De engine schrijft intern naar de tabel (geen HTTP-endpoint voor schrijven — alleen de engine schrijft).
- De BFF stuurt de `X-User-Id` mee; de rolcheck staat server-side in `router.py`.

## Gedeelde logica

- `huidige_beheerder` uit `shared/auth.py` — bestaat ✓
- Store (`api/app/features/llm_log/store.py`):
  - `schrijf_call(analyse_slug, activiteit, ronde, poging, fase, model, provider, system_prompt, user_prompt, response_text, tokens_in, tokens_out, ok, fout)` — best-effort INSERT.
  - `lijst_calls(analyse_slug)` → `list[LlmCallRead]`
- `runtime_config.capture_ingeschakeld()` (story 019) — de engine-laag controleert dit voor elke aanroep.
- Engine-integratie (story 012): voeg een `CapturingLlmClient`-decorator of een `_leg_vast()`-hulpfunctie toe die de store aanroept na elke LLM-aanroep wanneer capture ingeschakeld is.

## Implementatienoot

Logica kopiëren en aanpassen vanuit `wetsanalyse-ai/api/app/llm/capture.py` (decorator-patroon: `CapturingLLMClient` omhult elke LLM-aanroep) en `wetsanalyse-ai/api/app/routers/admin.py` (endpoint `lijst_llm_calls`). De call-context (analyse-slug, activiteit, ronde) is beschikbaar in de engine via een contextvar of via parameters. Schrijf de feature als `api/app/features/llm_log/` met een eigen `store.py` en `router.py`.

## UI

- **Uitklapbare sectie op de rapport-pagina** (`/analyse/{id}/rapport`): alleen zichtbaar voor beheerders; toont een tabel met kolommen activiteit, ronde, model, tokens_in, tokens_out, tijdstip; elke rij uitklapbaar voor de prompt en respons-inhoud.
- Alternatief: aparte pagina `/beheer/llm-log/` met een analyse-selector; minder ingrijpend voor de rapport-pagina.
- Mockup-varianten: geen capture (lege sectie met melding "LLM-calls vastleggen is uitgeschakeld"), capture aan met data.

**Gebouwd:** nee
