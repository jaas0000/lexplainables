# API-tokens

beheerders maken en trekken API-tokens in die door externe systemen als bearer-token gebruikt worden; de plaintext-waarde is éénmalig te zien bij aanmaken, daarna alleen de prefix.

**Waarom apart:** een eigen domein omdat token-hashing, prefix-weergave en intrekken los staan van gebruikersidentiteit — een token is een aparte credential, geen kolom op de gebruiker.

**Grens:** dit domein zorgt alleen voor opslag/intrekking van tokens; de daadwerkelijke verificatie van een binnenkomend bearer-token gebeurt in `shared/auth.py` (`vereist_api_token`), niet hier.

## Datamodel

### `api_tokens`
id + label + token_hash (SHA-256) + prefix (eerste 8 chars) + intrekker-info + timestamps.

| kolom | type | eigenschappen |
|---|---|---|
| `id` | `Text()` | primary key |
| `label` | `Text()` | NOT NULL |
| `token_hash` | `Text()` | NOT NULL |
| `token_prefix` | `Text()` | NOT NULL |
| `scope` | `Text()` | NOT NULL |
| `actief` | `Boolean()` | NOT NULL |
| `aangemaakt_door` | `Text()` | NOT NULL |
| `aangemaakt_op` | `DateTime(timezone=True)` | NOT NULL |
| `laatste_gebruik` | `DateTime(timezone=True)` | nullable |

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `GET` | `/admin/api-tokens` | beheerder | `list[ApiTokenRead]` |
| `POST` | `/admin/api-tokens` | beheerder | `ApiTokenAangemaakt` |
| `DELETE` | `/admin/api-tokens/{token_id}` | beheerder | — |

## Store-interface

```python
class ApiTokenStore(Protocol):
    async def lijst() -> list[ApiTokenRead]: ...
    async def maak(label, aangemaakt_door) -> tuple[ApiTokenRead, str]: ...
    async def trek_in(token_id) -> None: ...
    async def verifieer(plaintext) -> str | None: ...
    async def update_laatste_gebruik(token_id) -> None: ...
```

## Interacties

- shared/auth.py: `huidige_beheerder` dependency op alle endpoints; de verificatielaag in `vereist_api_token` leest deze tabel.
- db.py: `AsyncEngine` via `get_engine()` naar de store.

## Getest gedrag

- Aanmaken geeft token in response.
- Aanmaken zonder label.
- Aanmaken token niet in lijst.
- Lijst toont prefix niet plaintext.
- Lijst is leeg bij start.
- Intrekken geeft 204.
- Ingetrokken token verschijnt niet in lijst.
- Intrekken onbekend id geeft 404.
- Intrekken tweemaal geeft 404.
- Db token wordt geaccepteerd in auth.
- Ingetrokken db token wordt geweigerd.
- Verifieer update laatste gebruik.

## Beslissingen

- ADR-0007 (store-abstractie): router leunt op `ApiTokenStore` Protocol.
- ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
- Story 018 §Geheim: plaintext-token alleen bij POST-response teruggeven; lijst-endpoint toont uitsluitend de prefix — het volledige geheim leeft nergens meer na aanmaken.
