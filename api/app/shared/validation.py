"""Gedeelde JAS-klassen-constante (feature-bouwen regel 8: tweede onafhankelijke gebruiker).

`GELDIGE_JAS_KLASSEN` stond eerder uitsluitend in `engine/validation.py` (één gebruiker:
de LLM-orkestratie). Nu annotatie ook JAS-klassen valideert, is dit de tweede onafhankelijke
gebruiker — geen duidelijke eigenaar, vandaar naar `shared/` verplaatst (zelfde redenering als
`shared/tijd.py`). `engine/validation.py` importeert nu van hier.
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
