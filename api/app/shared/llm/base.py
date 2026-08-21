"""Kern-contracten van de LLM-toegangslaag.

Klein en generiek gehouden: één `complete()`-signature (system + user → tekst-antwoord +
telemetrie), geen JSON-schema-parsing, geen streaming, geen prompt-caching-slimmigheden. Die
uitbreidingen komen mee met de eerste concrete consumer (graph-qa in fase 4, of eerdere feature
die het nodig heeft).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class LlmConfig:
    """Resolved configuratie voor één LLM-call — afgeleid uit een modelprofiel of env-fallback."""

    provider: str = "azure_ai"
    model: str = ""
    api_base: str = ""
    api_key: str | None = None
    api_version: str | None = None
    temperature: float = 0.0
    # Wandklok-timeout per call in seconden (0 = geen expliciete timeout).
    timeout: float = 0.0


@dataclass
class LLMResult:
    """Resultaat van één succesvolle LLM-call."""

    tekst: str = field(default="", repr=False)
    model: str = ""
    provider: str = ""
    tokens_in: int = 0
    tokens_out: int = 0


class LLMFout(RuntimeError):
    """Basisklasse voor LLM-adapter-fouten (netwerk/provider). Erf voor specifieke gevallen."""


class LLMTransientFout(LLMFout):
    """Transient — mag geretryed worden (429, 5xx, netwerk-hiccup)."""

    def __init__(self, bericht: str, retry_after_s: float | None = None) -> None:
        super().__init__(bericht)
        self.retry_after_s = retry_after_s


class LLMPermanenteFout(LLMFout):
    """Permanent — retryen lost het niet op (auth-fout, 4xx anders dan 429)."""


@runtime_checkable
class LLMPort(Protocol):
    """Async LLM-client. Alle adapters (litellm, capture-wrapper, fake in tests) voldoen hieraan."""

    async def complete(self, system: str, user: str, config: LlmConfig) -> LLMResult:
        """Doe één LLM-call. Werpt `LLMTransientFout` of `LLMPermanenteFout` bij falen."""
        ...
