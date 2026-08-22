# ADR-0001: Multi-service topologie

**Status:** geaccepteerd
**Datum:** 2026-08-12

## Context

`werkwijze/docs/architectuur/adr/0002-meerdere-onafhankelijk-deploybare-services.md` stelt vast
dát een applicatie uit meerdere, onafhankelijk deploybare services bestaat, maar laat bewust
open hoeveel, hoe ze heten en hoe ze communiceren — dat is een keuze per applicatie. Voor dit
project is die keuze niet from scratch gemaakt: het bestaande, echte project waarvan dit de
werkwijze-conforme opvolger is, is al functioneel een multi-service-opzet (aparte
Docker-publish-workflows en dependency-tracks per onderdeel), alleen nog niet zo vastgelegd. De
kernbackend van dat project bevat wél acht domeinen die met drie verschillende, inconsistente
isolatieniveaus door elkaar heen in dezelfde verzamelbestanden zitten (een 440-regelig
databasebestand, een 629-regelig adminbestand) — dat is een probleem van interne indeling, geen
argument om nóg meer services te maken.

## Beslissing

Zes services, elk zijn eigen deploy-eenheid:

1. **`api`** — kernbackend: analyse/jobs, LLM-configuratie, auth (beide schema's, ADR-0009 van
   de werkwijze), wetcatalogus, runtime-configuratie, annotatie, berichten, feedback,
   admin-oppervlak. Blijft één service — deze domeinen delen zwaar dezelfde auth en vaak
   dezelfde project-context; verder opsplitsen zou vooral cross-service-contractlast toevoegen
   zonder een reëel onafhankelijk-schaalvoordeel. Wordt intern vertical-sliced per domein
   (werkwijze-ADR-0001) in plaats van de huidige verzamelbestanden.
2. **`frontend`** — hoofdwebapp (Next.js BFF).
3. **`frontend-chat`** — losse chatapp, eigen deploy-eenheid.
4. **`tools/bwb-import`** — ETL-pipeline die het Basiswettenbestand importeert in de
   GraphDB-kennisgraaf (`deploy/graphdb/`, infra, geen eigen "service" in deze lijst — third-party
   image, geen door ons gebouwde/gedeployde applicatiecode). *Correctie 2026-08-22: eerder stond
   hier `wettenbank-mcp` — die service is vóór dit ADR al (2026-08-06) uit de referentie-app
   verwijderd; de wettekst-toegang loopt sindsdien direct via de graaf (GraphDB's ingebouwde MCP),
   niet via een tussenliggende MCP-server. Zie `docs/project/migratie-wetsanalyse.md` en het
   fase-4-plan voor de volledige toelichting.*
5. **`graph-qa`** — QA-/annotatie-agent. Bevraagt de graaf rechtstreeks (SPARQL/similarity-search
   via GraphDB's ingebouwde MCP), geen tussenliggende wettenbank-mcp.
6. **`wetsanalyse-admin-mcp`** — admin-MCP, los van het admin-oppervlak binnen `api`.

**Orkestratie/workflow-engine** (de meerfasige analyse-aansturing) is een **module binnen
`api`**, geen eigen service — hij stuurt dezelfde `projects`/`rondes`-data aan die al in `api`
leeft; een eigen service zou een cross-service-aanroep toevoegen voor iets dat nu al binnen één
proces werkt, zonder een concreet ontkoppelingsprobleem dat dat rechtvaardigt.

**Communicatie tussen services:** synchroon HTTP, net als nu. Geen events/message queue —
lang-lopend werk wordt gedekt door async jobs (werkwijze-ADR-0008), niet door
service-naar-service-events. Events komen pas in beeld bij een concreet ontkoppelingsprobleem
dat sync HTTP niet oplost, niet vooruitlopend.

## Consequenties

- `docs/architectuur/stack-profiel.md` §Topologie van dit project verwijst naar dit ADR.
- `voorbeeld/wetsanalyse/CLAUDE.md` §Structuur kan nu de zes services benoemen in plaats van
  alleen te zeggen dat de referentie-implementatie nog leeg is.
- De echte winst zit in de interne herindeling van `api` (acht domeinen, drie inconsistente
  isolatieniveaus nu), niet in het aantal services — dat blijft de zwaarste stap.
- Nadeel, bewust geaccepteerd: `api` blijft de grootste, meest complexe service van de zes. Dat
  is een bewuste keuze (zie Beslissing), niet een gemiste kans om verder te splitsen.
- **Nog niet besloten in dit ADR:** hoe contracten tússen deze zes services precies vastliggen
  en geversioneerd worden (werkwijze-ADR-0002 stelt alleen dat het geen gedeelde import mag
  zijn) — dat blijft het open backlogpunt "Cross-service contracten".
- **`api`'s wetcatalogus-structuurdata gaat naar GraphDB, niet naar een MCP-tussenlaag**
  (vastgelegd 2026-08-22). `api/app/features/wetcatalogus/store.py:structuur()` draait nu op een
  hardgecodeerde fallback met commentaar dat wachtte op `tools/wettenbank-mcp` — die service komt
  er niet. In de referentie-app is de vergelijkbare functionaliteit zelfs uit de API-laag
  geschrapt (`api/app/routers/catalog.py` in wetsanalyse-ai: "de werkplek draait op de graaf...
  dus de API heeft de wettenbank-MCP niet meer nodig"). Voor lexplainables — waar de
  wetcatalogus-admin-feature al gebouwd is (PR #15, story 020) en blijft bestaan — betekent dat:
  zodra `deploy/graphdb` + `tools/bwb-import` er staan, queryt `structuur()` de graaf **direct**
  via SPARQL (leesrechten, geen MCP-tool ertussen), net zoals `graph-qa` en de backup-cron dat al
  rechtstreeks doen. Implementatie (credentials, welk account, wel/niet via de mcp-auth-proxy)
  volgt als aparte story zodra bwb-import gevuld is — deze regel legt alleen de richting vast.
