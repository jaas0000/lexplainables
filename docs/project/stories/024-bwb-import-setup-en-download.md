# Story 024: bwb-import — project-setup + SRU-discovery + download

**Prioriteit:** hoog
**Story points:** 3
**Service:** `tools/bwb-import/` (nieuw)
**Afhankelijkheid:** `deploy/graphdb` (service 1, gemerged in PR #52) — deze story schrijft nog
niet naar GraphDB, maar het project bestaat in dezelfde context.

## Verhaal

Als onderdeel van fase 4 (aparte services, zie `docs/project/migratie-wetsanalyse.md` en
`ai-notes/fase-4-aparte-services-plan.md`) wil ik een `tools/bwb-import`-project met een werkende
eerste stap van de ETL-pijplijn: het ontdekken van beschikbare toestanden (versies) van een
regeling via de SRU-zoekdienst van overheid.nl, en het downloaden + lokaal cachen van de
toestand-XML — zodat latere stories (XSD-validatie, parsen, GraphDB-schrijven) op een werkende
downloadlaag kunnen bouwen.

Referentie-architectuur: `wetsanalyse-ai/tools/bwb-import/app/downloader.py` +
`app/config.py` (niet 1:1 gekopieerd — eigen tests, eigen secrets-conventie per ADR-0006).

## Acceptatiecriteria

- [x] `tools/bwb-import/` is een zelfstandig Python-project (`pyproject.toml`, `uv`), met een
      eigen `CLAUDE.md` (lokale build/test-commando's) en `README.md`.
- [x] `Settings.from_env()` laadt configuratie (SRU-endpoint, data-directory, GraphDB-connectie)
      uit environment-variabelen; GraphDB-wachtwoord volgt ADR-0006 (`*_FILE`-env, niet de
      waarde zelf) — dit wijkt bewust af van de referentie, die de waarde direct als env-var
      leest.
- [x] `BwbDownloader.discover_toestanden(bwb_id)` bevraagt de SRU-zoekdienst
      (`https://zoekservice.overheid.nl/sru/Search`) en geeft een lijst `ToestandRef` terug,
      gesorteerd op geldigheidsstartdatum (oudste eerst).
- [x] `BwbDownloader.latest_toestand(bwb_id)` geeft de meest recente toestand.
- [x] `BwbDownloader.download_toestand(bwb_id, ref?)` downloadt de toestand-XML naar
      `data/<bwb_id>/<bestandsnaam>` en cachet: een tweede aanroep met hetzelfde doelbestand
      doet geen nieuwe HTTP-aanroep.
- [x] `requests.Session` is injecteerbaar (DI) zodat tests geen echt netwerkverkeer doen.
- [x] Ruff-schoon (`select = ["E", "F", "I", "UP", "B", "SIM"]`, lijnlengte 100, zelfde
      conventie als de referentie).
- [x] CI: pytest + ruff draaien op elke push/PR die `tools/bwb-import/**` raakt.

**Buiten scope van deze story** (latere stories): XSD-validatie/schema-fetch, WTI-download,
manifest-download, parser, collect, GraphDB-writer, RDF-ontologie, `main.py`-orkestratie,
FastAPI-service-wrapper (`/health`, `/import`), Dockerfile/image-publish.

## Schemabeslissing

Geen database — dit domein heeft geen eigen SQL-schema (schrijft uiteindelijk RDF naar GraphDB,
zie stack-profiel.md §Migraties). `ToestandRef` is een `dataclass` (niet Pydantic — intern
domeinmodel, geen API-contract dat gegenereerd hoeft te worden):

```python
@dataclass(slots=True)
class ToestandRef:
    bwb_id: str
    locatie_toestand: str
    geldig_vanaf: str | None = None
    geldig_tot: str | None = None
```

(Referentie heeft ook `zicht_vanaf`/`zicht_tot`/`locatie_wti`/`locatie_manifest` — bewust nu
weggelaten, worden toegevoegd in de story die WTI/manifest-download bouwt, om deze story klein
te houden.)

## Edge cases

- Lege of onleesbare SRU-respons → `DownloadError` met duidelijke context (bwb_id).
- Geen toestanden gevonden voor een bwb_id → `DownloadError`, niet een lege lijst (brongetrouwheid:
  stil doorgaan met niets is verboden).
- HTTP-fout of lege body bij download → `DownloadError`.
- Cache-hit (bestand bestaat al en is niet leeg) → geen nieuwe HTTP-aanroep, geen fout.

## Test-plan

- Unit-tests met een gemockte `requests.Session` (`responses`-library of een handgeschreven
  fake) — geen echt netwerkverkeer, geen `integration`-marker nodig voor deze story (die marker
  is gereserveerd voor tests die een echte GraphDB nodig hebben, komt in een latere story).
- Testcases: succesvolle discovery + sortering, lege respons → fout, download + cache-hit op
  tweede aanroep, HTTP-fout bij download.
