"""No-op-shims voor tracer/meter, zodat feature-code onvoorwaardelijk spans/metrics mag maken.

Met de `otel`-extra én een OTLP-endpoint: echte OTel-objecten. Anders: shims die alle methodes
accepteren en niets doen — code hoeft nooit `if OTEL_ENABLED:` te controleren.
"""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover — triviale import-guard
    from opentelemetry import metrics as _ot_metrics
    from opentelemetry import trace as _ot_trace

    _OTEL_API = True
except ImportError:  # pragma: no cover
    _OTEL_API = False


class _NoopSpan:
    def set_attribute(self, *_a: Any, **_k: Any) -> None: ...
    def record_exception(self, *_a: Any, **_k: Any) -> None: ...
    def set_status(self, *_a: Any, **_k: Any) -> None: ...
    def add_event(self, *_a: Any, **_k: Any) -> None: ...
    def end(self, *_a: Any, **_k: Any) -> None: ...

    def __enter__(self) -> _NoopSpan:
        return self

    def __exit__(self, *_a: Any) -> bool:
        return False


class _NoopInstrument:
    def add(self, *_a: Any, **_k: Any) -> None: ...
    def record(self, *_a: Any, **_k: Any) -> None: ...


class _NoopTracer:
    def start_as_current_span(self, *_a: Any, **_k: Any) -> _NoopSpan:
        return _NoopSpan()


class _NoopMeter:
    def create_counter(self, *_a: Any, **_k: Any) -> _NoopInstrument:
        return _NoopInstrument()

    def create_histogram(self, *_a: Any, **_k: Any) -> _NoopInstrument:
        return _NoopInstrument()

    def create_up_down_counter(self, *_a: Any, **_k: Any) -> _NoopInstrument:
        return _NoopInstrument()


def get_tracer(naam: str) -> Any:
    """Tracer voor de app. Echte tracer als de `otel`-extra beschikbaar is (no-op-provider als
    er geen endpoint is), anders shim. Callers mogen onvoorwaardelijk
    `tracer.start_as_current_span(...)` doen als contextmanager."""
    if _OTEL_API:
        return _ot_trace.get_tracer(naam)
    return _NoopTracer()


def get_meter(naam: str) -> Any:
    """Meter voor de app — echte meter met de extra, anders shim. Zie `get_tracer`."""
    if _OTEL_API:
        return _ot_metrics.get_meter(naam)
    return _NoopMeter()
