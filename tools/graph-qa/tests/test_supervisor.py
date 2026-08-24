"""`parse_supervisor`: het tweeregelige SPECIALIST/PLAN-antwoordformaat.

Eigen tests (niet geport van de referentie se `tests/test_supervisor.py` — niet gelezen), tegen
`agent/supervisor.py`, dat zelf wél geport is (ingekort, werkwijze-story 045 §Afwijkingen).
"""

from __future__ import annotations

from agent.supervisor import parse_supervisor


def test_herkent_elk_van_de_drie_specialisten() -> None:
    for naam in ("definitie", "duiding", "algemeen"):
        specialist, plan, afwijzen = parse_supervisor(f"SPECIALIST: {naam}\nPLAN: een korte aanpak")
        assert specialist == naam
        assert plan == "een korte aanpak"
        assert afwijzen is False


def test_hoofdletterongevoelig_en_witruimte_tolerant() -> None:
    specialist, _, _ = parse_supervisor("  specialist:   Definitie  \nplan: iets")
    assert specialist == "definitie"


def test_onbekende_specialist_valt_terug_op_algemeen() -> None:
    specialist, _, _ = parse_supervisor("SPECIALIST: verzonnen\nPLAN: iets")
    assert specialist == "algemeen"


def test_afwijzen_gedetecteerd_in_plan_regel() -> None:
    _, plan, afwijzen = parse_supervisor("SPECIALIST: algemeen\nPLAN: AFWIJZEN")
    assert afwijzen is True
    assert plan == "AFWIJZEN"


def test_geen_afwijzen_bij_gewoon_plan() -> None:
    _, _, afwijzen = parse_supervisor("SPECIALIST: duiding\nPLAN: leg de samenhang uit")
    assert afwijzen is False


def test_ontbrekende_plan_regel_valt_terug_op_de_ruwe_tekst() -> None:
    specialist, plan, afwijzen = parse_supervisor("gewoon wat proza zonder het gevraagde formaat")
    assert specialist == "algemeen"
    assert plan == "gewoon wat proza zonder het gevraagde formaat"
    assert afwijzen is False
