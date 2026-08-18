"""LiteLLM-implementatie van LLMClient (vereenvoudigd t.o.v. wetsanalyse-ai).

Geen json_object response_format, geen prompt_caching, geen throttle-semafoor.
De caller (orchestrator) draait zelf auto-correctie op schema-validatiefouten.
"""

from __future__ import annotations

import json

from .base import LlmConfig, LLMError, LLMResult, parse_json_strict

_REPAREER = (
    "Je vorige antwoord was geen geldige JSON. Geef UITSLUITEND geldig JSON terug dat exact "
    "voldoet aan het gevraagde schema. Geen uitleg, geen markdown-fences."
)


class LiteLLMClient:
    def __init__(self, config: LlmConfig) -> None:
        self.c = config
        if not config.model:
            raise RuntimeError("LLM-model niet geconfigureerd (leeg in profiel).")
        # Eenmalig berekend: config is immutable na constructie.
        model = config.model
        self._model_ref: str = model if "/" in model else f"{config.provider}/{model}"
        kw: dict = {"temperature": config.temperature}
        if config.api_base:
            kw["api_base"] = config.api_base
        if config.api_key:
            kw["api_key"] = config.api_key
        if config.api_version:
            kw["api_version"] = config.api_version
        self._kwargs: dict = kw

    async def complete(self, system: str, user: str) -> LLMResult:
        import litellm

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        resp = await litellm.acompletion(model=self._model_ref, messages=messages, **self._kwargs)
        tekst = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        tokens_in = getattr(usage, "prompt_tokens", 0) or 0
        tokens_out = getattr(usage, "completion_tokens", 0) or 0

        try:
            data = parse_json_strict(tekst)
        except json.JSONDecodeError:
            # Één gerichte repareer-retry bij JSON-parse-fout.
            messages.append({"role": "assistant", "content": tekst})
            messages.append({"role": "user", "content": _REPAREER})
            resp = await litellm.acompletion(
                model=self._model_ref, messages=messages, **self._kwargs
            )
            tekst = resp.choices[0].message.content or ""
            usage = getattr(resp, "usage", None)
            tokens_in += getattr(usage, "prompt_tokens", 0) or 0
            tokens_out += getattr(usage, "completion_tokens", 0) or 0
            try:
                data = parse_json_strict(tekst)
            except json.JSONDecodeError as e:
                raise LLMError(f"Geen geldige JSON na reparatie: {e}") from e

        return LLMResult(
            data=data,
            model=getattr(resp, "model", self.c.model) or self.c.model,
            provider=self.c.provider,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            ruwe_tekst=tekst,
        )


def bouw_llm_client(config: LlmConfig) -> LiteLLMClient:
    """Factory — nu altijd LiteLLM."""
    return LiteLLMClient(config)
