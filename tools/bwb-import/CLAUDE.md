# CLAUDE.md — tools/bwb-import

Werkgids bij het aanpassen van deze service. Het *wat* en *hoe start ik het* staat in
`README.md`; dit bestand is voor architectuurbeslissingen die je niet mag breken.

## Wat dit is

ETL-pipeline: BWB (Basiswettenbestand) → GraphDB-kennisgraaf. Losse Python-service
(`tools/bwb-import/`), eigen `pyproject.toml`/`uv`/tests — geen gedeelde dependency met `api`.

## Architectuurbeslissingen

- **Geen SQL-schema, dus geen Alembic.** Dit domein schrijft RDF naar GraphDB; de
  "schemabeslissing" is de RDF-ontologie in code (komt in een latere story), niet een
  migratiereeks. Zie `stack-profiel.md` §Migraties.
- **Secrets volgen werkwijze-ADR-0006**: `GRAPHDB_PASSWORD_FILE` wijst naar een bestand, nooit
  een platte env-var-waarde. Dit wijkt bewust af van de referentie-app (`wetsanalyse-ai`), die
  `GRAPHDB_PASSWORD` rechtstreeks als env-var leest.
- **DI voor netwerkcode**: `BwbDownloader` accepteert een `requests.Session` — tests injecteren
  een fake, geen echt netwerkverkeer. Zelfde patroon geldt voor de nog te bouwen GraphDB-writer.
- **Brongetrouwheid**: SRU-discovery zonder resultaten of een lege/onleesbare respons is een
  `DownloadError`, nooit een stille lege lijst — doorgaan met "niets gevonden" alsof dat een
  geldig antwoord is, is verboden (zelfde principe als de wetsanalyse-skill elders in dit
  werkspace).

## Tests

```bash
cd tools/bwb-import && uv run pytest -q
```

Geen `integration`-marker/echte-GraphDB-tests in deze story — komt zodra de GraphDB-writer
gebouwd wordt (tegen de lokale stack in `deploy/graphdb/`, niet tegen een mock).

## Codestandaard

`ruff` (`select = ["E", "F", "I", "UP", "B", "SIM"]`, lijnlengte 100) — zelfde conventie als de
referentie-app en als `api/` in dit project.
