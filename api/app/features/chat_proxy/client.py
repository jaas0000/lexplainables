"""Streamt `POST /v1/chat` van graph-qa door naar de aanroeper, event voor event.

Geen transformatie van het contract — elk JSON-event dat graph-qa produceert
(`token`/`sources`/`grounding`/`conversation_id`/`done`/`error`) gaat ongewijzigd door. Alleen een
verbindingsfout met graph-qa zelf krijgt hier een eigen `error`-event (zie `stream_chat`), zodat de
aanroeper niet apart hoeft te weten of een fout van de agent kwam of van deze proxy-laag.

Zelfde patroon als `shared/wettenbank.py`: een proces-brede lazy `httpx.AsyncClient`-singleton,
geen nieuwe client per verzoek.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

GRAPH_QA_URL = os.environ.get("GRAPH_QA_URL", "http://localhost:8099")
_TIMEOUT = 120.0

logger = logging.getLogger("app.chat_proxy")

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=_TIMEOUT)
    return _client


async def stream_chat(question: str, conversation_id: str | None) -> AsyncIterator[dict[str, Any]]:
    """Stream de SSE-events van graph-qa's `/v1/chat` door, ongewijzigd."""
    body = {"question": question, "conversation_id": conversation_id}
    try:
        async with _get_client().stream("POST", f"{GRAPH_QA_URL}/v1/chat", json=body) as response:
            async for regel in response.aiter_lines():
                if not regel.startswith("data:"):
                    continue
                payload = regel[len("data:") :].strip()
                if not payload:
                    continue
                try:
                    yield json.loads(payload)
                except json.JSONDecodeError:
                    logger.warning("onleesbaar SSE-event van graph-qa overgeslagen")
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError):
        logger.warning("graph-qa niet bereikbaar", exc_info=True)
        yield {
            "type": "error",
            "message": "Kon Lex niet bereiken. Probeer het opnieuw.",
        }
