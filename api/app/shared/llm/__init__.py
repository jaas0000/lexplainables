"""LLM-toegangslaag (fase 2 story 2 van de wetsanalyse-migratie).

Wat: een dunne shim rondom `litellm.acompletion` die alle features één stabiele `LLMPort`
biedt — met bounded retry op transient errors, een proces-globale concurrency-rem, en
best-effort capture naar `llm_calls`.
Waarom: `shared/`-module, geen feature — geen domein achter "LLM"; het is infrastructuur die
meerdere features (graph-qa in fase 4, mogelijk toekomstige analyse-flows) zullen delen. Één
plek voor provider-verschillen (Azure vs OpenAI vs Anthropic), één plek voor retry-beleid,
één plek voor capture-toggle-integratie.
Grens: geen streaming (komt met graph-qa in fase 4), geen JSON-schema-parsing (was voor de
JAS-engine — die is legacy), geen `max_prompt_tokens`-cost-guard, geen prompt-caching. Bewust
minimaal — de eerste consumer bepaalt welke uitbreiding het eerst nodig is.

Publieke API:
- `LlmConfig` — per-call configuratie (model, provider, auth, timeout)
- `LLMResult` — tekst-antwoord + telemetrie
- `LLMPort` — Protocol dat elke adapter implementeert
- `LLMFout` / `LLMTransientFout` / `LLMPermanenteFout` — foutenhiërarchie
- `LitellmClient` — de daadwerkelijke `litellm`-adapter (retry + throttle)
- `CapturingLLMClient` — decorator die schrijft naar `llm_calls` bij toggle aan
- `gebruik_context(...)` — context-manager voor capture-metadata (analyse_id, activiteit, bron_id)
- `throttle.configure(max_concurrency)` — semafoor-config vanuit `main.py` `lifespan`
- `throttle.llm_slot()` — één concurrency-slot claimen

Beslissingen:
- **Retry-beleid in de client, niet in de config**: uniform per proces, uit env. Als een
  consumer straks per-analyse-override wil, wordt dat een aparte parameter — niet als
  standaard-config.
- **Capture is best-effort**: een fout in het vastleggen wordt gelogd, nooit doorgegooid.
  Anders kan een DB-hapering een LLM-call laten falen — dat willen we niet.
- **Foutenhiërarchie is transient/permanent**: consumers hoeven geen provider-details te
  kennen om te weten of retry zin heeft. `Retry-After` uit een 429 wordt gehonoreerd binnen
  het backoff-plafond.

Interacties:
- `features/llm_calls`: capture-doel (SqlAlchemyLlmCallsStore.sla_op).
- `features/runtime_config`: capture-toggle (RuntimeConfigStore.capture_ingeschakeld).
- `features/llm_profielen`: bron van `LlmConfig` (profiel → config-mapping is aan de caller).
"""

from app.shared.llm.base import (
    LlmConfig,
    LLMFout,
    LLMPermanenteFout,
    LLMPort,
    LLMResult,
    LLMTransientFout,
)
from app.shared.llm.capture import CapturingLLMClient, gebruik_context, llm_call_ctx
from app.shared.llm.client import LitellmClient

__all__ = [
    "CapturingLLMClient",
    "LLMFout",
    "LLMPermanenteFout",
    "LLMPort",
    "LLMResult",
    "LLMTransientFout",
    "LitellmClient",
    "LlmConfig",
    "gebruik_context",
    "llm_call_ctx",
]
