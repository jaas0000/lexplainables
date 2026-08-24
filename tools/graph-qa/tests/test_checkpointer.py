"""`checkpointer_ctx`: kiest Postgres → SQLite-bestand → in-memory.

Eigen tests tegen `agent/checkpointer.py`, dat zelf 1:1 geport is (werkwijze-story 050).
"""

from __future__ import annotations

import asyncio

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agent.checkpointer import checkpointer_ctx
from tests.fakes import make_settings


def test_geen_url_geen_pad_geeft_memory_saver() -> None:
    async def _run() -> None:
        settings = make_settings()
        async with checkpointer_ctx(settings) as saver:
            assert isinstance(saver, MemorySaver)

    asyncio.run(_run())


def test_checkpoint_db_path_geeft_een_werkende_sqlite_saver(tmp_path) -> None:
    async def _run() -> None:
        db = tmp_path / "checkpoints.sqlite"
        settings = make_settings(checkpoint_db_path=str(db))
        async with checkpointer_ctx(settings) as saver:
            assert isinstance(saver, AsyncSqliteSaver)
            # Een echte put/get-cyclus bewijst dat het bestand daadwerkelijk werkt, niet alleen
            # dat de juiste klasse gekozen is.
            config = {"configurable": {"thread_id": "t1", "checkpoint_ns": ""}}
            checkpoint = {
                "v": 1,
                "id": "c1",
                "ts": "2026-01-01T00:00:00+00:00",
                "channel_values": {},
                "channel_versions": {},
                "versions_seen": {},
            }
            await saver.aput(config, checkpoint, {}, {})
            opgehaald = await saver.aget(config)
            assert opgehaald is not None

    asyncio.run(_run())


def test_checkpoint_db_url_kiest_het_postgres_pad() -> None:
    """Geen echte Postgres-server nodig — alleen bewijzen dat de url-branch wordt gekozen (een
    ongeldige/niet-bereikbare conn-string faalt bij het daadwerkelijk verbinden, niet bij het
    selecteren van de klasse)."""

    async def _run() -> None:
        settings = make_settings(checkpoint_db_url="postgresql://localhost:1/niet-bestaand")
        raised = False
        try:
            async with checkpointer_ctx(settings):
                pass
        except Exception as exc:  # noqa: BLE001 — we toetsen alleen dát het het pg-pad probeerde
            raised = True
            # Een connectiefout komt uit psycopg/asyncpg, niet uit onze eigen selectielogica.
            assert "sqlite" not in type(exc).__module__.lower()
        assert raised, "verwacht een connectiefout — dat bewijst dat het Postgres-pad geraakt werd"

    asyncio.run(_run())
