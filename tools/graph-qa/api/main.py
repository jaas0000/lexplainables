"""FastAPI-backend voor de graph-qa agent (werkwijze-story 053, eerste HTTP-story).

Endpoint: `POST /v1/chat` — body `ChatRequest` (`question`, `conversation_id?`), response een SSE-
stroom van `answer_stream()`'s events (`token`/`sources`/`grounding`/`conversation_id`/`done`/
`error`), rechtstreeks als JSON geserialiseerd (`json.dumps`) — geen tweede Pydantic-validatiestap,
zie `docs/project/stories/053-graph-qa-http-chat.md` §Afwijkingen punt 9.

Bewust smal: geen CORS, geen rate-limiting, geen runs-model, geen `/v1/artikel`, geen
`DELETE /v1/conversations/{id}`, geen observability-instrumentatie — zie die story se §Afwijkingen
voor de reden per punt. Auth: optioneel bearer-token (`QA_API_TOKEN`, timing-safe vergeleken) —
open als niet geconfigureerd.
"""

from __future__ import annotations

import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sse_starlette.sse import EventSourceResponse

from agent.agent import answer_stream
from agent.config import Settings
from agent.models import ChatRequest
from agent.ports import GraphPort, LLMPort

settings = Settings.from_env()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Fail-fast bij boot: zonder geldige graaf- of LLM-configuratie kan /v1/chat sowieso nooit iets
    # zinnigs teruggeven — liever een container die niet opstart dan een die pas per verzoek faalt.
    settings.require_graph()
    settings.require_llm()
    yield


app = FastAPI(title="Graph QA Agent", version="0.1.0", lifespan=_lifespan)

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
