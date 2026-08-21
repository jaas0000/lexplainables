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
- `api/app/features/projecten/` — analyses aanmaken/volgen, SSE voortgang, echte LLM-orkestratie act2/act3 (PR #11, #17, stories 012/024); rapport-endpoint + Markdown-download (PR #19, story 013); LLM-calls log (PR #20, story 021)
- `api/app/features/llm_calls/` — capture-tabel + store, endpoint blijft in projecten
- `api/app/features/annotatie/` — documenten, elementen, beslissingen, auditlog (PR #21, story 022)
- `api/app/features/api_tokens/` — aanmaken, intrekken, DB-verificatielaag (PR #18, story 018)
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
- `/projecten/{id}/rapport` — rapport bekijken + Markdown-download (PR #19, story 013)
- `/beheer/llm-calls` — LLM-calls log per analyse (PR #20, story 021)
- `/beheer/api-tokens` — API-tokens aanmaken + intrekken (PR #18, story 018)
- `/werkplek/`, `/werkplek/{slug}` — annotatie-werkplek: documentenlijst + beslissingen per element (PR #22, story 023)
- `app/mockup/` — resterende interactieve mockups (nog niet gepromoveerd)

**`tools/wetsanalyse-admin-mcp/`** — Admin-MCP (PR #6, story 007)

Keycloak is **volledig verwijderd** (PR #5, story 006). Geen Keycloak-service in docker-compose of CI.

**Alembic-migraties:** 0001–0011 draaien clean op SQLite.

**Nog te bouwen:** 2FA/TOTP (story 017, laag). Services: `frontend-chat`, `tools/wettenbank-mcp`, `tools/graph-qa`.

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

Zes services, zie [`docs/project/architectuur/adr/0001-multi-service-topologie.md`](docs/project/architectuur/adr/0001-multi-service-topologie.md)
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
[`docs/project/architectuur/stack-profiel.md`](docs/project/architectuur/stack-profiel.md) — `feature-bouwen`
regel 3 leest daaruit.

## Instellingen

- **Autonome merge:** ja <!-- ja | nee -->
  `ja` — `pr-triage` mergt direct zodra `code-review` niets blocking meer vindt (of bij een
  mechanische dependency-bump met CI groen). Zie `pr-triage` regel 2a/4/5 voor de exacte
  stappen bij het mergen.

- **Simplify bij feature-bouwen:** nee <!-- ja | nee -->
  `nee` — tijdens de wetsanalyse-migratie (zie `docs/project/migratie-wetsanalyse.md`)
  slaan we simplify standaard over. Reden: retrocatief simplify op fase 0-2 (PR #45) leverde
  in verhouding weinig substantie op (~2.5M tokens voor −13 lines, 1 echte dedup). De
  werkwijze aanvaardt dit expliciet — `feature-bouwen` regel 9 zet dan zelf
  `Simplify: overgeslagen (instelling staat op nee)` in het commit-/PR-bericht, zodat de
  keuze zichtbaar blijft en niet stilzwijgend wordt genegeerd. Zet weer op `ja` als de
  refactor voorbij is en er stabielere feature-ontwikkeling start.

## Docs-structuur

- `docs/project/` — hoe we werken en wat we hebben gebouwd: `architectuur/` (ADR's over dit
  project), `werkwijze/` (methodologie-ADR's + de originele werkwijze-`CLAUDE.md`), `features/`
  (gegenereerd door `scripts/docs/genereer-feature-docs.py`), `stories/`, `vervolgpunten.md`,
  `changelog-technisch.md`.
- `docs/domein/` — waar de app over gaat: JAS, wetsanalyse-methode, WetsTaal, referenties.
  Vult zich naarmate wetsanalyse-content wordt overgezet.
- `CHANGELOG.md` blijft op de root (open-source-conventie).

## Skills

De skills staan in `.claude/skills/` — in-project, geen sibling-repo-dependency. De methode
zelf staat in `docs/project/werkwijze/CLAUDE.md` (met bijbehorende ADR's onder
`docs/project/werkwijze/adr/`); dit CLAUDE.md hier verwijst naar die inhoud maar herhaalt hem
niet. Zodra de werkwijze stabiel is en herbruikbaar moet worden voor een tweede project, is de
afsplitsing terug naar een aparte werkwijze-repo triviaal (`.claude/skills/` +
`docs/project/werkwijze/` kopiëren).

## Volgende stap

Story 017 (2FA/TOTP, laag) is de enige resterende API/frontend-story. Daarna de vier nog te
bouwen services: `frontend-chat`, `tools/wettenbank-mcp`, `tools/graph-qa`
(`tools/wetsanalyse-admin-mcp/` is klaar).
