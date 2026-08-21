# Wetcatalogus

beheerders beheren een gecureerde lijst van wetten (naam + bwb_id) via CRUD; analisten lezen de lijst en de structuur (artikelen per wet) via wettenbank-MCP; admin-`resolve` kan een bwb_id opzoeken.

**Waarom apart:** eigen domein — een expliciete catalogus voorkomt dat elke analyse-invoer opnieuw de wettenbank moet raadplegen en houdt de lijst gecureerd (niet elke bwb_id in Nederland is relevant).

**Grens:** het domein zelf slaat alleen naam + bwb_id op; de structuur (artikelen/leden) en actuele tekst komen live via `shared/wettenbank` uit de externe MCP-service — geen dubbele opslag.

## Datamodel

### `wet_catalogus`
bwb_id (PK) + naam + bijgewerkt_door + timestamps.

| kolom | type | eigenschappen |
|---|---|---|
| `bwb_id` | `Text` | primary key |
| `naam` | `Text` | NOT NULL |
| `bijgewerkt_door` | `Text` | NOT NULL |
| `bijgewerkt` | `DateTime(timezone=True)` | NOT NULL |

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `GET` | `/wetten` | gebruiker | `list[WetKeuze]` |
| `GET` | `/wetten/{bwb_id}/structuur` | gebruiker | `WetStructuur` |
| `GET` | `/admin/wetten` | beheerder | `list[WetRead]` |
| `PUT` | `/admin/wetten/{bwb_id}` | beheerder | `WetRead` |
| `DELETE` | `/admin/wetten/{bwb_id}` | beheerder | — |
| `POST` | `/admin/wetten/{bwb_id}/resolve` | beheerder | `ResolveResultaat` |

## Store-interface

```python
class WetcatalogusStore(Protocol):
    async def lijst() -> list[WetKeuze]: ...
    async def lijst_met_metadata() -> list[WetRead]: ...
    async def upsert(bwb_id, naam, bijgewerkt_door) -> WetRead: ...
    async def verwijder(bwb_id) -> None: ...
    async def structuur(bwb_id) -> WetStructuur: ...
```

## Interacties

- shared/auth.py: `huidige_beheerder` voor admin, `huidige_gebruiker` voor de lezende endpoints.
- shared/wettenbank.py: MCP-client voor structuur-lookup en resolve.
- db.py: `AsyncEngine` via `get_engine()` naar de store.

## Getest gedrag

- Lijst wetten geeft drie wetten.
- Lijst wetten bevat naam.
- Structuur wwb geeft zes artikelen.
- Structuur onbekend bwb id geeft 404.
- Lege wettenlijst.
- Admin lijst bevat metadata.
- Admin lijst leeg.
- Upsert nieuwe wet.
- Upsert bestaande wet werkt bij.
- Upsert lege naam geeft 422.
- Upsert tweemaal dezelfde wet werkt.
- Verwijder bekende wet.
- Verwijder onbekend bwb id geeft 404.
- Resolve succesvol.
- Resolve mcp niet bereikbaar geeft 502.
- Resolve wet onbekend bij mcp geeft 404.
- Admin zonder auth geeft 401.

## Beslissingen

- ADR-0007 (store-abstractie): router leunt op `WetcatalogusStore` Protocol.
- ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
- Story 010 §Databron: catalogus in eigen tabel, structuur (artikelen) live via wettenbank-MCP; geen caching van artikelen om drift met bronnen te voorkomen.
- Story 020 §Admin-resolve: `POST /admin/wetten/resolve` accepteert een bwb_id en levert de naam uit de wettenbank terug — laat de beheerder handmatig invoeren voorkomen.
