# LLM-profielen

beheerders beheren benoemde LLM-configuratie-profielen (naam, provider, model, temperatuur, max_tokens) met een Fernet-versleutelde API-sleutel; profielen worden per analyse gekozen.

**Waarom apart:** eigen domein omdat een profiel meer is dan een sleutel — het combineert provider-keuze, modelparameters en credential, en meerdere profielen moeten naast elkaar bestaan (bijv. GPT-4 voor act2, Claude voor act3).

**Grens:** dit domein slaat profielen op en handelt sleutel-encryptie/decryptie af; de daadwerkelijke LLM-aanroep gebeurt in `engine/`, niet hier; sleutel-plaintext leeft alleen tijdens één request in-memory.

## Datamodel

### `llm_profielen`
id + naam (uniek) + provider + model + temperatuur + max_tokens + api_sleutel_encrypted (Fernet) + timestamps.

| kolom | type | eigenschappen |
|---|---|---|
| `naam` | `String(128)` | primary key |
| `provider` | `String(64)` | NOT NULL |
| `model` | `String(128)` | NOT NULL |
| `api_base` | `Text` | NOT NULL |
| `api_versie` | `String(64)` | nullable |
| `temperatuur` | `Float` | NOT NULL, default 0.0 |
| `api_sleutel_enc` | `Text` | nullable |
| `is_standaard` | `Boolean` | NOT NULL, default False |
| `updated` | `DateTime(timezone=True)` | NOT NULL |

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `GET` | `/admin/profielen` | beheerder | `list[LlmProfielRead]` |
| `POST` | `/admin/profielen` | beheerder | `LlmProfielRead` |
| `PUT` | `/admin/profielen/{naam}` | beheerder | `LlmProfielRead` |
| `DELETE` | `/admin/profielen/{naam}` | beheerder | — |

## Store-interface

```python
class LlmProfielenStore(Protocol):
    async def lijst() -> list[LlmProfielRead]: ...
    async def maak(naam, provider, model, api_base, api_versie, temperatuur, api_sleutel, is_standaard) -> LlmProfielRead: ...
    async def bewerk(naam, provider, model, api_base, api_versie, temperatuur, api_sleutel, is_standaard) -> LlmProfielRead: ...
    async def verwijder(naam) -> None: ...
```

## Interacties

- shared/auth.py: `huidige_beheerder` op alle endpoints (admin-only).
- shared/crypto.py: `versleutel_geheim` / `ontsleutel_geheim` + `CryptoFout` voor de sleutel-flow.
- db.py: `AsyncEngine` via `get_engine()` naar de store.

## Getest gedrag

- Lijst leeg.
- Lijst gevuld.
- Aanmaken succesvol.
- Aanmaken zonder sleutel geeft sleutel ingesteld false.
- Aanmaken met sleutel geeft sleutel ingesteld true.
- Naam conflict geeft 409.
- Bijwerken succesvol.
- Bijwerken lege sleutel laat bestaande ongewijzigd.
- Bijwerken onbekende naam geeft 404.
- Is standaard flip bij bijwerken.
- Is standaard flip bij aanmaken.
- Verwijderen succesvol.
- Verwijderen enige profiel geeft 409.
- Verwijderen onbekende naam geeft 404.
- Zonder auth geeft 401.

## Beslissingen

- ADR-0007 (store-abstractie): router leunt op `LlmProfielenStore` Protocol.
- ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
- Story 011 §Encryptie: Fernet-versleuteling met sleutel uit env; de sleutel-lees-fout wordt als `CryptoFout` → 500 gerapporteerd (config-fout, geen validatie).
- Story 011 §API-response: `sleutel_ingesteld: bool` in plaats van de ciphertext of plaintext — externe caller weet dat er een sleutel is zonder hem in handen te krijgen.
