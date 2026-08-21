---
name: feature-docs
description: >-
  Genereert een leesbare, altijd-actuele feature-doc uit de code zelf: leest de gestructureerde
  module-docstring in `features/<naam>/__init__.py`, extraheert endpoints uit `router.py`,
  Pydantic-klasses en tabellen uit `models.py`, de Store-interface uit `store.py` en de
  test-namen uit `tests/`, en schrijft dat samen naar `docs/project/features/<naam>.md`. Bedoeld als
  vervanging van "stories als levende documentatie" — stories blijven planningsartefact tot
  merge, deze skill produceert de doorlopende referentie. Gebruik bij "documenteer feature X",
  "werk de feature-docs bij", of automatisch aan het eind van `feature-bouwen` (regel 10, na
  Simplify). Niet voor project-brede overzichten (zie `architectuur-audit`) en niet voor
  cross-service flows (die horen in `docs/flows/<flow>.md`, met de hand geschreven).
---

# feature-docs — code is de bron, doc is de output

**Trigger:** een feature is nieuw gebouwd, gewijzigd, of iemand vraagt "werk de feature-docs
bij" / "documenteer feature X".

## Regels

1. **Elke feature-map heeft een gestructureerde module-docstring in `__init__.py`.** Vaste
   secties, in deze volgorde:

   ```python
   """<Feature-naam>.

   Wat: één zin — het domein van deze feature.
   Waarom: één zin — waarom bestaat dit apart, niet als deel van een andere feature.
   Grens: wat hoort er niet bij (en waar dan wél); welke andere feature raakt dit.

   Tabellen:
     - <tabel>: één zin over de rol.

   Beslissingen:
     - <ADR-nummer of story-sectie>: kort waarom.

   Interacties:
     - <andere feature/shared-module>: hoe en wanneer.
   """
   ```

   `__init__.py` mag verder leeg zijn — de docstring is de inhoud. Ontbreekt de docstring, of
   ontbreekt een verplichte sectie, dan is de feature niet af (net zoals ontbrekende tests dat
   maakt): `feature-bouwen` regel 10 en `code-review` regel 1 controleren dit.

2. **De skill draait een deterministisch script op de repo-root.** Het script leeft onder
   `<repo>/scripts/docs/genereer-feature-docs.py` — projectinfrastructuur onder een
   docs-groep, geen onderdeel van een service (het leest code uit één of meer services en
   schrijft naar `docs/project/features/` op repo-niveau). Twee modi:

   ```bash
   # Regenereer één feature of alle features:
   python scripts/docs/genereer-feature-docs.py generate [<naam>]

   # CI-modus: faal op drift én op ontbrekende docstring:
   python scripts/docs/genereer-feature-docs.py check
   ```

   Bronnen, in volgorde:

   | Bron | Wat eruit halen |
   |---|---|
   | `<service>/app/features/<naam>/__init__.py` | Module-docstring — Wat/Waarom/Grens/Tabellen/Beslissingen/Interacties |
   | `<service>/app/features/<naam>/models.py` | SQLAlchemy `Table(...)`-namen + kolommen; Pydantic `class ... (BaseModel)`-namen met korte docstring |
   | `<service>/app/features/<naam>/router.py` | `@router.<verb>("...")`-decorators, response-model, auth-dependency uit signatuur |
   | `<service>/app/features/<naam>/store.py` | De `Protocol`-klasse (interface) — methodenaam + signatuur, één-regel-docstring |
   | `<service>/app/features/<naam>/tests/test_*.py` | Test-namen als `def test_<naam>` — namen zijn gedrag-beschrijvingen (werkwijze-ADR-0006), dus letterlijk overnemen |

   Dat het script deterministisch is (dezelfde invoer → dezelfde uitvoer) is een expliciete
   eis van het verificatie-principe: zonder dat kan `check` geen betekenisvolle diff geven en
   verliest been 1 (CI) zijn vangnetfunctie.

3. **Doel-formaat: `docs/project/features/<naam>.md`.** Vaste secties, in deze volgorde:

   ```markdown
   # <Feature-naam>

   <Wat-zin uit de docstring>

   **Waarom apart:** <Waarom-zin>
   **Grens:** <Grens-zin>

   ## Datamodel

   ### <tabel-naam>
   <één-zin-rol uit docstring §Tabellen>

   | kolom | type | eigenschappen |
   |---|---|---|
   | ... |

   ## API

   | Methode | Pad | Auth | Response |
   |---|---|---|---|
   | POST | /feedback | user | FeedbackBevestigd |
   | ... |

   ## Store-interface

   ```python
   class FeedbackStore(Protocol):
       async def dien_in(...) -> FeedbackRead: ...
   ```

   ## Interacties

   - <andere feature>: <hoe/wanneer>

   ## Getest gedrag

   - <test-naam als leesbare zin>
   - ...

   ## Beslissingen

   - [ADR-0007](../architectuur/adr/0007-store-abstractie.md): kort waarom.
   ```

4. **CI-check dwingt afwezigheid van drift én aanwezigheid van docstring af.** Eén
   project-brede workflow (in lexplainables: `.github/workflows/feature-docs-ci.yml`) draait
   `python scripts/docs/genereer-feature-docs.py check` bij elke wijziging in `api/app/features/`,
   `docs/project/features/` of het script zelf. Geen service-CI — dit is projectinfrastructuur, niet
   iets van één service. De check faalt op:
   - een feature zonder module-docstring in `__init__.py`, of met ontbrekende verplichte sectie
   - een `docs/project/features/<naam>.md` dat niet overeenkomt met de gegenereerde uitvoer

   Dit is been 1 van het Verificatie-principe (zie `docs/project/werkwijze/CLAUDE.md` §Verificatie-principe).
   Zonder deze CI-check drijft de doc af en verliest zijn waarde; dat maakt de check niet
   optioneel.

5. **Wat NIET in `docs/project/features/<naam>.md` hoort.**
   - Cross-service flows (auth-flow, annotatie-flow, LLM-call-flow) → `docs/flows/<flow>.md`,
     met de hand.
   - Waarom-vragen over de architectuur → een ADR onder `docs/project/architectuur/adr/`.
   - Bouwbeslissingen ten tijde van een specifieke story → de story-doc zelf, blijft bevroren
     op mergemoment.
   - Snapshots van implementatie (functiehandtekening, private methodes) → daarvoor is de code
     zelf.

## Waar dit inhaakt op de rest van de werkwijze

- `feature-bouwen` regel 10 (nieuw, toe te voegen): "Voeg de module-docstring in `__init__.py`
  toe volgens `feature-docs` regel 1; draai `feature-docs` om `docs/project/features/<naam>.md` te
  genereren; commit beide bestanden mee." Zonder dit haal je de check in punt 4 niet.
- `code-review` regel 1: controleert of de docstring en gegenereerde doc bij deze PR
  meegecommit zijn en of de gegenereerde doc actueel is (deze check dubbelt met CI — bewust,
  been 1 én been 2).
- `pr-triage`: geen aparte regel, want CI dwingt het af (been 1).

## Wat het niet oplost

Deze skill produceert **structurele** documentatie ("wat is er, hoe roep je het aan, welke
tabellen heeft het, welk gedrag is getest"). Het produceert géén **intentionele** documentatie
("waarom bestaat dit"). Die staat in de docstring §Waarom/Beslissingen en in ADR's — de skill
kopieert die alleen door, redeneert er niet over.

Bij een feature die semantisch niet klopt (verkeerde grens, verkeerde eigendomsverdeling van
data) zal een gegenereerde doc *dat* niet vinden — dat is `architectuur-audit`'s taak.
