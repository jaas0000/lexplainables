"""De specialisten-registry: compleet, en met een veilige terugval bij onbekende namen.

Eigen tests (niet geport van de referentie se `tests/test_specialists.py` — niet gelezen), tegen
`agent/specialists.py`, dat zelf wél 1:1 geport is minus de `retrieval`-specialist (werkwijze-
story 045 §Afwijkingen).
"""

from __future__ import annotations

from agent import specialists


def test_registry_bevat_de_drie_specialisten() -> None:
    assert set(specialists.SPECIALISTS) == {"definitie", "duiding", "algemeen"}


def test_algemeen_heeft_geen_addendum_en_alle_tools() -> None:
    spec = specialists.get("algemeen")
    assert spec.system == ""
    assert spec.tools is None


def test_definitie_en_duiding_hebben_een_beperkte_toolset() -> None:
    definitie = specialists.get("definitie")
    duiding = specialists.get("duiding")
    assert definitie.system != ""
    assert duiding.system != ""
    assert definitie.tools is not None and "resolve_begrip" in definitie.tools
    assert duiding.tools is not None and "get_context" in duiding.tools


def test_get_valt_terug_op_algemeen_bij_onbekend_leeg_of_none() -> None:
    assert specialists.get("bestaat-niet") is specialists.SPECIALISTS["algemeen"]
    assert specialists.get("") is specialists.SPECIALISTS["algemeen"]
    assert specialists.get(None) is specialists.SPECIALISTS["algemeen"]


def test_get_is_hoofdletterongevoelig() -> None:
    assert specialists.get("DEFINITIE") is specialists.SPECIALISTS["definitie"]
