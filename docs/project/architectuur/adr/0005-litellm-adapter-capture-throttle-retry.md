# ADR-0005: Litellm-adapter met capture, throttle en retry als LLM-toegangslaag

**Status:** geaccepteerd
**Datum:** 2026-08-21

## Context

Lexplainables heeft nu een minimale LLM-wrapper die per profiel een client maakt en `chat` +
`stream` aanroept — geen retry, geen rate-limit-beheer, geen throttle om zichzelf niet te
DDoS-en, geen capture van de daadwerkelijke prompt/response voor debugging of audit.

Wetsanalyse-ai gebruikt **litellm** als provider-agnostisch model-invocation-laag, met een
eigen shim:
- **`llm/base.py`** — `LLMPort`-abstractie (behoud interface, verwissel implementatie).
- **`llm/litellm_client.py`** — de daadwerkelijke aanroep via `litellm.acompletion`.
- **`llm/throttle.py`** — semafoor met configureerbare `llm_max_concurrency`, per-app niveau.
- **`llm/capture.py`** — schrijft prompt/response/timing naar `llm_calls`-tabel als
  `runtime_config.capture_llm_calls = true` (via runtime-toggle).
- Retry-logic bij tijdelijke fouten (5xx, rate-limit-headers).

Alternatieven:
- **Eigen wrapper per provider** — dubbel werk, breekt zodra je meerdere providers gebruikt.
- **Langchain LLM-adapter** — meer dependency-oppervlak dan nodig, wij gebruiken maar één
  aspect ervan (acompletion). Ook: langchain's abstractie verandert vaker dan litellm's.
- **Direct provider-SDK's** (anthropic, openai) — geen abstractie, alle capture/throttle-logica
  moet dan per provider herhaald worden.

## Beslissing

**Litellm is de LLM-aanroeplaag**, verpakt in een dunne eigen shim onder `api/app/shared/llm/`
(shared-module, want meerdere features roepen 'm aan — `projecten`, later `graph-qa` via HTTP,
`engine`-module). Vier verantwoordelijkheden:

1. **`LLMPort`** — Protocol met `complete()` en `stream()`, gebruikt door alle feature-code.
2. **Throttle** — semafoor met `LLM_MAX_CONCURRENCY` uit config; voorkomt zelf-veroorzaakte
   rate-limits en beheerst OpenTelemetry-metric-explosie.
3. **Retry** — exponential backoff op transient errors (429, 5xx); niet op 4xx.
4. **Capture** — schrijft prompt/response/duur/tokens naar `llm_calls`-tabel wanneer
   `runtime_config.capture_llm_calls = true` (bestaat al in lex). Toegang tot deze feature
   loopt via de `llm_calls`-store, niet direct SQLAlchemy.

Model-selectie loopt via `features/llm_profielen` (bestaat al) — een profiel bevat
provider+model+api_key (Fernet-versleuteld) en wordt aan de shim doorgegeven per aanroep.

## Consequenties

- **Bewust geaccepteerd:** litellm is een extra dependency met eigen breaking-change-track.
  Winst: één plek voor auth + provider-verschillen; nieuwe providers zonder code-wijziging in
  de feature-code.
- **Openbaar contract:** `LLMPort` is stabiel; wisseling van litellm naar iets anders (of
  direct-SDK) raakt alleen `shared/llm/`, geen feature-code.
- **Capture is opt-in** via runtime-config; standaard uit in productie, aan tijdens debugging.
- **Kosten en throttling zichtbaar** in OpenTelemetry-metrics (ADR-0006).
- **Streaming werkt** via `stream()` — server-sent events terug naar de client via de
  BFF-passthrough (frontend), of via graph-qa's `answer_stream` (LangGraph).
