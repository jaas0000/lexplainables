"""Wetcatalogus.

Wat: beheerders beheren een gecureerde lijst van wetten (naam + bwb_id) via CRUD; analisten
lezen de lijst en de structuur (artikelen per wet); admin-`resolve` kan een bwb_id opzoeken.
Waarom: eigen domein — een expliciete catalogus voorkomt dat elke analyse-invoer opnieuw de
wettenbank moet raadplegen en houdt de lijst gecureerd (niet elke bwb_id in Nederland is
relevant).
Grens: het domein zelf slaat alleen naam + bwb_id op; de structuur (artikelen/leden) en
actuele tekst komen live uit een externe bron — geen dubbele opslag.

**Databron-correctie (2026-08-22, zie ADR-0001 §Consequenties):** oorspronkelijk gepland als
"wettenbank-MCP", die service bestaat niet en komt er niet. Vastgelegde vervolgrichting: directe
(read-only) SPARQL tegen de GraphDB-kennisgraaf zodra `deploy/graphdb` + `tools/bwb-import`
bestaan. Tot die tijd: `structuur()` op een hardgecodeerde fallback (zie
`DatabaseWetcatalogusStore`), `resolve` via `shared/wettenbank.haal_citeertitel_op` (faalt in de
praktijk — geen service op `WETTENBANK_MCP_URL`, zie de docstring van die module).

Tabellen:
  - wet_catalogus: bwb_id (PK) + naam + bijgewerkt_door + timestamps.

Beslissingen:
  - ADR-0007 (store-abstractie): router leunt op `WetcatalogusStore` Protocol.
  - ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
  - Story 010 §Databron: catalogus in eigen tabel, structuur (artikelen) live opgehaald;
    geen caching van artikelen om drift met bronnen te voorkomen.
  - Story 020 §Admin-resolve: `POST /admin/wetten/resolve` accepteert een bwb_id en levert
    de naam uit de wettenbank terug — laat de beheerder handmatig invoeren voorkomen.

Interacties:
  - shared/auth.py: `huidige_beheerder` voor admin, `huidige_gebruiker` voor de lezende
    endpoints.
  - shared/wettenbank.py: ophaal-client voor resolve (zie databron-correctie hierboven).
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
"""
