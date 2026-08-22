# bwb-import

ETL-pipeline die Nederlandse wetgeving uit het **Basiswettenbestand (BWB)** importeert in
**GraphDB** (RDF/SPARQL). Onderdeel van fase 4 (aparte services) — zie
`docs/project/migratie-wetsanalyse.md` en `docs/project/architectuur/adr/0001-multi-service-topologie.md`.

Referentie-architectuur: `wetsanalyse-ai/tools/bwb-import/` (niet 1:1 gekopieerd — eigen
werkwijze-v2-story-cyclus, eigen tests, eigen secrets-conventie per werkwijze-ADR-0006).

## Status

Story 024 (`docs/project/stories/024-bwb-import-setup-en-download.md`): SRU-discovery + download
+ lokale cache. XSD-validatie, parser, RDF-writer en GraphDB-integratie volgen in latere stories.

## Pijplijn (volledig, wordt stapsgewijs uitgebouwd)

```
SRU-discovery -> toestand-XML downloaden -> XSD-validatie -> lxml-parse -> collect -> GraphDB-writer
```

## Lokaal draaien

```bash
cd tools/bwb-import
uv sync
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
```

## Configuratie

| env-var | betekenis | default |
|---|---|---|
| `BWB_DATA_DIR` | lokale cache voor gedownloade XML | `./data` |
| `BWB_SRU_URL` | SRU-zoekdienst-endpoint | `https://zoekservice.overheid.nl/sru/Search` |
| `GRAPHDB_URL` | GraphDB-endpoint | `http://graphdb:7200` |
| `GRAPHDB_REPOSITORY` | GraphDB-repository | `inning` |
| `GRAPHDB_USER` | GraphDB-service-account | — |
| `GRAPHDB_PASSWORD_FILE` | pad naar een bestand met het GraphDB-wachtwoord (werkwijze-ADR-0006 — geen platte env-var-waarde) | — |

Zie `deploy/graphdb/README.md` voor hoe de GraphDB-stack lokaal opstart.
