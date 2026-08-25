"""FastAPI-backend voor de graph-qa agent (werkwijze-stories 053-054).

`POST /v1/chat` — body `ChatRequest` (`question`, `conversation_id?`), response een SSE-stroom van
`answer_stream()`'s events, rechtstreeks als JSON geserialiseerd (`json.dumps`) — geen tweede
Pydantic-validatiestap, zie `docs/project/stories/053-graph-qa-http-chat.md` §Afwijkingen punt 9.
Gekoppeld aan de verbinding — voor scripts/evals die geen run-model nodig hebben.

Story 054 voegt het **run-model** toe (`agent/runs.py`): een beurt draait als achtergrondtaak, een
client kijkt mee en kan opnieuw aanhaken. `POST /v1/runs` start, `GET /v1/runs/{id}/events` volgt,
`POST /v1/runs/{id}/cancel` vraagt te stoppen (via `stop_check`/`BeurtGestopt`, story 052), `GET
/v1/conversations/{id}/run` geeft de aanhaakbare run. Eigenaarschap via `X-User-Id` (leeg = open).

Bewust smal: geen CORS, geen rate-limiting, geen `agent/beurt.py`-persistentie, geen
`/v1/artikel`, geen `DELETE /v1/conversations/{id}`, geen observability-instrumentatie — zie
`docs/project/stories/053-graph-qa-http-chat.md` en `054-graph-qa-runs-model.md` §Afwijkingen.
Auth: optioneel bearer-token (`QA_API_TOKEN`, timing-safe vergeleken) — open als niet
geconfigureerd.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sse_starlette.sse import EventSourceResponse

from agent.agent import answer_stream
from agent.config import Settings
from agent.models import ChatRequest, RunStart
from agent.ports import GraphPort, LLMPort
from agent.runs import Run, RunBestaatAl, RunRegister

settings = Settings.from_env()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Fail-fast bij boot: zonder geldige graaf- of LLM-configuratie kan /v1/chat sowieso nooit iets
    # zinnigs teruggeven — liever een container die niet opstart dan een die pas per verzoek faalt.
    settings.require_graph()
    settings.require_llm()
    yield


app = FastAPI(title="Graph QA Agent", version="0.1.0", lifespan=_lifespan)

# Het run-register: een beurt leeft hier, niet in de HTTP-request van één client. Zie agent/runs.py
# voor de aannames (één proces, herstart wist het register, alleen de run-taak schrijft).
runs = RunRegister()

_bearer = HTTPBearer(auto_error=False)


def _check_auth(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> None:
    expected = settings.qa_api_token
    if not expected:
        return  # geen token geconfigureerd → open (lokale dev)
    provided = creds.credentials if creds else ""
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ongeldig of ontbrekend token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _llm_dependency() -> LLMPort:
    from agent.adapters.anthropic_llm import AnthropicLLM

    return AnthropicLLM(settings)


def _graph_dependency() -> GraphPort:
    from agent.adapters.graphdb_graph import make_graph

    return make_graph(settings)


def _aanroeper(request: Request) -> str:
    """Namens wie dit verzoek komt (`X-User-Id`). Leeg = geen eigenaar (open dev-gedrag) —
    lexplainables heeft nog geen frontend-chat/BFF die deze header zet."""
    return request.headers.get("x-user-id", "")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat")
async def chat(
    body: ChatRequest,
    llm: LLMPort = Depends(_llm_dependency),
    graph: GraphPort = Depends(_graph_dependency),
    _auth: None = Depends(_check_auth),
) -> EventSourceResponse:
    """Eén beurt, gekoppeld aan déze verbinding — geen runs-model (zie module-docstring)."""

    async def event_generator() -> AsyncIterator[dict]:
        async for event in answer_stream(
            body.question, body.conversation_id, settings=settings, llm=llm, graph=graph
        ):
            yield {"data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(event_generator())


# --- Runs: de beurt is van de server, niet van de verbinding (story 054) ----------------------


def _stroom_voor(body: ChatRequest, llm: LLMPort, graph: GraphPort):
    """De eventstroom van één run — `answer_stream()` met `stop_check` gekoppeld aan de run's
    stopvlag, zodat `POST /v1/runs/{id}/cancel` 'm daadwerkelijk kan laten stoppen."""

    def maak(run: Run) -> AsyncIterator[dict]:
        return answer_stream(
            body.question,
            body.conversation_id,
            settings=settings,
            llm=llm,
            graph=graph,
            stop_check=lambda: run.stop_gevraagd,
        )

    return maak


@app.post("/v1/runs", status_code=status.HTTP_201_CREATED)
async def start_run(
    body: ChatRequest,
    llm: LLMPort = Depends(_llm_dependency),
    graph: GraphPort = Depends(_graph_dependency),
    gebruiker: str = Depends(_aanroeper),
    _auth: None = Depends(_check_auth),
) -> RunStart:
    """Start een beurt als achtergrondtaak en geef het run_id terug.

    409 als er al een run voor dit gesprek loopt — geen nettigheid maar bescherming:
    `thread_id == conversation_id`, dus twee gelijktijdige lussen schrijven door elkaar heen in
    dezelfde checkpointer-thread. De aanroeper hoort dan aan te haken bij het meegegeven run_id.
    """
    try:
        run = runs.start(
            conversation_id=body.conversation_id or "",
            vraag=body.question or "",
            maak_stroom=_stroom_voor(body, llm, graph),
            user_id=gebruiker,
        )
    except RunBestaatAl as al:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reden": "run_loopt_al", "run_id": al.run_id},
        ) from al
    return RunStart(**run.samenvatting())


@app.get("/v1/runs/{run_id}/events")
async def run_events(
    run_id: str,
    vanaf: int = 0,
    gebruiker: str = Depends(_aanroeper),
    _auth: None = Depends(_check_auth),
) -> EventSourceResponse:
    """Kijk mee met een run: eerst wat je miste (vanaf `vanaf`), dan live.

    Bewust **geen** rate-limit: opnieuw aanhaken na een remount mag nooit op een limiet
    stuklopen. Losraken van deze stream laat de run ongemoeid.
    """
    run = runs.get(run_id, user_id=gebruiker)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onbekende run")

    async def event_generator() -> AsyncIterator[dict]:
        async for event in runs.volg(run, vanaf):
            yield {"data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(event_generator())


@app.post("/v1/runs/{run_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def stop_run(
    run_id: str,
    gebruiker: str = Depends(_aanroeper),
    _auth: None = Depends(_check_auth),
) -> RunStart:
    """Vraag een run te stoppen. 202, niet 204: stoppen is een verzoek, geen feit — de nodes zijn
    synchroon, dus een lopende LLM-call maakt zichzelf af en de run eindigt op de eerstvolgende
    nodegrens."""
    run = runs.get(run_id, user_id=gebruiker)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onbekende run")
    runs.vraag_stop(run)
    return RunStart(**run.samenvatting())


@app.get("/v1/conversations/{conversation_id}/run")
async def actieve_run(
    conversation_id: str,
    gebruiker: str = Depends(_aanroeper),
    _auth: None = Depends(_check_auth),
) -> RunStart | None:
    """De run van dit gesprek waar je op kunt aanhaken, of niets."""
    run = runs.actief_voor(conversation_id, user_id=gebruiker)
    return RunStart(**run.samenvatting()) if run else None
