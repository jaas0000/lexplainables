# Berichten

beheerders schrijven release notes en aankondigingen (concept → gepubliceerd → gedepubliceerd); analisten lezen de gepubliceerde berichten en per-user wordt bijgehouden welke al gelezen zijn.

**Waarom apart:** eigen domein voor systeem-brede aankondigingen met eigen publicatie-levenscyclus en leesbewijzen — losstaand van feedback (dat is user→admin, dit is admin→user) en van user-identiteit.

**Grens:** geen realtime-push (client polt); auth leunt op `shared/auth.py` met rollen (`huidige_beheerder` voor admin-CRUD, `huidige_gebruiker` voor lezen); publicatiedatum kan zowel automatisch als expliciet.

## Datamodel

### `berichten`
id + type + titel + inhoud + status + gepubliceerd_op + versie + timestamps.

| kolom | type | eigenschappen |
|---|---|---|
| `id` | `Integer` | primary key, autoincrement |
| `titel` | `Text` | NOT NULL |
| `inhoud` | `Text` | NOT NULL |
| `type` | `String(16)` | NOT NULL, default 'info' |
| `versie` | `String(32)` | nullable |
| `gepubliceerd` | `Boolean` | NOT NULL, default False, index |
| `gepubliceerd_op` | `DateTime(timezone=True)` | nullable |
| `aangemaakt_door` | `String(128)` | NOT NULL |
| `created` | `DateTime(timezone=True)` | NOT NULL, index |
| `updated` | `DateTime(timezone=True)` | NOT NULL |

### `bericht_leesbewijzen`
per (userid, bericht_id) tijdstip van lezen.

| kolom | type | eigenschappen |
|---|---|---|
| `bericht_id` | `Integer` | NOT NULL |
| `userid` | `String(128)` | NOT NULL |
| `gelezen_op` | `DateTime(timezone=True)` | NOT NULL |

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `GET` | `/berichten/ongelezen-aantal` | gebruiker | `OngelezenAantalOut` |
| `POST` | `/berichten/lees-alles` | gebruiker | — |
| `GET` | `/berichten` | gebruiker | `BerichtenPaginaOut` |
| `GET` | `/admin/berichten` | beheerder | `AdminBerichtenPaginaOut` |
| `POST` | `/admin/berichten` | beheerder | `BerichtAdminRead` |
| `PUT` | `/admin/berichten/{bericht_id}` | beheerder | `BerichtAdminRead` |
| `PATCH` | `/admin/berichten/{bericht_id}/publicatie` | beheerder | `BerichtAdminRead` |
| `DELETE` | `/admin/berichten/{bericht_id}` | beheerder | — |

## Store-interface

```python
class BerichtenStore(Protocol):
    async def lijst(userid, offset, limit, ongelezen_only) -> list[BerichtRead]: ...
    async def totaal(userid, ongelezen_only) -> int: ...
    async def ongelezen_aantal(userid) -> int: ...
    async def markeer_alles_gelezen(userid) -> None: ...
    async def lijst_admin(offset, limit) -> list[BerichtAdminRead]: ...
    async def totaal_admin() -> int: ...
    async def maak(titel, inhoud, type, versie, aangemaakt_door) -> BerichtAdminRead: ...
    async def bewerk(bericht_id, titel, inhoud, type, versie) -> BerichtAdminRead: ...
    async def zet_publicatie(bericht_id, gepubliceerd) -> BerichtAdminRead: ...
    async def verwijder(bericht_id) -> None: ...
```

## Interacties

- shared/auth.py: `huidige_beheerder` voor admin-router, `huidige_gebruiker` voor de lees-endpoints.
- shared/tijd.py: `nu()` als vervangbare klok voor `gepubliceerd_op` en leesbewijzen.
- db.py: `AsyncEngine` via `get_engine()` naar de store.

## Getest gedrag

- Aanmaken is altijd concept.
- Aanmaken met ongeldig type geeft 422.
- Bewerken.
- Bewerken onbekend id geeft 404.
- Publiceren en depubliceren.
- Publicatie onbekend id geeft 404.
- Verwijderen onbekend id geeft 404.
- Lijst met paginering en gelezen vlag.
- Lijst ongelezen filter.
- Ongelezen aantal voor en na lees alles.
- Lees alles is idempotent.
- Verwijderen cascadeert leesbewijzen.

## Beslissingen

- ADR-0007 (store-abstractie): router leunt op `BerichtenStore` Protocol.
- ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
- Story 002 §Type-enum: gesloten verzameling (`info`/`update`/`waarschuwing`/`kritiek`) als `Literal` → echte enum in OpenAPI.
- Story 003 §Bewerken: bewerken van concept OK, van gepubliceerd berichten reset niet de leesbewijzen — een correctie zet niet iedereen op ongelezen.
