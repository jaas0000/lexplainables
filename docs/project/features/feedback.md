# Feedback

analisten dienen feedback in over de applicatie; beheerders zien de lijst, verwijderen items en houden bij tot wanneer ze zelf de pagina hebben gezien.

**Waarom apart:** dit is een zelfstandig domein — het bezit zowel de feedback zelf als de per-beheerder leesbewijzen, en heeft geen andere functie nodig dan dat (werkwijze-ADR-0001, vertical slicing).

**Grens:** het feedbackdomein levert geen realtime-notificaties (dat is `berichten`); auth-checks op de router leunen op de gedeelde stand-in (`shared/auth.py`), niet op eigen identiteit.

## Datamodel

### `user_feedback`
append-only rij per ingediend item (id, client_id, userid, categorie, tekst, pagina, created).

| kolom | type | eigenschappen |
|---|---|---|
| `id` | `Integer` | primary key, autoincrement |
| `client_id` | `String(128)` | NOT NULL |
| `userid` | `String(128)` | NOT NULL |
| `categorie` | `String(32)` | NOT NULL |
| `tekst` | `Text` | NOT NULL |
| `pagina` | `Text` | nullable |
| `created` | `DateTime(timezone=True)` | NOT NULL, index |

### `feedback_leesbewijzen`
per beheerder tot welk tijdstip de feedbackpagina is gezien.

| kolom | type | eigenschappen |
|---|---|---|
| `admin_userid` | `String(128)` | primary key |
| `gezien_tot` | `DateTime(timezone=True)` | NOT NULL |

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `POST` | `/feedback` | gebruiker | `FeedbackBevestigd` |
| `DELETE` | `/admin/feedback/{feedback_id}` | beheerder | — |
| `GET` | `/admin/feedback/ongelezen-aantal` | beheerder | `OngelezenFeedbackOut` |
| `POST` | `/admin/feedback/markeer-gezien` | beheerder | — |
| `GET` | `/admin/feedback` | beheerder | `FeedbackPaginaOut` |

## Store-interface

```python
class FeedbackStore(Protocol):
    async def dien_in(client_id, userid, categorie, tekst, pagina) -> FeedbackRead: ...
    async def verwijder(feedback_id) -> None: ...
    async def lijst(offset, limit) -> list[FeedbackRead]: ...
    async def totaal() -> int: ...
    async def ongelezen_aantal(admin_userid) -> int: ...
    async def markeer_gezien(admin_userid, tot) -> None: ...
```

## Interacties

- shared/auth.py: `huidige_gebruiker` (indien-ingelogd) en `huidige_beheerder` (rol-check) dependency.
- shared/tijd.py: `nu()` als vervangbare klok voor `created`/`gezien_tot`.
- db.py: de `AsyncEngine` wordt via `get_engine()` in de router aan de store gegeven.

## Getest gedrag

- Indienen en admin ziet het terug.
- Indienen met ongeldige categorie geeft 422.
- Verwijderen.
- Verwijderen onbekend id geeft 404.
- Paginering.
- Ongelezen aantal voor en na markeer gezien.
- Markeer gezien met expliciete tot beschermt tegen race conditie.

## Beslissingen

- ADR-0001 (vertical slicing): eigen tabel `feedback_leesbewijzen` in plaats van kolom op users.
- ADR-0007 (store-abstractie): router leunt op een Protocol, tests draaien tegen de echte SQL-store.
- ADR-0011 (schema-eenheid + expliciete mapping): SQLAlchemy Core + Pydantic + `feedback_uit_rij` op één plek.
- Story 001 §Schemabeslissing: `Literal["verbeteridee", ...]` i.p.v. string+regex — genereert een echte enum in OpenAPI.
