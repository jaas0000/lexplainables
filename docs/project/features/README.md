# docs/project/features/

Deze map wordt **automatisch gegenereerd** door
[`scripts/docs/genereer-feature-docs.py`](../../../scripts/docs/genereer-feature-docs.py) uit de
`__init__.py`-docstring en de code van elke feature onder `api/app/features/`.

**Niet handmatig bewerken.** Wijzigingen worden bij de volgende `generate` overschreven, en
`feature-docs-ci.yml` faalt sowieso op elke drift tussen deze map en de gegenereerde uitvoer.

## Iets veranderen

- **Intentie** (Wat/Waarom/Grens/Beslissingen/Interacties) → bewerk de module-docstring in
  `api/app/features/<naam>/__init__.py`.
- **Structuur** (endpoints, tabellen, store-interface, getest gedrag) → bewerk de code zelf;
  de doc volgt automatisch.
- Regenereer met `python scripts/docs/genereer-feature-docs.py generate [<naam>]`.

Zie de [`feature-docs`-skill](../../../.claude/skills/feature-docs/SKILL.md) voor de volledige
regels en het verificatie-principe achter deze aanpak.
