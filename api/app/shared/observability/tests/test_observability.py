"""Gedragstests voor de observability-baseline (feature-bouwen regel 6).

Tests draaien zonder Docker/Postgres en zonder een echte OTel-collector — we testen de
no-op-paden, de logging-formatter en de request-middleware. De OTel-exporter-paden zijn
elders (integratietest) te dekken; hier is de eis dat setup() nooit crasht en de shims
werken.
"""

from __future__ import annotations

import json
import logging
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.shared.observability import (
    RequestContextMiddleware,
    get_meter,
    get_tracer,
    request_id_var,
    setup,
)
from app.shared.observability.setup import (
    GEHEIME_VELDEN,
    JsonFormatter,
    _redact_dict,
    _reset_voor_tests,
)


@pytest.fixture(autouse=True)
def reset_setup_idempotentie():
    """setup() is idempotent — reset de vlag zodat elke test 'm opnieuw kan aanroepen."""
    _reset_voor_tests()
    yield
    _reset_voor_tests()


# --- setup() idempotentie + no-endpoint pad --------------------------------------


def test_setup_idempotent(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    setup()
    setup()  # tweede aanroep mag niet crashen of handlers verdubbelen


def test_setup_zonder_endpoint_faalt_niet(monkeypatch):
    """Geen OTLP-endpoint: setup configureert alleen logging, geen OTel-crash."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    setup()  # mag niet raisen


def test_setup_met_endpoint_zonder_extra_logt_warning_en_gaat_door(monkeypatch, capsys):
    """Endpoint gezet maar OTel-extra ontbreekt → warning, geen crash. Op de test-runner
    zal `_OTEL_API` doorgaans False zijn (geen otel-dep), dus dit pad wordt echt getest."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    # `__init__.py` re-exporteert een functie `setup` met dezelfde naam als de submodule —
    # daardoor is `app.shared.observability.setup` de functie, niet de module. `importlib`
    # levert de submodule ondubbelzinnig.
    import importlib

    setup_module = importlib.import_module("app.shared.observability.setup")

    if setup_module._OTEL_API:
        pytest.skip(
            "opentelemetry is geïnstalleerd; deze test dekt alleen het niet-geïnstalleerd-pad"
        )
    # `caplog` werkt hier niet: `setup()` roept `logging.config.dictConfig` aan die de
    # root-logger-handlers vervangt, waarmee caplog's ingeplugde handler verdwijnt. We lezen
    # de warning uit stdout — daar landt de JsonFormatter-uitvoer.
    setup()
    uitvoer = capsys.readouterr().out
    assert "opentelemetry ontbreekt" in uitvoer.lower()


# --- get_tracer / get_meter --------------------------------------------------------


def test_get_tracer_werkt_als_contextmanager():
    """Zonder OTel geeft get_tracer een no-op-shim; met OTel een echte tracer. Beide
    moeten `start_as_current_span(...)` als contextmanager kunnen gebruiken."""
    tracer = get_tracer("test")
    with tracer.start_as_current_span("test-span") as span:
        span.set_attribute("test.key", "waarde")


def test_get_meter_maakt_instrumenten():
    meter = get_meter("test")
    counter = meter.create_counter("test_counter")
    histo = meter.create_histogram("test_histo")
    updown = meter.create_up_down_counter("test_updown")
    counter.add(1)
    histo.record(1.5)
    updown.add(-1)  # mag niet crashen


# --- JSON-logging + redactie --------------------------------------------------------


def test_json_formatter_produceert_geldige_json():
    formatter = JsonFormatter()
    record = logging.makeLogRecord(
        {"msg": "hallo %s", "args": ("wereld",), "levelno": logging.INFO, "name": "test"}
    )
    regel = formatter.format(record)
    parsed = json.loads(regel)
    assert parsed["bericht"] == "hallo wereld"
    assert parsed["niveau"] == "info"
    assert parsed["categorie"] == "functioneel"
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", parsed["ts"])


def test_json_formatter_neemt_extra_velden_mee():
    formatter = JsonFormatter()
    record = logging.makeLogRecord(
        {"msg": "test", "levelno": logging.INFO, "name": "test", "extra_veld": "waarde"}
    )
    parsed = json.loads(formatter.format(record))
    assert parsed["extra_veld"] == "waarde"


def test_json_formatter_redigeert_geheime_velden():
    formatter = JsonFormatter()
    record = logging.makeLogRecord(
        {
            "msg": "test",
            "levelno": logging.INFO,
            "name": "test",
            "password": "geheim123",
            "api_key": "sk-abc123",
        }
    )
    parsed = json.loads(formatter.format(record))
    assert parsed["password"] == "[GEREDACTEERD]"
    assert parsed["api_key"] == "[GEREDACTEERD]"


def test_redact_dict_redigeert_geheime_velden_recursief():
    data = {
        "gebruiker": "beheerder",
        "password": "geheim",
        "nested": {"api_key": "sk-123", "openbaar": "ok"},
    }
    schoon = _redact_dict(data)
    assert schoon["gebruiker"] == "beheerder"
    assert schoon["password"] == "[GEREDACTEERD]"
    assert schoon["nested"]["api_key"] == "[GEREDACTEERD]"
    assert schoon["nested"]["openbaar"] == "ok"


def test_geheime_velden_bevat_verwachte_namen():
    """Contract: het opsomming van geheime velden dekt de courante gevallen. Verandert deze
    lijst, dan is dat een bewuste keuze — de test maakt 'm zichtbaar in de review."""
    verwacht = {"password", "api_key", "token", "authorization", "secret"}
    assert verwacht <= GEHEIME_VELDEN


# --- RequestContextMiddleware ------------------------------------------------------


def _maak_app_met_middleware() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    def ping():
        return {"rid": request_id_var.get()}

    return app


def test_middleware_genereert_request_id_als_niet_meegegeven():
    with TestClient(_maak_app_met_middleware()) as c:
        resp = c.get("/ping")
    assert resp.status_code == 200
    assert "x-request-id" in resp.headers
    # UUID-hex is 32 hex-chars
    assert re.match(r"^[0-9a-f]{32}$", resp.headers["x-request-id"])
    body = resp.json()
    assert body["rid"] == resp.headers["x-request-id"]


def test_middleware_echoot_meegegeven_request_id():
    with TestClient(_maak_app_met_middleware()) as c:
        resp = c.get("/ping", headers={"X-Request-Id": "abc-123"})
    assert resp.headers["x-request-id"] == "abc-123"
    assert resp.json()["rid"] == "abc-123"


def test_middleware_logt_access_regel(caplog):
    with (
        caplog.at_level(logging.INFO, logger="lexplainables.access"),
        TestClient(_maak_app_met_middleware()) as c,
    ):
        c.get("/ping")
    treffers = [r for r in caplog.records if r.name == "lexplainables.access"]
    assert treffers, "access-logregel ontbreekt"
    laatste = treffers[-1]
    assert laatste.http_method == "GET"
    assert laatste.http_path == "/ping"
    assert laatste.http_status == 200
    assert isinstance(laatste.duur_ms, float)


def test_middleware_laat_niet_http_scope_ongewijzigd_door():
    """WebSocket/lifespan-scopes hebben geen request-id nodig — de middleware moet ze niet
    verstoren."""
    marker: list[str] = []

    class NietHttpApp:
        async def __call__(self, scope, receive, send):
            marker.append(scope["type"])
            await send({"type": "lifespan.startup.complete"})

    mw = RequestContextMiddleware(NietHttpApp())

    async def geen_receive():
        return {}

    async def geen_send(_msg):
        return None

    async def run():
        await mw({"type": "lifespan"}, geen_receive, geen_send)

    import asyncio

    asyncio.run(run())
    assert marker == ["lifespan"]
