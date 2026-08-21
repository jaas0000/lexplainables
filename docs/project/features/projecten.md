# Projecten (werkgebieden)

analisten maken werkgebieden aan met één of meer bronnen (bwb_id + artikel + lid); CRUD-endpoints leveren lijst/detail/verwijderen; annotatie op individuele elementen woont in `annotatie/`. Read-only LLM-calls-log koppelt aan `llm_calls`.

**Waarom apart:** eigen domein voor de werkgebied-metadata (naam + bronnen + omschrijving) los van annotatie (dat is een aparte werkplek-stap). De ooit gebouwde JAS-orkestratie (act2/act3, review-flow, rapport, SSE) is opgeruimd (migratie 0012, migratie-plan fase 1) — annotatie is de enige overgebleven analyse-stap.

**Grens:** geen orkestratie meer, geen SSE, geen rapport-endpoint; het domein bewaart alleen de werkgebied-metadata. Voor annotatie zie `annotatie/`; voor LLM-calls-registratie zie `llm_calls/`.

## Datamodel

### `analyses`
id + naam + status (`nieuw`) + bronnen (JSON) + omschrijving + timestamps (aangemaakt/bijgewerkt) + gebruiker_id.

| kolom | type | eigenschappen |
|---|---|---|
| `id` | `String(36)` | primary key |
| `naam` | `String(256)` | nullable |
| `status` | `String(32)` | NOT NULL |
| `bronnen` | `JSON` | NOT NULL |
| `omschrijving` | `Text` | nullable |
| `aangemaakt` | `DateTime(timezone=True)` | NOT NULL |
| `bijgewerkt` | `DateTime(timezone=True)` | NOT NULL, index |
| `gebruiker_id` | `String(128)` | NOT NULL, index |

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `POST` | `/projecten` | beheerder | `AangemaaktAcceptatie` |
| `GET` | `/projecten` | beheerder | `list[AnalyseOverzicht]` |
| `GET` | `/projecten/{analyse_id}` | beheerder | `AnalyseDetail` |
| `DELETE` | `/projecten/{analyse_id}` | beheerder | — |
| `GET` | `/projecten/{analyse_id}/llm-calls` | beheerder | `list[LlmCallRead]` |

## Store-interface

```python
class AnalyseStore(Protocol):
    async def maak(gebruiker_id, naam, bronnen, omschrijving) -> AnalyseDetail: ...
    async def lijst(gebruiker_id, is_beheerder) -> list[AnalyseOverzicht]: ...
    async def detail(analyse_id, gebruiker_id, is_beheerder) -> AnalyseDetail: ...
    async def verwijder(analyse_id, gebruiker_id, is_beheerder) -> None: ...
```

## Interacties

- shared/auth.py: `huidige_beheerder` op alle endpoints (BFF geeft rol door via X-User-Id).
- llm_calls/dependencies.py: `get_llm_calls_store` voor de log-per-werkgebied-route.
- db.py: `AsyncEngine` via `get_engine()` naar de store.

## Getest gedrag

- Aanmaken geeft 201 met id.
- Aanmaken naam optioneel.
- Aanmaken zonder bronnen geeft 422.
- Aanmaken met omschrijving.
- Lijst leeg.
- Lijst gevuld.
- Detail bestaand.
- Detail onbekend id geeft 404.
- Verwijder bestaand.
- Verwijder onbekend id geeft 404.
- Verwijder verdwijnt uit lijst.

## Beslissingen

- ADR-0007 (store-abstractie): router leunt op `AnalyseStore` Protocol; rolfilter (analist vs. beheerder) zit in de store, niet in de router.
- ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
- Migratie-plan fase 1: rapport (013) + analyse-engine (024) verwijderd — JAS-pipeline is legacy; annotatie is de enige overgebleven analyse-stap.
