"""FastAPI-dependencies voor het llm_calls-domein (werkwijze-ADR-0007).

Woont in `llm_calls/` (en niet in projecten's router) zodat een tweede DI-consument
niet via projecten's owner-export hoeft (audit ronde 2, punt 4). Projecten's router
importeert de factory hier; `dependency_overrides` in tests refereren aan hetzelfde
symbool.
"""

from __future__ import annotations

from ...db import get_engine
from .store import SqlAlchemyLlmCallsStore


def get_llm_calls_store() -> SqlAlchemyLlmCallsStore:
    """FastAPI-dependency voor de LLM-calls store."""
    return SqlAlchemyLlmCallsStore(get_engine())
