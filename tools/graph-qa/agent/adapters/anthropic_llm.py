"""LLMPort-adapter voor Anthropic via Azure AI Foundry (werkwijze-story 039).

Hier zit de enige plek die de concrete Anthropic-client en de prompt-caching kent. Poort van
`wetsanalyse-ai/tools/graph-qa/agent/adapters/anthropic_llm.py`, met één bewuste afwijking: de
referentie gebruikt `anthropic.Anthropic(base_url=..., default_query={"api-version": ...})` — een
generieke client met een Foundry-URL erin geplakt. Deze adapter gebruikt in plaats daarvan de
dedicated `anthropic.AnthropicFoundry(api_key=..., resource=...)`-client (de door Anthropic
aanbevolen weg voor Azure AI Foundry), live geverifieerd tegen de projectresource vóór deze story
gebouwd werd.
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from ..config import Settings
from ..ports import Systeem

logger = logging.getLogger("graph_qa.llm")

# Onder deze lengte heeft cachen geen zin. Het minimum cachebare voorvoegsel is modelafhankelijk
# (1024 tokens op de sonnet-4.6-klasse); daaronder slaat de provider de cache stilzwijgend over —
# geen fout, alleen de duurdere write zonder ooit een hit. Nederlands tokeniseert op ~3,5 tekens
# per token, dus 4000 tekens ≈ 1150 tokens: net boven het minimum, bewust aan de veilige kant.
# Zelfde drempel-redenering als de referentie-adapter.
_MIN_CACHE_TEKENS = 4000


class AnthropicLLM:
    """Dunne, blocking implementatie van LLMPort."""

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        settings.require_llm()
        self._caching = settings.prompt_caching
        self._client = client or anthropic.AnthropicFoundry(
            api_key=settings.azure_foundry_api_key,
            resource=settings.azure_foundry_resource,
        )

    def _system(self, system: Systeem, *, caching: bool | None = None) -> Any:
        """Zet het systeemblok om naar de vorm die de provider wil, met een cache-punt.

        Prompt-caching is een **prefix-match**: de provider hasht de gerenderde prompt tot aan het
        cache-punt, dus alles wat vóór dat punt staat moet byte-voor-byte gelijk zijn tussen calls.
        Vandaar de splitsing: de aanroeper levert het stabiele deel (identiteit, vaste instructies)
        apart van het variabele (de context van deze beurt), en het cache-punt gaat op het laatste
        stabiele blok.
        """
        aan = self._caching if caching is None else caching
        delen = [system] if isinstance(system, str) else [d for d in system if d]
        if not aan or not delen:
            return "\n\n".join(delen)

        stabiel = "\n\n".join(delen[:-1]) if len(delen) > 1 else delen[0]
        variabel = delen[-1] if len(delen) > 1 else ""
        if len(stabiel) < _MIN_CACHE_TEKENS:
            # Te kort om te cachen: één blok, geen cache-punt. Anders betaal je de (duurdere)
            # cache-write voor een voorvoegsel dat toch nooit als hit terugkomt.
            return "\n\n".join(d for d in (stabiel, variabel) if d)

        blokken: list[dict[str, Any]] = [
            {"type": "text", "text": stabiel, "cache_control": {"type": "ephemeral"}}
        ]
        if variabel:
            blokken.append({"type": "text", "text": variabel})
        return blokken

    def _zonder_caching(self, exc: Exception) -> bool:
        """Weigerde de provider het cache-punt? Zet caching uit en meld het één keer.

        Prompt-caching is op Azure AI Foundry een beta-functie. Zou hij `cache_control` niet
        accepteren, dan faalt zonder deze terugval elke LLM-call — en daarmee de hele agent. De
        prijs van caching mag nooit "de dienst ligt plat" zijn.
        """
        if not self._caching or "cache_control" not in str(exc):
            return False
        self._caching = False
        logger.warning(
            "prompt-caching geweigerd door de provider; voortaan zonder cache-punt",
            extra={"categorie": "technisch", "fout": str(exc)[:200]},
        )
        return True

    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        system: Systeem,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
    ) -> Any:
        try:
            return self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=self._system(system),
                tools=tools,
                messages=messages,
            )
        except anthropic.BadRequestError as exc:
            if not self._zonder_caching(exc):
                raise
            return self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=self._system(system),
                tools=tools,
                messages=messages,
            )

    def stream(
        self,
        *,
        model: str,
        max_tokens: int,
        system: Systeem,
        tools: list[dict[str, Any]],
        messages: list[dict[str, Any]],
    ) -> _AnthropicStream:
        # Bij streamen valt een weigering pas bij het openen van de stream (daar gaat de call de
        # deur uit), dus de terugval zit in `_AnthropicStream.__enter__` — met deze fabriek als
        # tweede poging.
        def open_stream(*, caching: bool):
            return self._client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=self._system(system, caching=caching),
                tools=tools,
                messages=messages,
            )

        return _AnthropicStream(
            open_stream(caching=self._caching),
            opnieuw=open_stream,
            terugval=self._zonder_caching,
        )


class _AnthropicStream:
    """Dunne wrapper om de Anthropic MessageStream (LLMStream-protocol)."""

    def __init__(self, manager: Any, opnieuw: Any = None, terugval: Any = None) -> None:
        self._manager = manager
        self._stream: Any = None
        self._opnieuw = opnieuw  # zelfde call, maar zonder cache-punt
        self._terugval = terugval  # beslist of de fout over caching ging

    def __enter__(self) -> _AnthropicStream:
        try:
            self._stream = self._manager.__enter__()
        except anthropic.BadRequestError as exc:
            if not (self._terugval and self._opnieuw and self._terugval(exc)):
                raise
            self._manager = self._opnieuw(caching=False)
            self._stream = self._manager.__enter__()
        return self

    def __exit__(self, *exc: Any) -> Any:
        return self._manager.__exit__(*exc)

    @property
    def text_deltas(self) -> Any:
        return self._stream.text_stream

    def final_message(self) -> Any:
        return self._stream.get_final_message()
