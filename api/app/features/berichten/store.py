"""Store-abstractie voor het berichten-domein (werkwijze-ADR-0007).

`BerichtenStore` beschrijft de operaties die router.py nodig heeft, niet de databasedetails.
`SqlAlchemyBerichtenStore` is de enige huidige implementatie (async SQLAlchemy Core). Tests
draaien 'm tegen een eigen, kortlevende SQLite-engine (zie tests/conftest.py) — dezelfde
implementatie, geen aparte fake, dus blijft de echte SQL ook in tests gedekt.

Geen gedeelde `LeesbewijsStore` met feedback: zie
../../../../docs/stories/002-berichten-lezen-en-beheren.md §Schemabeslissing voor de afweging
(cursor-per-beheerder bij feedback vs. fijnmazige jointabel hier — structureel verschillend).
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import ColumnElement, delete, func, insert, literal, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared.db import dialect_insert
from ...shared.tijd import nu
from .models import (
    BerichtAdminRead,
    BerichtRead,
    BerichtType,
    bericht_admin_uit_rij,
    bericht_leesbewijzen,
    bericht_uit_rij,
    berichten,
)


class BerichtNietGevonden(LookupError):
    """Onbekend bericht-id (bv. bewerken/publiceren/verwijderen van iets dat niet bestaat)."""


def _zichtbaar_vanaf() -> ColumnElement:
    """Sorteer-/zichtbaarheidsmoment van `berichten`: het publicatiemoment, of bij een (nog)
    ongepubliceerd concept het aanmaakmoment als fallback. Overgenomen uit het externe project —
    onafhankelijk van de weggelaten registratiemoment-filter (zie de story): een concept is toch
    al niet zichtbaar voor analisten omdat `gepubliceerd=False` het uitsluit, maar een
    gepubliceerd bericht hoort te sorteren op wannéér het live ging, niet op wanneer het als
    concept is geschreven."""
    return func.coalesce(berichten.c.gepubliceerd_op, berichten.c.created)


def _leesbewijs_join(userid: str) -> ColumnElement:
    """Join-conditie tussen `berichten` en `bericht_leesbewijzen` voor één gebruiker — dezelfde
    conditie werd drie keer verbatim herhaald in `lijst`/`totaal`/`ongelezen_aantal`."""
    return (bericht_leesbewijzen.c.bericht_id == berichten.c.id) & (
        bericht_leesbewijzen.c.userid == userid
    )


class BerichtenStore(Protocol):
    async def lijst(
        self, userid: str, offset: int, limit: int, ongelezen_only: bool
    ) -> list[BerichtRead]: ...

    async def totaal(self, userid: str, ongelezen_only: bool) -> int: ...

    async def ongelezen_aantal(self, userid: str) -> int: ...

    async def markeer_alles_gelezen(self, userid: str) -> None: ...

    async def lijst_admin(self, offset: int, limit: int) -> list[BerichtAdminRead]: ...

    async def totaal_admin(self) -> int: ...

    async def maak(
        self, titel: str, inhoud: str, type: BerichtType, versie: str | None, aangemaakt_door: str
    ) -> BerichtAdminRead: ...

    async def bewerk(
        self, bericht_id: int, titel: str, inhoud: str, type: BerichtType, versie: str | None
    ) -> BerichtAdminRead: ...

    async def zet_publicatie(self, bericht_id: int, gepubliceerd: bool) -> BerichtAdminRead: ...

    async def verwijder(self, bericht_id: int) -> None: ...


class SqlAlchemyBerichtenStore:
    """Implementatie tegen een async SQLAlchemy-engine (SQLite in tests, en lokaal via
    aiosqlite — productie zou Postgres/asyncpg zijn, zie stack-profiel.md)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    # --- analist-kant ------------------------------------------------------------

    async def lijst(
        self, userid: str, offset: int, limit: int, ongelezen_only: bool
    ) -> list[BerichtRead]:
        lb = bericht_leesbewijzen
        stmt = (
            select(berichten, lb.c.userid.isnot(None).label("gelezen"))
            .outerjoin(lb, _leesbewijs_join(userid))
            .where(berichten.c.gepubliceerd.is_(True))
            .order_by(_zichtbaar_vanaf().desc())
            .offset(offset)
            .limit(limit)
        )
        if ongelezen_only:
            stmt = stmt.where(lb.c.userid.is_(None))
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [bericht_uit_rij(rij, gelezen=bool(rij.gelezen)) for rij in rijen]

    async def totaal(self, userid: str, ongelezen_only: bool) -> int:
        lb = bericht_leesbewijzen
        stmt = select(func.count()).select_from(berichten).where(berichten.c.gepubliceerd.is_(True))
        if ongelezen_only:
            stmt = stmt.outerjoin(lb, _leesbewijs_join(userid)).where(lb.c.userid.is_(None))
        async with self._engine.connect() as conn:
            result = await conn.scalar(stmt)
        return int(result or 0)

    async def ongelezen_aantal(self, userid: str) -> int:
        """Aantal ongelezen == aantal gepubliceerde berichten zonder leesbewijs — zelfde vraag
        als `totaal(userid, ongelezen_only=True)`, dus hergebruikt in plaats van dezelfde query
        nogmaals uit te schrijven."""
        return await self.totaal(userid, ongelezen_only=True)

    async def markeer_alles_gelezen(self, userid: str) -> None:
        moment = nu()
        select_stmt = select(
            berichten.c.id, literal(userid).label("userid"), literal(moment).label("gelezen_op")
        ).where(berichten.c.gepubliceerd.is_(True))
        async with self._engine.begin() as conn:
            # Dialect-aware upsert: bij gelijktijdige aanroepen (twee tabbladen) kan dezelfde
            # (bericht_id, userid) twee keer geïnsert worden — de PK-constraint vangt dat af
            # i.p.v. een los "insert waar nog geen rij bestaat" dat onder concurrency een
            # duplicate-key-fout kan geven (check-then-insert is niet atomair). De
            # `from_select`-vorm past niet op `shared.db.upsert()` (die neemt een values-dict),
            # dus we gebruiken hier de laag-eronder-helper `dialect_insert`.
            stmt = (
                dialect_insert(conn, bericht_leesbewijzen)
                .from_select(["bericht_id", "userid", "gelezen_op"], select_stmt)
                .on_conflict_do_nothing(index_elements=["bericht_id", "userid"])
            )
            await conn.execute(stmt)

    # --- admin-kant ----------------------------------------------------------------

    async def lijst_admin(self, offset: int, limit: int) -> list[BerichtAdminRead]:
        stmt = select(berichten).order_by(_zichtbaar_vanaf().desc()).offset(offset).limit(limit)
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [bericht_admin_uit_rij(rij) for rij in rijen]

    async def totaal_admin(self) -> int:
        async with self._engine.connect() as conn:
            result = await conn.scalar(select(func.count()).select_from(berichten))
        return int(result or 0)

    async def maak(
        self, titel: str, inhoud: str, type: BerichtType, versie: str | None, aangemaakt_door: str
    ) -> BerichtAdminRead:
        """Maak een nieuw concept-bericht — altijd `gepubliceerd=False`, ongeacht wat een
        client zou proberen mee te sturen (het schema `BerichtCreate` heeft toch al geen
        `gepubliceerd`-veld, dit is de businessregel die dat afdwingt)."""
        moment = nu()
        async with self._engine.begin() as conn:
            result = await conn.execute(
                insert(berichten)
                .values(
                    titel=titel.strip(),
                    inhoud=inhoud,
                    type=type,
                    versie=versie.strip() if versie else None,
                    gepubliceerd=False,
                    gepubliceerd_op=None,
                    aangemaakt_door=aangemaakt_door,
                    created=moment,
                    updated=moment,
                )
                .returning(berichten)
            )
            rij = result.one()
        return bericht_admin_uit_rij(rij)

    async def _werk_bij(self, bericht_id: int, **waarden) -> BerichtAdminRead:
        """Gedeelde update-en-geef-terug voor `bewerk`/`zet_publicatie`: één transactie, één
        RETURNING-roundtrip, of `BerichtNietGevonden` als het id niet bestaat."""
        async with self._engine.begin() as conn:
            result = await conn.execute(
                update(berichten)
                .where(berichten.c.id == bericht_id)
                .values(**waarden)
                .returning(berichten)
            )
            rij = result.first()
        if rij is None:
            raise BerichtNietGevonden(f"Bericht {bericht_id} bestaat niet.")
        return bericht_admin_uit_rij(rij)

    async def bewerk(
        self, bericht_id: int, titel: str, inhoud: str, type: BerichtType, versie: str | None
    ) -> BerichtAdminRead:
        """Werk een bericht bij (inhoud/metadata). Leesbewijzen blijven ongemoeid — bewerken
        is geen nieuwe publicatie."""
        return await self._werk_bij(
            bericht_id,
            titel=titel.strip(),
            inhoud=inhoud,
            type=type,
            versie=versie.strip() if versie else None,
            updated=nu(),
        )

    async def zet_publicatie(self, bericht_id: int, gepubliceerd: bool) -> BerichtAdminRead:
        """Publiceer of depubliceer een bericht: zet resp. wist `gepubliceerd_op`."""
        moment = nu()
        return await self._werk_bij(
            bericht_id,
            gepubliceerd=gepubliceerd,
            gepubliceerd_op=moment if gepubliceerd else None,
            updated=moment,
        )

    async def verwijder(self, bericht_id: int) -> None:
        """Verwijder een bericht + al zijn leesbewijzen, in één transactie (cascade). Geen losse
        bestaans-check vooraf: de leesbewijzen-delete is een onschuldige no-op als het bericht
        niet bestaat, en de `berichten`-delete met `.returning()` bevestigt het bestaan in
        dezelfde round trip in plaats van er een aparte SELECT voor te doen."""
        async with self._engine.begin() as conn:
            await conn.execute(
                delete(bericht_leesbewijzen).where(bericht_leesbewijzen.c.bericht_id == bericht_id)
            )
            result = await conn.execute(
                delete(berichten).where(berichten.c.id == bericht_id).returning(berichten.c.id)
            )
            if result.first() is None:
                raise BerichtNietGevonden(f"Bericht {bericht_id} bestaat niet.")
