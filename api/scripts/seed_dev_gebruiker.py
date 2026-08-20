"""Seed een dev-beheerder in de database — gebruikt door CI (frontend-ci) en lokale setup."""

from __future__ import annotations

import asyncio

from app.db import get_engine
from app.features.identiteit_toegang.store import maak_gebruiker_indien_ontbreekt


async def _main() -> None:
    await maak_gebruiker_indien_ontbreekt(get_engine(), "beheerder", "beheerder123", "beheerder")


if __name__ == "__main__":
    asyncio.run(_main())
