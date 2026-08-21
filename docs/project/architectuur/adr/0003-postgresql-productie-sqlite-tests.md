# ADR-0003: PostgreSQL in productie, SQLite blijft voor tests

**Status:** geaccepteerd
**Datum:** 2026-08-21

## Context

Werkwijze-ADR-0005 vereist Alembic voor migraties maar laat de DB-keuze open. Lexplainables
draait tot nu toe op SQLite (`aiosqlite`) — snel en zonder externe afhankelijkheid, maar
onbruikbaar in een enterprise-productiescontext. De doelgroep van de applicatie (klein team in
een enterprise-omgeving) kent alleen PostgreSQL als operationele DB.

Wetsanalyse-ai gebruikt al PostgreSQL met async SQLAlchemy + `asyncpg`, met een lease-reaper
voor async jobs en een startup-retry-loop voor cold-start-race-condities.

Alternatieven die overwogen zijn:
- **Alleen SQLite** — niet acceptabel voor de doelomgeving.
- **Alleen PostgreSQL** — verlengt de test-run (elke test start een Postgres-container of leunt
  op transacties/rollback), en verplaatst een goedkope CI-check naar een dure.
- **Testcontainers voor Postgres** — geeft wél de echte DB in tests, maar 10× langzamere
  test-runs en fragieler in CI. Niet voldoende opbrengst voor deze fase.

## Beslissing

**PostgreSQL is de enige productie-database.** SQLite blijft toegestaan als
**test-DB** en voor lokale ontwikkelaars die geen Docker willen draaien — Alembic-migraties
moeten op beide DBs schoon draaien (CI-check `check-migraties` op beide).

Concrete keuzes:
- Driver: `asyncpg` voor Postgres, `aiosqlite` voor SQLite.
- Dialect-specifieke SQL vermijden: `ON CONFLICT DO NOTHING` (Postgres) én `INSERT OR IGNORE`
  (SQLite) — waar mogelijk gebruiken we een update-dan-insert-patroon dat op beide identiek werkt
  (voorbeeld: `feedback_leesbewijzen.markeer_gezien` in `api/app/features/feedback/store.py`).
- Startup: bounded retry op DB-connect voor cold-start (zoals in wetsanalyse-ai's `main.py`).

## Consequenties

- **Bewust geaccepteerd:** twee database-dialecten onderhouden. Elke feature moet zijn SQL zo
  schrijven dat 'ie op beide draait; dat kost aandacht en betekent dat sommige Postgres-only
  patronen (bijv. `JSONB`-indexen, `LATERAL JOIN`) niet gebruikt kunnen worden. Voor het
  feature-oppervlak van deze applicatie is die beperking mild.
- **CI weegt beide dialecten:** `check-migraties` draait upgrade+downgrade op zowel SQLite als
  Postgres. Elke feature-testrun draait alleen op SQLite — een aparte integratietest-suite tegen
  Postgres zit alleen op de kritieke paden (annotatie, async jobs).
- **Docker-compose met Postgres** wordt de standaard voor lokaal draaien. Ontwikkelaars die
  bewust op SQLite willen werken kunnen `DATABASE_URL=sqlite+aiosqlite:///./dev.db` zetten.
- **Vervangt niets uit werkwijze-v2** — dit is een projectkeuze binnen de vrijheid die ADR-0005
  van de werkwijze expliciet openlaat.
