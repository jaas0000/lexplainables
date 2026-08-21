"""LiteLLM-implementatie van `LLMPort` met bounded retry op transient errors.

De adapter kapselt provider-verschillen in (model-prefix, auth, timeout) en vertaalt
provider-fouten naar `LLMTransientFout`/`LLMPermanenteFout` zodat callers zonder litellm-kennis
kunnen redeneren over falen. Retry is bounded: N pogingen met exponentiële backoff, met respect
voor `Retry-After` uit een 429. Concurrency-rem via `throttle.llm_slot()`.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import time

from app.shared.observability import get_meter, get_tracer

from .base import LlmConfig, LLMFout, LLMPermanenteFout, LLMResult, LLMTransientFout
from .throttle import llm_slot

logger = logging.getLogger(__name__)

_tracer = get_tracer("app.shared.llm.client")
# Duur van een LLM-call in ms — histogram zodat percentiles zichtbaar worden. Bij no-op
# meter is dit een shim die niets doet.
_llm_call_duur_ms = get_meter("app.shared.llm.client").create_histogram(
    "llm_call_duration_ms",
    unit="ms",
    description="Wandklok-duur per LLM-call (inclusief retry-wachttijd).",
)

# Bounded retry-knoppen — env, met veilige defaults. 0 zet retry uit.
_MAX_POGINGEN = int(os.environ.get("LLM_RETRY_MAX", "3"))
_BACKOFF_S = float(os.environ.get("LLM_RETRY_BACKOFF_S", "2"))
_MAX_BACKOFF_S = float(os.environ.get("LLM_RETRY_MAX_BACKOFF_S", "60"))


def _is_transient(exc: BaseException) -> bool:
    """Kwalificeer een litellm-fout als transient (mag retryed worden)."""
    naam = type(exc).__name__
    if naam in {
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
        "APIConnectionError",
        "Timeout",
        "APIError",
    }:
        return True
    # HTTP-status uit litellm's ML-hiërarchie (BadRequestError → 400 = permanent).
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status >= 500:
        return True
    if status == 429:
        return True
    return False


def _retry_after(exc: BaseException) -> float | None:
    """Lees `Retry-After` uit een 429 als de provider die meestuurt (litellm exposeert vaak
    `.retry_after` of het onderliggende `response.headers['retry-after']`)."""
    val = getattr(exc, "retry_after", None)
    if val is not None:
        try:
            return float(val)
        except (TypeError, ValueError):
            pass
    resp = getattr(exc, "response", None)
    if resp is not None:
        headers = getattr(resp, "headers", None) or {}
        raw = headers.get("retry-after") if hasattr(headers, "get") else None
        if raw:
            try:
                return float(raw)
            except (TypeError, ValueError):
                pass
    return None


def _wachttijd(poging: int, retry_after_s: float | None) -> float:
    """Backoff met jitter; honoreer `Retry-After` als de provider die meestuurt (met plafond)."""
    if retry_after_s is not None:
        return min(retry_after_s, _MAX_BACKOFF_S)
    basis = _BACKOFF_S * (2 ** (poging - 1))
    jitter = random.uniform(0, basis * 0.25)  # noqa: S311 — niet cryptografisch, alleen jitter
    return min(basis + jitter, _MAX_BACKOFF_S)


class LitellmClient:
    """`LLMPort`-implementatie via `litellm.acompletion`.

    De adapter is stateless — één instance kan door meerdere callers met verschillende `LlmConfig`
    gedeeld worden (de config gaat per-call mee). Retry-parameters komen uit env, niet uit config,
    omdat het beleid uniform hoort te zijn per proces.
    """

    async def complete(self, system: str, user: str, config: LlmConfig) -> LLMResult:
        if not config.model:
            raise LLMPermanenteFout("LLM-model niet geconfigureerd.")

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        laatste_fout: BaseException | None = None
        start = time.perf_counter()
        with _tracer.start_as_current_span("llm.complete") as span:
            span.set_attribute("llm.provider", config.provider)
            span.set_attribute("llm.model", config.model)
            for poging in range(1, max(_MAX_POGINGEN, 1) + 1):
                try:
                    async with llm_slot():
                        resp = await self._call_litellm(config, messages)
                    tekst = resp.choices[0].message.content or ""
                    usage = getattr(resp, "usage", None)
                    tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
                    tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
                    span.set_attribute("llm.tokens.in", tokens_in)
                    span.set_attribute("llm.tokens.out", tokens_out)
                    span.set_attribute("llm.pogingen", poging)
                    _llm_call_duur_ms.record(
                        (time.perf_counter() - start) * 1000,
                        {"provider": config.provider, "model": config.model, "ok": "true"},
                    )
                    return LLMResult(
                        tekst=tekst,
                        model=getattr(resp, "model", config.model) or config.model,
                        provider=config.provider,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                    )
                except LLMFout as exc:
                    span.record_exception(exc)
                    _llm_call_duur_ms.record(
                        (time.perf_counter() - start) * 1000,
                        {"provider": config.provider, "model": config.model, "ok": "false"},
                    )
                    raise
                except Exception as exc:  # noqa: BLE001 — vertaal provider-fout naar LLM*Fout
                    laatste_fout = exc
                    if not _is_transient(exc) or poging >= _MAX_POGINGEN:
                        span.record_exception(exc)
                        _llm_call_duur_ms.record(
                            (time.perf_counter() - start) * 1000,
                            {"provider": config.provider, "model": config.model, "ok": "false"},
                        )
                        if _is_transient(exc):
                            raise LLMTransientFout(
                                f"LLM-call transient gefaald na {poging} pogingen: {exc}",
                                retry_after_s=_retry_after(exc),
                            ) from exc
                        raise LLMPermanenteFout(f"LLM-call permanent gefaald: {exc}") from exc
                    wacht = _wachttijd(poging, _retry_after(exc))
                    logger.info(
                        "LLM-call transient gefaald (poging %d/%d), wacht %.1fs: %s",
                        poging,
                        _MAX_POGINGEN,
                        wacht,
                        type(exc).__name__,
                    )
                    await asyncio.sleep(wacht)
        # Onbereikbaar — de laatste iteratie raist altijd. Zekerheidshalve:
        raise LLMTransientFout(
            f"LLM-call onverwacht buiten de retry-lus zonder resultaat: {laatste_fout}"
        )

    async def _call_litellm(self, config: LlmConfig, messages: list[dict]):
        """Wrapper rond `litellm.acompletion`; apart zodat tests deze mock'en zonder de
        retry/throttle-logica te hoeven vervangen."""
        import litellm

        kwargs: dict = {"temperature": config.temperature}
        if config.api_base:
            kwargs["api_base"] = config.api_base
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.api_version:
            kwargs["api_version"] = config.api_version
        if config.timeout:
            kwargs["timeout"] = config.timeout
        model_ref = config.model if "/" in config.model else f"{config.provider}/{config.model}"
        return await litellm.acompletion(model=model_ref, messages=messages, **kwargs)
