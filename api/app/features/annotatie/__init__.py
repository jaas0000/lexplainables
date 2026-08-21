"""Annotatie.

Wat: analisten annoteren wetsartikelen met JAS-klasse-elementen; per element een
human-beslissing (goedkeuren/bewerken/afwijzen/opmerking) met levenscyclus, plus een
append-only auditlog.
Waarom: annotatie is de kern-analyse-stap en heeft eigen levensduur, status-berekening en
auditregels — geen slice van projecten (die orkestreert enkel), geen slice van wetcatalogus
(die is puur lookup).
Grens: verwerkt geen tekst-analyse zelf (JAS-suggesties komen van graph-qa); auth-check is
`huidige_gebruiker` via `shared/auth`, eigenaarschap wordt in de router afgedwongen (404 bij
ander client_id — geen 403 om bestaan niet te lekken).

Tabellen:
  - annotatie_documenten: werkdocument per (werkgebied, bwb_id, artikel, lid) met JSON-lijst
    van elementen.
  - annotatie_audit: append-only auditlog; tijdlijn = ORDER BY id (BIGINT autoincrement).

Beslissingen:
  - ADR-0007 (store-abstractie): router leunt op `AnnotatieStore` Protocol, tests draaien
    tegen de echte SQL-store.
  - ADR-0011 (schema-eenheid): SQLAlchemy Core + Pydantic + expliciete `document_uit_rij` /
    `samenvatting_uit_rij` / `audit_uit_rij`.
  - Feature-bouwen regel 8: `GELDIGE_JAS_KLASSEN` staat in `shared/validation.py` — tweede
    onafhankelijke gebruiker naast `engine/validation.py`.
  - Story 022 §Levenscyclus: `bewerken` vereist `reden`+`wijziging`; `afwijzen` vereist
    `reden` — afgedwongen door `BeslissingInvoer.model_validator` → 422.

Interacties:
  - shared/auth.py: `huidige_gebruiker` (client_id-scoping in de router).
  - shared/tijd.py: `nu()` als vervangbare klok voor
    `aangemaakt`/`bijgewerkt`/beslissing-tijdstippen.
  - shared/validation.py: `GELDIGE_JAS_KLASSEN` voor element-validatie bij PUT (ongeldige
    klasse → overgeslagen, niet 422).
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
"""
