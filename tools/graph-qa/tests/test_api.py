"""`api/main.py`: het eerste HTTP-endpoint (`POST /v1/chat`, werkwijze-story 053).

Providers gaan via `app.dependency_overrides` (fakes) i.p.v. de echte adapters — zie
`_llm_dependency`/`_graph_dependency` in `api/main.py`. De meeste tests gebruiken een **bare**
`TestClient(main.app)`, die de lifespan niet draait; `test_lifespan_...` gebruikt bewust
`with TestClient(main.app):` om de fail-fast-startupcheck zelf te toetsen — zelfde patroon als de
referentie se `api/`-tests (zie `tools/graph-qa/CLAUDE.md` §Tests).
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from agent.config import Settings
from api import main
from tests.fakes import FakeGraph, FakeLLM, make_settings, response, text_block


def _supervisor_ok(specialist: str = "algemeen", plan: str = "beantwoord de vraag"):
    return response([text_block(f"SPECIALIST: {specialist}\nPLAN: {plan}")], "end_turn")


def _parse_sse(text: str) -> list[dict]:
    events = []
    for blok in text.split("\n\n"):
        for regel in blok.splitlines():
            if regel.startswith("data:"):
                events.append(json.loads(regel[len("data:") :].strip()))
    return events


@pytest.fixture(autouse=True)
def _override_providers():
    llm = FakeLLM(
        [_supervisor_ok(), response([text_block("Een antwoord zonder tools.")], "end_turn")]
    )
    graph = FakeGraph(result="")
    main.app.dependency_overrides[main._llm_dependency] = lambda: llm
    main.app.dependency_overrides[main._graph_dependency] = lambda: graph
    yield llm, graph
    main.app.dependency_overrides.clear()


def test_health() -> None:
    client = TestClient(main.app)

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_levert_sse_stream_met_events(_override_providers) -> None:
    client = TestClient(main.app)

    resp = client.post("/v1/chat", json={"question": "Een algemene vraag"})

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    types = [e["type"] for e in events]
    assert "token" in types
    assert "sources" in types
    assert "grounding" in types
    assert types[-1] == "done"
    grounding = next(e for e in events if e["type"] == "grounding")
    assert set(grounding) == {
        "type",
        "grounded",
        "niveau",
        "cited",
        "unsupported",
        "niet_letterlijk",
    }


def test_chat_zonder_token_geconfigureerd_is_open() -> None:
    """Standaard-`settings` (geen `QA_API_TOKEN` in de omgeving) laat een verzoek zonder
    Authorization-header gewoon door."""
    client = TestClient(main.app)

    resp = client.post("/v1/chat", json={"question": "Een vraag"})

    assert resp.status_code == 200


def test_chat_met_token_geconfigureerd_weigert_zonder_of_met_verkeerd_token() -> None:
    origineel = main.settings
    main.settings = make_settings(qa_api_token="het-juiste-token")
    try:
        client = TestClient(main.app)

        zonder = client.post("/v1/chat", json={"question": "Een vraag"})
        assert zonder.status_code == 401

        verkeerd = client.post(
            "/v1/chat",
            json={"question": "Een vraag"},
            headers={"Authorization": "Bearer fout-token"},
        )
        assert verkeerd.status_code == 401

        goed = client.post(
            "/v1/chat",
            json={"question": "Een vraag"},
            headers={"Authorization": "Bearer het-juiste-token"},
        )
        assert goed.status_code == 200
    finally:
        main.settings = origineel


def test_lifespan_weigert_zonder_geldige_configuratie() -> None:
    origineel = main.settings
    main.settings = Settings()  # leeg — geen graph- of LLM-config
    try:
        with pytest.raises(ValueError), TestClient(main.app):
            pass
    finally:
        main.settings = origineel
