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
- `api/app/features/projecten/` — werkgebied-metadata (naam + bronnen + omschrijving), CRUD-endpoints (PR #11, story 012); LLM-calls log (PR #20, story 021). De ooit gebouwde JAS-orkestratie (act2/act3, review-flow, rapport, SSE — PR #17/#19, stories 013/024) is opgeruimd (PR #36, migratie 0012) — annotatie (`annotatie/`) is de enige overgebleven analyse-stap.
- `api/app/features/llm_calls/` — capture-tabel + store, endpoint blijft in projecten
- `api/app/features/annotatie/` — documenten, elementen, beslissingen, auditlog (PR #21, story 022)
- `api/app/features/api_tokens/` — aanmaken, intrekken, DB-verificatielaag (PR #18, story 018)
- `api/app/features/runtime_config/` — `app_instellingen`-tabel (migratie 0008), toggle `capture_llm_calls`, TTL-cache (PR #16, story 019)
- `api/app/shared/auth.py` — API_TOKEN-gate + X-User-Id-header (geen Keycloak)
- `api/app/shared/crypto.py` — Fernet-encryptie

**`frontend/` — pagina's:**
- `/` — startpagina (banner)
- `/login`, `/setup` — auth-flow
- `/instellingen/[[...tab]]` — instellingenvenster: Account + 8 beheer-secties (modelprofielen,
  gebruikers, wetten, instellingen, llm-calls, api-tokens, feedback, berichten) als tabs van één
  gedeeld venster, bereikbaar als volle pagina of als dialoog over de huidige pagina heen via de
  intercepting route `app/@modal/(.)instellingen/…` (PR #79, story 042; poort van
  `wetsanalyse-ai`'s `Dialog`/`Tabs`-patroon). `/account` en `/beheer/*` blijven bestaan als
  redirects naar het bijbehorende tabpad (PR #12/#10/#14/#15/#16/#20/#18, stories 011-021 —
  content nu in `components/{account,beheer}/*Panel.tsx`).
- `/berichten` — berichten voor analisten
- `/wetcatalogus` — wetcatalogus lezen
- `/projecten`, `/projecten/nieuw`, `/projecten/{id}` — werkgebieden aanmaken/bekijken (PR #11, story 012; SSE/rapport-flow opgeruimd in PR #36)
- `/werkplek/`, `/werkplek/{slug}` — annotatie-werkplek: documentenlijst + beslissingen per element, incl. echte wetsartikeltekst via GraphDB-SPARQL (PR #22 story 023, PR #68 story 037)
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
`tools/graph-qa` is gestart (story 029: projectskelet + poorten `GraphPort`/`LLMPort` + fakes;
story 039: `LLMPort`-implementatie `AnthropicLLM` via Azure AI Foundry; story 040: `GraphPort`-
implementatie `MCPClient` tegen de GraphDB-MCP-server; story 041: getypeerde domein-toollaag
(13 tools, 11 SPARQL-bouwers) — alle drie live geverifieerd tegen de lokale, gevulde GraphDB,
met drie schemacorrecties t.o.v. de `wetsanalyse-ai`-referentie onderweg gevonden en gefixt).
Story 044 knoopt die drie bouwstenen voor het eerst daadwerkelijk aan elkaar: een minimale
LangGraph-antwoord-agent-loop (`agent_node ⇄ tools_node → verify_node → correct/finalize`), bewust
zonder supervisor/annotatieketen/decompositie/checkpointer/streaming/API-laag — live geverifieerd
tegen de Invorderingswet-fixture. Story 045 zet daar een supervisor vóór: kiest een specialist
(`definitie`/`duiding`/`algemeen`, elk met een eigen prompt-addendum en beperkte toolset) en wijst
een vraag buiten de wetgeving direct af zonder graafbevraging — live geverifieerd (begripsvraag →
`definitie` met een letterlijk citaat, structuurvraag → `duiding`, weervraag → afgewezen). Story 046
voegt een tweede graaf-topologie toe (`enable_decomposition`, standaard uit): een samengestelde
vraag wordt gesplitst in deelvragen, elke deelvraag krijgt een eigen agent⇄tools-lus, en de
bevindingen worden samengevoegd tot één antwoord — live geverifieerd (een vraag over twee begrippen
routeerde correct naar twee verschillende onderdelen van hetzelfde artikel). Story 047 begint de
**annotatieketen**: `annoteer_node` classificeert één bepaling volgens het Juridisch
Analyseschema (JAS) in één LLM-call, brongetrouw en ontdubbeld — bewust losstaand (nog niet in de
graaf gewired). Story 048 voegt `critic_node` toe: beoordeelt diezelfde voorstellen met een
aandacht-niveau (groen/geel/rood) + actie per element, dempt zelfweerspreking bij een tweede
ronde, en breekt de keten nooit op een mislukte call — ook losstaand. Live geverifieerd tegen
artikel 1 van de Invorderingswet 1990; de Critic ving daarbij een echte misclassificatie van de
annotator. Story 049 rondt de annotatieketen af: `patch_node` (code-only, voert rood+vervang
door), `herzie_node` (LLM-call, herstelt verworpen fragmenten/gemiste elementen), `emit_node`
(finale structuur, geen SSE), en de graaf-wiring — `state["doel"]` routeert om de supervisor heen
recht naar de annotatieketen. Live geverifieerd: 4 correcties daadwerkelijk toegepast op artikel
1. De annotatieketen zelf is daarmee inhoudelijk compleet (geen `advance_node`/worker-chaining
nodig — één worker per beurt). Story 050 voegt LangGraph-checkpointing toe (`agent/
checkpointer.py`: Postgres → SQLite-bestand → `MemorySaver`) plus `nieuwe_beurt_invoer()` voor het
per-beurt-resetpatroon, zodat `messages` daadwerkelijk over losse `.ainvoke()`-aanroepen heen
blijft bestaan — live geverifieerd, en onderweg twee zelf gevonden bugs gefixt (Source-
serialisatie, en een supervisor die de gesprekshistorie niet meelas). Story 051 voegt streaming
toe: `agent_node`/`synthesize_node` sturen hun eind-antwoord nu token-voor-token via
`get_stream_writer()`, en de nieuwe wrapper `agent/agent.py`'s `answer_stream()` levert het
SSE-event-contract (token/sources/grounding/done/error) als async generator — nog geen HTTP.
Story 052 voegt `stop_check` toe: `build_graph(..., stop_check=...)` laat een lopende beurt op
een nodegrens stoppen (`BeurtGestopt`, `agent/agent_common.py`) — infrastructuur zonder aanroeper,
dat wacht op het latere runs-model (`POST /v1/runs/{id}/cancel`). Story 053 opent `tools/graph-qa/
api/` (was een leeg skelet): `GET /health` + `POST /v1/chat` (SSE, providers via FastAPI
`Depends()`, optioneel bearer-token) — de eerste echte HTTP-aanroeper van de agent, live
geverifieerd tegen de Invorderingswet-fixture. Story 054 voegt het run-model toe (`agent/
runs.py`): een beurt draait als server-side achtergrondtaak i.p.v. gekoppeld aan de verbinding —
`POST /v1/runs`/`GET /v1/runs/{id}/events`/`POST /v1/runs/{id}/cancel`/`GET
/v1/conversations/{id}/run`, met eigenaarschap via `X-User-Id`. Eerste échte aanroeper van
`stop_check` (052) — live geverifieerd dat `cancel` een lopende beurt naar `status: "gestopt"`
brengt. Story 055 knoopt `api` en `graph-qa` voor het eerst aan elkaar: `api/app/features/
chat_proxy/` streamt graph-qa's `POST /v1/chat` ongewijzigd door — de gedocumenteerde route
`frontend-chat → api → graph-qa` (ADR-0001), niet rechtstreeks. Live geverifieerd door de hele
keten heen. Nog geen CORS/rate-limiting/`agent/beurt.py`-persistentie (geen vastgestelde
frontend-chat) — die is de eerstvolgende stap (story 056), daarna de rest van de API-laag
(~25-35 stories geschat in totaal voor de hele werkstroom).

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

Geen resterende API/frontend-story meer op de kernfeatures (story 017 bleek al gebouwd; story
023's laatste open acceptatiecriterium — echte wetsartikeltekst i.p.v. placeholder — is gesloten
via story 037, PR #68: nieuw GraphDB-SPARQL-leesendpoint
`GET /v1/annotatie/documenten/{slug}/wetsartikel`; PR #70 bracht die weergave op parity met
wetsanalyse-ai's `graph-qa`-agent: onderdelen a/b/c onder een lid, numerieke lid-sortering,
bepaling-fallback voor decimale circulaire-nummers). `tools/bwb-import` heeft zijn volledige
scope uit story 027 §Buiten scope afgerond (stories 024-028, 030-036, zie hierboven) — inhoudelijk
klaar. Story 038 voegde BFF-rolautorisatie toe voor alle admin-routes (PR #75). Stories 042-043
trokken de frontend-GUI gelijk met de `wetsanalyse-ai`-referentie: Account/Beheer zijn nu tabs van
één instellingenvenster (`/instellingen/[[...tab]]`, dialoog- en volle-paginavorm, PR #79), en het
sidebar-uitklapmenu is 1:1 met de referentie (Account & instellingen/Beheer/Feedback geven/
Uitloggen, PR #80).

De Azure Foundry-key is beschikbaar en al live geverifieerd (stories 039-041). Story 044 bewees
dat de drie bouwstenen — `LLMPort` (`AnthropicLLM`), `GraphPort` (`MCPClient`) en de
domein-toollaag (13 tools) — daadwerkelijk samenwerken: een minimale antwoord-agent-loop
(LangGraph) beantwoordt een vraag met een gegrond, letterlijk citaat uit de Invorderingswet-
fixture. Story 045 voegde daar een supervisor aan toe die per vraag een specialist kiest
(`definitie`/`duiding`/`algemeen`) of een vraag buiten de wetgeving direct afwijst zonder de
graaf te raken — ook live geverifieerd. Story 046 voegde een tweede graaf-topologie toe
(`enable_decomposition`, standaard uit) die een samengestelde vraag splitst in deelvragen, elk
apart beantwoordt met een gedeelde bronnenlijst, en samenvoegt tot één antwoord — ook live
geverifieerd, en de eerste plek die de al bestaande prompt-cachingsplit (story 039) daadwerkelijk
gebruikt. Story 047 begint de annotatieketen: `annoteer_node` classificeert één bepaling volgens
het JAS in één LLM-call, brongetrouw en ontdubbeld — losstaand, nog niet in de graaf gewired. Live
geverifieerd tegen artikel 1 van de Invorderingswet 1990 (5 grounded voorstellen, 0 verworpen).
Story 048 voegt `critic_node` toe: beoordeelt diezelfde voorstellen met een aandacht-niveau
(groen/geel/rood) + actie per element, dempt zelfweerspreking bij een tweede beoordelingsronde, en
breekt de keten nooit op een mislukte call — ook losstaand. Live geverifieerd: de Critic ving een
echte misclassificatie van de annotator op artikel 1. Story 049 rondt de annotatieketen af:
`patch_node` (code-only), `herzie_node` (LLM-call), `emit_node` (finale structuur, geen SSE), en
de graaf-wiring (`state["doel"]` routeert om de supervisor heen). Live geverifieerd: 4 correcties
daadwerkelijk toegepast op artikel 1 — de annotatieketen zelf is nu inhoudelijk compleet. Story 050
voegt gespreksgeheugen toe: een LangGraph-checkpointer (`agent/checkpointer.py`, Postgres → SQLite-
bestand → `MemorySaver`) plus `nieuwe_beurt_invoer()` die alle ephemere State-velden per beurt
reset, zodat een vervolgvraag in hetzelfde gesprek de context van eerdere vragen kent — live
geverifieerd, met twee zelf gevonden en binnen dezelfde PR gefixte bugs (Source-Pydantic-objecten
i.p.v. plain dicts in de state; de supervisor las de gesprekshistorie niet mee bij het routeren).
Story 051 voegt streaming toe: `agent_node`/`synthesize_node` streamen hun eind-antwoord
token-voor-token (`llm.stream()` + `get_stream_writer()`), en de nieuwe wrapper `agent/agent.py`'s
`answer_stream()` levert het SSE-event-contract (token/sources/grounding/conversation_id/done/
error) als async generator — live geverifieerd (token-events komen aantoonbaar vóór `done`).
Story 052 voegt `stop_check` toe: alle 16 node-registraties in `build_graph` lopen nu via een
`stopbaar()`-wrapper die op een nodegrens `BeurtGestopt` (nieuwe `agent/agent_common.py`) gooit
i.p.v. de node te draaien, en `answer_stream()` vangt die als een normale afronding (`done`, geen
`error`) — bewust zonder aanroeper, dat is het latere runs-model. Story 053 opent de HTTP-laag:
`tools/graph-qa/api/main.py` (was een leeg skelet) krijgt `GET /health` + `POST /v1/chat`
(SSE via `sse-starlette`, providers via FastAPI `Depends()` voor testbaarheid, optioneel
`QA_API_TOKEN`-bearer-token, fail-fast lifespan) — live geverifieerd met een echte vraag over de
HTTP-server. Story 054 voegt het run-model toe: `agent/runs.py` (`RunRegister`, een
`Condition`-gebaseerd event-log met selectief cappen en een bewaartermijn) plus vier endpoints
(`POST /v1/runs`, `GET /v1/runs/{id}/events`, `POST /v1/runs/{id}/cancel`, `GET
/v1/conversations/{id}/run`) — een beurt draait nu als server-side achtergrondtaak i.p.v.
gekoppeld aan de HTTP-verbinding, en `cancel` is de eerste échte aanroeper van `stop_check`
(story 052). Live geverifieerd: zowel het gewone verloop tot `status: "klaar"` als een
`cancel`-vóór-de-eerste-node die `status: "gestopt"` opleverde zonder `error`-event. Story 055
knoopt `api` en `graph-qa` voor het eerst daadwerkelijk aan elkaar: nieuwe feature `api/app/
features/chat_proxy/` — `POST /v1/chat` streamt graph-qa's SSE-contract ongewijzigd door, volgens
de al vastgelegde architectuur (`frontend-chat → api → graph-qa`, ADR-0001/C4-model). Live
geverifieerd door de hele keten heen (`curl → api → graph-qa → GraphDB + Foundry`). Nog geen
CORS/rate-limiting/`agent/beurt.py`-persistentie/`/v1/artikel` en nog geen enkel aangesloten
UI-endpoint — `frontend-chat` zelf (story 056) is de eerstvolgende stap, daarna de rest van de
API-laag (~25-35 stories geschat in totaal) (`tools/wetsanalyse-admin-mcp/` is klaar).
