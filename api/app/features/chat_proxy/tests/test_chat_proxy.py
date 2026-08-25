"""Gedragstests voor de chat-proxy (story 055): `POST /v1/chat` → graph-qa.

`httpx.MockTransport` injecteert de HTTP-laag op de proces-brede client (zelfde patroon als
`shared/tests/test_wettenbank.py`) — geen echte graph-qa-server nodig voor deze tests.
"""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app.features.chat_proxy.client as chat_proxy_client
from app.main import app


def _sse_response(events: list[dict]) -> httpx.Response:
    body = "".join(f"data: {json.dumps(e)}\n\n" for e in events)
    return httpx.Response(200, content=body.encode())


@pytest.fixture(autouse=True)
def _reset_client(monkeypatch):
    monkeypatch.setattr(chat_proxy_client, "_client", None)
    yield
    monkeypatch.setattr(chat_proxy_client, "_client", None)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    from app.shared.rate_limit import wis

    wis()
    yield
    wis()


def _monkeypatch_transport(monkeypatch, handler) -> None:
    monkeypatch.setattr(
        chat_proxy_client,
        "_client",
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


def _parse_sse(text: str) -> list[dict]:
    events = []
    for blok in text.split("\n\n"):
        for regel in blok.splitlines():
            if regel.startswith("data:"):
                events.append(json.loads(regel[len("data:") :].strip()))
    return events


def test_zonder_auth_geeft_401() -> None:
    """Losse, kale `TestClient` — geen `huidige_beheerder`-override, dus het echte 401-pad."""
    with TestClient(app) as kaal_client:
        resp = kaal_client.post("/v1/chat", json={"question": "Wat is een belastingschuldige?"})

    assert resp.status_code == 401


def test_events_worden_ongewijzigd_doorgegeven(client, monkeypatch) -> None:
    canned = [
        {"type": "token", "content": "hoi"},
        {"type": "sources", "sources": []},
        {"type": "grounding", "grounded": True, "niveau": "gegrond"},
        {"type": "done"},
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat"
        body = json.loads(request.content)
        assert body["question"] == "Wat is een belastingschuldige?"
        return _sse_response(canned)

    _monkeypatch_transport(monkeypatch, handler)

    resp = client.post("/v1/chat", json={"question": "Wat is een belastingschuldige?"})

    assert resp.status_code == 200
    assert _parse_sse(resp.text) == canned


def test_onbereikbare_graph_qa_geeft_error_event_geen_500(client, monkeypatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _monkeypatch_transport(monkeypatch, handler)

    resp = client.post("/v1/chat", json={"question": "Een vraag"})

    assert resp.status_code == 200  # de SSE-verbinding zelf opent gewoon
    events = _parse_sse(resp.text)
    assert events == [{"type": "error", "message": "Kon Lex niet bereiken. Probeer het opnieuw."}]


def test_te_veel_chatverzoeken_geeft_429(client, monkeypatch) -> None:
    """Zelfde `probeer_toestaan`-rem als de login-brute-force-test in
    `identiteit_toegang/tests/test_auth.py` — module-constante patchen i.p.v. env-var (die wordt
    alleen bij import gelezen)."""
    monkeypatch.setattr("app.features.chat_proxy.router._CHAT_MAX", 2)

    async def handler(request: httpx.Request) -> httpx.Response:
        return _sse_response([{"type": "done"}])

    _monkeypatch_transport(monkeypatch, handler)

    for _ in range(2):
        resp = client.post("/v1/chat", json={"question": "Vraag"})
        assert resp.status_code == 200

    resp = client.post("/v1/chat", json={"question": "Vraag"})
    assert resp.status_code == 429
    assert "retry-after" in {k.lower() for k in resp.headers}
