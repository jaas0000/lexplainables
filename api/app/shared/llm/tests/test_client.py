"""Gedragstests voor de LitellmClient — retry-logica, fout-mapping, model-referentie.

We mock'en `_call_litellm` in plaats van `litellm.acompletion` zelf, zodat we niet in de
provider-SDK hoeven te grijpen. Dat test wat we willen testen (retry/mapping) zonder de
externe interface na te bootsen.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.shared.llm import throttle
from app.shared.llm.base import LlmConfig, LLMPermanenteFout, LLMTransientFout
from app.shared.llm.client import LitellmClient


@pytest.fixture(autouse=True)
def reset_throttle():
    throttle.configure(0)
    yield
    throttle.configure(0)


def _resp(tekst: str, model: str = "test-model", tokens_in: int = 10, tokens_out: int = 20):
    """Bouw een minimale litellm-achtige respons — genoeg voor de client om uit te lezen."""
    keuze = SimpleNamespace(message=SimpleNamespace(content=tekst))
    usage = SimpleNamespace(prompt_tokens=tokens_in, completion_tokens=tokens_out)
    return SimpleNamespace(choices=[keuze], usage=usage, model=model)


async def test_complete_gelukkig_pad(monkeypatch):
    """Eén succesvolle call → LLMResult met tekst + telemetrie."""
    client = LitellmClient()

    async def mock_call(config, messages):
        return _resp("hallo wereld", model="mocked", tokens_in=5, tokens_out=7)

    monkeypatch.setattr(client, "_call_litellm", mock_call)

    result = await client.complete("sys", "user", LlmConfig(model="gpt-4"))
    assert result.tekst == "hallo wereld"
    assert result.model == "mocked"
    assert result.tokens_in == 5
    assert result.tokens_out == 7


async def test_leeg_model_faalt_permanent():
    """Een LlmConfig zonder model → LLMPermanenteFout vóór er iets naar de provider gaat."""
    client = LitellmClient()
    with pytest.raises(LLMPermanenteFout):
        await client.complete("sys", "user", LlmConfig(model=""))


async def test_retry_op_transient_error(monkeypatch):
    """Een transient error (RateLimitError) retryed en slaagt de tweede poging."""

    class RateLimitError(Exception):
        pass

    pogingen = 0

    async def mock_call(config, messages):
        nonlocal pogingen
        pogingen += 1
        if pogingen == 1:
            raise RateLimitError("throttled")
        return _resp("succes na retry")

    monkeypatch.setattr("app.shared.llm.client._BACKOFF_S", 0.001)
    monkeypatch.setattr("app.shared.llm.client._MAX_BACKOFF_S", 0.001)

    client = LitellmClient()
    monkeypatch.setattr(client, "_call_litellm", mock_call)

    result = await client.complete("sys", "user", LlmConfig(model="gpt-4"))
    assert result.tekst == "succes na retry"
    assert pogingen == 2


async def test_retry_uitgeput_gooit_transient(monkeypatch):
    """Als alle retry-pogingen falen met een transient error → LLMTransientFout."""

    class InternalServerError(Exception):
        pass

    async def mock_call(config, messages):
        raise InternalServerError("still broken")

    monkeypatch.setattr("app.shared.llm.client._MAX_POGINGEN", 2)
    monkeypatch.setattr("app.shared.llm.client._BACKOFF_S", 0.001)
    monkeypatch.setattr("app.shared.llm.client._MAX_BACKOFF_S", 0.001)

    client = LitellmClient()
    monkeypatch.setattr(client, "_call_litellm", mock_call)

    with pytest.raises(LLMTransientFout):
        await client.complete("sys", "user", LlmConfig(model="gpt-4"))


async def test_permanente_fout_retryed_niet(monkeypatch):
    """Een 400-achtige fout (BadRequest) is permanent → geen retry, direct doorgooien."""

    class BadRequestError(Exception):
        status_code = 400

    aantal = 0

    async def mock_call(config, messages):
        nonlocal aantal
        aantal += 1
        raise BadRequestError("nope")

    client = LitellmClient()
    monkeypatch.setattr(client, "_call_litellm", mock_call)

    with pytest.raises(LLMPermanenteFout):
        await client.complete("sys", "user", LlmConfig(model="gpt-4"))
    assert aantal == 1  # geen retry


async def test_retry_after_wordt_gehonoreerd(monkeypatch):
    """Een 429 met `.retry_after`-attribuut wordt gebruikt in plaats van backoff-berekening."""

    class RateLimitError(Exception):
        retry_after = 0.005  # 5ms — heel klein, zodat de test snel is

    pogingen = 0

    async def mock_call(config, messages):
        nonlocal pogingen
        pogingen += 1
        if pogingen == 1:
            raise RateLimitError("throttled")
        return _resp("ok")

    monkeypatch.setattr("app.shared.llm.client._MAX_BACKOFF_S", 1.0)
    client = LitellmClient()
    monkeypatch.setattr(client, "_call_litellm", mock_call)

    result = await client.complete("sys", "user", LlmConfig(model="gpt-4"))
    assert result.tekst == "ok"
