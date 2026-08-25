# Story 055 — api: chat-proxy naar graph-qa

## Verhaal

Als jurist wil ik via de webapp een vraag aan Lex (graph-qa) kunnen stellen, zonder dat de
browser rechtstreeks met de agent-service hoeft te praten — zodat de bestaande auth-,
CORS- en netwerkgrenzen van het platform (frontend praat alleen met `api`) intact blijven.

## Aanleiding

Eerste story die `api` en `graph-qa` daadwerkelijk aan elkaar knoopt. De architectuur ligt al
vast (ADR-0001, `docs/project/architectuur/c4-model.md`, `docs/project/architectuur/stack-profiel.md`
§Topologie): `frontend-chat → api → graph-qa`, niet rechtstreeks. Deze story bouwt de middelste
schakel. Geen poort van de wetsanalyse-ai-referentie (die heeft geen tussenliggende `api`-laag
voor de chat — de werkplek praat daar rechtstreeks met graph-qa) maar nieuwe architectuur
specifiek voor lexplainables' topologie-keuze.

## Schemabeslissing

- Request: `{"question": str, "conversation_id": str | None}` — zelfde vorm als graph-qa's eigen
  `ChatRequest` (`tools/graph-qa/agent/models.py`), hier apart gedefinieerd (geen gedeelde
  package tussen de twee services, ADR-0002).
- Response: `text/event-stream`, elke regel het ongewijzigde JSON-event dat graph-qa zelf al
  produceert (`token`/`sources`/`grounding`/`conversation_id`/`done`/`error`) — deze laag
  transformeert het contract niet, hij geeft het door.
- Geen eigen `error`-vertaling bovenop graph-qa's eigen `_foutmelding`, behalve bij een verbindings-
  fout met graph-qa zelf (zie §Wijzigingen) — dat is een fout van déze laag, niet van de agent.

## Wijzigingen

- `api/pyproject.toml` — `sse-starlette` toegevoegd (al gebruikt in `tools/graph-qa`).
- `api/app/features/chat_proxy/` (nieuwe feature-map, feature-bouwen regel 2):
  - `models.py` — `ChatRequest` (`question: str`, `conversation_id: str | None`).
  - `client.py` — `GRAPH_QA_URL` (env-constante, default `http://localhost:8099`, patroon van
    `shared/wettenbank.py`'s `WETTENBANK_MCP_URL`), lazy `httpx.AsyncClient`-singleton,
    `stream_chat(question, conversation_id) -> AsyncIterator[dict]`: doet
    `client.stream("POST", f"{GRAPH_QA_URL}/v1/chat", json=body)`, itereert de SSE-regels
    (`data: ...`) en yieldt het geparste JSON-event. Bij een netwerk-/verbindingsfout: één
    `{"type": "error", "message": "Kon Lex niet bereiken. Probeer het opnieuw."}`-event i.p.v.
    een kale 500 — de aanroeper (frontend-chat) hoeft dan geen apart foutpad voor "de proxy zelf
    faalde" te bouwen, hij ziet gewoon een `error`-event zoals bij elke andere agent-fout.
  - `router.py` — `POST /v1/chat`, `Depends(huidige_beheerder)` (bestaand auth-patroon,
    zelfde als elke andere geauthenticeerde route in deze service), retourneert een
    `EventSourceResponse` om `stream_chat(...)`.
- `api/app/main.py` — import + `app.include_router(chat_proxy_router, prefix="/v1")`.

## Acceptatiecriteria

- [x] `POST /v1/chat` zonder `Authorization`/`X-User-Id` → 401 (bestaand `huidige_beheerder`-
      gedrag, niet apart heruitgevonden).
- [x] Een geldig verzoek streamt de events van een (gemockte) graph-qa-respons ongewijzigd door,
      inclusief `token`/`sources`/`grounding`/`done`.
- [x] Een onbereikbare graph-qa (verbindingsfout) levert één `error`-event op, geen 500.
- [x] Live: een echt verzoek door de proxy heen tegen de daadwerkelijk draaiende graph-qa-
      dev-server levert een compleet, gegrond antwoord op — bewijst dat de hele keten
      (`api` → `graph-qa` → GraphDB + Foundry) werkt, niet alleen de gemockte eenheidstests.
- [x] Bestaande `api`-tests blijven groen zonder aanpassing (de 192 pre-existing errors/failures
      zijn onafhankelijk van deze wijziging — bevestigd door dezelfde run op `master` zonder deze
      wijziging: identiek patroon, veroorzaakt door het ontbreken van een lokale Postgres-server
      in deze sandbox, niet door `chat_proxy`).

## Buiten scope

CORS/rate-limiting op deze route (bestaand `api`-CORS-beleid blijft ongewijzigd van toepassing,
geen aparte regel voor deze route), het runs-model (deze route blijft aan de verbinding gekoppeld,
zoals graph-qa's eigen `/v1/chat`), `GRAPH_QA_URL` in `deploy/`/docker-compose (er bestaat nog
geen Dockerfile voor graph-qa — bekend vervolgpunt).

## Prioriteit / story points

Prioriteit: **high**. Story points: **3** (nieuwe feature-map, één endpoint, een SSE-doorgeef-
laag zonder eigen state — geen database, geen nieuw datamodel dat blijft bestaan).

## Verificatie

- `uv run pytest -q app/features/chat_proxy/`: 3 passed.
- `uv run pytest -q` (hele service): 192 errors/4 failed zijn pre-existing en identiek op
  `master` zonder deze wijziging (geen lokale Postgres beschikbaar in deze sandbox, ADR-0003)
  — niets daarvan raakt `chat_proxy`.
- `ruff check . && ruff format --check .`: schoon (geen nieuwe `per-file-ignores` nodig —
  `**/router.py` had `B008` al project-breed genegeerd).
- Live: `uvicorn app.main:app` lokaal (met `API_TOKEN`/`GRAPH_QA_URL` naar de draaiende
  graph-qa-dev-server) — een curl-verzoek met een geldig token + `X-User-Id` gaf een compleet,
  gegrond antwoord (token-events, sources, `grounding.niveau == "gegrond"`, `done`); zonder token
  → 401.

## Gebouwd:

Ja (PR #93).
