"""Gedeelde database-helpers (feature-bouwen regel 8).

De dialect-aware upsert-boilerplate (`pg_insert if is_pg else sqlite_insert`) stond eerder
gedupliceerd in `berichten/store.py` en `runtime_config/store.py`. Deze module centraliseert
dat patroon. Ownerless: een generieke SQLAlchemy-utility die evengoed bij elke feature had
kunnen ontstaan, geen natuurlijke eigenaar-feature (zelfde redenering als `shared/tijd.py`).

Contract:
- `dialect_insert(engine_or_conn, table)` — retourneert een dialect-specifieke
  `insert(table)` (pg_insert of sqlite_insert). Voor callers die zelf een `.from_select()` of
  andere insert-vorm samenstellen en op `.on_conflict_*()` willen chainen.
- `upsert(engine_or_conn, table, values, conflict_cols, update_cols=None)` — bouwt een
  compleet upsert-statement en retourneert het (caller doet `await conn.execute(stmt)`, en
  chainet eventueel `.returning(...)` voor de opgeslagen rij). `update_cols=None` mapt naar
  `on_conflict_do_nothing`; een lijst kolomnamen naar `on_conflict_do_update` op die kolommen.

Werkt met zowel synchrone als async Engines/Connections — beide exposen `.dialect.name`.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


def dialect_insert(engine_or_conn: Any, table: Table) -> Any:
    """Retourneer een dialect-specifieke `insert(table)` — `pg_insert` voor PostgreSQL,
    `sqlite_insert` voor SQLite. Callers chainen zelf `.values()`/`.from_select()` en
    `.on_conflict_*()`."""
    is_pg = engine_or_conn.dialect.name == "postgresql"
    return (pg_insert if is_pg else sqlite_insert)(table)


def upsert(
    engine_or_conn: Any,
    table: Table,
    values: dict[str, Any],
    conflict_cols: list[str],
    update_cols: list[str] | None = None,
) -> Any:
    """Bouw een dialect-aware upsert-statement en geef het terug.

    - `values`: kolom→waarde voor de INSERT-branche.
    - `conflict_cols`: kolommen die de conflict-index vormen (PK of unique).
    - `update_cols`:
        - `None` → `on_conflict_do_nothing(index_elements=conflict_cols)`.
        - `list[str]` → update alleen die kolommen met de bijbehorende waarden uit `values`.

    De caller voert het statement zelf uit (`await conn.execute(stmt)`) en kan er
    `.returning(...)` op chainen voor de opgeslagen rij.
    """
    stmt = dialect_insert(engine_or_conn, table).values(**values)
    if update_cols is None:
        return stmt.on_conflict_do_nothing(index_elements=conflict_cols)
    return stmt.on_conflict_do_update(
        index_elements=conflict_cols,
        set_={col: values[col] for col in update_cols},
    )
