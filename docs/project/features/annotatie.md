# Annotatie

analisten annoteren wetsartikelen met JAS-klasse-elementen; per element een human-beslissing (goedkeuren/bewerken/afwijzen/opmerking) met levenscyclus, plus een append-only auditlog.

**Waarom apart:** annotatie is de enige analyse-stap (JAS-pipeline is legacy) en heeft eigen levensduur, status-berekening en auditregels — geen slice van projecten (dat is enkel werkgebied-metadata), geen slice van wetcatalogus (dat is puur lookup).

**Grens:** verwerkt geen tekst-analyse zelf (JAS-suggesties komen van graph-qa); auth-check is `huidige_gebruiker` via `shared/auth`, eigenaarschap wordt in de router afgedwongen (404 bij ander client_id — geen 403 om bestaan niet te lekken).

## Datamodel

### `annotatie_documenten`
werkdocument per (werkgebied, bwb_id, artikel, lid) met JSON-lijst van elementen.

| kolom | type | eigenschappen |
|---|---|---|
| `slug` | `Text` | primary key |
| `client_id` | `Text` | NOT NULL, index |
| `werkgebied` | `Text` | NOT NULL |
| `bwb_id` | `Text` | NOT NULL |
| `artikel` | `Text` | NOT NULL |
| `lid` | `Text` | NOT NULL, default '' |
| `status` | `Text` | NOT NULL, default 'voorgesteld' |
| `elementen` | `JSON` | NOT NULL, default list |
| `aangemaakt` | `DateTime(timezone=True)` | NOT NULL |
| `bijgewerkt` | `DateTime(timezone=True)` | NOT NULL |

### `annotatie_audit`
append-only auditlog; tijdlijn = ORDER BY id (BIGINT autoincrement).

| kolom | type | eigenschappen |
|---|---|---|
| `id` | `Integer` | primary key, autoincrement |
| `document_slug` | `Text` | NOT NULL, index |
| `client_id` | `Text` | NOT NULL |
| `actor` | `Text` | NOT NULL |
| `actie` | `Text` | NOT NULL |
| `element_id` | `Text` | nullable |
| `detail` | `JSON` | NOT NULL, default dict |
| `tijdstip` | `DateTime(timezone=True)` | NOT NULL |

## API

| Methode | Pad | Auth | Response |
|---|---|---|---|
| `POST` | `/annotatie/documenten` | gebruiker | `AnnotatieDocument` |
| `GET` | `/annotatie/documenten` | gebruiker | `DocumentenLijstOut` |
| `GET` | `/annotatie/documenten/{slug}` | gebruiker | `AnnotatieDocument` |
| `DELETE` | `/annotatie/documenten/{slug}` | gebruiker | — |
| `PUT` | `/annotatie/documenten/{slug}/elementen` | gebruiker | `ElementenZettenOut` |
| `POST` | `/annotatie/documenten/{slug}/elementen/{element_id}/beslissing` | gebruiker | `AnnotatieDocument` |
| `GET` | `/annotatie/documenten/{slug}/audit` | gebruiker | `AuditlogOut` |

## Store-interface

```python
class AnnotatieStore(Protocol):
    async def maak_document(doc) -> AnnotatieDocument: ...
    async def laad_document(slug) -> AnnotatieDocument | None: ...
    async def lijst_documenten_samenvatting(client_id, limit, offset) -> list[DocumentSamenvatting]: ...
    async def verwijder_document(slug) -> None: ...
    async def vervang_elementen(slug, elementen, status) -> None: ...
    async def schrijf_audit(slug, client_id, actor, actie) -> None: ...
    async def lees_audit(slug) -> list[AuditRegel]: ...
```

## Interacties

- shared/auth.py: `huidige_gebruiker` (client_id-scoping in de router).
- shared/tijd.py: `nu()` als vervangbare klok voor `aangemaakt`/`bijgewerkt`/beslissing-tijdstippen.
- shared/validation.py: `GELDIGE_JAS_KLASSEN` voor element-validatie bij PUT (ongeldige klasse → overgeslagen, niet 422).
- db.py: `AsyncEngine` via `get_engine()` naar de store.

## Getest gedrag

- Document aanmaken en ophalen.
- Lijst eigen documenten.
- Document verwijderen.
- Elementen zetten geldig.
- Elementen ongeldige klasse overgeslagen.
- Elementen lege tekst overgeslagen.
- Beslissing goedkeuren.
- Beslissing bewerken met reden en wijziging.
- Beslissing bewerken zonder reden geeft 422.
- Beslissing bewerken zonder wijziging geeft 422.
- Beslissing afwijzen met reden.
- Beslissing afwijzen zonder reden geeft 422.
- Beslissing element niet gevonden geeft 404.
- Auditlog bijgehouden.
- Auditlog na beslissing.
- Client scoping andermans document geeft 404.
- Client scoping lijst isoleert gebruikers.
- Document met optioneel lid.
- Gedeeltelijk gereviewd status.

## Beslissingen

- ADR-0007 (store-abstractie): router leunt op `AnnotatieStore` Protocol, tests draaien tegen de echte SQL-store.
- ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete `document_uit_rij` / `samenvatting_uit_rij` / `audit_uit_rij`.
- Feature-bouwen regel 8: `GELDIGE_JAS_KLASSEN` staat in `shared/validation.py` als gedeelde constante.
- Story 022 §Levenscyclus: `bewerken` vereist `reden`+`wijziging`; `afwijzen` vereist `reden` — afgedwongen door `BeslissingInvoer.model_validator` → 422.
