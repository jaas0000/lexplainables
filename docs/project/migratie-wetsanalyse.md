# Migratie wetsanalyse-ai → lexplainables

Plan om de bestaande wetsanalyse-ai-codebase over te zetten naar lexplainables onder
werkwijze-v2. Vastgelegd 2026-08-21.

## Context

Lexplainables is voortgekomen als proefopstelling voor werkwijze-v2 en heeft nu ~10 features
werkwijze-conform gebouwd (feedback, berichten, identiteit_toegang, wetcatalogus, llm_profielen,
projecten, annotatie, api_tokens, runtime_config, llm_calls). Wetsanalyse-ai is een breder maar
structureel platter platform (29 losse modules onder `api/app/`, god-modules van 500-1000
regels) met wél volwassener operationele elementen: Postgres, OpenTelemetry, litellm, Azure
Container Apps, Auth.js.

Doel: **één codebase** die de features van wetsanalyse-ai heeft en de werkwijze van
lexplainables volgt. Lex is de basis, wetsanalyse-ai levert de missing pieces.

## Kernbeslissingen

- **Route B**: lex is refactor-basis, geen greenfield en geen in-place refactor van
  wetsanalyse-ai. Reden: greenfield-basis in werkwijze-vorm is klaar, in-place refactor van 5000+
  regels wetsanalyse-code kost meer dan opnieuw bouwen onder de werkwijze.
- **Bij conflicten wint wetsanalyse-ai**: Postgres i.p.v. SQLite, Auth.js i.p.v. custom login,
  litellm i.p.v. eenvoudige wrapper, OpenTelemetry i.p.v. niets, echte deploy i.p.v. niets.
- **Niets uit lex hoeft behouden**: alles is expliciet dienend aan de migratie.
- **JAS-pipeline is legacy**: alleen annotatie blijft als analyse-stap. Wat in wetsanalyse-ai
  onder `engine/*` (`orchestrator.py` 1023r, `regelspraak_*`, `validation.py`,
  `render_regelspraak.py`) staat gaat níét mee. Consequentie voor lex: **story 013 (rapport) en
  story 024 (analyse-engine) moeten weer opgeruimd worden** — die zijn tijdens de eerste opbouw
  gebouwd op basis van de oude aanname dat act2/act3 nog relevant waren.
- **Skills 1:1 gekopieerd**: `.claude/skills/wetsanalyse` en `.claude/skills/regelspraak` uit
  wetsanalyse-ai gaan letterlijk over — regelspraak-skill wordt niet meer op runtime gebruikt
  maar de `references/` blijven bruikbaar als domein-materiaal.

## Doelgroep + operationele eisen

- **Enterprise-klein-team** dat alleen Postgres kent → Postgres is verplicht, geen SQLite in
  productie (test-DB mag SQLite blijven zolang alle Alembic-migraties op beide draaien).
- **AI-first ontwikkeling** door één developer → werkwijze-v2 is precies daarvoor ontworpen; de
  prescriptiviteit is een pluspunt, niet een last.
- **Nog niet in productie** → nu is het goedkoopste moment om structureel te wijzigen.

## Ontbrekende delta (uit wetsanalyse-ai)

**Infrastructuur (plumbing):**
1. PostgreSQL + Alembic-migraties op beide DBs
2. OpenTelemetry-observability
3. Rate limiting
4. Secrets crypto uitbreiding
5. Litellm-adapter met capture + throttle + retry
6. Auth.js in frontend (custom-store aan de api-kant blijft)
7. Async jobstore met lease-reaper op Postgres
8. Docker-compose voor lokaal draaien (Postgres + services)
9. CI/CD-workflows naar Azure Container Apps

**Domein:**
10. 2FA/TOTP (story 017 in lex — nog niet gebouwd)
11. Rijkshuisstijl volledig (Belastingdienst-stijlvak, JAS-klassekleuren, Fira-fonts)

**Aparte services:**
12. `tools/wettenbank-mcp` — MCP-server met bwbId/artikel/lid/jci-uri
13. `tools/graph-qa` — LangGraph-agent, supervisor + antwoord-worker (specialisten
    definitie/duiding/algemeen) + annotatie-worker + provenance + grounding (~3286r)
14. `frontend-chat` — losse Next.js chat-app met SSE-streaming tegen graph-qa

**Frontend-uitbreidingen:**
15. Werkplek volledig maken tegen echte graph-qa (nu leunt lex op eigen backend)
16. Analyse-webapp UI: nieuwe project-creatie, review-visualisaties

## Aanpak — 6 fases

Master mag niet lang stuk zijn. Elke fase eindigt op werkende master, met concrete winst.

### Fase 0 — Fundering (1 week, 1 PR)

- Migratieplan-doc committen (dit bestand)
- Stack-profiel aanvullen met de definitieve keuzes (Postgres, Auth.js, litellm, OTel, deploy)
- Nieuwe project-ADR's schrijven voor de zes belangrijkste keuzes
- Alembic ondersteunt Postgres én SQLite; asyncpg toegevoegd
- Docker-compose met Postgres + api + frontend, werkend `docker compose up`

**Eindstaat:** stack-profiel klopt met de bestemming; iemand die de repo cloont kan lokaal
Postgres draaien.

### Fase 1 — Opruimen + Postgres-migratie (2 weken, 3-5 PRs)

- Story: `rm -rf` op story 013 (rapport) en story 024 (analyse-engine) — deprecated JAS-pipeline
- Story: SQLite → Postgres in alle bestaande features; `INSERT OR IGNORE` → `ON CONFLICT`
- Story: async jobstore-basis (lease-reaper op Postgres) — nodig voor annotatie-jobs later
- Ci: `check-migraties` draait tegen SQLite én Postgres

**Eindstaat:** lex draait op Postgres, alle tests groen, JAS-orchestratie weg.

### Fase 2 — Infrastructuur-upgrades (3 weken, 5-6 PRs)

- Story: Auth.js in frontend, sessie-management uit lex's custom auth halen
- Story: OpenTelemetry-setup — traces + metrics + logs, per service
- Story: Rate limiting als `shared/`-module
- Story: Litellm-adapter met capture (in `llm_calls`-tabel) + throttle + retry
- Story: 2FA/TOTP afmaken (was story 017 in lex, wetsanalyse-ai heeft dit al)

**Eindstaat:** operationele volwassenheid van wetsanalyse-ai overgezet.

### Fase 3 — Rijkshuisstijl + fine-tuning (1 week, 2 PRs)

- Story: Belastingdienst-stijlvak, JAS-klassekleuren, Fira-fonts, Belastingdienst-logo
- Story: UI-details die tijdens fase 2 aan het licht zijn gekomen

**Eindstaat:** lex ziet er visueel uit als wetsanalyse-ai.

### Fase 4 — Aparte services (6-10 weken, gedeeltelijk parallel)

- **`tools/wettenbank-mcp`** — TypeScript MCP-service, contract-first per tool
  (~5-8 stories)
- **`tools/graph-qa`** — LangGraph-agent volledig herbouwd onder werkwijze: supervisor,
  antwoord-worker (specialisten), annotatie-worker, tools, provenance, grounding
  (~15-20 stories)
- **`frontend-chat`** — losse Next.js-app met SSE-streaming tegen graph-qa, gedeelde Auth.js
  (~8-10 stories)
- **Werkplek uitbreiden**: hoofdfrontend praat via BFF met graph-qa i.p.v. eigen backend

**Eindstaat:** alle 6 services uit wetsanalyse-ai bestaan onder de werkwijze.

### Fase 5 — Deploy + operations (2 weken, 2-3 PRs)

- Azure Bicep + workflows per service
- Portainer-stacks
- Observability-stack (Grafana + Prometheus + Loki + Tempo)

**Eindstaat:** lex is deploybaar naar dezelfde targets als wetsanalyse-ai.

## Ruwe totaalinschatting

25-30 stories, **3-5 maanden** met werkwijze-v2 strikt gevolgd. Ter vergelijking: de
docs-infra-refactor van 2026-08-21 kostte ~785k tokens (~4 features aan werk); een gemiddelde
story-cluster kost 300-500k. Totaal daarmee ~10-15 miljoen tokens.

## Status

**Huidige fase:** 0 — Fundering (gestart 2026-08-21).

## Wat níét in dit plan hoort

- **Detail-implementaties per feature**: die staan in `docs/project/stories/<nr>-<naam>.md`
  zoals de werkwijze voorschrijft. Dit plan is de meta-laag daarboven.
- **Domein-inhoud** (JAS-schema, WetsTaal, wet-referenties) — die verhuist tijdens fase 4/5
  naar `docs/domein/` uit wetsanalyse-ai's `docs/`-map.
- **Vervolgpunten binnen een fase**: eindigen in `docs/project/vervolgpunten.md` zoals gewoon.
