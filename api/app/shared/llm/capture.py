"""Capture-decorator rond een `LLMPort`: legt system/user-prompt + ruwe respons vast.

Persisteert — als `runtime_config.capture_llm_calls = true` — één `llm_calls`-rij per call.
Vangt ook gefaalde calls (best-effort; de originele fout wordt doorgegooid). De call-context
(analyse-id, activiteit, bron-id) komt uit een `ContextVar` die de caller vult via
`gebruik_context()`; ontbreekt de context of het analyse_id → capture wordt overgeslagen
(de `llm_calls`-tabel vereist een analyse_id).

Capture is nooit blocking voor de call: elke fout in het vastleggen wordt gelogd, nooit
doorgegooid.
"""

from __future__ import annotations

import contextlib
import contextvars
import logging

from app.features.llm_calls.store import SqlAlchemyLlmCallsStore
from app.features.runtime_config.store import RuntimeConfigStore

from .base import LlmConfig, LLMPort, LLMResult

logger = logging.getLogger(__name__)

# Per-async-task call-context; default None (leeg). Callers vullen 'm via gebruik_context().
# `default={}` triggert B039 (mutable default kan tussen tasks lekken); None is defensiever
# — we lezen 'm via `llm_call_ctx.get() or {}` overal.
llm_call_ctx: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "llm_call_ctx", default=None
)


@contextlib.contextmanager
def gebruik_context(**velden):
    """Zet de call-context voor de duur van het blok (gemerged met de huidige) en herstel daarna.

    Verwachte velden voor volledige capture: `analyse_id` (verplicht om te loggen),
    `activiteit`, `bron_id`. Ontbrekende velden worden als lege string / None opgeslagen.
    """
    huidig = dict(llm_call_ctx.get() or {})
    huidig.update({k: v for k, v in velden.items() if v is not None})
    token = llm_call_ctx.set(huidig)
    try:
        yield
    finally:
        llm_call_ctx.reset(token)


class CapturingLLMClient:
    """LLMPort-decorator die elke call best-effort vastlegt. Passthrough als capture uit staat
    of als het analyse-id ontbreekt in de context."""

    def __init__(
        self,
        inner: LLMPort,
        calls_store: SqlAlchemyLlmCallsStore,
        config_store: RuntimeConfigStore,
    ) -> None:
        self._inner = inner
        self._calls = calls_store
        self._config = config_store

    async def complete(self, system: str, user: str, config: LlmConfig) -> LLMResult:
        try:
            result = await self._inner.complete(system, user, config)
        except Exception as exc:
            await self._leg_vast(system, user, config, resultaat=None, fout=repr(exc))
            raise
        await self._leg_vast(system, user, config, resultaat=result, fout=None)
        return result

    async def _leg_vast(
        self,
        system: str,
        user: str,
        config: LlmConfig,
        resultaat: LLMResult | None,
        fout: str | None,
    ) -> None:
        """Best-effort persist; nooit een exception naar buiten laten lekken."""
        try:
            if not await self._config.capture_ingeschakeld():
                return
            ctx = llm_call_ctx.get() or {}
            analyse_id = ctx.get("analyse_id")
            if not analyse_id:
                # Geen analyse-id → geen zinnige capture-rij mogelijk (tabel vereist het).
                return
            await self._calls.sla_op(
                analyse_id=analyse_id,
                activiteit=ctx.get("activiteit", ""),
                bron_id=ctx.get("bron_id"),
                system_prompt=system,
                user_prompt=user,
                ruwe_respons=(resultaat.tekst if resultaat else (fout or "")),
                model=(resultaat.model if resultaat else config.model) or "",
                tokens_in=resultaat.tokens_in if resultaat else 0,
                tokens_out=resultaat.tokens_out if resultaat else 0,
            )
        except Exception:  # noqa: BLE001 — capture is best-effort, nooit de call breken
            logger.warning("LLM-call-capture mislukt (genegeerd)", exc_info=True)
