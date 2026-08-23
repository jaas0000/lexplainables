"""semantic_search: MCPClient bouwt de juiste similarity_search-argumenten.

Poort van `wetsanalyse-ai/tools/graph-qa/tests/test_mcp_client.py`, 1:1 (werkwijze-story 040).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.mcp_client import MCPClient, MCPError
from agent.ports import GraphPort


def test_mcpclient_voldoet_aan_graphport() -> None:
    assert isinstance(MCPClient(url="http://x/mcp", token="t"), GraphPort)


def test_semantic_search_gebruikt_similarity_search() -> None:
    c = MCPClient(
        url="http://x/mcp", token="t", repository_id="inning", similarity_index="bwb_similarity"
    )
    captured: dict = {}

    def _fake_call_tool(name, arguments):
        captured["name"] = name
        captured["arguments"] = arguments
        return [{"type": "text", "text": "resultaat"}]

    c.call_tool = _fake_call_tool  # type: ignore[assignment]
    out = c.semantic_search("belasting niet op tijd betaald", limit=5)

    assert out == "resultaat"
    assert captured["name"] == "similarity_search"
    args = captured["arguments"]
    assert args["similarityIndex"] == "bwb_similarity"
    assert args["connectorType"] == "similarity"
    assert args["repositoryId"] == "inning"
    assert args["query"] == "belasting niet op tijd betaald"


def test_rpc_non_2xx_zonder_result_raist(monkeypatch) -> None:
    # Een 5xx met een JSON-body zonder `result`/`error` mag niet stil een leeg resultaat geven.
    c = MCPClient(url="http://x/mcp", token="t", repository_id="inning")
    resp = SimpleNamespace(
        status_code=500,
        headers={"content-type": "application/json"},
        json=lambda: {"jsonrpc": "2.0", "id": 1},  # geen result, geen error
        text="internal error",
    )
    monkeypatch.setattr(c._client, "post", lambda *a, **k: resp)
    with pytest.raises(MCPError) as exc:
        c._rpc("tools/call", {"name": "x", "arguments": {}})
    assert "500" in str(exc.value)


def test_rpc_2xx_result_ok(monkeypatch) -> None:
    # Regressie: een gewone 200 met result blijft werken (statuscheck raakt het happy-path niet).
    c = MCPClient(url="http://x/mcp", token="t", repository_id="inning")
    resp = SimpleNamespace(
        status_code=200,
        headers={"content-type": "application/json"},
        json=lambda: {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "ok"}]},
        },
        text="",
    )
    monkeypatch.setattr(c._client, "post", lambda *a, **k: resp)
    assert c.call_tool("x", {}) == [{"type": "text", "text": "ok"}]


def test_eerste_call_doet_lazy_initialize_handshake(monkeypatch) -> None:
    """Live geverifieerd tegen GraphDB 11.4.0: die weigert `tools/call` zonder eerst een sessie
    te openen via `initialize` (400 `McpError`, geen `Mcp-Session-Id`-header). Anders dan de
    referentie-app (die nergens expliciet `initialize()` aanroept) moet deze client dat zelf
    lazy doen, één keer per instantie."""
    c = MCPClient(url="http://x/mcp", token="t", repository_id="inning")
    methods: list[str] = []

    def _fake_post(url, json, headers):
        methods.append(json["method"])
        if json["method"] == "initialize":
            return SimpleNamespace(
                status_code=200,
                headers={"content-type": "application/json", "Mcp-Session-Id": "sess-1"},
                json=lambda: {"jsonrpc": "2.0", "id": 1, "result": {}},
                text="",
            )
        return SimpleNamespace(
            status_code=200,
            headers={"content-type": "application/json"},
            json=lambda: {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"content": [{"type": "text", "text": "ok"}]},
            },
            text="",
        )

    monkeypatch.setattr(c._client, "post", _fake_post)

    assert c.call_tool("x", {}) == [{"type": "text", "text": "ok"}]
    assert methods == ["initialize", "tools/call"]
    assert c._session_id == "sess-1"

    # Tweede aanroep: sessie staat al, geen herhandshake meer.
    methods.clear()
    assert c.call_tool("x", {}) == [{"type": "text", "text": "ok"}]
    assert methods == ["tools/call"]
