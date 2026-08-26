"""Gedeelde JAS-klassen-constante (feature-bouwen regel 8: tweede onafhankelijke gebruiker).

`GELDIGE_JAS_KLASSEN` stond eerder uitsluitend in `engine/validation.py` (één gebruiker:
de LLM-orkestratie). Nu annotatie ook JAS-klassen valideert, is dit de tweede onafhankelijke
gebruiker — geen duidelijke eigenaar, vandaar naar `shared/` verplaatst (zelfde redenering als
`shared/tijd.py`). `engine/validation.py` importeert nu van hier.

`JAS_KLASSEN_VOLGORDE`/`JAS_KLASSE_KLEUREN`/`JAS_TEKSTKLEUR`/`jas_sorteersleutel` zijn 1:1
overgenomen uit wetsanalyse-ai's `.claude/skills/wetsanalyse/scripts/validate_analyse.py` (de
canonieke bron voor de JAS-labelkleuren, per pixel gesampled uit de officiële JAS-tabel) — nodig
voor de PDF-export in `annotatie/export.py`. Bewust hier neergezet i.p.v. de hele skill te
kopiëren: deze module is de enige runtime-gebruiker in lexplainables (de skill zelf wordt hier
niet als Claude-skill gebruikt, zie `docs/project/migratie-wetsanalyse.md`).
"""

from __future__ import annotations

# De 13 JAS-klassen uit jas-klassen-referentie.md (enige toegestane waarden).
GELDIGE_JAS_KLASSEN: frozenset[str] = frozenset(
    {
        "Rechtssubject",
        "Rechtsobject",
        "Rechtsbetrekking",
        "Rechtsfeit",
        "Voorwaarde",
        "Afleidingsregel",
        "Variabele en variabelewaarde",
        "Parameter en parameterwaarde",
        "Operator",
        "Tijdsaanduiding",
        "Plaatsaanduiding",
        "Delegatiebevoegdheid en delegatie-invulling",
        "Brondefinitie",
    }
)

# Canonieke weergave-volgorde van de dertien JAS-klassen (docs/wetsanalyse/wa-table.png). Alle
# resultaatweergaves (PDF-export, frontend) sorteren hierop.
JAS_KLASSEN_VOLGORDE: tuple[str, ...] = (
    "Rechtssubject",
    "Rechtsobject",
    "Rechtsbetrekking",
    "Rechtsfeit",
    "Voorwaarde",
    "Afleidingsregel",
    "Variabele en variabelewaarde",
    "Parameter en parameterwaarde",
    "Operator",
    "Tijdsaanduiding",
    "Plaatsaanduiding",
    "Delegatiebevoegdheid en delegatie-invulling",
    "Brondefinitie",
)


def jas_sorteersleutel(klasse: str) -> int:
    """Sorteersleutel voor presentatie: klasse-index in de wa-table-volgorde; onbekende klassen
    achteraan. Gebruik met een stabiele sort zodat de onderlinge (document)volgorde binnen een
    klasse behouden blijft."""
    try:
        return JAS_KLASSEN_VOLGORDE.index(klasse)
    except ValueError:
        return len(JAS_KLASSEN_VOLGORDE)


# De labelkleuren per JAS-klasse uit de officiële JAS-tabel, per pixel gesampled: (achtergrond,
# rand). De rand is dezelfde kleur ~22% donkerder; de tekst is altijd JAS_TEKSTKLEUR (≥ 5,4:1 op
# elke tint). Samengevoegde klassen nemen de hoofdkleur uit de tabel (Variabele / Parameter /
# Delegatiebevoegdheid).
JAS_KLASSE_KLEUREN: dict[str, tuple[str, str]] = {
    "Rechtssubject": ("#d8eaf7", "#a8b6c0"),
    "Rechtsobject": ("#b2c3e3", "#8a98b1"),
    "Rechtsbetrekking": ("#90a2d0", "#707ea2"),
    "Rechtsfeit": ("#bad8f1", "#91a8bb"),
    "Voorwaarde": ("#b7d8cd", "#8ea89f"),
    "Afleidingsregel": ("#d47479", "#a55a5e"),
    "Variabele en variabelewaarde": ("#f5dc5e", "#bfab49"),
    "Parameter en parameterwaarde": ("#e6b8bb", "#b38f91"),
    "Operator": ("#d7e8e2", "#a7b4b0"),
    "Tijdsaanduiding": ("#cbb8d6", "#9e8fa6"),
    "Plaatsaanduiding": ("#e6d3e5", "#b3a4b2"),
    "Delegatiebevoegdheid en delegatie-invulling": ("#b0b1b2", "#898a8a"),
    "Brondefinitie": ("#edefef", "#b8baba"),
}

JAS_TEKSTKLEUR = "#1A1A1A"
