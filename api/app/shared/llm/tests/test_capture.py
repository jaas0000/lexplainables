"""Gedragstests voor de capture-decorator.

We gebruiken twee fakes: een `LLMPort`-fake voor de inner client, en een lichte fake voor de
llm_calls- en runtime_config-stores. Dat houdt de test hermetisch — geen DB, geen litellm.
"""

from __future__ import annotations

import pytest

from app.shared.llm.base import LlmConfig, LLMResult
from app.shared.llm.capture import CapturingLLMClient, gebruik_context


class FakeLLMPort:
    """Fake LLMPort — retourneert een vaste respons of gooit een vooraf gezette exception."""

    def __init__(self, result: LLMResult | None = None, exc: Exception | None = None) -> None:
        self._result = result or LLMResult(
            tekst="antwoord", model="fake", tokens_in=1, tokens_out=2
        )
        self._exc = exc
        self.aanroepen: list[tuple[str, str]] = []

    async def complete(self, system: str, user: str, config: LlmConfig) -> LLMResult:
        self.aanroepen.append((system, user))
        if self._exc:
            raise self._exc
        return self._result


class FakeCallsStore:
    """Fake llm_calls-store: verzamelt calls in-memory zodat tests ze kunnen inspecteren."""

    def __init__(self, gooit: Exception | None = None) -> None:
        self.opgeslagen: list[dict] = []
        self._gooit = gooit

    async def sla_op(self, **kwargs) -> None:
        if self._gooit:
            raise self._gooit
        self.opgeslagen.append(kwargs)


class FakeConfigStore:
    """Fake runtime_config-store: retourneert de vooraf ingestelde toggle."""

    def __init__(self, aan: bool) -> None:
        self._aan = aan

    async def capture_ingeschakeld(self) -> bool:
        return self._aan


def _client(aan: bool, inner: FakeLLMPort | None = None, calls_gooit: Exception | None = None):
    inner = inner or FakeLLMPort()
    calls = FakeCallsStore(gooit=calls_gooit)
    return CapturingLLMClient(inner, calls, FakeConfigStore(aan=aan)), calls, inner


async def test_toggle_uit_slaat_niets_op():
    client, calls, _ = _client(aan=False)
    with gebruik_context(analyse_id="a", activiteit="test"):
        result = await client.complete("sys", "user", LlmConfig(model="gpt-4"))
    assert result.tekst == "antwoord"
    assert calls.opgeslagen == []


async def test_toggle_aan_slaat_op_met_context():
    client, calls, _ = _client(aan=True)
    with gebruik_context(analyse_id="a-123", activiteit="genereer", bron_id="bwbr-1"):
        await client.complete("sys-tekst", "user-tekst", LlmConfig(model="gpt-4"))
    assert len(calls.opgeslagen) == 1
    rij = calls.opgeslagen[0]
    assert rij["analyse_id"] == "a-123"
    assert rij["activiteit"] == "genereer"
    assert rij["bron_id"] == "bwbr-1"
    assert rij["system_prompt"] == "sys-tekst"
    assert rij["user_prompt"] == "user-tekst"
    assert rij["ruwe_respons"] == "antwoord"
    assert rij["tokens_in"] == 1
    assert rij["tokens_out"] == 2


async def test_zonder_analyse_id_geen_capture():
    """Als de context geen analyse_id draagt, wordt capture overgeslagen (tabel vereist het)."""
    client, calls, _ = _client(aan=True)
    # Geen `gebruik_context`-blok = lege context.
    await client.complete("sys", "user", LlmConfig(model="gpt-4"))
    assert calls.opgeslagen == []


async def test_capture_faal_breekt_call_niet(caplog):
    """Als sla_op() gooit, moet de call gewoon doorgaan met z'n resultaat — capture is
    best-effort. De fout wordt gelogd, niet doorgegooid."""
    client, _, _ = _client(aan=True, calls_gooit=RuntimeError("DB weg"))
    with gebruik_context(analyse_id="a"):
        result = await client.complete("sys", "user", LlmConfig(model="gpt-4"))
    assert result.tekst == "antwoord"


async def test_gefaalde_call_wordt_ook_vastgelegd():
    """Bij een fout in de inner client legt de decorator de gefaalde call vast met de repr
    van de exception als ruwe_respons — en gooit dan de originele fout door."""

    class ProviderFout(Exception):
        pass

    inner = FakeLLMPort(exc=ProviderFout("provider gaf op"))
    client, calls, _ = _client(aan=True, inner=inner)
    with gebruik_context(analyse_id="a", activiteit="test"):
        with pytest.raises(ProviderFout):
            await client.complete("sys", "user", LlmConfig(model="gpt-4"))

    assert len(calls.opgeslagen) == 1
    assert "provider gaf op" in calls.opgeslagen[0]["ruwe_respons"]


async def test_context_wordt_hersteld_na_blok():
    """Na het `gebruik_context`-blok is de context weer leeg."""
    client, calls, _ = _client(aan=True)

    with gebruik_context(analyse_id="a"):
        await client.complete("sys", "user", LlmConfig(model="gpt-4"))
    # Buiten het blok — geen analyse_id → geen capture.
    await client.complete("sys", "user", LlmConfig(model="gpt-4"))

    assert len(calls.opgeslagen) == 1
