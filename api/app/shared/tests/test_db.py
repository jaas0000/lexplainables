"""Unit-tests voor `app.shared.db` (dialect_insert + upsert).

Twee sporen:
- **Echt tegen SQLite** — bewijst het insert- én update-pad tegen een levende engine, dat is
  waar de bugs opduiken (constraint-namen, RETURNING, PK-conflict).
- **Dialect-only tegen Postgres** — één test die de gecompileerde SQL controleert
  (`ON CONFLICT ... DO UPDATE`), zonder daadwerkelijke PG-server. Genoeg om te bewijzen dat de
  dialectkeuze switcht; de rest van het gedrag is identiek qua statement-vorm.
"""

from __future__ import annotations

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.dialects.postgresql import dml as pg_dml

from app.shared.db import dialect_insert, upsert


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


@pytest.fixture
def sqlite_engine(tabel: Table):
    engine = create_engine("sqlite://")
    tabel.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


# --- SQLite: insert-pad ---------------------------------------------------------


def test_upsert_insert_do_nothing_bij_conflict(sqlite_engine, tabel):
    """`update_cols=None` → tweede insert doet niets, eerste waarde blijft staan."""
    with sqlite_engine.begin() as conn:
        conn.execute(upsert(conn, tabel, {"sleutel": "s", "waarde": "eerst"}, ["sleutel"]))
        conn.execute(upsert(conn, tabel, {"sleutel": "s", "waarde": "tweede"}, ["sleutel"]))
        rij = conn.execute(select(tabel).where(tabel.c.sleutel == "s")).one()
    assert rij.waarde == "eerst"


def test_upsert_update_pad_bij_conflict(sqlite_engine, tabel):
    """`update_cols=["waarde"]` → tweede insert overschrijft de bestaande rij."""
    with sqlite_engine.begin() as conn:
        conn.execute(
            upsert(conn, tabel, {"sleutel": "s", "waarde": "eerst"}, ["sleutel"], ["waarde"])
        )
        conn.execute(
            upsert(conn, tabel, {"sleutel": "s", "waarde": "tweede"}, ["sleutel"], ["waarde"])
        )
        rij = conn.execute(select(tabel).where(tabel.c.sleutel == "s")).one()
    assert rij.waarde == "tweede"


def test_upsert_met_returning(sqlite_engine, tabel):
    """De helper geeft een statement terug waar `.returning(...)` op te chainen valt."""
    stmt = upsert(
        sqlite_engine, tabel, {"sleutel": "s", "waarde": "v"}, ["sleutel"], ["waarde"]
    ).returning(tabel)
    with sqlite_engine.begin() as conn:
        rij = conn.execute(stmt).one()
    assert (rij.sleutel, rij.waarde) == ("s", "v")


def test_dialect_insert_from_select(sqlite_engine, tabel):
    """`dialect_insert` ondersteunt `from_select` — het pad dat berichten.store gebruikt."""
    bron = select(tabel.c.sleutel, tabel.c.waarde).where(tabel.c.sleutel == "s")
    with sqlite_engine.begin() as conn:
        conn.execute(upsert(conn, tabel, {"sleutel": "s", "waarde": "v"}, ["sleutel"]))
        # Insert-from-select met conflict → do_nothing (idempotent).
        stmt = (
            dialect_insert(conn, tabel)
            .from_select(["sleutel", "waarde"], bron)
            .on_conflict_do_nothing(index_elements=["sleutel"])
        )
        conn.execute(stmt)
        aantal = conn.execute(select(tabel)).all()
    assert len(aantal) == 1


# --- PostgreSQL: alleen dialect-keuze, gecompileerde SQL ------------------------


class _FakePgEngine:
    """Minimale stand-in voor een PG-engine — de helper leest alleen `.dialect.name`, dus
    een echte driver of connectie is niet nodig."""

    class _Dialect:
        name = "postgresql"

    dialect = _Dialect()


def test_upsert_kiest_pg_insert_op_postgres_engine(tabel):
    """Op een Postgres-dialect switcht de helper naar `pg_insert`. Bewijs: het gebouwde
    statement is een instance van het PG-specifieke `Insert`-DML-type. SQLite's `on_conflict`
    genereert dezelfde SQL-vorm — we asserten daarom op de klasse, niet op de gecompileerde
    string (die zou ook slagen als de switch verkeerd stond)."""
    stmt = upsert(
        _FakePgEngine(),
        tabel,
        {"sleutel": "s", "waarde": "v"},
        ["sleutel"],
        ["waarde"],
    )
    assert isinstance(stmt, pg_dml.Insert)
