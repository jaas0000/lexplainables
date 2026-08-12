# Stack-profiel — wetsanalyse

Wat dit project concreet gekozen heeft op de punten die de skills anders zouden aannemen (zie
werkwijze-ADR-0004). Elke sectie citeert waar mogelijk een al bestaande methodologie-ADR — dit
bestand bedenkt die keuzes niet opnieuw, het bevestigt ze voor dit project (zie ADR-0004:
"een stack-profiel.md hoeft dit patroon niet opnieuw te bedenken, alleen te bevestigen").

## Topologie

Zes services, vastgelegd in [`docs/architectuur/adr/0001-multi-service-topologie.md`](adr/0001-multi-service-topologie.md):

| Service | Map | Verantwoordelijk voor | Praat met |
|---|---|---|---|
| `api` | `api/` | Analyse/jobs, LLM-configuratie, auth, wetcatalogus, runtime-config, annotatie, berichten, feedback, admin-oppervlak, orkestratie (module, geen eigen service) | database (eigen), `wettenbank-mcp`, `graph-qa` |
| `frontend` | `frontend/` | Hoofdwebapp (BFF) | `api` |
| `frontend-chat` | `frontend-chat/` | Losse chatapp | `api` |
| `wettenbank-mcp` | `tools/wettenbank-mcp/` | MCP-server, wetcatalogus-lookups | database (eigen, indien nodig) |
| `graph-qa` | `tools/graph-qa/` | QA-/annotatie-agent | `api` |
| `wetsanalyse-admin-mcp` | `tools/wetsanalyse-admin-mcp/` | Admin-MCP, los van `api`'s eigen admin-oppervlak | `api` |

Communicatie: synchroon HTTP tussen alle services. Geen events — lang-lopend werk loopt via
async jobs (werkwijze-ADR-0008) binnen de service die het werk doet, niet via
service-naar-service-events.

## De ene bron

Zoals werkwijze-ADR-0011: per entiteit een SQLAlchemy Core `Table` + Pydantic-model(len)
(Base/Create/Read) in hetzelfde `models.py` van de feature, met een expliciete, met de hand
geschreven mapping-functie ertussen. Geldt binnen elke service afzonderlijk (werkwijze-ADR-0002:
een service is de grens van "de ene bron").

## Contractgeneratie

Ja, zoals werkwijze-ADR-0011: `scripts/genereer-types.sh` binnen elke service die een frontend
bedient (dus `api`, niet in de MCP-tool-services — die hebben hun eigen contractvorm, zie
werkwijze-ADR-0013/0014).

Contract tússen services: zoals werkwijze-ADR-0017. `frontend` en `frontend-chat` genereren elk
hun eigen TypeScript-client uit `api`'s OpenAPI-schema (`openapi-typescript`). `graph-qa`
(Python) genereert uit datzelfde schema zijn eigen Pydantic-modellen (`datamodel-code-generator`)
en schrijft de aanroep + error-boundary zelf (werkwijze-ADR-0014). Geen gedeelde package die
twee services samen importeren. Zolang alle services in deze monorepo staan, leest elke
consument `api`'s `openapi.json` via een relatief pad; dat verandert naar een gepubliceerd
endpoint zodra een service als eigen repo wordt losgetrokken.

## Feature-eenheid

Een feature-map binnen `api/features/<domein>/` bevat: `models.py` (Table + Pydantic, "de ene
bron"), `contracts.py` (indien de Pydantic-modellen los van `models.py` overzichtelijker zijn
bij een groter domein — optioneel per feature, `models.py` alleen is ook toegestaan), `store.py`
(het Protocol + implementatie(s), werkwijze-ADR-0007), `router.py` (businesslogica),
`migrations.py`-registratie (werkwijze-ADR-0005) en `tests/`. Dit volgt het patroon dat al
eerder voor dit project is uitgewerkt in `voorstel-losse-koppeling.md` (ai-notes), nu als
verplichte structuur i.p.v. voorstel.

De acht bestaande domeinen (analyse/jobs, LLM-configuratie, identiteit/toegang, wetcatalogus,
runtime-config, annotatie, berichten, feedback) worden elk zo'n feature-map — dat is de
concrete invulling van de interne herindeling die ADR-0001 §Consequenties als "de echte winst"
aanwijst.

## Dunne verzamelaars

Binnen `api`: het routes-samenvoegpunt (huidige `admin.py`/hoofdrouter) en de
database-setup (huidige `db.py`) — beide bevatten nu domeinkennis (tabellen, routelogica) die
naar de feature-mappen hoort te verhuizen. `architectuur-audit` regel 3 bewaakt dat ze dun
blijven na de herindeling.

## Migraties

Alembic, zoals werkwijze-ADR-0005 — één migratiehistorie per service met een eigen database
(`api`, en `wettenbank-mcp` indien die een eigen database krijgt). Vervangt de huidige
`reconcile_schema()`-functie in `api`.

## Frontend(s)

Twee, zoals vastgelegd in de Topologie hierboven: `frontend/` (hoofdwebapp) en `frontend-chat/`
(losse chatapp) — allebei praten uitsluitend met `api`, allebei krijgen hun eigen
`generated/`-map met TypeScript-types uit `api`'s contract en hun eigen `tests/e2e/`.

## Codestandaard

Zoals werkwijze-ADR-0003: `ruff` voor Python-services (`api`, `graph-qa`), `eslint` + `prettier`
voor TypeScript-services (`frontend`, `frontend-chat`, `wettenbank-mcp`). CI-checknamen volgen
het sjabloon uit werkwijze-ADR-0016 zodra de daadwerkelijke workflows per service bestaan.
