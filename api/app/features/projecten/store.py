"""Store-abstractie voor het projecten-domein (werkwijze-ADR-0007).

`AnalyseStore` beschrijft de operaties die router.py nodig heeft. `SqlAlchemyAnalyseStore`
is de enige huidige implementatie. Tests draaien 'm tegen een eigen, kortlevende SQLite-engine.

Rolfilter staat hier, niet in router.py (werkwijze-ADR-0007):
- `is_beheerder=True`  → geen gebruiker_id-filter; beheerder ziet en verwijdert alles.
- `is_beheerder=False` → filter op gebruiker_id; analist ziet en verwijdert alleen eigen.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared.tijd import nu
from .models import (
    AnalyseDetail,
    AnalyseOverzicht,
    BronKeuze,
    analyse_detail_uit_rij,
    analyse_overzicht_uit_rij,
    analyses,
)


class AnalyseNietGevonden(LookupError):
    """Analyse-id onbekend, of de aanvragende gebruiker heeft geen toegang."""


class AnalyseStore(Protocol):
    async def maak(
        self,
        gebruiker_id: str,
        naam: str | None,
        bronnen: list[BronKeuze],
        omschrijving: str | None,
    ) -> AnalyseDetail: ...

    async def lijst(self, gebruiker_id: str, is_beheerder: bool) -> list[AnalyseOverzicht]: ...

    async def detail(
        self, analyse_id: str, gebruiker_id: str, is_beheerder: bool
    ) -> AnalyseDetail: ...

    async def verwijder(self, analyse_id: str, gebruiker_id: str, is_beheerder: bool) -> None: ...


class SqlAlchemyAnalyseStore:
    """Implementatie tegen een async SQLAlchemy-engine."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def maak(
        self,
        gebruiker_id: str,
        naam: str | None,
        bronnen: list[BronKeuze],
        omschrijving: str | None,
    ) -> AnalyseDetail:
        analyse_id = str(uuid.uuid4())
        moment = nu()
        bronnen_data = [b.model_dump() for b in bronnen]

        async with self._engine.begin() as conn:
            result = await conn.execute(
                insert(analyses)
                .values(
                    id=analyse_id,
                    naam=naam,
                    status="nieuw",
                    bronnen=bronnen_data,
                    omschrijving=omschrijving,
                    aangemaakt=moment,
                    bijgewerkt=moment,
                    gebruiker_id=gebruiker_id,
                )
                .returning(analyses)
            )
            rij = result.one()
        return analyse_detail_uit_rij(rij)

    async def lijst(self, gebruiker_id: str, is_beheerder: bool) -> list[AnalyseOverzicht]:
        stmt = select(analyses).order_by(analyses.c.bijgewerkt.desc())
        if not is_beheerder:
            stmt = stmt.where(analyses.c.gebruiker_id == gebruiker_id)
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [analyse_overzicht_uit_rij(rij) for rij in rijen]

    async def detail(self, analyse_id: str, gebruiker_id: str, is_beheerder: bool) -> AnalyseDetail:
        stmt = select(analyses).where(analyses.c.id == analyse_id)
        if not is_beheerder:
            stmt = stmt.where(analyses.c.gebruiker_id == gebruiker_id)
        async with self._engine.connect() as conn:
            rij = (await conn.execute(stmt)).first()
        if rij is None:
            raise AnalyseNietGevonden(f"Analyse {analyse_id} niet gevonden.")
        return analyse_detail_uit_rij(rij)

    async def verwijder(self, analyse_id: str, gebruiker_id: str, is_beheerder: bool) -> None:
        stmt = delete(analyses).where(analyses.c.id == analyse_id)
        if not is_beheerder:
            stmt = stmt.where(analyses.c.gebruiker_id == gebruiker_id)
        async with self._engine.begin() as conn:
            result = await conn.execute(stmt)
        if result.rowcount == 0:
            raise AnalyseNietGevonden(f"Analyse {analyse_id} niet gevonden.")
