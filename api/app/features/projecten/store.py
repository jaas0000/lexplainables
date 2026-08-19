"""Store-abstractie voor het projecten-domein (werkwijze-ADR-0007).

`AnalyseStore` beschrijft de operaties die router.py nodig heeft. `SqlAlchemyAnalyseStore`
is de enige huidige implementatie. Tests draaien 'm tegen een eigen, kortlevende SQLite-engine.

Rolfilter staat hier, niet in router.py (story 012 §Auth/rollen):
- `is_beheerder=True`  → geen gebruiker_id-filter; beheerder ziet en verwijdert alles.
- `is_beheerder=False` → filter op gebruiker_id; analist ziet en verwijdert alleen eigen.
"""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared.tijd import nu
from .models import (
    AnalyseDetail,
    AnalyseOverzicht,
    BegripInvoer,
    BronKeuze,
    analyse_detail_uit_rij,
    analyse_overzicht_uit_rij,
    analyses,
    llm_calls,
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
        analysefocus: str | None,
        begrippenlijst: list[BegripInvoer] | None,
        model_profiel: str | None,
        human_in_the_loop: bool,
    ) -> AnalyseDetail: ...

    async def lijst(self, gebruiker_id: str, is_beheerder: bool) -> list[AnalyseOverzicht]: ...

    async def detail(
        self, analyse_id: str, gebruiker_id: str, is_beheerder: bool
    ) -> AnalyseDetail: ...

    async def verwijder(self, analyse_id: str, gebruiker_id: str, is_beheerder: bool) -> None: ...

    async def zet_status(
        self,
        analyse_id: str,
        status: str,
        huidige_fase: str | None = None,
        foutmelding: str | None = None,
    ) -> None: ...

    async def haal_status(self, analyse_id: str) -> str | None: ...

    async def haal_rij_op_id(self, analyse_id: str): ...

    async def sla_rapport_op(self, analyse_id: str, rapport: dict) -> None: ...


class SqlAlchemyAnalyseStore:
    """Implementatie tegen een async SQLAlchemy-engine (aiosqlite in tests en lokaal)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def maak(
        self,
        gebruiker_id: str,
        naam: str | None,
        bronnen: list[BronKeuze],
        omschrijving: str | None,
        analysefocus: str | None,
        begrippenlijst: list[BegripInvoer] | None,
        model_profiel: str | None,
        human_in_the_loop: bool,
    ) -> AnalyseDetail:
        analyse_id = str(uuid.uuid4())
        moment = nu()
        bronnen_data = [b.model_dump() for b in bronnen]
        begrippen_data = [b.model_dump() for b in begrippenlijst] if begrippenlijst else None

        async with self._engine.begin() as conn:
            result = await conn.execute(
                insert(analyses)
                .values(
                    id=analyse_id,
                    naam=naam,
                    status="wachtrij",
                    bronnen=bronnen_data,
                    model_profiel=model_profiel,
                    omschrijving=omschrijving,
                    analysefocus=analysefocus,
                    human_in_the_loop=human_in_the_loop,
                    begrippenlijst=begrippen_data,
                    huidige_fase=None,
                    foutmelding=None,
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

    async def zet_status(
        self,
        analyse_id: str,
        status: str,
        huidige_fase: str | None = None,
        foutmelding: str | None = None,
    ) -> None:
        """Werk status, fase en eventuele foutmelding bij (gebruikt door de background-job)."""
        async with self._engine.begin() as conn:
            await conn.execute(
                update(analyses)
                .where(analyses.c.id == analyse_id)
                .values(
                    status=status,
                    huidige_fase=huidige_fase,
                    foutmelding=foutmelding,
                    bijgewerkt=nu(),
                )
            )

    async def haal_status(self, analyse_id: str) -> str | None:
        """Lees alleen de huidige status op (poll-endpoint voor de background-job)."""
        async with self._engine.connect() as conn:
            rij = await conn.execute(select(analyses.c.status).where(analyses.c.id == analyse_id))
            result = rij.first()
        return result.status if result else None

    async def haal_rij_op_id(self, analyse_id: str):
        """Geef de volledige rij terug voor de background-job (inclusief alle config-velden)."""
        async with self._engine.connect() as conn:
            rij = await conn.execute(select(analyses).where(analyses.c.id == analyse_id))
            return rij.first()

    async def sla_rapport_op(self, analyse_id: str, rapport: dict) -> None:
        """Sla het eindrapport op in analyses.rapport (migratie 0009)."""
        async with self._engine.begin() as conn:
            await conn.execute(
                update(analyses)
                .where(analyses.c.id == analyse_id)
                .values(rapport=rapport, bijgewerkt=nu())
            )


class SqlAlchemyLlmCallsStore:
    """Store voor het opslaan van LLM-calls (capture-toggle, migratie 0009)."""

    def __init__(self, engine) -> None:
        self._engine = engine

    async def sla_op(
        self,
        *,
        analyse_id: str,
        activiteit: str,
        bron_id: str | None,
        system_prompt: str,
        user_prompt: str,
        ruwe_respons: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        """Sla één LLM-call op. Best-effort: gooit geen exception als de tabel ontbreekt."""
        async with self._engine.begin() as conn:
            await conn.execute(
                insert(llm_calls).values(
                    analyse_id=analyse_id,
                    activiteit=activiteit,
                    bron_id=bron_id,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    ruwe_respons=ruwe_respons,
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    aangemaakt=nu(),
                )
            )
