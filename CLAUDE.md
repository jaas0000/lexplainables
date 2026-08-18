# CLAUDE.md — lexplainables

Startpunt voor een nieuw project op basis van de multi-service contract-first werkwijze. De
methodologie, skills en achtergrond staan in
[werkwijze-v2-multi-service](https://github.com/jaas0000/werkwijze-v2-multi-service).

**Stand van zaken:** topologie en stack-profiel liggen vast (zie hieronder). Gebouwde features:
- `api/app/features/feedback/` — indienen, admin-lijst, verwijderen, ongelezen-aantal, markeer-gezien
- `api/app/features/berichten/` — aanmaken, bewerken, publiceren/depubliceren, verwijderen (admin); lezen, ongelezen-status, lees-alles (analist)
- `api/app/features/identiteit_toegang/` — eigen `gebruikers`-tabel, bcrypt, `POST /v1/auth/verify` achter API_TOKEN
- `api/app/shared/auth.py` — API_TOKEN-gate + X-User-Id-header (geen Keycloak meer)
- `api/app/shared/crypto.py` — Fernet-encryptie voor API-sleutels (PR #10, story 011)
- `api/app/features/wetcatalogus/` — wettenlijst + structuuropvraag (PR #9, story 010)
- `api/app/features/llm_profielen/` — CRUD voor LLM-profielen + Fernet-encryptie van API-sleutels (PR #10, story 011)
- `frontend/` — login (Auth.js v5 Credentials, httpOnly cookie); navigatie (logobalk, nav met Beheer-tab + bel-icoon popover); pagina's:
  - `app/page.tsx` — startpagina (banner)
  - `app/beheer/page.tsx` — beheer (berichten CRUD + LLM-profielen teller via BFF; gebruikers/feedback/instellingen placeholder)
  - `app/beheer/llm-profielen/page.tsx` — LLM-profielen CRUD (aanmaken, bewerken, standaard instellen, verwijderen) (PR #10, story 011)
  - `app/berichten/page.tsx` — berichten lees-weergave voor analisten (gepubliceerde berichten + lees-alles)
  - `app/wetcatalogus/page.tsx` — wetcatalogus met WetSelector-component (PR #9, story 010)
  - `app/mockup/` — interactieve mockups met nepdata (fase 1 `frontend-bouwen`); staan los van de echte routes
  - BFF-routes: `app/api/admin/berichten/`, `app/api/berichten/`, `app/api/wetten/`, `app/api/admin/profielen/`
- `tools/wetsanalyse-admin-mcp/` — Admin-MCP (PR #6, story 007): 4 tools (`list_berichten_admin`, `maak_bericht`, `update_bericht`, `publiceer_bericht`); registreerbaar in `.mcp.json`

Keycloak is **volledig verwijderd** (PR #5, story 006). Geen Keycloak-service in docker-compose of CI.

De overige zes domeinen van `api` en de vier andere services uit de topologie hieronder staan nog niet (`tools/wetsanalyse-admin-mcp/` is gebouwd, PR #6).

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

De overige zes domeinen van `api` (analyse/jobs, LLM-configuratie, wetcatalogus, runtime-config,
annotatie, orkestratie) als evenzoveel feature-mappen herbouwen — dat is nog steeds de grootste
stap, zie het topologie-ADR §Consequenties — daarna de vier resterende services opzetten
(`frontend-chat`, `tools/wettenbank-mcp`, `tools/graph-qa`; `tools/wetsanalyse-admin-mcp` is
klaar), het CI/CD-sjabloon invullen, en cross-service-contracten instantiëren zodra er meer dan
één service is om te verbinden.
