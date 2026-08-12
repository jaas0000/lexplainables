"""Store-abstractie voor het feedback-domein (werkwijze-ADR-0007).

`FeedbackStore` beschrijft de operaties die router.py nodig heeft, niet de databasedetails.
`SqlAlchemyFeedbackStore` is de enige huidige implementatie (async SQLAlchemy Core). Tests
draaien 'm tegen een eigen, kortlevende SQLite-engine (zie tests/conftest.py) — dezelfde
implementatie, geen aparte fake, dus blijft de echte SQL ook in tests gedekt.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sqlalchemy import ColumnElement, delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from .models import FeedbackRead, feedback_leesbewijzen, feedback_uit_rij, nu, user_feedback


class FeedbackNietGevonden(LookupError):
    """Onbekend feedback-id (bv. verwijderen van iets dat niet bestaat)."""


class FeedbackStore(Protocol):
    async def dien_in(
        self, client_id: str, userid: str, categorie: str, tekst: str, pagina: str | None
    ) -> FeedbackRead: ...

    async def verwijder(self, feedback_id: int) -> None: ...

    async def lijst(self, offset: int, limit: int) -> list[FeedbackRead]: ...

    async def totaal(self) -> int: ...

    async def ongelezen_aantal(self, admin_userid: str) -> int: ...

    async def markeer_gezien(self, admin_userid: str, tot: datetime | None) -> None: ...


class SqlAlchemyFeedbackStore:
    """Implementatie tegen een async SQLAlchemy-engine (SQLite in tests, en lokaal via
    aiosqlite — productie zou Postgres/asyncpg zijn, zie stack-profiel.md)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def dien_in(
        self, client_id: str, userid: str, categorie: str, tekst: str, pagina: str | None
    ) -> FeedbackRead:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                insert(user_feedback)
                .values(
                    client_id=client_id,
                    userid=userid,
                    categorie=categorie,
                    tekst=tekst.strip(),
                    pagina=pagina,
                    created=nu(),
                )
                .returning(user_feedback)
            )
            rij = result.one()
        return feedback_uit_rij(rij)

    async def verwijder(self, feedback_id: int) -> None:
        async with self._engine.begin() as conn:
            result = await conn.execute(
                delete(user_feedback).where(user_feedback.c.id == feedback_id)
            )
        if result.rowcount == 0:
            raise FeedbackNietGevonden(f"Feedback {feedback_id} bestaat niet.")

    async def lijst(self, offset: int, limit: int) -> list[FeedbackRead]:
        stmt = (
            select(user_feedback)
            .order_by(user_feedback.c.created.desc())
            .offset(offset)
            .limit(limit)
        )
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [feedback_uit_rij(rij) for rij in rijen]

    async def totaal(self) -> int:
        return await self._tel()

    async def _tel(self, where: ColumnElement[bool] | None = None) -> int:
        """Gedeelde count-query-opbouw voor `totaal()` en `ongelezen_aantal()` — beide tellen
        rijen in `user_feedback`, met een optionele extra voorwaarde."""
        stmt = select(func.count()).select_from(user_feedback)
        if where is not None:
            stmt = stmt.where(where)
        async with self._engine.connect() as conn:
            result = await conn.scalar(stmt)
        return int(result or 0)

    async def _gezien_tot(self, admin_userid: str) -> datetime | None:
        """Tot welk moment deze beheerder gezien heeft, of None als hij nog nooit gemarkeerd
        heeft. Puur intern (geen extern contract op `feedback_leesbewijzen`, zie models.py) —
        vandaar geen Pydantic-mapping, alleen de kale kolomwaarde."""
        stmt = select(feedback_leesbewijzen.c.gezien_tot).where(
            feedback_leesbewijzen.c.admin_userid == admin_userid
        )
        async with self._engine.connect() as conn:
            return await conn.scalar(stmt)

    async def ongelezen_aantal(self, admin_userid: str) -> int:
        """Aantal feedback-items ingediend ná het laatste moment dat deze beheerder gezien
        heeft. Heeft de beheerder nog nooit gemarkeerd (geen rij in `feedback_leesbewijzen`),
        dan telt alle feedback als ongelezen — zie de story voor waarom dit hier "alles" is
        i.p.v. de registratiedatum-fallback van het externe project (dit domein heeft geen
        eigen gebruikersregistratie)."""
        gezien_tot = await self._gezien_tot(admin_userid)
        where = user_feedback.c.created > gezien_tot if gezien_tot is not None else None
        return await self._tel(where)

    async def markeer_gezien(self, admin_userid: str, tot: datetime | None) -> None:
        """Sla op tot welk tijdstip deze beheerder de feedback gezien heeft. Zonder `tot`
        geldt het huidige moment; met een expliciete `tot` (de created-timestamp van het
        nieuwste getoonde item) voorkomt de aanroeper dat feedback die tussen het laden en het
        markeren binnenkomt ten onrechte als gezien telt."""
        moment = tot or nu()
        async with self._engine.begin() as conn:
            # Update-dan-insert i.p.v. een dialect-specifieke ON CONFLICT: werkt identiek op
            # SQLite (tests) en Postgres (productie). Geen bescherming tegen een gelijktijdige
            # eerste markering door dezelfde beheerder (theoretische race, geen reëel risico
            # voor een single-user-actie als "ik heb de pagina gezien").
            result = await conn.execute(
                update(feedback_leesbewijzen)
                .where(feedback_leesbewijzen.c.admin_userid == admin_userid)
                .values(gezien_tot=moment)
            )
            if result.rowcount == 0:
                await conn.execute(
                    insert(feedback_leesbewijzen).values(
                        admin_userid=admin_userid, gezien_tot=moment
                    )
                )
