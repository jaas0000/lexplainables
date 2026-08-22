# CLAUDE.md — lexplainables

Project op basis van de multi-service contract-first werkwijze. De methodologie, skills en
achtergrond staan in dit repo zelf onder [`docs/project/werkwijze/`](docs/project/werkwijze/CLAUDE.md)
(geen sibling-repo-dependency meer).

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

**Alembic-migraties:** 0001–0014, draaien tegen Postgres (SQLite volledig verwijderd sinds
ADR-0003).

**Nog te bouwen:** Service `frontend-chat` nog niet gestart. (2FA/TOTP, story 017, bleek bij
onderzoek al gebouwd onder de oude fase-indeling — zie de story-doc.)
`tools/bwb-import` heeft een werkende kernpijplijn: SRU-discovery + download (024),
XSD-validatie + kernparser (025), onderdelen + verwijzingen (026), RDF/GraphDB-writer (027),
CLI + FastAPI-service + Dockerfile + CI-publish (028), WTI-verrijking (030: citeertitels,
thesaurustermen, grondslagen, opt-in via `BWB_IMPORT_WTI`), artikel/lid/onderdeel-verrijking
(031: provenance, voetnoten, definities, illustraties, tabellen-als-tekst), wet-brondata/
aanhef/considerans/ondertekenaars (032), bijlagen (033: container + tekstdrager, citeerbaar,
eigen artikelen, `VOLGT_OP`-documentvolgorde), circulaires (034: `<circulaire.divisie>`-boom,
`parse()` gooit niet langer `ParseError` voor circulaires — alleen nog voor het écht-onherkende
restgeval, bewuste afwijking van de referentie). GraphDB-licentie is geregeld (Free, Licensee:
Belastingdienst, dev/test — zie `ai-notes/licenties-en-juridisch.md`); een echte import
(`python -m app.main BWBR0004770`, de actuele Invorderingswet 1990) is end-to-end geverifieerd
tegen de live GraphDB, inclusief WTI-, artikel- en wet-brondata-verrijking (afkorting/
eerstverantwoordelijke/citeertitel/uitgegevenDoor-, bron/effect/status- en publicatiejaar/
dossier/toestandUrl/ondertekendDoor-triples geverifieerd via SPARQL); bijlagen en circulaires
zijn los geverifieerd met een synthetische `Wet` (de Invorderingswet-fixture heeft geen van
beide) — `heeftBijlage`/`heeftDivisie`/`volgtOp`/geneste-relaties bevestigd. Lucene-FTS-connector
(035, `ensure_fts_connector` in `prepare()`) draait tegen de live GraphDB en geeft echte,
gerankte zoekresultaten (bv. "invordering" → artikel 1 lid 1). Tekstuele fallback-
verwijzingsdetectie (036: kleine hardcoded afkortingentabel + regex, elke treffer
`soort=tekstueel`/`betrouwbaarheid=laag`, aanpak afgestemd met de gebruiker vóór bouwen) vindt
22 echte, correct opgeloste verwijzingen in de Invorderingswet-fixture. Daarmee is `bwb-import`'s
volledige scope uit story 027 §Buiten scope afgerond — divisies/bijlagen/illustraties/tabellen
én FTS én tekstuele detectie, alles handmatig geverifieerd tegen de live GraphDB.
`tools/graph-qa` is gestart (story 029: projectskelet + poorten `GraphPort`/`LLMPort` + fakes,
21 tests) — de agent-loop zelf (orkestrator, supervisor, toollaag, annotatieketen, ~25-35 stories
geschat) moet nog gebouwd worden, zie `ai-notes/fase-4-aparte-services-plan.md` §Service 3.

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
| `tools/bwb-import/` | ETL-pipeline: BWB → GraphDB-kennisgraaf |
| `tools/graph-qa/` | QA-/annotatie-agent |
| `tools/wetsanalyse-admin-mcp/` | Admin-MCP |

Alle projectspecifieke stack-keuzes (de ene bron, contractgeneratie, feature-eenheid, dunne
verzamelaars, migraties, frontends, codestandaard) staan in
[`docs/project/architectuur/stack-profiel.md`](docs/project/architectuur/stack-profiel.md) — `feature-bouwen`
regel 3 leest daaruit.

## Instellingen

Staan (uitsluitend) in [`docs/project/werkwijze/CLAUDE.md`](docs/project/werkwijze/CLAUDE.md) §Instellingen — dat is de
enige plek waar Autonome merge en Simplify bij feature-bouwen worden bijgehouden. Niet hier
herhalen; verander de waarde daar, niet in de skill zelf.

## Docs-structuur

- `docs/project/werkwijze/` — de methodologie zelf: `CLAUDE.md` (incl. §Instellingen) + ADR's onder
  `docs/project/werkwijze/adr/`. Portable naar een volgend project; zie §Skills hieronder.
- `docs/project/` — hoe we werken aan dít project en wat we hebben gebouwd: `architectuur/`
  (ADR's over dit project), `features/` (gegenereerd door `scripts/docs/genereer-feature-docs.py`),
  `stories/`, `vervolgpunten.md`, `changelog-technisch.md`.
- `docs/domein/` — waar de app over gaat: JAS, wetsanalyse-methode, WetsTaal, referenties.
  Vult zich naarmate wetsanalyse-content wordt overgezet.
- `CHANGELOG.md` blijft op de root (open-source-conventie).

## Skills

De skills staan in `.claude/skills/` — in-project, geen sibling-repo-dependency. De methode
zelf staat in [`docs/project/werkwijze/CLAUDE.md`](docs/project/werkwijze/CLAUDE.md) (met bijbehorende ADR's onder
`docs/project/werkwijze/adr/`); dit CLAUDE.md hier verwijst naar die inhoud maar herhaalt hem niet. Zodra de
werkwijze stabiel is en herbruikbaar moet worden voor een tweede project, is de afsplitsing terug
naar een aparte werkwijze-repo triviaal (`.claude/skills/` + `docs/project/werkwijze/` kopiëren).

## Volgende stap

Geen resterende API/frontend-story meer (story 017 bleek al gebouwd). `tools/bwb-import` heeft
zijn volledige scope uit story 027 §Buiten scope afgerond (stories 024-028, 030-036, zie
hierboven) — inhoudelijk klaar. Vervolg: `tools/graph-qa` (service 3, zie
`ai-notes/fase-4-aparte-services-plan.md`) zodra de Azure Foundry-key beschikbaar is, daarna
`frontend-chat` (`tools/wetsanalyse-admin-mcp/` is klaar).
