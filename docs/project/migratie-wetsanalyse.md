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

**Bijgewerkt 2026-08-26** — de status hieronder liep sinds fase 0 niet meer synchroon met wat
er daadwerkelijk gebouwd is; onderstaande vinkjes zijn geverifieerd tegen de huidige codebase
(niet aangenomen).

**Infrastructuur (plumbing):**
1. ✅ PostgreSQL + Alembic-migraties (SQLite blijft voor tests, ADR-0003)
2. ✅ OpenTelemetry-observability (`api/app/shared/observability.py`)
3. ✅ Rate limiting (`api/app/shared/rate_limit/` — login én `chat_proxy`, PR #97)
4. ✅ Secrets crypto (`api/app/shared/crypto.py`)
5. ✅ Litellm-adapter met capture + throttle + retry (`api/app/shared/llm/`)
6. ✅ Auth.js in `frontend/` én `frontend-chat/` (custom-store aan de api-kant, ADR-0003)
7. ✅ Async jobstore met lease-reaper op Postgres (`api/app/shared/jobs/`, reaper-loop in
   `api/app/main.py`)
8. Docker-compose voor lokaal draaien — nog niet geverifieerd, mogelijk nog open
9. CI/CD-workflows naar Azure Container Apps — nog niet geverifieerd, mogelijk nog open

**Domein:**
10. ✅ 2FA/TOTP (`api/app/features/identiteit_toegang/` — `/2fa/begin`/`/activate`/`/disable`)
11. Rijkshuisstijl volledig (Belastingdienst-stijlvak, JAS-klassekleuren, Fira-fonts) — de
    JAS-klassekleuren zelf zijn overgenomen (`shared/validation.py`, PR #98, voor de
    annotatie-PDF-export), de rest (stijlvak, Fira-fonts, logo) nog niet
12. ✅ Annotatie-domein op api-parity met de referentie (PR #98): jurist kan zelf elementen
    aanmaken/verwijderen, een annotatie expliciet afronden/heropenen (schrijf-slot), en
    exporteren (PDF/CSV/JSON)

**Aparte services (herzien 2026-08-22 — zie ai-notes/fase-4-aparte-services-plan.md voor de
volledige toelichting: `tools/wettenbank-mcp` bestaat niet meer in wetsanalyse-ai, vóór dit
migratieplan al verwijderd; wettekst komt daar via een GraphDB-kennisgraaf):**
13. ✅ `deploy/graphdb` (infra) + `tools/bwb-import` — ETL-pipeline die het Basiswettenbestand
    in een GraphDB-kennisgraaf zet — inhoudelijk afgerond (stories 024-036)
14. ✅ `tools/graph-qa` grotendeels — LangGraph-agent: supervisor, antwoord-worker
    (specialisten definitie/duiding/algemeen), annotatie-worker (annoteren → critic →
    patch/herzie → emit), HTTP-laag + run-model, en een schrijfpad terug naar `api` (annotatie
    + gespreksgeschiedenis, PR #96/#97) — `/v1/artikel`-achtige losse lookup-endpoints e.d. nog
    niet geïnventariseerd
15. ✅ `frontend-chat` — losse Next.js chat-app met SSE-streaming tegen graph-qa, incl.
    doel-annotatietrigger en een gespreksgeschiedenis-sidebar (PR #97)

**Frontend-uitbreidingen:**
16. Werkplek (`frontend/`) volledig maken tegen echte graph-qa (nu leunt lex op eigen backend
    voor annotatie) — nog niet gestart, de api-laag (item 12) is er nu wel klaar voor
17. Analyse-webapp UI: nieuwe project-creatie, review-visualisaties — nog niet gestart

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

- **`deploy/graphdb`** — GraphDB-kennisgraaf (infra-deploy, geen story-cyclus) +
  **`tools/bwb-import`** — ETL-pipeline BWB → GraphDB, contract-first per stap (~10-15 stories)
- **`tools/graph-qa`** — LangGraph-agent volledig herbouwd onder werkwijze: supervisor,
  antwoord-worker (specialisten), annotatie-worker, tools, provenance, grounding, run-model
  (~25-35 stories — herzien 2026-08-22, was ~15-20)
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

**Herzien 2026-08-22** (was 25-30 stories / 3-5 maanden — te laag ingeschat, zie
ai-notes/fase-4-aparte-services-plan.md §Herzieningslog): fase 4 alleen al ~46-65 stories
(deploy/graphdb + bwb-import ~10-15, graph-qa ~25-35, frontend-chat ~8-10,
werkplek-koppeling ~3-5), plus fases 0-3 (grotendeels afgerond) en fase 5. Totaal ~60-75
stories, eerder **6-9 maanden** dan 3-5. Ter vergelijking: de docs-infra-refactor van
2026-08-21 kostte ~785k tokens (~4 features aan werk); een gemiddelde story-cluster kost
300-500k. Totaal daarmee eerder 20-25 miljoen tokens dan de eerdere 10-15 miljoen.

## Status

**Huidige fase:** 0 — Fundering (gestart 2026-08-21).

## Wat níét in dit plan hoort

- **Detail-implementaties per feature**: die staan in `docs/project/stories/<nr>-<naam>.md`
  zoals de werkwijze voorschrijft. Dit plan is de meta-laag daarboven.
- **Domein-inhoud** (JAS-schema, WetsTaal, wet-referenties) — die verhuist tijdens fase 4/5
  naar `docs/domein/` uit wetsanalyse-ai's `docs/`-map.
- **Vervolgpunten binnen een fase**: eindigen in `docs/project/vervolgpunten.md` zoals gewoon.
