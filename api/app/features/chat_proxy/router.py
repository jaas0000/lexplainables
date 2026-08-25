"""Routelaag voor de chat-proxy (story 055): `POST /v1/chat` naar graph-qa.

Elke request vereist authenticatie via `huidige_beheerder` — zelfde patroon als elke andere
geauthenticeerde route in deze service (API_TOKEN + X-User-Id-header vanuit de BFF). Elke
aanroep triggert een echte LLM- + GraphDB-beurt bij graph-qa — een misbruik-rem per gebruiker
is hier dus op zijn plaats, zelfde `probeer_toestaan`-patroon als de login-rem in
`identiteit_toegang/router.py`. Geen globale/gedeelde factor nodig zoals bij login (dit is geen
password-spraying-dreiging over meerdere userids): elke aanvrager is hier al geauthenticeerd,
dus een per-gebruiker-limiet volstaat.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from sse_starlette.sse import EventSourceResponse

from ...shared.auth import GebruikerContext, huidige_beheerder
from ...shared.rate_limit import probeer_toestaan
from .client import stream_chat
from .models import ChatRequest

router = APIRouter(tags=["chat"])

_CHAT_MAX = int(os.environ.get("CHAT_RATE_LIMIT_MAX", "30"))
_CHAT_WINDOW = float(os.environ.get("CHAT_RATE_LIMIT_WINDOW_S", "60"))


@router.post("/chat")
async def chat(
    body: ChatRequest,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
) -> EventSourceResponse:
    if not probeer_toestaan(f"chat:{gebruiker.gebruikersnaam}", _CHAT_MAX, _CHAT_WINDOW):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Te veel chatverzoeken; probeer later opnieuw.",
            headers={"Retry-After": str(int(_CHAT_WINDOW))},
        )

    async def event_generator() -> AsyncIterator[dict]:
        async for event in stream_chat(
            body.model_dump(exclude_none=True), gebruiker.gebruikersnaam
        ):
            yield {"data": json.dumps(event, ensure_ascii=False)}

    return EventSourceResponse(event_generator())
