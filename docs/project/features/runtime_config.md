# Runtime-config

applicatie-brede instellingen die beheerders live kunnen aan-/uitzetten (bijv. `capture_llm_calls`) zonder redeploy; TTL-cache voor lees-latentie; PATCH-endpoint voor selectieve updates.

**Waarom apart:** eigen domein omdat runtime-instellingen niet in code horen (env-vars zijn deploy-tijd) en niet in per-feature-config passen — een centrale key/value-tabel met defaults en type-checks is de goede vorm.

**Grens:** alleen boolean/scalar-instellingen die de applicatie zelf gebruikt; geen gebruikersvoorkeuren (dat is per-user, zit in `identiteit_toegang`); geen secrets (die staan versleuteld in `llm_profielen` en env).

## Datamodel

### `app_instellingen`
sleutel (PK) + waarde (Text, JSON-serialized) + bijgewerkt.

| kolom | type | eigenschappen |
|---|---|---|
| `sleutel` | `Text()` | primary key |
| `waarde` | `Text()` | NOT NULL |
| `bijgewerkt` | `DateTime(timezone=True)` | NOT NULL |

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `GET` | `/admin/instellingen` | beheerder | `AppInstellingen` |
| `PUT` | `/admin/instellingen` | beheerder | `AppInstellingen` |

## Interacties

- shared/auth.py: `huidige_beheerder` op admin-endpoint.
- db.py: `AsyncEngine` via `get_engine()` naar de store.
- llm_calls (indirect): capture-laag leest `capture_llm_calls` uit deze feature om te bepalen of er iets opgeslagen wordt.

## Getest gedrag

- Lees defaults zonder rijen in db.
- Schrijf en lees capture llm calls aan.
- Schrijf en lees capture llm calls uit.
- Ttl cache geeft zelfde object terug zonder db hit.
- Put met lege patch muteert niet.
- Zonder auth geeft 401.

## Beslissingen

- ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic contract voor `AppInstellingen` (typed schema over de generieke tabel).
- Story 019 §TTL-cache: reads gebruiken een in-memory cache met TTL (default 30s); write-through zet de cache direct bij.
- Story 019 §PATCH: partiële update — een lege patch is een no-op (geen 422); alleen expliciet meegegeven velden worden overschreven.
