"""Gedragstests voor de proces-globale concurrency-rem."""

from __future__ import annotations

import asyncio

import pytest

from app.shared.llm import throttle


@pytest.fixture(autouse=True)
def reset_throttle():
    """Elk test-item begint met een lege config."""
    throttle.configure(0)
    yield
    throttle.configure(0)


async def test_niet_geconfigureerd_geen_rem():
    """Zonder configure(): elke `llm_slot()` past direct — geen wachten."""
    async with throttle.llm_slot():
        async with throttle.llm_slot():
            pass


async def test_nul_of_negatief_zet_uit():
    throttle.configure(0)
    assert throttle.is_geconfigureerd() is False
    throttle.configure(-1)
    assert throttle.is_geconfigureerd() is False


async def test_max_concurrency_wordt_gerespecteerd():
    """Bij max=1 draait er nooit meer dan één slot tegelijk."""
    throttle.configure(1)
    tegelijk = 0
    max_gezien = 0

    async def taak():
        nonlocal tegelijk, max_gezien
        async with throttle.llm_slot():
            tegelijk += 1
            max_gezien = max(max_gezien, tegelijk)
            await asyncio.sleep(0.01)
            tegelijk -= 1

    await asyncio.gather(*(taak() for _ in range(5)))
    assert max_gezien == 1


async def test_max_concurrency_twee_slots():
    """Bij max=2 kunnen er twee tegelijk draaien, nooit meer."""
    throttle.configure(2)
    tegelijk = 0
    max_gezien = 0

    async def taak():
        nonlocal tegelijk, max_gezien
        async with throttle.llm_slot():
            tegelijk += 1
            max_gezien = max(max_gezien, tegelijk)
            await asyncio.sleep(0.01)
            tegelijk -= 1

    await asyncio.gather(*(taak() for _ in range(6)))
    assert max_gezien == 2
