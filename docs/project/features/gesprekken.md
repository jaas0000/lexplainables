# Gesprekken

de persistente chatgeschiedenis van de werkplek — per gebruiker een lijst gesprekken, elk met een geordende reeks berichten (vraag + antwoord, of een annotatieverwijzing).

**Waarom apart:** zonder dit domein leeft een gesprek alleen client-side (`conversation_id` in React-state) — een herlaad of gesloten tabblad verliest het dan, ook als de agent zijn beurt al had afgerond. graph-qa legt het resultaat van een beurt hier zelf vast (zie `tools/graph-qa/agent/beurt.py`), zodat niemand aan het eind nog hoeft te kijken.

**Grens:** bewust los van het annotatie-domein — een bericht kan naar een annotatiedocument verwijzen (`annotatie_slug` + het leesbare `annotatie_titel` op het moment van de beurt), maar de review-state zelf blijft in `annotatie`. Geen rolautorisatie hier (dat draagt de BFF); wel eigenaarschap: een gebruiker ziet en muteert alleen zijn eigen gesprekken.

## Datamodel

### `gesprekken`
één rij per gesprek (id, gebruiker, titel, aangemaakt, bijgewerkt).

| kolom | type | eigenschappen |
|---|---|---|
| `id` | `Text` | primary key |
| `gebruiker` | `Text` | NOT NULL, index |
| `titel` | `Text` | NOT NULL, default '' |
| `aangemaakt` | `DateTime(timezone=True)` | NOT NULL |
| `bijgewerkt` | `DateTime(timezone=True)` | NOT NULL |

### `gesprek_berichten`
append-only, geordend op id; de heterogene beurt-payload (tekst/denk/ bronnen/annotatieverwijzing) staat als JSON in de kolom `inhoud`.

| kolom | type | eigenschappen |
|---|---|---|
| `id` | `Integer` | primary key, autoincrement |
| `gesprek_id` | `Text` | NOT NULL, index |
| `rol` | `Text` | NOT NULL |
| `inhoud` | `JSON` | NOT NULL, default dict |
| `aangemaakt` | `DateTime(timezone=True)` | NOT NULL |

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `POST` | `/gesprekken` | beheerder | `Gesprek` |
| `GET` | `/gesprekken` | beheerder | `list[GesprekSamenvatting]` |
| `GET` | `/gesprekken/{gesprek_id}` | beheerder | `Gesprek` |
| `POST` | `/gesprekken/{gesprek_id}/berichten` | beheerder | `Bericht` |
| `PATCH` | `/gesprekken/{gesprek_id}` | beheerder | `Gesprek` |
| `DELETE` | `/gesprekken/{gesprek_id}` | beheerder | — |

## Store-interface

```python
class GesprekStore(Protocol):
    async def maak_gesprek(gesprek) -> Gesprek: ...
    async def laad_gesprek(gesprek_id) -> Gesprek | None: ...
    async def lijst_samenvattingen(gebruiker, limit, offset) -> list[GesprekSamenvatting]: ...
    async def voeg_bericht_toe(gesprek_id, inv) -> Bericht: ...
    async def hernoem_gesprek(gesprek_id, titel) -> None: ...
    async def verwijder_gesprek(gesprek_id) -> None: ...
```

## Interacties

- shared/auth.py: `huidige_beheerder` voor auth + eigenaarschap.
- shared/tijd.py: `nu()` als vervangbare klok voor `aangemaakt`/`bijgewerkt`.
- db.py: `AsyncEngine` via `get_engine()` naar de store.
- tools/graph-qa/agent/beurt.py: enige schrijver van assistent-berichten (poort van wetsanalyse-ai se `agent/beurt.py::voer_beurt_uit`).

## Getest gedrag

- Maak gesprek en haal op.
- Onbekend gesprek geeft 404.
- Andermans gesprek geeft 404.
- Lijst toont alleen eigen gesprekken nieuwste eerst.
- Bericht toevoegen verschijnt in gesprek.
- Bericht op onbekend gesprek geeft 404.
- Zelfde run id levert niet twee berichten op.
- Annotatieverwijzing op bericht.
- Hernoem gesprek.
- Verwijder gesprek.
- Zonder auth geeft 401.

## Beslissingen

- Eigenaarschap via `gebruiker` (uit `huidige_beheerder`'s `X-User-Id`), zelfde bearer-token+identiteit-combinatie als `chat_proxy` — sterker dan annotatie se kale `huidige_gebruiker`, omdat chatgeschiedenis persoonlijker is dan een agent-werkdocument. 404 (niet 403) bij andermans gesprek — bestaan lekt niet.
- `POST .../berichten` is idempotent op `run_id`: dezelfde agent-run mag maar één assistent-bericht opleveren, ook als er twee tabbladen dezelfde run volgen.
