# C4-model — lexplainables

Drie niveaus: Context (wie gebruikt het systeem en wat zijn de externe grenzen),
Container (welke services zijn er en hoe praten ze), Component (welke features zitten
binnen elke service). Code (L4) wordt niet bijgehouden — dat staat in de code zelf.

Zie §Bijhouden voor wanneer elk niveau bijgewerkt moet worden.

---

## L1 — Context

Twee gebruikersrollen, één systeem. Geen externe authenticatieservice — auth is intern
afgehandeld via een eigen gebruikers-tabel (PR #5, story 006).

```mermaid
C4Context
  title Systeemcontext — lexplainables

  Person(beheerder, "Beheerder", "Beheert berichten, analyseprojecten, LLM-configuratie en annotaties.")
  Person(analist, "Analist", "Voert wetsanalyses uit, leest berichten, beoordeelt annotaties.")

  System(wetsanalyse, "Lexplainables", "Multi-service applicatie voor juridische wetsanalyse met LLM-ondersteuning.")

  Rel(beheerder, wetsanalyse, "Beheert via", "HTTPS")
  Rel(analist, wetsanalyse, "Gebruikt via", "HTTPS")
```

---

## L2 — Container

Zes services (ADR-0001). Gebouwd: `api`, `frontend` en `wetsanalyse-admin-mcp`. De overige
drie (`frontend-chat`, `bwb-import`, `graph-qa`) zijn vastgelegd in de topologie maar nog niet
geïmplementeerd — ze staan hier al om het volledige plaatje te tonen; markeer ze als gebouwd
zodra de eerste code er is. GraphDB staat er ook bij (voor de leesbaarheid van het plaatje) maar
telt niet mee als "service" in ADR-0001 — het is een third-party image, gedeployd via
`deploy/graphdb/`, geen applicatiecode die wij bouwen/publiceren.

```mermaid
C4Container
  title Containers — lexplainables

  Person(beheerder, "Beheerder")
  Person(analist, "Analist")

  System_Boundary(wetsanalyse, "Lexplainables") {
    Container(frontend, "frontend", "Next.js / Auth.js v5", "Hoofdwebapp (BFF). Login via eigen credentials-formulier (httpOnly cookie). Alle schermen voor beheer, berichten, projecten, werkplek en wetcatalogus zijn gebouwd.")
    Container(frontend_chat, "frontend-chat", "nog niet gebouwd", "Losse chatapp.")
    Container(api, "api", "FastAPI / Python", "Kernbackend: alle geplande features gebouwd (feedback, berichten, identiteit/toegang, wetcatalogus, llm_profielen, projecten, annotatie, api_tokens, runtime_config, llm_calls). Analyse-engine draait via `engine/`-module met LLM-orkestratie.")
    ContainerDb(db, "database", "SQLite (dev) / PostgreSQL", "Tabel per feature binnen api.")
    ContainerDb(graphdb, "GraphDB", "third-party, deploy/graphdb/", "BWB-kennisgraaf, ingebouwde MCP op /mcp. Geen door ons gebouwde service.")
    Container(bwb_import, "bwb-import", "nog niet gebouwd", "ETL-pipeline: BWB → GraphDB.")
    Container(graph_qa, "graph-qa", "nog niet gebouwd", "QA-/annotatie-agent. Bevraagt GraphDB direct (SPARQL/similarity-search).")
    Container(admin_mcp, "wetsanalyse-admin-mcp", "TypeScript / Node.js (stdio)", "Admin-MCP: berichten aanmaken, bewerken, publiceren via Claude Code.")
  }

  Rel(beheerder, frontend, "Gebruikt via browser", "HTTPS")
  Rel(analist, frontend, "Gebruikt via browser", "HTTPS")
  Rel(analist, frontend_chat, "Gebruikt via browser", "HTTPS")
  Rel(frontend, api, "BFF-aanroepen met API_TOKEN + X-User-Id", "HTTP/JSON")
  Rel(frontend_chat, api, "Roept aan", "HTTP/JSON")
  Rel(api, db, "Leest/schrijft", "SQLAlchemy")
  Rel(api, graphdb, "Leest (SPARQL, read-only)", "HTTP")
  Rel(bwb_import, graphdb, "Schrijft (RDF)", "HTTP")
  Rel(graph_qa, graphdb, "Bevraagt (SPARQL/similarity-search)", "MCP")
  Rel(api, graph_qa, "Roept aan", "HTTP/JSON")
  Rel(admin_mcp, api, "Roept admin-API aan met API_TOKEN + X-User-Id", "HTTP/JSON")
```

---

## L3 — Component

Alleen voor gebouwde containers. Voeg een component toe zodra een nieuwe feature-map
(`api/app/features/<naam>/`) of een nieuw scherm (`frontend/app/<naam>/`) wordt aangemaakt.

### `api`

```mermaid
C4Component
  title Componenten — api

  Container_Boundary(api, "api") {
    Component(feedback, "feedback", "features/feedback/", "Indienen, admin-lijst, verwijderen, ongelezen-aantal, markeer-gezien.")
    Component(berichten, "berichten", "features/berichten/", "Aanmaken, bewerken, publiceren/depubliceren, verwijderen (admin). Lezen, ongelezen-status, lees-alles (analist).")
    Component(identiteit_toegang, "identiteit_toegang", "features/identiteit_toegang/", "Eigen gebruikers-tabel (bcrypt). POST /v1/auth/verify + CRUD beheerders + account/wachtwoord-wijzigen + setup.")
    Component(wetcatalogus, "wetcatalogus", "features/wetcatalogus/", "Wet-tabel + admin CRUD + resolve. Structuur/resolve-databron wordt GraphDB (SPARQL) zodra bwb-import bestaat, zie ADR-0001 §Consequenties.")
    Component(llm_profielen, "llm_profielen", "features/llm_profielen/", "CRUD + Fernet-encryptie van API-sleutels.")
    Component(projecten, "projecten", "features/projecten/", "Analyses aanmaken/volgen (SSE), akkoord/afwijzen (human-in-the-loop), rapport (JSON + Markdown), llm-calls-endpoint.")
    Component(annotatie, "annotatie", "features/annotatie/", "Documenten, elementen, beslissingen, auditlog. Client-scoping via X-User-Id.")
    Component(api_tokens, "api_tokens", "features/api_tokens/", "Aanmaken/intrekken tokens + owner-export `verifieer_db_token` voor shared/auth.")
    Component(runtime_config, "runtime_config", "features/runtime_config/", "app_instellingen-tabel, capture_llm_calls-toggle, TTL-cache.")
    Component(llm_calls, "llm_calls", "features/llm_calls/", "Capture-tabel + store voor vastgelegd LLM-verkeer. Endpoint blijft in projecten.")

    Component(engine, "engine", "engine/", "Analyse-orkestrator (act2 → human-in-the-loop → act3), steps, prompts, retry met exponential backoff.")

    Component(shared_auth, "shared/auth", "shared/auth.py", "API_TOKEN-gate (constant-time) + X-User-Id-header. `huidige_beheerder` verifieert token én leest gebruikersidentiteit.")
    Component(shared_wettenbank, "shared/wettenbank", "shared/wettenbank.py", "Ophaal-client voor `haal_citeertitel_op`. Nu JSON-RPC tegen een niet-bestaande service (faalt in de praktijk); wordt directe SPARQL tegen GraphDB zodra bwb-import bestaat, zie ADR-0001 §Consequenties.")
    Component(shared_llm, "shared/llm", "shared/llm/", "LLMClient Protocol + LiteLLMClient met JSON-parse-herpoging.")
    Component(shared_db, "shared/db", "shared/db.py", "Dialect-aware upsert-helpers (`dialect_insert`, `upsert`).")
    Component(shared_crypto, "shared/crypto", "shared/crypto.py", "Fernet-encryptie voor gevoelige velden.")
    Component(shared_validation, "shared/validation", "shared/validation.py", "JAS-klasscheck + brongetrouwheid (NFKC-substring).")
    Component(shared_tijd, "shared/tijd", "shared/tijd.py", "Tijd-utility (UTC-nu).")
  }

  Rel(berichten, shared_auth, "Gebruikt")
  Rel(feedback, shared_auth, "Gebruikt")
  Rel(identiteit_toegang, shared_auth, "Gebruikt voor /v1/auth/verify")
  Rel(wetcatalogus, shared_auth, "Gebruikt")
  Rel(llm_profielen, shared_auth, "Gebruikt")
  Rel(projecten, shared_auth, "Gebruikt")
  Rel(annotatie, shared_auth, "Gebruikt")
  Rel(api_tokens, shared_auth, "Gebruikt")
  Rel(runtime_config, shared_auth, "Gebruikt")

  Rel(shared_auth, api_tokens, "Verifieert DB-tokens via")
  Rel(wetcatalogus, shared_wettenbank, "Roept aan voor resolve")
  Rel(projecten, engine, "Start analyse-orkestratie")
  Rel(engine, shared_wettenbank, "Haalt artikelen op")
  Rel(engine, shared_llm, "Roept LLM aan")
  Rel(engine, shared_validation, "Valideert JAS-klassen + brongetrouwheid")
  Rel(engine, llm_calls, "Capture LLM-verkeer (indien toggle aan)")
  Rel(engine, runtime_config, "Leest capture_llm_calls-toggle")
  Rel(engine, llm_profielen, "Leest LLM-configuratie")
  Rel(berichten, shared_db, "Gebruikt upsert")
  Rel(runtime_config, shared_db, "Gebruikt upsert")
  Rel(wetcatalogus, shared_db, "Gebruikt upsert")
  Rel(llm_profielen, shared_crypto, "Encrypt/decrypt API-sleutels")
```

### `frontend`

```mermaid
C4Component
  title Componenten — frontend

  Container_Boundary(frontend, "frontend") {
    Component(startpagina, "StartPagina", "app/page.tsx", "Landingspagina met lintblauwe banner.")
    Component(login_pagina, "LoginPagina", "app/login/page.tsx", "Toont het login-formulier; redirect naar / als al ingelogd.")
    Component(setup_pagina, "SetupPagina", "app/setup/", "Eenmalige eerste-beheerder-setup.")
    Component(account_pagina, "AccountPagina", "app/account/", "Eigen profiel + wachtwoord wijzigen.")
    Component(beheer_pagina, "BeheerPagina", "app/beheer/", "Overzicht met navigatie naar alle beheer-secties.")
    Component(beheer_gebruikers, "GebruikersBeheer", "app/beheer/gebruikers/", "CRUD beheerders.")
    Component(beheer_wetten, "WettenBeheer", "app/beheer/wetten/", "Wetcatalogus admin CRUD + resolve.")
    Component(beheer_llm_profielen, "LlmProfielenBeheer", "app/beheer/llm-profielen/", "LLM-profielen CRUD.")
    Component(beheer_instellingen, "InstellingenBeheer", "app/beheer/instellingen/", "capture_llm_calls-toggle.")
    Component(beheer_api_tokens, "ApiTokensBeheer", "app/beheer/api-tokens/", "Tokens aanmaken/intrekken met eenmalig-token-modal.")
    Component(beheer_llm_calls, "LlmCallsBeheer", "app/beheer/llm-calls/", "LLM-calls log per analyse.")
    Component(beheer_feedback, "FeedbackBeheer", "app/beheer/feedback/", "Feedback-lijst + verwijderen.")
    Component(berichten_pagina, "BerichtenPagina", "app/berichten/", "Leest gepubliceerde berichten, markeert alle als gelezen op open.")
    Component(wetcatalogus_pagina, "WetcatalogusPagina", "app/wetcatalogus/", "Wetcatalogus lezen.")
    Component(projecten_pagina, "ProjectenPagina", "app/projecten/", "Analyses-overzicht + Nieuwe analyse.")
    Component(project_detail, "ProjectDetail", "app/projecten/[id]/", "SSE-voortgang + rapport bekijken + Markdown-download.")
    Component(werkplek_lijst, "WerkplekLijst", "app/werkplek/", "Annotatie-documentenlijst + aanmaken.")
    Component(werkplek_detail, "WerkplekDetail", "app/werkplek/[slug]/", "Elementen + beslissingen + auditlog per document.")
    Component(disclaimer_pagina, "DisclaimerPagina", "app/disclaimer/", "Statische disclaimer.")

    Component(navigatie, "NavigatieHeader", "components/NavigatieHeader.tsx", "Nav met Beheer-tab, Werkplek-link, Projecten-link, BerichtenPopover, gebruikersnaam, uitloggen.")
    Component(berichten_popover, "BerichtenPopover", "components/BerichtenPopover.tsx", "Bel-icoon met ongelezen-badge (poll 60s). Rollout-menu, markeer-alles-gelezen.")
    Component(login_formulier, "LoginFormulier", "components/auth/LoginFormulier.tsx", "Client Component: signIn('credentials').")
    Component(verwijder_knop, "VerwijderKnop", "components/", "Herbruikbare bevestigings-verwijderknop.")

    Component(auth_config, "Auth.js config", "auth.ts / auth.config.ts", "Credentials provider roept POST /v1/auth/verify aan. httpOnly sessiecookie.")
    Component(api_proxy, "apiProxy", "lib/apiProxy.ts", "Gedeelde BFF-proxy-helper. Voegt API_TOKEN + X-User-Id toe. Optionele forwardHeaders.")
    Component(bff, "BFF-routes", "app/api/", "Server-side proxies naar api: admin/berichten, admin/feedback, admin/gebruikers, admin/wetten, admin/llm-profielen, admin/instellingen, admin/api-tokens, berichten, wetten, projecten (+ /rapport /llm-calls /akkoord /afwijzen), annotatie, feedback, auth, disclaimer.")
  }

  Rel(beheer_pagina, navigatie, "Rendert")
  Rel(navigatie, berichten_popover, "Rendert")
  Rel(login_pagina, login_formulier, "Rendert")

  Rel(berichten_pagina, bff, "Roept aan", "fetch")
  Rel(berichten_popover, bff, "Roept aan", "fetch")
  Rel(beheer_gebruikers, bff, "Roept aan", "fetch")
  Rel(beheer_wetten, bff, "Roept aan", "fetch")
  Rel(beheer_llm_profielen, bff, "Roept aan", "fetch")
  Rel(beheer_instellingen, bff, "Roept aan", "fetch")
  Rel(beheer_api_tokens, bff, "Roept aan", "fetch")
  Rel(beheer_llm_calls, bff, "Roept aan", "fetch")
  Rel(beheer_feedback, bff, "Roept aan", "fetch")
  Rel(wetcatalogus_pagina, bff, "Roept aan", "fetch")
  Rel(projecten_pagina, bff, "Roept aan", "fetch")
  Rel(project_detail, bff, "Roept aan (SSE + rapport + llm-calls)", "fetch")
  Rel(werkplek_lijst, bff, "Roept aan", "fetch")
  Rel(werkplek_detail, bff, "Roept aan", "fetch")

  Rel(bff, api_proxy, "Delegeert naar")
  Rel(api_proxy, auth_config, "Leest sessie via")
```

### `wetsanalyse-admin-mcp`

```mermaid
C4Component
  title Componenten — wetsanalyse-admin-mcp

  Container_Boundary(admin_mcp, "wetsanalyse-admin-mcp") {
    Component(tools, "TOOLS-array", "src/index.ts", "Vier tools: list_berichten_admin, maak_bericht, update_bericht, publiceer_bericht. Zod-inputvalidatie per tool.")
    Component(api_fetch, "apiFetch", "src/index.ts", "Centrale fetch-wrapper. Voegt Authorization: Bearer + X-User-Id toe. Vertaalt API-fouten naar leesbare tekst.")
    Component(server, "StdioServer", "src/index.ts", "MCP-server (stdio). ListTools + CallTool handlers. Fail-closed bij ontbrekende env-vars.")
  }

  Rel(tools, api_fetch, "Gebruikt")
  Rel(server, tools, "Dispatcht naar")
```

---

## Bijhouden

| Niveau | Bijwerken wanneer |
|---|---|
| L1 Context | Een nieuw gebruikerstype of een externe service (buiten de systeemgrens) wordt toegevoegd of verwijderd. |
| L2 Container | Een nieuwe service wordt aangemaakt of de eerste code van een geplande service wordt gebouwd; een service wordt verwijderd of samengevoegd. |
| L3 Component | Een nieuwe `api/app/features/<naam>/`-map of een nieuw scherm in `frontend/app/` wordt toegevoegd; een component wordt verwijderd of hernoemd. |
| L4 Code | Niet bijgehouden — staat in de code zelf. |
