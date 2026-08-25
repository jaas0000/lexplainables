"""Routelaag voor de chat-proxy (story 055): `POST /v1/chat` naar graph-qa.

Elke request vereist authenticatie via `huidige_beheerder` — zelfde patroon als elke andere
geauthenticeerde route in deze service (API_TOKEN + X-User-Id-header vanuit de BFF).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from ...shared.auth import GebruikerContext, huidige_beheerder
from .client import stream_chat
from .models import ChatRequest

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(
    body: ChatRequest,
    _gebruiker: GebruikerContext = Depends(huidige_beheerder),
) -> EventSourceResponse:
    async def event_generator() -> AsyncIterator[dict]:
        async for event in stream_chat(body.question, body.conversation_id):
            yield {"data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(event_generator())
