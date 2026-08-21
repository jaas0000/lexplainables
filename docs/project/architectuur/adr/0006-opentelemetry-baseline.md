# ADR-0006: OpenTelemetry baseline per service

**Status:** geaccepteerd
**Datum:** 2026-08-21

## Context

Lexplainables heeft nu geen observability — geen tracing, geen metrics-export, alleen
stdout-logs. Voor een enterprise-target is dat onvoldoende: incidenten in productie zijn niet
te reconstrueren zonder gedistribueerde traces over api/frontend/graph-qa/wettenbank-mcp.

Wetsanalyse-ai heeft **OpenTelemetry** als backbone: `observability.py` (~359r in `api/app/`,
+ vergelijkbaar in `graph-qa/agent/`). Traces naar Tempo, metrics naar Prometheus, logs naar
Loki — allemaal via OTLP naar een Grafana-observability-stack. Frontend heeft
`instrumentation.ts` voor Next.js-server-side traces.

Werkwijze-ADR-0012 (observability-baseline) legt een baseline vast; deze ADR bevestigt de
concrete keuze voor OpenTelemetry en zegt wat elke service minimaal exporteert.

Alternatieven:
- **Alleen logs** — verliest per-request traces over service-grenzen.
- **Provider-specifieke SDK** (Datadog, New Relic, Application Insights) — vendor-lock. Azure
  Application Insights heeft wel een OTel-compatibele receiver, dus OTel is ook daar
  bruikbaar.
- **Alleen metrics zonder tracing** — voor debugging van LLM-jobs en async-taken zijn traces
  onmisbaar (langlopende jobs, meerfasige pipelines).

## Beslissing

**Elke service exporteert OpenTelemetry-traces, metrics en logs via OTLP.** Configuratie via
env-variabelen (`OTEL_EXPORTER_OTLP_ENDPOINT` etc.); geen endpoint = no-op (idempotent, geen
crash op ontbrekende infra).

Minimum per service:
- **`api`** (Python) — `opentelemetry-instrumentation-fastapi` +
  `opentelemetry-instrumentation-sqlalchemy` +
  `opentelemetry-instrumentation-asyncpg`. Trace per HTTP-request, span per DB-query, span per
  LLM-call (via de litellm-shim). Custom metrics: `llm_call_duration_ms`,
  `llm_call_tokens_used`, `active_async_jobs`.
- **`frontend`** — `@vercel/otel` in `instrumentation.ts`. Trace per request door de
  BFF-proxy; trace-context propageert naar api via `traceparent`-header.
- **`graph-qa`** — eigen instrumentation (LangGraph-nodes) + FastAPI-instrumentation. Span per
  worker/supervisor-node.
- **`wettenbank-mcp`** — `@opentelemetry/instrumentation-http` + custom spans per tool-call.

Deploy: aparte observability-stack (Grafana + Prometheus + Loki + Tempo) — één per omgeving,
gedeeld door alle services. Draait via docker-compose voor lokaal en Bicep voor Azure.

## Consequenties

- **Bewust geaccepteerd:** OpenTelemetry heeft veel dependency-oppervlak (Python-packages per
  instrumentation). Winst: geen vendor-lock, en gemeenschappelijk gereedschap voor de hele
  stack.
- **Logs blijven structured JSON**; logs, metrics en traces worden gecorreleerd via de
  trace-id.
- **Kosten voor devs**: elke nieuwe feature met een LLM-call of async-job voegt custom spans
  toe — dat is deel van `feature-bouwen` regel 5 (tests) → `feature-docs` kan naar de spans
  verwijzen in de docstring.
- **Geen APM-provider verplicht**: OTLP is de export-vorm, de stack die het ontvangt kan
  Grafana zijn, Azure Application Insights, of iets anders — dat is een deploy-keuze
  (ADR-0007), niet een code-keuze.
