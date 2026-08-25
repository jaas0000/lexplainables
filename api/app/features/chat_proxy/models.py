"""Pydantic-modellen voor de chat-proxy (story 055).

Geen gedeelde package met `tools/graph-qa` (ADR-0002) — `ChatRequest` is hier een eigen, kleine
kopie van dezelfde vorm als graph-qa's `agent/models.py::ChatRequest`.
"""

from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None
