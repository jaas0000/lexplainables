"""Tests voor de LLMPort-adapter (werkwijze-story 039).

Unit-tests draaien tegen een stub-client (geen netwerk); `_StubClient` bootst alleen het stukje
`anthropic`-oppervlak na dat de adapter aanraakt (`messages.create`/`messages.stream`). De ene
`@pytest.mark.integration`-test onderaan raakt de echte Foundry-resource en is standaard geskipt.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from agent.adapters.anthropic_llm import AnthropicLLM, _AnthropicStream
from agent.config import Settings
from agent.ports import LLMPort


def _settings(**overrides: object) -> Settings:
    return Settings(azure_foundry_api_key="k", azure_foundry_resource="r", **overrides)


def _bad_request(message: str) -> anthropic.BadRequestError:
    req = httpx2.Request("POST", "http://x")
    resp = httpx2.Response(400, request=req, json={"error": {"message": message}})
    return anthropic.BadRequestError(message, response=resp, body=None)


class _StubStreamManager:
    """Bootst de context-manager na die `anthropic`'s `messages.stream()` teruggeeft."""

    def __init__(self, outcome: object) -> None:
        self._outcome = outcome

    def __enter__(self) -> SimpleNamespace:
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return SimpleNamespace(
            text_stream=iter(["een", "twee"]),
            get_final_message=lambda: self._outcome,
        )

    def __exit__(self, *exc: object) -> bool:
        return False


class _StubMessages:
    """Speelt een vaste reeks uitkomsten af (response óf exception) via `create()`/`stream()`."""

    def __init__(self, plan: list[object]) -> None:
        self._plan = list(plan)
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        item = self._plan.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def stream(self, **kwargs: object) -> _StubStreamManager:
        self.calls.append(kwargs)
        return _StubStreamManager(self._plan.pop(0))


class _StubClient:
    def __init__(self, plan: list[object]) -> None:
        self.messages = _StubMessages(plan)


# --- Protocol-conformance ---


def test_anthropic_llm_voldoet_aan_llmport() -> None:
    llm = AnthropicLLM(_settings(), client=_StubClient([]))
    assert isinstance(llm, LLMPort)


# --- _system: cache-punt-logica ---


def test_system_enkele_string_ongewijzigd() -> None:
    llm = AnthropicLLM(_settings(), client=_StubClient([]))
    assert llm._system("hallo") == "hallo"


def test_system_korte_lijst_wordt_samengevoegd_zonder_cache_control() -> None:
    llm = AnthropicLLM(_settings(), client=_StubClient([]))
    assert llm._system(["stabiel", "variabel"]) == "stabiel\n\nvariabel"


def test_system_lange_lijst_krijgt_cache_control_op_stabiel_deel() -> None:
    llm = AnthropicLLM(_settings(), client=_StubClient([]))
    stabiel = "x" * 4000

    result = llm._system([stabiel, "variabel"])

    assert result == [
        {"type": "text", "text": stabiel, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "variabel"},
    ]


def test_system_caching_uit_geeft_nooit_cache_blok() -> None:
    llm = AnthropicLLM(_settings(prompt_caching=False), client=_StubClient([]))
    stabiel = "x" * 4000

    assert llm._system([stabiel, "variabel"]) == f"{stabiel}\n\nvariabel"


# --- create() ---


def test_create_gelukkig_pad_geeft_response_door() -> None:
    resp = SimpleNamespace(content=[], stop_reason="end_turn")
    client = _StubClient([resp])
    llm = AnthropicLLM(_settings(), client=client)

    result = llm.create(model="m", max_tokens=10, system="s", tools=[], messages=[])

    assert result is resp
    assert client.messages.calls[0]["system"] == "s"


def test_create_bad_request_met_cache_control_retryt_zonder_caching() -> None:
    resp = SimpleNamespace(content=[], stop_reason="end_turn")
    client = _StubClient([_bad_request("cache_control is not supported"), resp])
    llm = AnthropicLLM(_settings(), client=client)

    result = llm.create(model="m", max_tokens=10, system="s", tools=[], messages=[])

    assert result is resp
    assert llm._caching is False
    assert len(client.messages.calls) == 2


def test_create_bad_request_zonder_cache_control_wordt_doorgegooid() -> None:
    client = _StubClient([_bad_request("model niet gevonden")])
    llm = AnthropicLLM(_settings(), client=client)

    with pytest.raises(anthropic.BadRequestError):
        llm.create(model="m", max_tokens=10, system="s", tools=[], messages=[])

    assert llm._caching is True
    assert len(client.messages.calls) == 1


# --- stream() ---


def test_stream_gelukkig_pad() -> None:
    resp = SimpleNamespace(content=[], stop_reason="end_turn")
    client = _StubClient([resp])
    llm = AnthropicLLM(_settings(), client=client)

    with llm.stream(model="m", max_tokens=10, system="s", tools=[], messages=[]) as stream:
        assert isinstance(stream, _AnthropicStream)
        assert list(stream.text_deltas) == ["een", "twee"]
        assert stream.final_message() is resp


def test_stream_bad_request_met_cache_control_retryt_zonder_caching() -> None:
    resp = SimpleNamespace(content=[], stop_reason="end_turn")
    client = _StubClient([_bad_request("cache_control is not supported"), resp])
    llm = AnthropicLLM(_settings(), client=client)

    with llm.stream(model="m", max_tokens=10, system="s", tools=[], messages=[]) as stream:
        assert stream.final_message() is resp

    assert llm._caching is False
    assert len(client.messages.calls) == 2


def test_stream_bad_request_zonder_cache_control_wordt_doorgegooid() -> None:
    client = _StubClient([_bad_request("model niet gevonden")])
    llm = AnthropicLLM(_settings(), client=client)

    with (
        pytest.raises(anthropic.BadRequestError),
        llm.stream(model="m", max_tokens=10, system="s", tools=[], messages=[]),
    ):
        pass

    assert len(client.messages.calls) == 1


# --- integration (standaard geskipt) ---


@pytest.mark.integration
def test_live_create_tegen_foundry() -> None:
    settings = Settings.from_env(os.environ)
    if not settings.azure_foundry_api_key or not settings.azure_foundry_resource:
        pytest.skip("AZURE_FOUNDRY_API_KEY(_FILE)/AZURE_FOUNDRY_RESOURCE niet in de omgeving")

    llm = AnthropicLLM(settings)

    response = llm.create(
        model=settings.llm_model,
        max_tokens=16,
        system="Antwoord in precies één woord.",
        tools=[],
        messages=[{"role": "user", "content": "Zeg 'ja'."}],
    )

    assert response.stop_reason in ("end_turn", "max_tokens")
    assert any(block.type == "text" for block in response.content)
