"""Gedeelde database-helpers (feature-bouwen regel 8).

Upsert-boilerplate voor PostgreSQL. Sinds project-ADR-0003 (Postgres-only) is er geen
dialect-branching meer nodig — `pg_insert` is de enige insert-variant. Ownerless: een
generieke SQLAlchemy-utility die evengoed bij elke feature had kunnen ontstaan, geen
natuurlijke eigenaar-feature (zelfde redenering als `shared/tijd.py`).

Contract:
- `upsert(table, values, conflict_cols, update_cols=None)` — bouwt een compleet
  upsert-statement en retourneert het (caller doet `await conn.execute(stmt)`, en chainet
  eventueel `.returning(...)` voor de opgeslagen rij). `update_cols=None` mapt naar
  `on_conflict_do_nothing`; een lijst kolomnamen naar `on_conflict_do_update` op die kolommen.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Table
from sqlalchemy.dialects.postgresql import insert as pg_insert


def upsert(
    table: Table,
    values: dict[str, Any],
    conflict_cols: list[str],
    update_cols: list[str] | None = None,
) -> Any:
    """Bouw een Postgres-upsert en geef het statement terug.

    - `values`: kolom→waarde voor de INSERT-branche.
    - `conflict_cols`: kolommen die de conflict-index vormen (PK of unique).
    - `update_cols`:
        - `None` → `on_conflict_do_nothing(index_elements=conflict_cols)`.
        - `list[str]` → update alleen die kolommen met de bijbehorende waarden uit `values`.

    De caller voert het statement zelf uit (`await conn.execute(stmt)`) en kan er
    `.returning(...)` op chainen voor de opgeslagen rij.
    """
    stmt = pg_insert(table).values(**values)
    if update_cols is None:
        return stmt.on_conflict_do_nothing(index_elements=conflict_cols)
    return stmt.on_conflict_do_update(
        index_elements=conflict_cols,
        set_={col: values[col] for col in update_cols},
    )
