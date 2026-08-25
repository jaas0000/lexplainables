# Chat-proxy naar graph-qa

`POST /v1/chat` streamt graph-qa's eigen SSE-antwoord (token/sources/grounding/done/error) ongewijzigd door naar de aanroeper.

**Waarom apart:** de architectuur (ADR-0001, C4-model) laat `frontend-chat` niet rechtstreeks met `graph-qa` praten — alle verkeer loopt via `api`, zodat de bestaande auth-/CORS-grens van het platform intact blijft.

**Grens:** geen transformatie van het event-contract, geen eigen state, geen conversatie- geschiedenis (die woont in graph-qa's eigen checkpointer). Alleen een verbindingsfout met graph-qa zelf krijgt hier een eigen `error`-event.

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `POST` | `/chat` | beheerder | — |

## Interacties

- shared/auth.py: `huidige_beheerder` voor auth, zelfde patroon als elke andere geauthenticeerde route.
- graph-qa (`tools/graph-qa/api/main.py`, extern proces): `GRAPH_QA_URL`, `POST /v1/chat`.

## Getest gedrag

- Zonder auth geeft 401.
- Events worden ongewijzigd doorgegeven.
- Onbereikbare graph qa geeft error event geen 500.

## Beslissingen

- Story 055: route via `api` (niet rechtstreeks `frontend-chat → graph-qa`), zoals ADR-0001/C4-model/stack-profiel al vastleggen.
