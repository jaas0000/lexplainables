"""`api/main.py`: `POST /v1/chat` (werkwijze-story 053) en het run-model (story 054).

Providers gaan via `app.dependency_overrides` (fakes) i.p.v. de echte adapters — zie
`_llm_dependency`/`_graph_dependency` in `api/main.py`. De meeste tests gebruiken een **bare**
`TestClient(main.app)`, die de lifespan niet draait; `test_lifespan_...` gebruikt bewust
`with TestClient(main.app):` om de fail-fast-startupcheck zelf te toetsen — zelfde patroon als de
referentie se `api/`-tests (zie `tools/graph-qa/CLAUDE.md` §Tests). De run-tests gebruiken ook
bewust `with TestClient(...) as client:`: dat opent een blocking-portal met een levende event-loop
in een achtergrondthread, zodat `asyncio.create_task(...)` (de run's achtergrondtaak) blijft
doorlopen tussen twee losse synchrone client-aanroepen — zonder die context zou de taak nooit de
kans krijgen te draaien tussen de POST en de daaropvolgende GET.
"""

from __future__ import annotations

import json
import time

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
    # `with TestClient(...):` draait de lifespan (`require_graph`/`require_llm`) tegen de
    # module-level `settings` — los van de bovenstaande provider-fakes, die alleen de routes
    # raken. Zet 'm hier op geldig-lijkende dummy-waarden, zodat elke test die de lifespan
    # draait niet zelf dit boilerplate hoeft te herhalen.
    origineel = main.settings
    main.settings = make_settings(
        graphdb_mcp_url="http://fake",
        graphdb_token="fake",
        azure_foundry_api_key="fake",
        azure_foundry_resource="fake",
    )
    yield llm, graph
    main.app.dependency_overrides.clear()
    main.settings = origineel


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


# ---- Runs (story 054) -----------------------------------------------------------------------


def test_start_run_en_volg_events_tot_done(_override_providers) -> None:
    with TestClient(main.app) as client:
        start = client.post("/v1/runs", json={"question": "Een algemene vraag"})
        assert start.status_code == 201
        body = start.json()
        assert body["status"] == "loopt"
        run_id = body["run_id"]

        # Blokkerende GET: de generator (`runs.volg`) sluit vanzelf zodra de achtergrondtaak
        # (die op dezelfde portal-event-loop draait) de run afrondt.
        events_resp = client.get(f"/v1/runs/{run_id}/events")

    events = _parse_sse(events_resp.text)
    types = [e["type"] for e in events]
    assert "token" in types
    assert types[-1] == "done"


class _TregeLLM:
    """`create()` vertraagt kunstmatig, zodat de run gegarandeerd nog `loopt` als een tweede
    `POST /v1/runs` op hetzelfde gesprek arriveert — voor een deterministische 409-test (de
    onderliggende `RunBestaatAl`-logica zelf is al deterministisch unit-getest in
    `test_runs.py`; dit toetst alleen de HTTP-laag se mapping naar 409)."""

    def __init__(self, resp) -> None:
        self._resp = resp

    def create(self, **kwargs):
        time.sleep(0.3)
        return self._resp


def test_tweede_run_op_hetzelfde_gesprek_geeft_409() -> None:
    main.app.dependency_overrides[main._llm_dependency] = lambda: _TregeLLM(_supervisor_ok())
    main.app.dependency_overrides[main._graph_dependency] = lambda: FakeGraph(result="")
    with TestClient(main.app) as client:
        eerste = client.post(
            "/v1/runs", json={"question": "Vraag 1", "conversation_id": "gesprek-1"}
        )
        assert eerste.status_code == 201

        tweede = client.post(
            "/v1/runs", json={"question": "Vraag 2", "conversation_id": "gesprek-1"}
        )

    assert tweede.status_code == 409
    assert tweede.json()["detail"]["reden"] == "run_loopt_al"
    assert tweede.json()["detail"]["run_id"] == eerste.json()["run_id"]


def test_onbekende_run_geeft_404_op_events_en_cancel() -> None:
    client = TestClient(main.app)

    assert client.get("/v1/runs/onbekend/events").status_code == 404
    assert client.post("/v1/runs/onbekend/cancel").status_code == 404


def test_cancel_op_andermans_run_geeft_404(_override_providers) -> None:
    with TestClient(main.app) as client:
        start = client.post(
            "/v1/runs",
            json={"question": "Vraag"},
            headers={"X-User-Id": "alice"},
        )
        run_id = start.json()["run_id"]

        # Zonder de bijpassende X-User-Id-header (of met een verkeerde) is de run onvindbaar.
        zonder_header = client.post(f"/v1/runs/{run_id}/cancel")
        anders = client.post(f"/v1/runs/{run_id}/cancel", headers={"X-User-Id": "bob"})
        goed = client.post(f"/v1/runs/{run_id}/cancel", headers={"X-User-Id": "alice"})

    assert zonder_header.status_code == 404
    assert anders.status_code == 404
    assert goed.status_code == 202


def test_conversations_run_geeft_null_zonder_run_en_de_samenvatting_mét(
    _override_providers,
) -> None:
    with TestClient(main.app) as client:
        leeg = client.get("/v1/conversations/onbekend-gesprek/run")
        assert leeg.status_code == 200
        assert leeg.json() is None

        client.post("/v1/runs", json={"question": "Vraag", "conversation_id": "gesprek-42"})
        gevuld = client.get("/v1/conversations/gesprek-42/run")

    assert gevuld.status_code == 200
    assert gevuld.json()["conversation_id"] == "gesprek-42"


# ---- `doel`-gedreven annotatiebeurten via HTTP (werkwijze-vervolg op stories 053-054) ---------


def _annotatie_llm() -> FakeLLM:
    import json as _json

    return FakeLLM(
        [
            response(
                [
                    text_block(
                        _json.dumps(
                            {"elementen": [{"klasse": "Rechtssubject", "tekst": "De aanslag"}]}
                        )
                    )
                ],
                "end_turn",
            ),
            response(
                [
                    text_block(
                        _json.dumps(
                            {"oordelen": [{"index": 0, "aandacht": "groen"}], "ontbrekend": []}
                        )
                    )
                ],
                "end_turn",
            ),
        ]
    )


_CORPUS_TSV = (
    "?tekst\t?jci\t?lid\t?lidnummer\t?lidtekst\t?onderdeel\t?onderdeeltekst\n"
    '\t\t\t"1"\t"De aanslag wordt vastgesteld."@nl\t\t'
)


def test_chat_met_doel_routeert_naar_de_annotatieketen() -> None:
    main.app.dependency_overrides[main._llm_dependency] = lambda: _annotatie_llm()
    main.app.dependency_overrides[main._graph_dependency] = lambda: FakeGraph(result=_CORPUS_TSV)

    client = TestClient(main.app)
    resp = client.post(
        "/v1/chat",
        json={"doel": {"bwbId": "BWBR0004770", "artikel": "1"}, "werkgebied": "sociaal"},
        headers={"X-User-Id": "jurist-1"},
    )

    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    types = [e["type"] for e in events]
    assert types[0] == "doel"
    assert "element" in types
    assert types[-1] == "done"


def test_runs_met_doel_routeert_ook_naar_de_annotatieketen() -> None:
    main.app.dependency_overrides[main._llm_dependency] = lambda: _annotatie_llm()
    main.app.dependency_overrides[main._graph_dependency] = lambda: FakeGraph(result=_CORPUS_TSV)

    with TestClient(main.app) as client:
        start = client.post(
            "/v1/runs",
            json={"doel": {"bwbId": "BWBR0004770", "artikel": "1"}, "werkgebied": "sociaal"},
        )
        assert start.status_code == 201
        run_id = start.json()["run_id"]

        events_resp = client.get(f"/v1/runs/{run_id}/events")

    types = [e["type"] for e in _parse_sse(events_resp.text)]
    assert types[0] == "doel"
    assert types[-1] == "done"
