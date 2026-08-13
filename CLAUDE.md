# CLAUDE.md — lexplainables

Startpunt voor een nieuw project op basis van de multi-service contract-first werkwijze. De
methodologie, skills en achtergrond staan in
[werkwijze-v2-multi-service](https://github.com/jaas0000/werkwijze-v2-multi-service).

**Stand van zaken:** topologie en stack-profiel liggen vast (zie hieronder), en de `api`-service
bevat zijn eerste feature: het feedback-domein (`api/app/features/feedback/`) — indienen,
admin-lijst met paginering, verwijderen, ongelezen-aantal en markeer-gezien. Herbouwd op basis
van het feedback-domein van een extern, bestaand project (niet gekopieerd, opnieuw opgezet met
vertical slicing, een store-abstractie en een eigen `feedback_leesbewijzen`-tabel in plaats van
een geleende kolom op een users-tabel) — zie
[`docs/stories/001-feedback-indienen-en-beheren.md`](docs/stories/001-feedback-indienen-en-beheren.md)
voor de volledige afweging. De overige zeven domeinen van `api` en de vijf andere services uit
de topologie hieronder staan nog niet.

Draai het lokaal: `cd api && uv sync && uv run pytest -q` (tests groen), `uv run ruff check . &&
uv run ruff format --check .` (codestandaard schoon), `alembic upgrade head` tegen een schone
SQLite-db (migratie draait).

## Structuur (topologie vastgelegd, `api`/feedback gebouwd, rest nog niet)

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

De overige zeven domeinen van `api` (analyse/jobs, LLM-configuratie, auth, wetcatalogus,
runtime-config, annotatie, berichten) als evenzoveel feature-mappen herbouwen — dat is nog
steeds de grootste stap, zie het topologie-ADR §Consequenties — daarna de vijf andere services
opzetten, het CI/CD-sjabloon invullen, en cross-service-contracten instantiëren zodra er meer
dan één service is om te verbinden.
