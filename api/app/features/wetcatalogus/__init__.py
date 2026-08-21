"""Wetcatalogus.

Wat: beheerders beheren een gecureerde lijst van wetten (naam + bwb_id) via CRUD; analisten lezen de lijst en de structuur (artikelen per wet) via wettenbank-MCP; admin-`resolve` kan een bwb_id opzoeken.
Waarom: eigen domein — een expliciete catalogus voorkomt dat elke analyse-invoer opnieuw de wettenbank moet raadplegen en houdt de lijst gecureerd (niet elke bwb_id in Nederland is relevant).
Grens: het domein zelf slaat alleen naam + bwb_id op; de structuur (artikelen/leden) en actuele tekst komen live via `shared/wettenbank` uit de externe MCP-service — geen dubbele opslag.

Tabellen:
  - wet_catalogus: bwb_id (PK) + naam + bijgewerkt_door + timestamps.

Beslissingen:
  - ADR-0007 (store-abstractie): router leunt op `WetcatalogusStore` Protocol.
  - ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
  - Story 010 §Databron: catalogus in eigen tabel, structuur (artikelen) live via wettenbank-MCP; geen caching van artikelen om drift met bronnen te voorkomen.
  - Story 020 §Admin-resolve: `POST /admin/wetten/resolve` accepteert een bwb_id en levert de naam uit de wettenbank terug — laat de beheerder handmatig invoeren voorkomen.

Interacties:
  - shared/auth.py: `huidige_beheerder` voor admin, `huidige_gebruiker` voor de lezende endpoints.
  - shared/wettenbank.py: MCP-client voor structuur-lookup en resolve.
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
"""
