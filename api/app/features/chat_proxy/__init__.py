"""Chat-proxy naar graph-qa.

Wat: `POST /v1/chat` streamt graph-qa's eigen SSE-antwoord (token/sources/grounding/done/error)
ongewijzigd door naar de aanroeper.
Waarom: de architectuur (ADR-0001, C4-model) laat `frontend-chat` niet rechtstreeks met
`graph-qa` praten — alle verkeer loopt via `api`, zodat de bestaande auth-/CORS-grens van het
platform intact blijft.
Grens: geen transformatie van het event-contract, geen eigen state, geen conversatie-
geschiedenis (die woont in graph-qa's eigen checkpointer). Alleen een verbindingsfout met
graph-qa zelf krijgt hier een eigen `error`-event.

Tabellen:
  - geen: stateless doorgeefluik, geen eigen opslag (zie `client.py`).

Beslissingen:
  - Story 055: route via `api` (niet rechtstreeks `frontend-chat → graph-qa`), zoals
    ADR-0001/C4-model/stack-profiel al vastleggen.

Interacties:
  - shared/auth.py: `huidige_beheerder` voor auth, zelfde patroon als elke andere
    geauthenticeerde route.
  - graph-qa (`tools/graph-qa/api/main.py`, extern proces): `GRAPH_QA_URL`, `POST /v1/chat`.
"""
