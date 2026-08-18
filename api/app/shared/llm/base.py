"""LLMClient-protocol + resultaattype en parse-hulpfuncties.

Gedeelde module (feature-bouwen regel 8): geen natuurlijke eigenaar-feature —
de LLM-client is infrastructurele zorg, niet gebonden aan één domein.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Protocol

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass
class LlmConfig:
    """Resolved configuratie voor één LLM-call — afgeleid uit een modelprofiel."""

    provider: str = "openai"
    model: str = ""
    api_base: str = ""
    api_key: str | None = None
    api_version: str | None = None
    temperature: float = 0.0


@dataclass
class LLMResult:
    data: dict
    model: str = ""
    provider: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    ruwe_tekst: str = field(default="", repr=False)


class LLMError(RuntimeError):
    """Het LLM leverde geen bruikbare/parseerbare JSON na een reparatiepoging."""


class LLMClient(Protocol):
    async def complete(self, system: str, user: str) -> LLMResult:
        """Genereer JSON. Werpt LLMError bij onparseerbaar resultaat."""
        ...


def parse_json_strict(tekst: str) -> dict:
    """Parse JSON; strip defensief code-fences en eventuele preamble vóór het eerste '{'."""
    kandidaat = _FENCE.sub("", tekst.strip())
    try:
        return json.loads(kandidaat)
    except json.JSONDecodeError:
        start = kandidaat.find("{")
        end = kandidaat.rfind("}")
        if start != -1 and end > start:
            return json.loads(kandidaat[start : end + 1])
        raise
