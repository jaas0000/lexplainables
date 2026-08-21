"""Projecten (werkgebieden).

Wat: analisten maken werkgebieden aan met één of meer bronnen (bwb_id + artikel + lid);
CRUD-endpoints leveren lijst/detail/verwijderen; annotatie op individuele elementen woont in
`annotatie/`. Read-only LLM-calls-log koppelt aan `llm_calls`.
Waarom: eigen domein voor de werkgebied-metadata (naam + bronnen + omschrijving) los van
annotatie (dat is een aparte werkplek-stap). De ooit gebouwde JAS-orkestratie (act2/act3,
review-flow, rapport, SSE) is opgeruimd (migratie 0012, migratie-plan fase 1) — annotatie is
de enige overgebleven analyse-stap.
Grens: geen orkestratie meer, geen SSE, geen rapport-endpoint; het domein bewaart alleen de
werkgebied-metadata. Voor annotatie zie `annotatie/`; voor LLM-calls-registratie zie
`llm_calls/`.

Tabellen:
  - analyses: id + naam + status (`nieuw`) + bronnen (JSON) + omschrijving + timestamps
    (aangemaakt/bijgewerkt) + gebruiker_id.

Beslissingen:
  - ADR-0007 (store-abstractie): router leunt op `AnalyseStore` Protocol; rolfilter (analist
    vs. beheerder) zit in de store, niet in de router.
  - ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
  - Migratie-plan fase 1: rapport (013) + analyse-engine (024) verwijderd — JAS-pipeline is
    legacy; annotatie is de enige overgebleven analyse-stap.

Interacties:
  - shared/auth.py: `huidige_beheerder` op alle endpoints (BFF geeft rol door via X-User-Id).
  - llm_calls/dependencies.py: `get_llm_calls_store` voor de log-per-werkgebied-route.
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
"""
