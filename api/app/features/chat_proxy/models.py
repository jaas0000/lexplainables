"""Pydantic-modellen voor de chat-proxy (story 055, uitgebreid voor annotatiebeurten).

Geen gedeelde package met `tools/graph-qa` (ADR-0002) — `ChatRequest` is hier een eigen, kleine
kopie van dezelfde vorm als graph-qa's `agent/models.py::ChatRequest`.
"""

from __future__ import annotations

from pydantic import BaseModel


class AgentDoel(BaseModel):
    bwbId: str
    artikel: str
    lid: str = ""


class ChatRequest(BaseModel):
    question: str = ""
    conversation_id: str | None = None
    doel: AgentDoel | None = None
    werkgebied: str | None = None
