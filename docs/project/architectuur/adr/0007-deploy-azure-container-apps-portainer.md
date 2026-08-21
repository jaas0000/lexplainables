# ADR-0007: Deploy naar Azure Container Apps én Portainer

**Status:** geaccepteerd
**Datum:** 2026-08-21

## Context

Lexplainables heeft nu geen deploy-configuratie — er is alleen een lokale docker-compose
zonder productie-target. Voor de doelomgeving (klein enterprise-team) is een concreet
deploy-model nodig, met de kanttekening dat de doelklant twee omgevingen naast elkaar draait:
Azure Container Apps voor cloud, en Portainer voor on-premise / edge.

Wetsanalyse-ai deployt naar beide targets uit dezelfde container-images (GitHub Container
Registry). Elke service heeft een eigen `Dockerfile`, een eigen GitHub-workflow die naar GHCR
pusht, en aparte deploy-workflows per target.

Alternatieven:
- **Alleen Azure Container Apps** — sluit de on-premise-optie uit die de doelklant wil houden.
- **Alleen Portainer / eigen orchestratie** — Azure Container Apps geeft standaard
  scale-to-zero, ingress, secrets en revision-management; opgeven zou dagen werk kosten voor
  functionaliteit die "gratis" is.
- **Kubernetes (AKS)** — te zwaar voor deze schaal (klein team, ~10 services). Container Apps
  is Kubernetes onder de motorkap zonder dat je dat hoeft te managen.

## Beslissing

**Twee deploy-targets uit dezelfde images:** Azure Container Apps (cloud, primair) en
Portainer-stack (on-premise, secundair).

Concreet:
- Elke service heeft één `Dockerfile` in zijn map (`api/Dockerfile`,
  `frontend/Dockerfile`, `tools/graph-qa/Dockerfile`, `tools/wettenbank-mcp/Dockerfile`,
  `frontend-chat/Dockerfile`, `tools/wetsanalyse-admin-mcp/Dockerfile`).
- CI-workflow per service (`<service>-docker-publish.yml`) bouwt en pusht naar `ghcr.io/<owner>/<service>`.
- **Azure**: één Bicep-file (`main.bicep`) provisioneert de Container Apps + Container Apps
  Environment + Log Analytics + de bijbehorende secrets vault. Deploy-workflow
  (`azure-infra.yml`) draait de Bicep bij een push naar `master`.
- **Portainer**: een `deploy/compose/` map bevat één `docker-compose.yml` per Portainer-stack.
  Portainer pulled uit GHCR bij een release-tag.
- **Secrets**: bestandsgebaseerd zoals werkwijze-ADR-0006 — geen env-variabelen die geheimen
  bevatten; in Azure via `Key Vault → CSI-mount`, in Portainer via `secrets:` mount.

## Consequenties

- **Bewust geaccepteerd:** twee deploy-targets betekent twee CI-paden onderhouden. Winst:
  klant heeft flexibiliteit tussen cloud en on-premise zonder dat de code verandert.
- **Één image-bron**: GHCR. Beide targets pullen dezelfde images — geen
  target-specifieke-builds die uit elkaar kunnen drijven.
- **Observability**: aparte stack (ADR-0006) draait in beide omgevingen; endpoint-configuratie
  via env-variabelen per target.
- **Cold start** in Container Apps met scale-to-zero: de api heeft daar een bounded startup-retry
  op de DB-connectie (ADR-0003) om te voorkomen dat een cold Postgres-verbinding een crash-loop
  wordt.
- **Portainer is niet cross-service `depends_on`-bewust**: elke stack heeft zijn eigen
  service-set, geen cross-stack afhankelijkheden — de api moet omgaan met een Postgres die
  onafhankelijk restart.
