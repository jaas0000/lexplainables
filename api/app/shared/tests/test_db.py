"""Unit-tests voor `app.shared.db` (`upsert`).

Draait tegen de Postgres-testserver (ADR-0003, Postgres-only). De helper produceert altijd
`pg_insert` — een echte engine bewijst het pad end-to-end (insert, update-bij-conflict,
`.returning(...)`-chaining).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import Column, Integer, MetaData, String, Table, select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.shared.db import upsert
from conftest import maak_test_engine, sync_engine_voor


@pytest.fixture
def tabel() -> Table:
    """Kleine tabel met een unique key (`sleutel`) voor conflict-tests."""
    meta = MetaData()
    return Table(
        "shared_db_test",
        meta,
        Column("sleutel", String, primary_key=True),
        Column("waarde", String, nullable=False),
        Column("teller", Integer, nullable=False, server_default="0"),
    )


@pytest_asyncio.fixture
async def engine(tabel: Table, tmp_path) -> AsyncIterator[AsyncEngine]:
    """Postgres-async-engine met alleen de test-tabel."""
    async_engine = maak_test_engine(tabel.metadata, tmp_path=tmp_path)
    try:
        yield async_engine
    finally:
        await async_engine.dispose()


def _sync_execute(async_engine: AsyncEngine, stmt) -> list:
    """Run een statement synchroon op dezelfde DB — voor de blocking test-body."""
    sync = sync_engine_voor(async_engine)
    with sync.begin() as conn:
        result = conn.execute(stmt)
        rijen = result.fetchall() if result.returns_rows else []
    sync.dispose()
    return rijen


def test_upsert_insert_do_nothing_bij_conflict(engine: AsyncEngine, tabel):
    """`update_cols=None` → tweede insert doet niets, eerste waarde blijft staan."""
    sync = sync_engine_voor(engine)
    with sync.begin() as conn:
        conn.execute(upsert(tabel, {"sleutel": "s", "waarde": "eerst"}, ["sleutel"]))
        conn.execute(upsert(tabel, {"sleutel": "s", "waarde": "tweede"}, ["sleutel"]))
        rij = conn.execute(select(tabel).where(tabel.c.sleutel == "s")).one()
    sync.dispose()
    assert rij.waarde == "eerst"


def test_upsert_update_pad_bij_conflict(engine: AsyncEngine, tabel):
    """`update_cols=["waarde"]` → tweede insert overschrijft de bestaande rij."""
    sync = sync_engine_voor(engine)
    with sync.begin() as conn:
        conn.execute(upsert(tabel, {"sleutel": "s", "waarde": "eerst"}, ["sleutel"], ["waarde"]))
        conn.execute(upsert(tabel, {"sleutel": "s", "waarde": "tweede"}, ["sleutel"], ["waarde"]))
        rij = conn.execute(select(tabel).where(tabel.c.sleutel == "s")).one()
    sync.dispose()
    assert rij.waarde == "tweede"


def test_upsert_met_returning(engine: AsyncEngine, tabel):
    """De helper geeft een statement terug waar `.returning(...)` op te chainen valt."""
    stmt = upsert(tabel, {"sleutel": "s", "waarde": "v"}, ["sleutel"], ["waarde"]).returning(tabel)
    rijen = _sync_execute(engine, stmt)
    assert len(rijen) == 1
    assert (rijen[0].sleutel, rijen[0].waarde) == ("s", "v")
