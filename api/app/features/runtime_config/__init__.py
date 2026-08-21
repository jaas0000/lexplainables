"""Runtime-config.

Wat: applicatie-brede instellingen die beheerders live kunnen aan-/uitzetten (bijv.
`capture_llm_calls`) zonder redeploy; TTL-cache voor lees-latentie; PATCH-endpoint voor
selectieve updates.
Waarom: eigen domein omdat runtime-instellingen niet in code horen (env-vars zijn
deploy-tijd) en niet in per-feature-config passen — een centrale key/value-tabel met
defaults en type-checks is de goede vorm.
Grens: alleen boolean/scalar-instellingen die de applicatie zelf gebruikt; geen
gebruikersvoorkeuren (dat is per-user, zit in `identiteit_toegang`); geen secrets (die
staan versleuteld in `llm_profielen` en env).

Tabellen:
  - app_instellingen: sleutel (PK) + waarde (Text, JSON-serialized) + bijgewerkt.

Beslissingen:
  - ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic contract voor `AppInstellingen`
    (typed schema over de generieke tabel).
  - Story 019 §TTL-cache: reads gebruiken een in-memory cache met TTL (default 30s);
    write-through zet de cache direct bij.
  - Story 019 §PATCH: partiële update — een lege patch is een no-op (geen 422); alleen
    expliciet meegegeven velden worden overschreven.

Interacties:
  - shared/auth.py: `huidige_beheerder` op admin-endpoint.
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
  - llm_calls (indirect): capture-laag leest `capture_llm_calls` uit deze feature om te
    bepalen of er iets opgeslagen wordt.
"""
