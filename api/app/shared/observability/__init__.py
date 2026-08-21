"""Observability-baseline (fase 2, wetsanalyse-migratie).

Wat: één setup-punt voor gestructureerde JSON-logging + optionele OpenTelemetry (traces,
metrics, logs) via OTLP. Elke feature krijgt via `get_tracer()`/`get_meter()` een tracer/meter
die veilig werkt — met echte OTel als de `otel`-extra én endpoint gezet zijn, anders no-op.
Waarom: `shared/`-module, geen feature — observability is generieke infra die door alle
features (en de app-bootstrap zelf) gedeeld wordt (werkwijze-ADR-0001, project-ADR-0006).
Grens: geen frontend-instrumentation (komt met Auth.js/graph-qa in fase 4), geen
Grafana-stack-deployment (fase 5), geen custom SLO's/dashboards. Deze module levert alleen
de bron van signalen; de sink is een OTLP-endpoint dat elders draait.

Beslissingen:
  - ADR-0006 (project): OpenTelemetry als backbone; endpoint via env-var; leeg = no-op zodat
    lokale dev en tests zonder OTel-server werken.
  - Geen hard-dep op `opentelemetry-*`: opgenomen als `[project.optional-dependencies].otel`.
    `_OTEL_API` guardt elke import; zonder de extra werkt logging + middleware, OTel is uit.
  - Pure ASGI-middleware (geen `BaseHTTPMiddleware`): die zou SSE-streams bufferen en breken —
    de zelfde reden dat wetsanalyse-ai het zo heeft.

Interacties:
  - main.py: `setup(app)` in lifespan vóór het yield; `RequestContextMiddleware` op de app.
  - shared/llm/client.py: `get_tracer(...)` voor span per LLM-call + duur-metric.
  - shared/jobs/store.py: `get_tracer(...)` voor spans op claim/voltooi/faal + gauge-metric.

Publieke API:
- `setup(app)` — configureer logging + OTel (idempotent)
- `RequestContextMiddleware` — pure-ASGI-middleware voor `X-Request-Id`-correlatie
- `request_id_var` — `ContextVar` waar logs/spans zichzelf op refereren
- `get_tracer(naam)` / `get_meter(naam)` — retourneert echte OTel of no-op-shim
"""

from app.shared.observability.helpers import get_meter, get_tracer
from app.shared.observability.middleware import RequestContextMiddleware, request_id_var
from app.shared.observability.setup import setup

__all__ = [
    "RequestContextMiddleware",
    "get_meter",
    "get_tracer",
    "request_id_var",
    "setup",
]
