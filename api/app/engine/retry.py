"""Bounded retry met exponentiële backoff op transiënte LLM/MCP-fouten (story 024).

Vereenvoudigd t.o.v. wetsanalyse-ai: geen Retry-After-header, geen WettenbankError-klassen.
"""

from __future__ import annotations

import asyncio
import logging
import random

from ..shared.wettenbank import WettenbankFout

logger = logging.getLogger(__name__)

# LiteLLM-exceptieklassen die een tijdelijke conditie aanduiden.
# Gebruik isinstance voor robuustheid; val terug op een lege tuple als litellm niet beschikbaar is.
try:
    import litellm as _litellm

    _TRANSIENTE_LLM_TYPES: tuple = (
        _litellm.RateLimitError,
        _litellm.Timeout,
        _litellm.APITimeoutError,
        _litellm.APIConnectionError,
        _litellm.InternalServerError,
        _litellm.ServiceUnavailableError,
    )
except (ImportError, AttributeError):
    _TRANSIENTE_LLM_TYPES = ()

_TRANSIENTE_STATUS = {429, 500, 502, 503, 504}


def is_transient(e: BaseException) -> bool:
    """Geeft True als de fout tijdelijk is en opnieuw proberen zin heeft."""
    if isinstance(e, WettenbankFout):
        return True  # netwerk/timeout — altijd transiënt (permanent = nep-MCP-fout)
    if _TRANSIENTE_LLM_TYPES and isinstance(e, _TRANSIENTE_LLM_TYPES):
        return True
    for http_status in (
        getattr(e, "status_code", None),
        getattr(getattr(e, "response", None), "status_code", None),
    ):
        if isinstance(http_status, int) and http_status in _TRANSIENTE_STATUS:
            return True
    return False


async def met_retry(maak, *, max_retries: int = 3, backoff: float = 2.0, max_backoff: float = 30.0):
    """Roep de coroutine-factory `maak` aan; herhaal bij een transiënte fout.

    Wachttijd = exponentiële backoff met jitter, begrensd op `max_backoff`.
    """
    poging = 0
    while True:
        try:
            return await maak()
        except Exception as e:  # noqa: BLE001
            if poging >= max_retries or not is_transient(e):
                raise
            basis = backoff * (2**poging)
            wacht = min(basis, max_backoff)
            wacht += random.uniform(0, min(wacht, max_backoff) * 0.25)
            logger.warning(
                "Transiënte fout (%s); retry %d/%d na %.1fs",
                type(e).__name__,
                poging + 1,
                max_retries,
                wacht,
            )
            await asyncio.sleep(wacht)
            poging += 1
