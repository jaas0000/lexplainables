# Projecten (analyses)

analisten maken analyses aan met één of meer bronnen (bwb_id + artikel + lid); een background-job orkestreert act2/act3 via `engine/orchestrator`; SSE geeft live status; rapport-endpoint levert eindresultaat + Markdown-download; LLM-calls-log koppelt aan `llm_calls`.

**Waarom apart:** eigen domein voor analyse-orkestratie — status-machine, background-task-lifecycle, SSE-stream, human-in-the-loop akkoord/afwijzen. Los van annotatie (dat is post-analyse werkplek) en van de engine zelf (dat is stateless orkestratie-code).

**Grens:** het rekenwerk zit in `engine/orchestrator.py`, niet hier; de analyse-status en tussenresultaten worden hier bewaard; annotatie op individuele elementen woont in `annotatie/`.

## Datamodel

### `analyses`
id + naam + client_id + status (actief/wacht_op_review/klaar/fout) + fase + bronnen (JSON) + begrippenlijst (JSON, optioneel) + human_in_the_loop + resultaat (JSON) + timestamps.

| kolom | type | eigenschappen |
|---|---|---|
| `id` | `String(36)` | primary key |
| `naam` | `String(256)` | nullable |
| `status` | `String(32)` | NOT NULL |
| `bronnen` | `JSON` | NOT NULL |
| `model_profiel` | `String(128)` | nullable |
| `omschrijving` | `Text` | nullable |
| `analysefocus` | `Text` | nullable |
| `human_in_the_loop` | `Boolean` | NOT NULL |
| `begrippenlijst` | `JSON` | nullable |
| `huidige_fase` | `Text` | nullable |
| `foutmelding` | `Text` | nullable |
| `rapport` | `JSON` | nullable |
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
| `GET` | `/projecten/{analyse_id}/rapport` | beheerder | `dict` |
| `GET` | `/projecten/{analyse_id}/rapport.md` | beheerder | — |
| `GET` | `/projecten/{analyse_id}/events` | beheerder | — |
| `POST` | `/projecten/{analyse_id}/akkoord` | beheerder | — |
| `POST` | `/projecten/{analyse_id}/afwijzen` | beheerder | — |
| `GET` | `/projecten/{analyse_id}/llm-calls` | beheerder | `list[LlmCallRead]` |

## Store-interface

```python
class AnalyseStore(Protocol):
    async def maak(gebruiker_id, naam, bronnen, omschrijving, analysefocus, begrippenlijst, model_profiel, human_in_the_loop) -> AnalyseDetail: ...
    async def lijst(gebruiker_id, is_beheerder) -> list[AnalyseOverzicht]: ...
    async def detail(analyse_id, gebruiker_id, is_beheerder) -> AnalyseDetail: ...
    async def verwijder(analyse_id, gebruiker_id, is_beheerder) -> None: ...
    async def zet_status(analyse_id, status, huidige_fase, foutmelding) -> None: ...
    async def haal_status(analyse_id) -> str | None: ...
    async def haal_rij_op_id(analyse_id) -> None: ...
    async def sla_rapport_op(analyse_id, rapport) -> None: ...
    async def haal_rapport(analyse_id, gebruiker_id, is_beheerder) -> dict: ...
```

## Interacties

- engine/orchestrator.py: `voer_analyse_uit` is de background-task; roept LLM aan via `engine/`, schrijft naar `llm_calls`.
- shared/auth.py: `huidige_beheerder` op alle endpoints (BFF geeft rol door via X-User-Id).
- llm_calls/dependencies.py: `get_llm_calls_store` voor de log-per-analyse-route.
- db.py: `AsyncEngine` via `get_engine()` naar de store.

## Getest gedrag

- Aanmaken geeft 202 met id.
- Aanmaken naam optioneel.
- Aanmaken zonder bronnen geeft 422.
- Aanmaken met begrippenlijst.
- Aanmaken human in the loop default true.
- Aanmaken human in the loop false.
- Lijst leeg.
- Lijst gevuld.
- Detail bestaand.
- Detail onbekend id geeft 404.
- Verwijder bestaand.
- Verwijder onbekend id geeft 404.
- Verwijder verdwijnt uit lijst.
- Events endpoint bestaat.
- Events onbekend id stuurt fout event.
- Rapport 200 als klaar.
- Rapport 409 als wachtrij.
- Rapport 409 als actief.
- Rapport 409 als klaar maar rapport leeg.
- Rapport 404 als onbekend.
- Rapport md 200 met content disposition.
- Rapport md 409 als niet klaar.

## Beslissingen

- ADR-0007 (store-abstractie): router leunt op `AnalyseStore` Protocol; rolfilter (analist vs. beheerder) zit in de store, niet in de router (story 012 §Auth).
- ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete mapping.
- Story 012 §Human-in-the-loop: default `true`; `akkoord` zet status terug op `actief` (job pikt op via polling), `afwijzen` zet status op `fout` (job stopt).
- Story 024: echte LLM-orkestratie via `engine/orchestrator.voer_analyse_uit`, geen mock.
