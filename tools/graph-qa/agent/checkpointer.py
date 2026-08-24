"""LangGraph-checkpointer-selectie: gespreksgeheugen (`thread_id = conversation_id`).

Voorrang: `checkpoint_db_url` → **Postgres** (`AsyncPostgresSaver`; gedeeld tussen replica's,
horizontaal veilig) → `checkpoint_db_path` → **SQLite** (durable bestand, maar per-instance) →
anders in-proces (`MemorySaver`).

Poort van `wetsanalyse-ai/tools/graph-qa/agent/agent.py`'s `_checkpointer_ctx`, 1:1 (werkwijze-
story 050). Bewust **niet** meegenomen: `delete_conversation` (hoort bij de API-laag, die hier
nog niet bestaat) en observability — beide latere stories.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from .config import Settings


def checkpointer_ctx(settings: Settings):
    """Async context manager die de gekozen checkpointer levert."""
    url = settings.checkpoint_db_url
    if url:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        @asynccontextmanager
        async def _pg():
            async with AsyncPostgresSaver.from_conn_string(url) as saver:
                await saver.setup()  # idempotent: maakt de checkpoint-tabellen als ze ontbreken
                yield saver

        return _pg()

    path = settings.checkpoint_db_path
    if path:
        p = Path(path)
        if not p.is_absolute():
            p = Path(__file__).parent.parent / p  # stabiel t.o.v. cwd (graph-qa-root)
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        return AsyncSqliteSaver.from_conn_string(str(p))

    from langgraph.checkpoint.memory import MemorySaver

    @asynccontextmanager
    async def _mem():
        yield MemorySaver()

    return _mem()
