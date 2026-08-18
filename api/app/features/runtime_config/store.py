"""Store-abstractie voor het runtime_config-domein.

`RuntimeConfigStore` leest en schrijft runtime-instellingen via de `app_instellingen`-tabel.
Een module-niveau TTL-cache (≤ 10 seconden) vermijdt een DB-hit bij elke LLM-call.

Businessregels:
- Ontbrekende rij → gebruik standaardwaarde; schrijf pas bij de eerste PUT.
- Ongeldige JSON → standaardwaarde + log-waarschuwing (zie models._str_naar_bool).
- PUT met alleen None-velden → geen schrijfactie; retourneer de huidige waarden.
- Gelijktijdige PUT-requests → laatste schrijver wint (niet transactioneel-kritisch).
"""

from __future__ import annotations

import json
import time

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared.tijd import nu
from .models import (
    SLEUTEL_CAPTURE_LLM_CALLS,
    AppInstellingen,
    AppInstellingenPatch,
    _str_naar_bool,
    app_instellingen,
)

_TTL_S = 10.0

# Module-niveau TTL-cache: sleutel → {"data": AppInstellingen, "ts": float}
_cache: dict[str, object] = {}


def _cache_leeg() -> None:
    """Wis de cache — alleen voor tests."""
    _cache.clear()


class RuntimeConfigStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def lees_alle(self) -> AppInstellingen:
        """Geef alle instellingen terug; gebruikt TTL-cache."""
        treffer = _cache.get("alle")
        if treffer is not None:
            entry = treffer  # type: ignore[assignment]
            if isinstance(entry, dict) and entry["ts"] > time.monotonic():
                return entry["data"]  # type: ignore[return-value]

        stmt = select(app_instellingen)
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()

        waarden: dict[str, str] = {rij.sleutel: rij.waarde for rij in rijen}

        instelling = AppInstellingen(
            capture_llm_calls=_str_naar_bool(
                waarden.get(SLEUTEL_CAPTURE_LLM_CALLS, "false"),
                standaard=False,
            ),
        )
        _cache["alle"] = {"data": instelling, "ts": time.monotonic() + _TTL_S}
        return instelling

    async def schrijf(self, patch: AppInstellingenPatch) -> AppInstellingen:
        """Upsert elke niet-None waarde, wis de cache, retourneer lees_alle."""
        te_schrijven: dict[str, str] = {}
        if patch.capture_llm_calls is not None:
            te_schrijven[SLEUTEL_CAPTURE_LLM_CALLS] = json.dumps(patch.capture_llm_calls)

        if te_schrijven:
            moment = nu()
            async with self._engine.begin() as conn:
                for sleutel, waarde in te_schrijven.items():
                    stmt = (
                        sqlite_insert(app_instellingen)
                        .values(sleutel=sleutel, waarde=waarde, bijgewerkt=moment)
                        .on_conflict_do_update(
                            index_elements=["sleutel"],
                            set_={"waarde": waarde, "bijgewerkt": moment},
                        )
                    )
                    await conn.execute(stmt)
            _cache.pop("alle", None)

        return await self.lees_alle()

    async def capture_ingeschakeld(self) -> bool:
        """Staat het vastleggen van LLM-calls aan? Gebruik cache (story 021)."""
        instelling = await self.lees_alle()
        return instelling.capture_llm_calls
