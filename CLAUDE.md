# CLAUDE.md — lexplainables

Startpunt voor een nieuw project op basis van de multi-service contract-first werkwijze. De
methodologie, skills en achtergrond staan in
[werkwijze-v2-multi-service](https://github.com/jaas0000/werkwijze-v2-multi-service).

**Stand van zaken:** topologie en stack-profiel liggen vast (zie hieronder). Gebouwde features:

**`api/` — feature-mappen:**
- `api/app/features/feedback/` — indienen, admin-lijst, verwijderen, ongelezen-aantal, markeer-gezien (PR #1–#8)
- `api/app/features/berichten/` — aanmaken, bewerken, publiceren/depubliceren, verwijderen (admin); lezen, ongelezen-status, lees-alles (analist)
- `api/app/features/identiteit_toegang/` — gebruikers-tabel, bcrypt, auth/verify, setup (eerste beheerder), CRUD beheerder, account/wachtwoord-wijzigen (PR #12, #13, #14)
- `api/app/features/wetcatalogus/` — database-backed (tabel `wet_catalogus`, migratie 0007), admin CRUD + resolve via Wettenbank-MCP (PR #9 story 010, PR #15 story 020)
- `api/app/features/llm_profielen/` — CRUD + Fernet-encryptie van API-sleutels (PR #10, story 011)
- `api/app/features/projecten/` — analyses aanmaken/volgen, SSE voortgang, nep-engine (PR #11, story 012); **echte LLM-orkestratie nog niet gebouwd**
- `api/app/features/runtime_config/` — `app_instellingen`-tabel (migratie 0008), toggle `capture_llm_calls`, TTL-cache (PR #16, story 019)
- `api/app/shared/auth.py` — API_TOKEN-gate + X-User-Id-header (geen Keycloak)
- `api/app/shared/crypto.py` — Fernet-encryptie

**`frontend/` — pagina's:**
- `/` — startpagina (banner)
- `/login`, `/setup` — auth-flow
- `/account` — eigen profiel + wachtwoord wijzigen (PR #12)
- `/beheer` — overzicht met navigatie naar alle beheer-secties
- `/beheer/llm-profielen` — LLM-profielen CRUD (PR #10)
- `/beheer/gebruikers` — gebruikersbeheer CRUD (PR #14)
- `/beheer/wetten` — wetcatalogus admin CRUD + resolve (PR #15)
- `/beheer/instellingen` — LLM-invoer vastleggen toggle (PR #16)
- `/berichten` — berichten voor analisten
- `/wetcatalogus` — wetcatalogus lezen
- `/projecten`, `/projecten/nieuw` — analyses aanmaken + SSE volgen (PR #11)
- `app/mockup/` — resterende interactieve mockups (nog niet gepromoveerd)

**`tools/wetsanalyse-admin-mcp/`** — Admin-MCP (PR #6, story 007)

Keycloak is **volledig verwijderd** (PR #5, story 006). Geen Keycloak-service in docker-compose of CI.

**Alembic-migraties:** 0001–0008 draaien clean op SQLite.

**Nog te bouwen:** analyse-engine (LLM-orkestratie, act2/act3), rapport bekijken (story 013), 2FA (017), API-tokens (018), LLM-calls log (021), annotatie-backend (022), werkplek-UI (023).

Draai het lokaal: `cd api && uv sync && uv run pytest -q` (tests groen), `uv run ruff check . &&
uv run ruff format --check .` (codestandaard schoon), `alembic upgrade head` tegen een schone
SQLite-db (migratie draait). Seed een dev-gebruiker:
```bash
uv run python -c "
import asyncio
from app.db import get_engine
from app.features.identiteit_toegang.store import maak_gebruiker_indien_ontbreekt
asyncio.run(maak_gebruiker_indien_ontbreekt(get_engine(), 'beheerder', 'beheerder123', 'beheerder'))
"
```

## Structuur (topologie vastgelegd; gebouwd: `api`, `frontend`, `tools/wetsanalyse-admin-mcp`)

Zes services, zie [`docs/architectuur/adr/0001-multi-service-topologie.md`](docs/architectuur/adr/0001-multi-service-topologie.md)
voor de volledige afweging:

| Service | Verantwoordelijk voor |
|---|---|
| `api/` | Kernbackend: analyse/jobs, LLM-configuratie, auth, wetcatalogus, runtime-config, annotatie, berichten, feedback, admin, orkestratie (module) |
| `frontend/` | Hoofdwebapp (BFF) |
| `frontend-chat/` | Losse chatapp |
| `tools/wettenbank-mcp/` | MCP-server, wetcatalogus-lookups |
| `tools/graph-qa/` | QA-/annotatie-agent |
| `tools/wetsanalyse-admin-mcp/` | Admin-MCP |

Alle projectspecifieke stack-keuzes (de ene bron, contractgeneratie, feature-eenheid, dunne
verzamelaars, migraties, frontends, codestandaard) staan in
[`docs/architectuur/stack-profiel.md`](docs/architectuur/stack-profiel.md) — `feature-bouwen`
regel 3 leest daaruit.

## Instellingen

- **Autonome merge:** ja <!-- ja | nee -->
  `ja` — `pr-triage` mergt direct zodra `code-review` niets blocking meer vindt (of bij een
  mechanische dependency-bump met CI groen). Zie `pr-triage` regel 2a/4/5 voor de exacte
  stappen bij het mergen.

- **Simplify bij feature-bouwen:** ja <!-- ja | nee -->
  `ja` — `feature-bouwen` regel 9 draait `/simplify` vóór elke aflevering.

## Skills

De skills staan in `werkwijze-v2-multi-service/werkwijze/.claude/skills/` — niets kopiëren.
Zolang die repo als sibling-map in dezelfde workspace staat als deze repo, ontdekt Claude Code
`.claude/skills/` uit elke aanwezige repo zelf en scoped ze automatisch op pad (bv.
`werkwijze-v2-multi-service/werkwijze:code-review`), ook als een andere, niet-verwante repo in
dezelfde workspace toevallig een skill met dezelfde naam heeft.

## Volgende stap

De analyse-engine (echte LLM-orkestratie, act2/act3, rapportgeneratie) is het grootste resterende
werk — de nep-`BackgroundTask` in `projecten/` moet vervangen worden. Daarna story 013 (rapport
bekijken), 021 (LLM-calls log), 017 (2FA), 018 (API-tokens), 022 (annotatie-backend) en 023
(werkplek-UI). De vier resterende services (`frontend-chat`, `tools/wettenbank-mcp`,
`tools/graph-qa`) staan nog niet; `tools/wetsanalyse-admin-mcp/` is klaar.
