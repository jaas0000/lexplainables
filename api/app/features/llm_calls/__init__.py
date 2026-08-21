"""LLM-calls.

Wat: capture-tabel voor uitgaande LLM-calls per analyse; per call worden prompt, response, tokens, kosten en tijdsduur opgeslagen voor auditing en debugging van analyse-runs.
Waarom: eigen domein omdat capture cross-cutting is (elke LLM-call — vanuit welke feature dan ook — schrijft hier), en de projecten-router leest ze weer als log-lijst; twee onafhankelijke DI-consumenten (opslag + weergave), dus store en dependency-factory horen los.
Grens: de router die de log per analyse toont woont in `projecten/` (want alleen daar hoort een `analyse_id` bij); dit domein levert uitsluitend de opslag- en query-laag, geen eigen endpoints.

Tabellen:
  - llm_calls: id + analyse_id + fase + prompt + response + model + input_tokens + output_tokens + kosten_cent + duur_ms + aangemaakt.

Beslissingen:
  - ADR-0007 (store-abstractie): dependency-factory in `dependencies.py`, geen router hier — `projecten/router.py` importeert `get_llm_calls_store`.
  - ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
  - Audit ronde 2 punt 4: `dependencies.py` los van router — twee DI-consumenten (capture-schrijvers en projecten-leesrouter) hoeven niet via elkaars owner-export.
  - Story 021 §Toggle: opnemen van calls staat aan/uit via `runtime_config` `capture_llm_calls` — bij `false` schrijft de capture-laag niets, tabel blijft leeg.

Interacties:
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
  - projecten/router.py: consumeert `get_llm_calls_store` via `dependencies.py` voor de log-per-analyse-endpoint.
  - runtime_config: `capture_llm_calls`-instelling bepaalt of er überhaupt opgeslagen wordt.
  - shared/auth.py: leesroute in projecten leunt op `huidige_beheerder`; deze feature zelf heeft geen auth omdat het geen router heeft.
"""
