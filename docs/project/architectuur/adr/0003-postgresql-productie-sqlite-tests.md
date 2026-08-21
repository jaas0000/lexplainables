# ADR-0003: PostgreSQL — enige database, ook in tests

**Status:** geaccepteerd
**Datum:** 2026-08-21
**Bijgewerkt:** 2026-08-21 (SQLite volledig verwijderd; oorspronkelijke tekst hieronder)

## Context

Werkwijze-ADR-0005 vereist Alembic voor migraties maar laat de DB-keuze open. De doelgroep
(klein team in een enterprise-omgeving) kent alleen PostgreSQL als operationele DB.

Aanvankelijk (versie 1 van deze ADR, hieronder in het historische spoor) was de keuze:
Postgres in productie, SQLite blijft toegestaan als test-DB en voor lokale dev. Dat leek
comfortabel, maar bracht drie kosten mee:

- **Twee dialecten onderhouden.** Elke feature moet SQL zo schrijven dat 'ie op beide draait.
- **Latent bugs.** Postgres/asyncpg is strikter dan SQLite (tz-aware datetimes op
  `timestamptz`-kolommen, boolean server-defaults). Die kwamen pas naar boven toen fase 1
  story 2 (PR #37) een echte Postgres-CI-matrix invoerde — precies wat je niet wil.
- **Ondersteboven prioriteit.** SQLite maakte lokaal draaien iets makkelijker, maar productie
  is Postgres — de tests horen te bewijzen dat de productiepad werkt, niet de dev-comfort-pad.

Alternatieven op het moment van deze update:
- **SQLite behouden voor tests** (versie 1): de bewezen bron van latent-bugs.
- **Testcontainers** (SQLite eruit + Postgres per test-run gepromoveerd): de gekozen route.
- **In-memory Postgres-alternatief**: bestaat niet betrouwbaar; testcontainers is de norm.

## Beslissing

**PostgreSQL is de enige database — ook in tests.** SQLite (en `aiosqlite`) volledig
verwijderd. Zowel productie als CI als lokale dev draaien tegen Postgres.

Concreet:
- Driver: `asyncpg` (runtime, via SQLAlchemy async), `psycopg2-binary` (Alembic sync-migraties).
- CI: één Postgres-service per relevante job (`test-api`, `check-migraties`).
- Lokaal draaien: `docker compose up -d postgres`, dan `TEST_DATABASE_URL(_SYNC)` zetten.
- Test-schema-reset: `metadata.drop_all → metadata.create_all` per test (via de
  `maak_test_engine`-helper in `api/conftest.py`), met `NullPool` om verbindingsuitputting te
  voorkomen bij ~166 tests.

## Consequenties

- **Bewust geaccepteerd:** ontwikkelaars hebben Docker (of een lokale Postgres) nodig om
  tests te draaien. Voor deze doelgroep (enterprise-team, kant-en-klare docker-compose
  meegeleverd) is dat geen echte drempel.
- **Winst:** één set SQL-patronen. Elke bug die zich alleen op Postgres manifesteert,
  manifesteert zich ook in CI. Geen valse zekerheid meer via "SQLite is groen, dus goed".
- **Test-run iets langzamer:** Postgres-schema-reset per test kost meer dan een fresh
  in-memory SQLite. Compenseert door NullPool zodat verbindingen niet ophopen. Netto op deze
  suite: van ~7s (SQLite-only) naar ~45s (Postgres). Acceptabel — geen deployment-bottleneck.
- **Migraties simpeler:** geen dialect-agnostische SQL meer nodig. Postgres-specifieke
  features (JSONB, `SELECT FOR UPDATE SKIP LOCKED`, advisory locks, partial indexes) mogen
  vanaf hier zonder omweg — nodig voor bijv. story 3 (async jobstore met lease-reaper).

## Historisch spoor: versie 1 (2026-08-21)

De eerste versie van deze ADR koos voor "Postgres in productie, SQLite in tests" als
compromis. Dat werd binnen dezelfde dag herzien: fase 1 story 2 introduceerde een echte
Postgres-test-matrix (PR #37) die 2 latent-bugs onthulde (naive datetime,
boolean-server-default). Kort daarna volgde het besluit om SQLite volledig te schrappen — de
bewijskracht van "onze tests draaien tegen productie-DB" woog zwaarder dan het gemak van
SQLite-fixtures.

Geen aparte "vervangen door"-ADR: dit is dezelfde beslissing, aangescherpt op basis van wat we
zagen. De tekst hierboven weerspiegelt de definitieve stand.
