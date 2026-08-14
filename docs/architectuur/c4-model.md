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
drie zijn vastgelegd in de topologie maar nog niet geïmplementeerd — ze staan hier al om het
volledige plaatje te tonen; markeer ze als gebouwd zodra de eerste code er is.

```mermaid
C4Container
  title Containers — lexplainables

  Person(beheerder, "Beheerder")
  Person(analist, "Analist")

  System_Boundary(wetsanalyse, "Lexplainables") {
    Container(frontend, "frontend", "Next.js / Auth.js v5", "Hoofdwebapp (BFF). Login via eigen credentials-formulier (httpOnly cookie). Beheer- en berichtenschermen gebouwd. Overige schermen nog niet.")
    Container(frontend_chat, "frontend-chat", "nog niet gebouwd", "Losse chatapp.")
    Container(api, "api", "FastAPI / Python", "Kernbackend: berichten, feedback, identiteit/toegang gebouwd. Analyse, wetcatalogus, annotatie, runtime-config nog niet.")
    ContainerDb(db, "database", "SQLite (dev) / PostgreSQL", "Tabel per feature binnen api.")
    Container(wettenbank_mcp, "wettenbank-mcp", "nog niet gebouwd", "MCP-server, wetcatalogus-lookups.")
    Container(graph_qa, "graph-qa", "nog niet gebouwd", "QA-/annotatie-agent.")
    Container(admin_mcp, "wetsanalyse-admin-mcp", "TypeScript / Node.js (stdio)", "Admin-MCP: berichten aanmaken, bewerken, publiceren via Claude Code.")
  }

  Rel(beheerder, frontend, "Gebruikt via browser", "HTTPS")
  Rel(analist, frontend, "Gebruikt via browser", "HTTPS")
  Rel(analist, frontend_chat, "Gebruikt via browser", "HTTPS")
  Rel(frontend, api, "BFF-aanroepen met API_TOKEN + X-User-Id", "HTTP/JSON")
  Rel(frontend_chat, api, "Roept aan", "HTTP/JSON")
  Rel(api, db, "Leest/schrijft", "SQLAlchemy")
  Rel(api, wettenbank_mcp, "Roept aan", "MCP")
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
    Component(identiteit_toegang, "identiteit_toegang", "features/identiteit_toegang/", "Eigen gebruikers-tabel (bcrypt). POST /v1/auth/verify achter API_TOKEN-gate.")
    Component(shared_auth, "shared/auth", "shared/auth.py", "API_TOKEN-gate (constant-time vergelijking) + X-User-Id-header. huidige_beheerder verifieert token én leest gebruikersidentiteit. huidige_gebruiker leest X-User-Id (analist-routes).")
  }

  Rel(berichten, shared_auth, "Gebruikt")
  Rel(feedback, shared_auth, "Gebruikt")
  Rel(identiteit_toegang, shared_auth, "Gebruikt voor /v1/auth/verify")
```

### `frontend`

```mermaid
C4Component
  title Componenten — frontend

  Container_Boundary(frontend, "frontend") {
    Component(startpagina, "StartPagina", "app/page.tsx", "Landingspagina met lintblauwe banner.")
    Component(login_pagina, "LoginPagina", "app/login/page.tsx", "Toont het login-formulier; redirect naar / als al ingelogd.")
    Component(login_formulier, "LoginFormulier", "components/auth/LoginFormulier.tsx", "Client Component: gebruikersnaam/wachtwoord, signIn('credentials'), foutmelding bij mislukken.")
    Component(beheer_pagina, "BeheerPagina", "app/beheer/page.tsx", "Berichten CRUD (aanmaken, bewerken, publiceren, verwijderen) via BFF. Gebruikers/feedback/instellingen als placeholder.")
    Component(berichten_pagina, "BerichtenPagina", "app/berichten/page.tsx", "Leest gepubliceerde berichten, markeert alle als gelezen op open.")
    Component(navigatie, "NavigatieHeader", "components/NavigatieHeader.tsx", "Nav met Beheer-tab, BerichtenPopover, gebruikersnaam, uitloggen.")
    Component(berichten_popover, "BerichtenPopover", "components/BerichtenPopover.tsx", "Bel-icoon met ongelezen-badge (poll 60s). Rollout-menu met ongelezen berichten, markeer-alles-gelezen.")
    Component(auth_config, "Auth.js config", "auth.ts / auth.config.ts", "Credentials provider roept POST /v1/auth/verify aan. JWT-callback slaat gebruikersnaam + rol op. httpOnly sessiecookie.")
    Component(bff_admin, "BFF admin-berichten", "app/api/admin/berichten/", "Server-side proxy naar api /v1/admin/berichten/*. Voegt API_TOKEN + X-User-Id toe.")
    Component(bff_berichten, "BFF berichten", "app/api/berichten/", "Server-side proxy naar api /v1/berichten/* (GET, ongelezen-aantal, lees-alles).")
  }

  Rel(beheer_pagina, bff_admin, "Roept aan", "fetch")
  Rel(berichten_pagina, bff_berichten, "Roept aan", "fetch")
  Rel(berichten_popover, bff_berichten, "Roept aan (ongelezen-aantal, lees-alles)", "fetch")
  Rel(navigatie, berichten_popover, "Rendert")
  Rel(login_pagina, login_formulier, "Rendert")
  Rel(bff_admin, auth_config, "Leest sessie via")
  Rel(bff_berichten, auth_config, "Leest sessie via")
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
