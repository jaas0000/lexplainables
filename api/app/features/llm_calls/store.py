"""Store voor het llm_calls-domein (werkwijze-ADR-0007).

`SqlAlchemyLlmCallsStore` is de enige implementatie. De engine gebruikt `sla_op`
(best-effort capture), de projecten-router gebruikt `lijst_calls` voor
`GET /v1/projecten/{id}/llm-calls`.

Geen Protocol-abstractie tot een tweede implementatie/gebruiker langskomt
(vervolgpunt bij PR #20).
"""

from __future__ import annotations

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared.tijd import nu
from .models import LlmCallRead, llm_calls


class SqlAlchemyLlmCallsStore:
    """Store voor het opslaan en teruglezen van LLM-calls (capture-toggle, migratie 0009)."""

    def __init__(self, engine: AsyncEngine) -> None:
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

    async def lijst_calls(self, analyse_id: str) -> list[LlmCallRead]:
        """Geeft alle LLM-calls voor een analyse gesorteerd op aangemaakt asc.

        Lege lijst als analyse_id onbekend of nog geen calls zijn vastgelegd.
        """
        stmt = (
            select(llm_calls)
            .where(llm_calls.c.analyse_id == analyse_id)
            .order_by(llm_calls.c.aangemaakt)
        )
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [LlmCallRead(**rij._mapping) for rij in rijen]
