"""Proces-globale concurrency-rem op LLM-calls.

Een `asyncio.Semaphore` begrenst hoeveel LLM-calls er TEGELIJK lopen in dit proces. Zonder rem
kan een zwerm gelijktijdige analyses samen tegen provider-quota knallen → 429-storm. Per proces
(in-process); bij >1 replica schaalt de effectieve grens met het aantal replicas.

De semafoor wordt in `main.py` `lifespan` geconfigureerd (uit env `LLM_MAX_CONCURRENCY`). Tests
mogen 'm direct herconfigureren.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

_sem: asyncio.Semaphore | None = None


def configure(max_concurrency: int) -> None:
    """(Her)initialiseer de globale semafoor. <= 0 schakelt de rem uit (yield direct)."""
    global _sem
    _sem = asyncio.Semaphore(max_concurrency) if max_concurrency and max_concurrency > 0 else None


def is_geconfigureerd() -> bool:
    """Voor tests: is er een actieve rem?"""
    return _sem is not None


@asynccontextmanager
async def llm_slot():
    """Reserveer één concurrency-slot voor de duur van een LLM-completion.

    Zonder geconfigureerde rem: no-op (yield direct). Anders: wacht tot een slot vrijkomt.
    """
    if _sem is None:
        yield
        return
    async with _sem:
        yield
