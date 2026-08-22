# Story 028: bwb-import — orkestratie, FastAPI-service, Dockerfile, CI-publish

**Prioriteit:** hoog
**Story points:** 3
**Service:** `tools/bwb-import/`
**Afhankelijkheid:** story 027 (GraphDB-writer)

## Verhaal

De losse bouwstenen (downloader, parser, writer) bestaan; deze story rijgt ze aaneen tot een
daadwerkelijk draaiende service: een CLI voor handmatige/gescripte imports en een FastAPI-wrapper
zodat een andere service (of een cron) een import kan triggeren, plus de Dockerfile en
CI-publish-workflow zodat de image naar GHCR gaat (ADR-0007).

Referentie: `wetsanalyse-ai/tools/bwb-import/app/main.py` + `app/service.py` + `Dockerfile`. Niet
1:1 gekopieerd — geen WTI-verrijking (nog niet gebouwd, zie story 027 §Buiten scope), eigen
secrets-conventie (`BWB_SERVICE_API_KEY_FILE`, ADR-0006).

## Acceptatiecriteria

- [x] `Settings` uitgebreid met `schemas_dir`, `validate_xsd`, `service_api_key` (dit laatste via
      `*_FILE`, ADR-0006).
- [x] `main.run_import(bwb_id, settings, writer=None)`: download → (niet-blokkerende
      XSD-validatie) → parse → `writer.write_wet`. Zonder meegegeven `writer` draait `prepare()`
      (repo + ontologie) eerst.
- [x] `main.run_imports(bwb_ids, settings)`: één gedeelde writer, `prepare()` één keer voor de
      hele batch; een falende wet breekt de batch niet — komt terecht in het per-wet
      `ImportResult`.
- [x] `main.main(argv)`: CLI-entrypoint (`python -m app.main <bwb-id> [<bwb-id> ...]`), print een
      overzicht per geslaagde wet, foutmelding per mislukte; exit-code 1 als er iets mislukte.
- [x] `service.py` (FastAPI): `GET /health`, `POST /import` (`bwb_id` enkel of `bwb_ids` batch),
      optionele `X-API-Key`-check (alleen actief als `service_api_key` geconfigureerd is).
- [x] `Dockerfile`: multi-stage (`uv`-builder + slanke runtime), build-context = repo-root
      (`docker build -f tools/bwb-import/Dockerfile .`) — **gebouwd en gedraaid, `/health`
      geverifieerd** (niet alleen geschreven).
- [x] Root `.dockerignore` toegevoegd (eerste Dockerfile in dit project; geldt voor elke
      toekomstige service-build vanaf de repo-root).
- [x] `bwb-import-docker-publish.yml`: bouwt + Trivy-scant (CRITICAL/HIGH blokkerend) + pusht naar
      `ghcr.io/<owner>/bwb-import`, alleen op push naar master (niet op PR's).

## Buiten scope van deze story

- WTI-verrijking, divisies/bijlagen/illustraties/tabellen — wachten op hun parser-onderdeel.
- Daadwerkelijk een import tegen een echte GraphDB draaien (blokkeert nog op de licentie, zie
  story 027 en `deploy/graphdb/README.md` §Licentie).
- OpenTelemetry-instrumentatie (ADR-0006 werkwijze) — aparte story zodra de service echt draait.
- Portainer-stack voor bwb-import zelf (`deploy/bwb-import/`) — fase 5.

## Test-plan

- `test_main.py`: `run_import`/`run_imports`/`main` met een `FakeWriter` (geen HTTP) en een
  gemockte downloader (retourneert de bestaande fixture) — geen netwerk.
- `test_service.py`: FastAPI `TestClient`, `run_import`/`run_imports` gemonkeypatcht — health,
  enkele/batch-import, foutafhandeling (500), validatiefout (422 zonder bwb_id/lege bwb_ids),
  API-key-check (401 bij verkeerde key, 200 bij juiste).
- Dockerfile: handmatig geverifieerd via `podman build` + `podman run` + `curl /health` (geen
  geautomatiseerde test hiervoor — dat is precies wat de CI-publish-workflow bij elke
  master-push doet).
