# Story 053 — graph-qa: HTTP-laag (`POST /v1/chat`)

## Verhaal

Als aanroeper (een script, een toekomstige frontend-BFF) wil ik een vraag over een HTTP-endpoint
kunnen stellen en het SSE-event-contract terugkrijgen, zonder zelf een Python-proces te starten
dat `answer_stream()` importeert.

## Aanleiding

Eerste story van de HTTP-laag — de rest van de agent (checkpointer/streaming/stop_check, stories
050-052) staat, maar `tools/graph-qa/api/` is nog een leeg skelet. Bewust **smal**: alleen
`GET /health` + `POST /v1/chat` (SSE, gekoppeld aan de verbinding — geen runs-model). De
referentie se `api/main.py` bundelt hier veel meer bij (CORS, rate-limiting, het runs-model,
`/v1/artikel`, `/v1/conversations/{id}` delete, observability) — allemaal expliciet ontbundeld,
zie §Afwijkingen. Dit is ook de eerste story met een **echte aanroeper** voor `stop_check`
(story 052): dat blijft hier nog steeds ongebruikt (`/v1/chat` geeft 'm niet door), want zonder
het runs-model is er niets dat een stop-vlag kán zetten — een latere story sluit dat pas aan.

## lexplainables-specifieke afwijkingen

1. **Geen CORS-middleware.** De referentie staat de browser toe rechtstreeks met graph-qa te
   praten (de werkplek praat direct via SSE). lexplainables' `frontend/` volgt tot nu toe overal
   het BFF-patroon (Next.js-server-routes proxyen naar `api`, nooit rechtstreeks browser→backend)
   — of `frontend-chat` straks hetzelfde doet is nog niet besloten. CORS toevoegen zonder een
   vastgestelde consument zou gokken zijn naar een origin-lijst die niemand gebruikt. Komt terug
   zodra `frontend-chat` bestaat en de keuze (BFF vs. direct) gemaakt is.
2. **Geen rate-limiting.** Dezelfde reden als CORS: de referentie se rate-limit-sleutel
   (`X-User-Id`, gezet door de BFF) veronderstelt een aanroeper-architectuur die hier nog niet
   vastligt. Geen productierisico op dit moment (geen consument, geen internetblootstelling).
3. **Geen runs-model (`POST /v1/runs`/`/cancel`/`/events`), geen `agent/beurt.py`-persistentie,
   geen `DELETE /v1/conversations/{id}`, geen `GET /v1/artikel`.** Elk daarvan is een eigen,
   latere story — zie ook story 051 §Afwijkingen punt 3 en story 052 §Afwijkingen. `/v1/chat`
   blijft de simpele, aan-de-verbinding-gekoppelde vorm (zoals de referentie 'm oorspronkelijk
   ook had, vóórdat het runs-model erbij kwam).
4. **Geen observability/OTel-instrumentatie op de app.** Nog geen OTel-stack in lexplainables
   (zie story 051 §Afwijkingen punt 2) — de lifespan doet alleen de fail-fast configuratiecheck,
   geen `observability.setup()`/`instrument_fastapi()`.
5. **Auth: `QA_API_TOKEN` (optioneel bearer-token, timing-safe vergeleken)** — 1:1 met de
   referentie, want dit is de enige beveiligingslaag die nu al zinvol is zonder een vastgestelde
   aanroeper-architectuur (CORS/rate-limit hierboven wél uitgesteld, auth niet: een onbeveiligd
   endpoint dat de LLM- en graafkosten opent is een reëel risico, ook zonder consument).
6. **Lifespan faalt fail-fast op zowel `require_graph()` als `require_llm()`.** De referentie
   faalt hier alleen op de graaf (plus een eigen `require_api()` die hier niet bestaat, want er is
   geen `agent/beurt.py`). Zonder een geldige LLM-configuratie kan `/v1/chat` sowieso nooit iets
   zinnigs teruggeven, dus dezelfde fail-fast-logica geldt hier voor allebei.
7. **`ChatRequest`** (nieuw in `agent/models.py`, was expliciet uitgesloten in stories 044-048)
   heeft alleen `question`/`conversation_id` — geen `modus`/`context`/`doel`, want die bestaan nog
   niet in `answer_stream()` (zie story 050 §Afwijkingen punt 3, story 051 §Afwijkingen punt 6).
8. **`GroundingEvent`-pariteit.** `answer_stream()`'s grounding-event kreeg tot nu toe alleen
   `grounded`/`niveau`/`unsupported`; de al bestaande (nog ongebruikte) `GroundingEvent`-klasse in
   `agent/models.py` heeft ook `cited`/`niet_letterlijk`. Nu er een echte HTTP-consument komt, is
   dat een reële omissie (niet nieuwe scope) — `answer_stream()` levert vanaf deze story alle
   velden.
9. **Geen Pydantic-validatie van de SSE-events zelf.** De al bestaande `TokenEvent`/`SourcesEvent`/
   `GroundingEvent`/`DoneEvent`/`ErrorEvent`-klassen in `agent/models.py` blijven gedocumenteerd
   contract, geen runtime-stap: `/v1/chat` serialiseert `answer_stream()`'s dicts rechtstreeks
   (`json.dumps`), zoals de referentie ook doet — een dict-vorm die al door 231 tests bewaakt
   wordt, een dubbele validatielaag zou geen nieuw risico afdekken.

## Wijzigingen

- `tools/graph-qa/pyproject.toml` — `fastapi`, `uvicorn[standard]`, `sse-starlette` toegevoegd
  (zelfde ondergrenzen als `api/pyproject.toml` waar van toepassing).
- `agent/config.py` — `qa_api_token: str | None = None` (env `QA_API_TOKEN`/`QA_API_TOKEN_FILE`,
  via `_read_secret`).
- `agent/models.py` — nieuw `ChatRequest` (§Afwijkingen punt 7); docstring bijgewerkt.
- `agent/agent.py` — het grounding-event krijgt `cited`/`niet_letterlijk` (§Afwijkingen punt 8).
- `tools/graph-qa/api/main.py` (nieuw, was leeg skelet):
  - `_lifespan`: `settings.require_graph()` + `settings.require_llm()`, fail-fast bij boot.
  - `GET /health` → `{"status": "ok"}`.
  - `POST /v1/chat`: body `ChatRequest`, providers via `Depends(_llm_dependency)`/
    `Depends(_graph_dependency)` (zodat tests fakes kunnen injecteren via
    `app.dependency_overrides`), auth via `Depends(_check_auth)`. Retourneert een
    `EventSourceResponse` die `answer_stream(...)` doorgeeft.
  - `_check_auth`: timing-safe bearer-check tegen `settings.qa_api_token`; open (geen check) als
    die niet gezet is.

## Acceptatiecriteria

- [x] `GET /health` → 200, `{"status": "ok"}`.
- [x] `POST /v1/chat` met een geldige vraag levert een SSE-stream met `token`/`sources`/
      `grounding`/`done`-events, geserialiseerd als JSON per regel.
- [x] Zonder `QA_API_TOKEN` geconfigureerd: `/v1/chat` accepteert verzoeken zonder Authorization-
      header.
- [x] Met `QA_API_TOKEN` geconfigureerd: een ontbrekend of onjuist token geeft 401; het juiste
      token (timing-safe vergeleken) laat het verzoek door.
- [x] De lifespan weigert te starten zonder geldige graaf- of LLM-configuratie
      (`with TestClient(app):`).
- [x] Bestaande 231 tests blijven groen zonder aanpassing.

## Buiten scope

CORS, rate-limiting, het runs-model, `agent/beurt.py`-persistentie, `DELETE
/v1/conversations/{id}`, `GET /v1/artikel`, observability/OTel-instrumentatie op de app. Zie
§Afwijkingen per punt.

## Prioriteit / story points

Prioriteit: **high**. Story points: **3** (één nieuw endpoint-bestand met auth + lifespan, een
kleine config-uitbreiding, een nieuw request-model, een kleine event-contract-aanvulling — geen
graaf-topologiewijziging).

## Verificatie

- `pytest -q -m "not integration"`: 236 passed (231 bestaand + 5 nieuw in `tests/test_api.py`,
  geen enkele bestaande test aangepast).
- `ruff check . && ruff format --check .`: schoon (nieuwe `per-file-ignores`-regel voor `B008` op
  `api/main.py` — FastAPI's `Depends()`-in-default is het idiomatische patroon, zelfde aanpak als
  `api/pyproject.toml`).
- `pytest -q -m integration`: ongewijzigd (deze story raakt de agent-laag niet, alleen een nieuwe
  HTTP-laag erbovenop).
- Live: `uvicorn api.main:app` gestart tegen de echte GraphDB + Foundry, `curl -N -X POST
  /v1/chat` met "Wat is een belastingschuldige volgens de Invorderingswet 1990?" — echte
  token-events, een gevulde `sources`-lijst, `grounding.niveau == "gegrond"`, `done`. `GET
  /health` → 200.

## Gebouwd:

Ja (PR #91).
