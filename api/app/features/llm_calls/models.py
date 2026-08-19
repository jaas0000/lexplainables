"""De ene bron voor het llm_calls-domein (werkwijze-ADR-0011).

Eén entiteit: `llm_calls` — vastgelegd LLM-verkeer per analyse (capture-toggle,
migratie 0009). De engine schrijft (best-effort capture), de projecten-router leest
via `GET /v1/projecten/{id}/llm-calls`.

Wonen als eigen feature (audit ronde 2, punt 4): engine + projecten + toekomstige
consumenten importeren hier zonder over projecten's owner-export te gaan.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import (
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

llm_calls = Table(
    "llm_calls",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("analyse_id", String(36), nullable=False),
    Column("activiteit", String(32), nullable=False),
    Column("bron_id", String(32), nullable=True),
    Column("system_prompt", Text, nullable=False),
    Column("user_prompt", Text, nullable=False),
    Column("ruwe_respons", Text, nullable=False),
    Column("model", String(128), nullable=False),
    Column("tokens_in", Integer, nullable=False),
    Column("tokens_out", Integer, nullable=False),
    Column("aangemaakt", DateTime(timezone=True), nullable=False),
    Index("ix_llm_calls_analyse_id", "analyse_id"),
)


class LlmCallRead(BaseModel):
    """Vastgelegde LLM-aanroep, leesbaar via GET /v1/projecten/{id}/llm-calls."""

    id: int
    analyse_id: str
    activiteit: str
    bron_id: str | None
    system_prompt: str
    user_prompt: str
    ruwe_respons: str
    model: str
    tokens_in: int
    tokens_out: int
    aangemaakt: datetime
