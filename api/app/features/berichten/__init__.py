"""Berichten.

Wat: beheerders schrijven release notes en aankondigingen (concept → gepubliceerd →
gedepubliceerd); analisten lezen de gepubliceerde berichten en per-user wordt bijgehouden
welke al gelezen zijn.
Waarom: eigen domein voor systeem-brede aankondigingen met eigen publicatie-levenscyclus en
leesbewijzen — losstaand van feedback (dat is user→admin, dit is admin→user) en van
user-identiteit.
Grens: geen realtime-push (client polt); auth leunt op `shared/auth.py` met rollen
(`huidige_beheerder` voor admin-CRUD, `huidige_gebruiker` voor lezen); publicatiedatum kan
zowel automatisch als expliciet.

Tabellen:
  - berichten: id + type + titel + inhoud + status + gepubliceerd_op + versie + timestamps.
  - bericht_leesbewijzen: per (userid, bericht_id) tijdstip van lezen.

Beslissingen:
  - ADR-0007 (store-abstractie): router leunt op `BerichtenStore` Protocol.
  - ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
  - Story 002 §Type-enum: gesloten verzameling (`info`/`update`/`waarschuwing`/`kritiek`)
    als `Literal` → echte enum in OpenAPI.
  - Story 003 §Bewerken: bewerken van concept OK, van gepubliceerd berichten reset niet de
    leesbewijzen — een correctie zet niet iedereen op ongelezen.

Interacties:
  - shared/auth.py: `huidige_beheerder` voor admin-router, `huidige_gebruiker` voor de
    lees-endpoints.
  - shared/tijd.py: `nu()` als vervangbare klok voor `gepubliceerd_op` en leesbewijzen.
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
"""
