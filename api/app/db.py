"""Dunne, gedeelde database-laag (stack-profiel.md §Dunne verzamelaars, werkwijze-ADR-0001).

Bevat alleen de async engine — geen tabeldefinities. Die horen bij de feature zelf (zie
app/features/feedback/models.py, werkwijze-ADR-0011). Schema-opbouw loopt via Alembic
(werkwijze-ADR-0005, zie ../alembic/), niet via een create_all()-aanroep hier.
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./wetsanalyse.db")

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Geef de proces-brede engine terug, lazily aangemaakt.

    Features krijgen deze engine binnen via hun eigen store (werkwijze-ADR-0007) — dit
    bestand kent geen feature-specifieke code. Tests overschrijven de store-dependency van de
    router met een eigen, kortlevende engine in plaats van deze functie aan te passen (zie
    features/feedback/tests/conftest.py).
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, echo=False)
    return _engine
