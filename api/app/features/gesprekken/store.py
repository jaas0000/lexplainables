"""Store-abstractie voor het gesprekken-domein (zelfde ADR-0007-patroon als annotatie).

`GesprekStore` beschrijft de operaties die router.py nodig heeft. `SqlAlchemyGesprekStore` is
de enige huidige implementatie (async SQLAlchemy Core); tests draaien tegen een eigen,
kortlevende testengine (`conftest.py::maak_test_engine`).
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared.tijd import nu
from .models import (
    Bericht,
    BerichtInvoer,
    Gesprek,
    GesprekSamenvatting,
    _inhoud_uit,
    bericht_uit_rij,
    gesprek_berichten,
    gesprekken,
    samenvatting_uit_rij,
)


class GesprekStore(Protocol):
    async def maak_gesprek(self, gesprek: Gesprek) -> Gesprek: ...

    async def laad_gesprek(self, gesprek_id: str) -> Gesprek | None: ...

    async def lijst_samenvattingen(
        self, gebruiker: str, limit: int, offset: int
    ) -> list[GesprekSamenvatting]: ...

    async def voeg_bericht_toe(self, gesprek_id: str, inv: BerichtInvoer) -> Bericht: ...

    async def hernoem_gesprek(self, gesprek_id: str, titel: str) -> None: ...

    async def verwijder_gesprek(self, gesprek_id: str) -> None: ...


class SqlAlchemyGesprekStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def maak_gesprek(self, gesprek: Gesprek) -> Gesprek:
        now = nu()
        async with self._engine.begin() as conn:
            await conn.execute(
                insert(gesprekken).values(
                    id=gesprek.id,
                    gebruiker=gesprek.gebruiker,
                    titel=gesprek.titel,
                    aangemaakt=now,
                    bijgewerkt=now,
                )
            )
        return gesprek.model_copy(
            update={"aangemaakt": now.isoformat(), "bijgewerkt": now.isoformat()}
        )

    async def laad_gesprek(self, gesprek_id: str) -> Gesprek | None:
        async with self._engine.connect() as conn:
            rij = (
                await conn.execute(select(gesprekken).where(gesprekken.c.id == gesprek_id))
            ).first()
            if rij is None:
                return None
            berichten_rijen = (
                await conn.execute(
                    select(gesprek_berichten)
                    .where(gesprek_berichten.c.gesprek_id == gesprek_id)
                    .order_by(gesprek_berichten.c.id)
                )
            ).all()
        return Gesprek(
            id=rij.id,
            gebruiker=rij.gebruiker,
            titel=rij.titel,
            berichten=[bericht_uit_rij(b) for b in berichten_rijen],
            aangemaakt=rij.aangemaakt.isoformat(),
            bijgewerkt=rij.bijgewerkt.isoformat(),
        )

    async def lijst_samenvattingen(
        self, gebruiker: str, limit: int = 100, offset: int = 0
    ) -> list[GesprekSamenvatting]:
        aantal = func.count(gesprek_berichten.c.id).label("aantal_berichten")
        async with self._engine.connect() as conn:
            rijen = (
                await conn.execute(
                    select(
                        gesprekken.c.id,
                        gesprekken.c.titel,
                        gesprekken.c.bijgewerkt,
                        aantal,
                    )
                    .select_from(
                        gesprekken.outerjoin(
                            gesprek_berichten,
                            gesprekken.c.id == gesprek_berichten.c.gesprek_id,
                        )
                    )
                    .where(gesprekken.c.gebruiker == gebruiker)
                    .group_by(gesprekken.c.id, gesprekken.c.titel, gesprekken.c.bijgewerkt)
                    .order_by(gesprekken.c.bijgewerkt.desc())
                    .limit(limit)
                    .offset(offset)
                )
            ).all()
        return [samenvatting_uit_rij(r) for r in rijen]

    @staticmethod
    async def _bericht_van_run(conn, gesprek_id: str, run_id: str) -> Bericht | None:
        """Staat de uitkomst van deze run er al? Alleen de staart bekijken volstaat: een run
        schrijft aan het eind van zijn eigen beurt, dus verder terugzoeken heeft geen zin."""
        rijen = (
            await conn.execute(
                select(gesprek_berichten)
                .where(gesprek_berichten.c.gesprek_id == gesprek_id)
                .order_by(gesprek_berichten.c.id.desc())
                .limit(20)
            )
        ).fetchall()
        for rij in rijen:
            if (rij.inhoud or {}).get("run_id") == run_id:
                return bericht_uit_rij(rij)
        return None

    async def voeg_bericht_toe(self, gesprek_id: str, inv: BerichtInvoer) -> Bericht:
        """Append-only, behalve dat een `run_id` maar één keer mag landen (zie `__init__.py`).

        Check-then-insert in dezelfde transactie; geen unieke index (er is per run feitelijk
        één schrijver tegelijk — zelfde aanname als de referentie-implementatie)."""
        now = nu()
        async with self._engine.begin() as conn:
            if inv.run_id:
                bestaand = await self._bericht_van_run(conn, gesprek_id, inv.run_id)
                if bestaand is not None:
                    return bestaand
            result = await conn.execute(
                insert(gesprek_berichten).values(
                    gesprek_id=gesprek_id,
                    rol=inv.rol.value,
                    inhoud=_inhoud_uit(inv),
                    aangemaakt=now,
                )
            )
            await conn.execute(
                update(gesprekken).where(gesprekken.c.id == gesprek_id).values(bijgewerkt=now)
            )
            nieuw_id = result.inserted_primary_key[0] if result.inserted_primary_key else None
        return Bericht(
            id=nieuw_id,
            rol=inv.rol,
            tekst=inv.tekst,
            denk=inv.denk,
            bronnen=inv.bronnen,
            annotatie_slug=inv.annotatie_slug,
            annotatie_titel=inv.annotatie_titel,
            ontbrekend=inv.ontbrekend,
            run_id=inv.run_id,
            aangemaakt=now.isoformat(),
        )

    async def hernoem_gesprek(self, gesprek_id: str, titel: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                update(gesprekken)
                .where(gesprekken.c.id == gesprek_id)
                .values(titel=titel, bijgewerkt=nu())
            )

    async def verwijder_gesprek(self, gesprek_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                delete(gesprek_berichten).where(gesprek_berichten.c.gesprek_id == gesprek_id)
            )
            await conn.execute(delete(gesprekken).where(gesprekken.c.id == gesprek_id))
