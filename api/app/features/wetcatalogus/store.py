"""Store-abstractie voor het wetcatalogus-domein (werkwijze-ADR-0007).

Story 020: `HardgecodeerdeWetcatalogusStore` is vervangen door `DatabaseWetcatalogusStore`.
`WetcatalogusStore` (Protocol) is uitgebreid met de nieuwe beheeroperaties.
De hardgecodeerde structuurdata (`_STRUCTUUR`) blijft als fallback totdat `deploy/graphdb` +
`tools/bwb-import` bestaan en de structuurdata via een directe SPARQL-query op de
GraphDB-kennisgraaf kan worden opgehaald (niet via een MCP-tussenlaag — zie ADR-0001
§Consequenties, 2026-08-22-correctie).

Businessregel: `verwijder` gooit `WetNietGevonden` als het bwb_id onbekend is.
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared.db import upsert
from ...shared.tijd import nu
from .models import ArtikelKeuze, WetKeuze, WetRead, WetStructuur, wet_catalogus, wet_uit_rij

# Hardgecodeerde structuurdata (fallback; wordt vervangen zodra GraphDB/bwb-import klaar zijn).
_STRUCTUUR: dict[str, list[ArtikelKeuze]] = {
    "BWBR0011823": [
        ArtikelKeuze(artikel="1", pad="Hoofdstuk 1 / Artikel 1"),
        ArtikelKeuze(artikel="2", pad="Hoofdstuk 1 / Artikel 2"),
        ArtikelKeuze(artikel="3", pad="Hoofdstuk 1 / Artikel 3"),
        ArtikelKeuze(artikel="11", pad="Hoofdstuk 2 / Artikel 11"),
        ArtikelKeuze(artikel="17", pad="Hoofdstuk 2 / Artikel 17"),
        ArtikelKeuze(artikel="31", pad="Hoofdstuk 3 / Artikel 31"),
    ],
    "BWBR0015703": [
        ArtikelKeuze(artikel="1", pad="Hoofdstuk 1 / Artikel 1"),
        ArtikelKeuze(artikel="7", pad="Hoofdstuk 2 / Artikel 7"),
        ArtikelKeuze(artikel="30", pad="Hoofdstuk 4 / Artikel 30"),
    ],
    "BWBR0020183": [
        ArtikelKeuze(artikel="1", pad="Hoofdstuk 1 / Artikel 1"),
        ArtikelKeuze(artikel="8a", pad="Hoofdstuk 2 / Artikel 8a"),
        ArtikelKeuze(artikel="10", pad="Hoofdstuk 2 / Artikel 10"),
        ArtikelKeuze(artikel="44", pad="Hoofdstuk 3 / Artikel 44"),
    ],
}


class WetNietGevonden(LookupError):
    """Onbekend bwb_id."""


class WetcatalogusStore(Protocol):
    async def lijst(self) -> list[WetKeuze]: ...

    async def lijst_met_metadata(self) -> list[WetRead]: ...

    async def upsert(self, bwb_id: str, naam: str, bijgewerkt_door: str) -> WetRead: ...

    async def verwijder(self, bwb_id: str) -> None: ...

    async def structuur(self, bwb_id: str) -> WetStructuur: ...


class DatabaseWetcatalogusStore:
    """SQLAlchemy Core-implementatie — leest en schrijft uit de `wet_catalogus`-tabel."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def lijst(self) -> list[WetKeuze]:
        stmt = select(wet_catalogus.c.bwb_id, wet_catalogus.c.naam).order_by(wet_catalogus.c.naam)
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [WetKeuze(bwb_id=rij.bwb_id, naam=rij.naam) for rij in rijen]

    async def lijst_met_metadata(self) -> list[WetRead]:
        stmt = select(wet_catalogus).order_by(wet_catalogus.c.naam)
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [wet_uit_rij(rij) for rij in rijen]

    async def upsert(self, bwb_id: str, naam: str, bijgewerkt_door: str) -> WetRead:
        # Postgres-only ON CONFLICT DO UPDATE met RETURNING — zie `shared/db.py` en ADR-0003.
        moment = nu()
        stmt = upsert(
            wet_catalogus,
            values={
                "bwb_id": bwb_id,
                "naam": naam,
                "bijgewerkt_door": bijgewerkt_door,
                "bijgewerkt": moment,
            },
            conflict_cols=["bwb_id"],
            update_cols=["naam", "bijgewerkt_door", "bijgewerkt"],
        ).returning(wet_catalogus)
        async with self._engine.begin() as conn:
            result = await conn.execute(stmt)
            rij = result.one()
        return wet_uit_rij(rij)

    async def verwijder(self, bwb_id: str) -> None:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                delete(wet_catalogus)
                .where(wet_catalogus.c.bwb_id == bwb_id)
                .returning(wet_catalogus.c.bwb_id)
            )
            if result.first() is None:
                raise WetNietGevonden(f"Wet {bwb_id!r} niet gevonden.")

    async def structuur(self, bwb_id: str) -> WetStructuur:
        """Geeft de artikel-structuur van een wet.

        Huidige implementatie: hardgecodeerde fallback. Wordt vervangen door een directe
        SPARQL-query op GraphDB zodra `deploy/graphdb` + `tools/bwb-import` beschikbaar zijn.
        Controleert eerst of het bwb_id in de database bestaat.
        """
        wet_bestaat = await self._wet_bestaat(bwb_id)
        if not wet_bestaat:
            raise WetNietGevonden(f"Wet {bwb_id!r} niet gevonden.")
        artikelen = _STRUCTUUR.get(bwb_id, [])
        return WetStructuur(bwb_id=bwb_id, artikelen=list(artikelen))

    async def _wet_bestaat(self, bwb_id: str) -> bool:
        async with self._engine.connect() as conn:
            rij = await conn.scalar(
                select(wet_catalogus.c.bwb_id).where(wet_catalogus.c.bwb_id == bwb_id)
            )
        return rij is not None
