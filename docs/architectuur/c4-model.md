# C4-model — wetsanalyse

Drie niveaus: Context (wie gebruikt het systeem en wat zijn de externe grenzen),
Container (welke services zijn er en hoe praten ze), Component (welke features zitten
binnen elke service). Code (L4) wordt niet bijgehouden — dat staat in de code zelf.

Zie §Bijhouden voor wanneer elk niveau bijgewerkt moet worden.

---

## L1 — Context

Twee gebruikersrollen, één systeem, nog geen externe services in gebruik.

```mermaid
C4Context
  title Systeemcontext — wetsanalyse

  Person(beheerder, "Beheerder", "Beheert berichten, analyseprojecten, LLM-configuratie en annotaties.")
  Person(analist, "Analist", "Voert wetsanalyses uit, leest berichten, beoordeelt annotaties.")

  System(wetsanalyse, "Wetsanalyse", "Multi-service applicatie voor juridische wetsanalyse met LLM-ondersteuning.")

  Rel(beheerder, wetsanalyse, "Beheert via", "HTTPS")
  Rel(analist, wetsanalyse, "Gebruikt via", "HTTPS")
```

---

## L2 — Container

Zes services (ADR-0001). Gebouwd: `api` en `frontend`. De overige vier zijn vastgelegd
in de topologie maar nog niet geïmplementeerd — ze staan hier al om het volledige plaatje
te tonen; markeer ze als gebouwd zodra de eerste code er is.

```mermaid
C4Container
  title Containers — wetsanalyse

  Person(beheerder, "Beheerder")
  Person(analist, "Analist")

  System_Boundary(wetsanalyse, "Wetsanalyse") {
    Container(frontend, "frontend", "Next.js", "Hoofdwebapp. Beheerscherm voor berichten (gebouwd). Overige schermen nog niet.")
    Container(frontend_chat, "frontend-chat", "nog niet gebouwd", "Losse chatapp.")
    Container(api, "api", "FastAPI / Python", "Kernbackend: berichten, feedback (gebouwd). Analyse, auth, wetcatalogus, annotatie, runtime-config nog niet.")
    ContainerDb(db, "database", "SQLite (dev) / PostgreSQL", "Tabel per feature binnen api.")
    Container(wettenbank_mcp, "wettenbank-mcp", "nog niet gebouwd", "MCP-server, wetcatalogus-lookups.")
    Container(graph_qa, "graph-qa", "nog niet gebouwd", "QA-/annotatie-agent.")
    Container(admin_mcp, "wetsanalyse-admin-mcp", "nog niet gebouwd", "Admin-MCP, los van api's eigen admin-oppervlak.")
  }

  Rel(beheerder, frontend, "Gebruikt via browser", "HTTPS")
  Rel(analist, frontend, "Gebruikt via browser", "HTTPS")
  Rel(analist, frontend_chat, "Gebruikt via browser", "HTTPS")
  Rel(frontend, api, "Roept aan", "HTTP/JSON")
  Rel(frontend_chat, api, "Roept aan", "HTTP/JSON")
  Rel(api, db, "Leest/schrijft", "SQLAlchemy")
  Rel(api, wettenbank_mcp, "Roept aan", "MCP")
  Rel(api, graph_qa, "Roept aan", "HTTP/JSON")
  Rel(admin_mcp, api, "Roept aan", "HTTP/JSON")
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
    Component(shared_auth, "shared/auth", "shared/auth.py", "Auth-stand-in: huidige_gebruiker / huidige_beheerder via X-User-Id / X-Admin-Id header.")
  }

  Rel(berichten, shared_auth, "Gebruikt")
  Rel(feedback, shared_auth, "Gebruikt")
```

### `frontend`

```mermaid
C4Component
  title Componenten — frontend

  Container_Boundary(frontend, "frontend") {
    Component(berichten_admin, "BerichtenAdminPagina", "app/page.tsx", "Overzicht + aanmaken/bewerken/publiceren/verwijderen van berichten. Auth-stand-in via localStorage.")
  }
```

---

## Bijhouden

| Niveau | Bijwerken wanneer |
|---|---|
| L1 Context | Een nieuw gebruikerstype of een externe service (buiten de systeemgrens) wordt toegevoegd of verwijderd. |
| L2 Container | Een nieuwe service wordt aangemaakt of de eerste code van een geplande service wordt gebouwd; een service wordt verwijderd of samengevoegd. |
| L3 Component | Een nieuwe `api/app/features/<naam>/`-map of een nieuw scherm in `frontend/app/` wordt toegevoegd; een component wordt verwijderd of hernoemd. |
| L4 Code | Niet bijgehouden — staat in de code zelf. |
