"""Configureer logging + optionele OpenTelemetry-providers.

Idempotent: `setup()` mag meermalen aangeroepen worden (o.a. tests, TestClient-lifespan).
Fail-open: elke OTel-tak is guarded, mag de app-start nooit blokkeren.
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import logging.config
import os
from typing import Any

from app.shared.observability.middleware import request_id_var

try:  # pragma: no cover — triviale import-guard
    from opentelemetry import trace as _ot_trace

    _OTEL_API = True
except ImportError:  # pragma: no cover
    _OTEL_API = False

logger = logging.getLogger(__name__)

# Veldnamen die nooit in een logregel mogen verschijnen. Data-minimalisatie (AVG) + BIO2.
GEHEIME_VELDEN = {
    "authorization",
    "token",
    "bearer",
    "secret",
    "password",
    "api_key",
    "apikey",
    "wachtwoord",
    "fernet_key",
}

_NIVEAU = {
    logging.DEBUG: "debug",
    logging.INFO: "info",
    logging.WARNING: "warn",
    logging.ERROR: "error",
    logging.CRITICAL: "error",
}

_STD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}

_geconfigureerd = False


def _trace_context() -> dict[str, str]:
    """Geef `{trace_id, span_id}` van de actieve span, of leeg als er geen (recording) span is."""
    if not _OTEL_API:
        return {}
    try:
        span = _ot_trace.get_current_span()
        ctx = span.get_span_context()
        if not ctx or not ctx.is_valid:
            return {}
        return {"trace_id": f"{ctx.trace_id:032x}", "span_id": f"{ctx.span_id:016x}"}
    except Exception:  # noqa: BLE001 — logging mag nooit omvallen
        return {}


def _redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Redacteer alle geheime velden in een dict (recursief). Bewaart de structuur."""
    schoon: dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in GEHEIME_VELDEN:
            schoon[k] = "[GEREDACTEERD]"
        elif isinstance(v, dict):
            schoon[k] = _redact_dict(v)
        else:
            schoon[k] = v
    return schoon


class JsonFormatter(logging.Formatter):
    """Serialiseer elke LogRecord als één JSON-regel."""

    def format(self, record: logging.LogRecord) -> str:
        regel: dict[str, Any] = {
            "ts": _dt.datetime.fromtimestamp(record.created, _dt.UTC).isoformat(),
            "niveau": _NIVEAU.get(record.levelno, "info"),
            "categorie": getattr(record, "categorie", "functioneel"),
            "logger": record.name,
            "bericht": record.getMessage(),
        }
        regel.update(_trace_context())
        rid = request_id_var.get()
        if rid:
            regel["request_id"] = rid
        # Vrije `extra=`-velden meenemen (geredigeerd op sleutelnaam).
        for k, v in record.__dict__.items():
            if k in _STD_ATTRS or k == "categorie":
                continue
            if v is None:
                continue
            if isinstance(v, dict):
                regel[k] = _redact_dict(v)
            elif k.lower() in GEHEIME_VELDEN:
                regel[k] = "[GEREDACTEERD]"
            else:
                regel[k] = v
        if record.exc_info:
            regel["exception"] = self.formatException(record.exc_info)
        return json.dumps(regel, ensure_ascii=False, default=str)


def _dict_config() -> dict[str, Any]:
    """Bouw de logging.dictConfig uit env: LOG_LEVEL (info) + LOG_FORMAT (json|text)."""
    is_json = os.environ.get("LOG_FORMAT", "json").lower() != "text"
    level = os.environ.get("LOG_LEVEL", "info").upper()
    # Dictconfig's `()`-sleutel accepteert een callable object direct — dat is robuuster dan
    # een dotted-path-string voor klasses in modules-die-niet-packages-zijn (dan probeert
    # Python die string als submodule te importeren en faalt met "is not a package").
    formatter = (
        {"()": JsonFormatter}
        if is_json
        else {"format": "%(asctime)s %(levelname)-7s %(name)s | %(message)s"}
    )
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"lex": formatter},
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "lex",
            }
        },
        "root": {"level": level, "handlers": ["stdout"]},
        "loggers": {
            name: {"level": level, "handlers": [], "propagate": True}
            for name in ("uvicorn", "uvicorn.error", "uvicorn.access")
        },
    }


def _setup_otel_providers(endpoint: str) -> None:
    """Configureer TracerProvider/MeterProvider/LoggerProvider met OTLP-exporters. Alleen
    aangeroepen als `_OTEL_API` en de endpoint niet-leeg zijn."""
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create(
        {"service.name": os.environ.get("OTEL_SERVICE_NAME", "lexplainables-api")}
    )
    _setup_traces(resource)
    _setup_metrics(resource)
    _setup_logs(resource)
    logger.info(
        "OpenTelemetry actief",
        extra={"categorie": "functioneel", "otel_endpoint": endpoint},
    )


def _proto() -> str:
    return os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf").lower()


def _setup_traces(resource: Any) -> None:
    from opentelemetry import trace as _ot_trace_mod
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    if _proto().startswith("grpc"):
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    else:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    _ot_trace_mod.set_tracer_provider(provider)


def _setup_metrics(resource: Any) -> None:
    from opentelemetry import metrics as _ot_metrics_mod
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

    if _proto().startswith("grpc"):
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    else:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    _ot_metrics_mod.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))


def _setup_logs(resource: Any) -> None:
    """Stuur stdlib-logs óók via OTLP (naast de JSON-stdout-regels)."""
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    if _proto().startswith("grpc"):
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    else:
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(provider)
    logging.getLogger().addHandler(LoggingHandler(level=logging.INFO, logger_provider=provider))


def _instrument_libraries() -> None:
    """Auto-instrumenteer bekende bibliotheken (best-effort per lib, guarded)."""
    for naam, doe in (
        ("sqlalchemy", _instr_sqlalchemy),
        ("asyncpg", _instr_asyncpg),
    ):
        try:
            doe()
        except Exception:  # noqa: BLE001
            logger.debug("OTel-instrumentatie van %s overgeslagen", naam, exc_info=True)


def _instr_sqlalchemy() -> None:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    SQLAlchemyInstrumentor().instrument()


def _instr_asyncpg() -> None:
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

    AsyncPGInstrumentor().instrument()


def _instrument_fastapi(app: Any) -> None:
    """Auto-instrumenteer de FastAPI-app; guarded (endpoint kan leeg zijn / extra ontbreken)."""
    if not _OTEL_API:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception:  # noqa: BLE001
        logger.debug("FastAPI-instrumentatie overgeslagen", exc_info=True)


def setup(app: Any = None) -> None:
    """Configureer logging + (optioneel) OpenTelemetry. Idempotent.

    - Logging wordt altijd geconfigureerd (JSON of tekst afhankelijk van `LOG_FORMAT`).
    - OpenTelemetry alleen als `OTEL_EXPORTER_OTLP_ENDPOINT` gezet is én de `otel`-extra
      geïnstalleerd. Anders: waarschuwing (endpoint zonder extra) of stil (geen endpoint).
    - `app` is optioneel — als meegegeven, wordt de FastAPI-instrumentation daarop gekoppeld.
    """
    global _geconfigureerd
    if _geconfigureerd:
        # Idempotent — herconfigureren zou de handlers verdubbelen. Alleen FastAPI-hook
        # updaten voor het geval de app-instance verandert (bijv. tests met per-run app).
        if app is not None:
            _instrument_fastapi(app)
        return

    logging.config.dictConfig(_dict_config())

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    if endpoint:
        if not _OTEL_API:
            logger.warning(
                "OTEL_EXPORTER_OTLP_ENDPOINT is gezet maar opentelemetry ontbreekt; "
                "installeer de 'otel'-extra. OpenTelemetry blijft uit."
            )
        else:
            try:
                _setup_otel_providers(endpoint)
                _instrument_libraries()
                if app is not None:
                    _instrument_fastapi(app)
            except Exception:  # noqa: BLE001 — observability mag nooit de start blokkeren
                logger.warning("OpenTelemetry-setup mislukt (genegeerd)", exc_info=True)

    _geconfigureerd = True


def _reset_voor_tests() -> None:
    """Zet de idempotentie-vlag terug — alleen voor tests. Niet uit `__init__` exporteren."""
    global _geconfigureerd
    _geconfigureerd = False
