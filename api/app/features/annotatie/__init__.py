"""Annotatie.

Wat: analisten annoteren wetsartikelen met JAS-klasse-elementen; per element een
human-beslissing (goedkeuren/bewerken/afwijzen/opmerking) met levenscyclus, plus een
append-only auditlog.
Waarom: annotatie is de enige analyse-stap (JAS-pipeline is legacy) en heeft eigen
levensduur, status-berekening en auditregels — geen slice van projecten (dat is enkel
werkgebied-metadata), geen slice van wetcatalogus (dat is puur lookup).
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
  - Feature-bouwen regel 8: `GELDIGE_JAS_KLASSEN` (en de export-kleuren) staan in
    `shared/validation.py` als gedeelde constante.
  - Story 022 §Levenscyclus: `bewerken` vereist `reden`+`wijziging`; `afwijzen` vereist
    `reden` — afgedwongen door `BeslissingInvoer.model_validator` → 422.
  - Wetsanalyse-migratie-vervolg (werkwijze-lager-ceremonie-tempo): `DocumentStatus`
    kreeg een vierde, uitsluitend-expliciete waarde `geaccordeerd` (`POST .../status`) naast de
    drie automatisch-berekende — bevriest het document, alle andere schrijfpaden (incl.
    agent-write-back) weigeren dan met 409 (`router.py::_vereis_niet_afgerond`). Jurist kan
    eigen elementen aanmaken/verwijderen (`POST`/`DELETE .../elementen[/{id}]`, `herkomst`
    onderscheidt "mens" van "agent" — origin-type, geen attributie) los van de agent-PUT.
    `POST .../export` (PDF/CSV/JSON, `export.py`) haalt de
    wettekst zelf op via `graphdb.py` i.p.v. dat de client 'm meestuurt (architectuurverschil
    met de referentie: dit domein heeft al een graafverbinding, story 037).

Interacties:
  - shared/auth.py: `huidige_gebruiker` (client_id-scoping in de router).
  - shared/tijd.py: `nu()` als vervangbare klok voor
    `aangemaakt`/`bijgewerkt`/beslissing-tijdstippen.
  - shared/validation.py: `GELDIGE_JAS_KLASSEN` voor element-validatie bij PUT/POST (ongeldige
    klasse → overgeslagen resp. 422), `JAS_KLASSE_KLEUREN`/`jas_sorteersleutel` voor de export.
  - db.py: `AsyncEngine` via `get_engine()` naar de store.
  - graphdb.py: `haal_wetsartikel_op` voor zowel `GET .../wetsartikel` als `POST .../export`.
"""
