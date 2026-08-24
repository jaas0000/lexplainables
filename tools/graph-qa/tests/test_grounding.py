"""Grounding-/verificatie van het antwoord tegen de tool-executietrace.

Poort van `wetsanalyse-ai/tools/graph-qa/tests/test_grounding.py`, getrimd (werkwijze-story 044).
"""

from __future__ import annotations

from agent.grounding import check_grounding, curate_sources, komt_letterlijk_voor
from agent.models import Source


def test_komt_letterlijk_voor_is_witruimte_tolerant() -> None:
    corpus = "Deze  wet\nverstaat onder belastingschuldige: degene die belasting is verschuldigd."
    assert komt_letterlijk_voor(corpus, "wet verstaat onder belastingschuldige")
    assert not komt_letterlijk_voor(corpus, "een tekst die er niet in staat")


def test_gegrond_bij_kloppende_vindplaats_en_citaat() -> None:
    trace = [("get_lid", '<urn:bwb:BWBR0004770:artikel:2:lid:1> "belastingschuldige degene die"')]
    antwoord = 'Zie <urn:bwb:BWBR0004770:artikel:2:lid:1>: "belastingschuldige degene die".'
    report = check_grounding(antwoord, trace)
    assert report.niveau == "gegrond"
    assert report.grounded is True
    assert report.unsupported == []
    assert report.niet_letterlijk == []


def test_ongegrond_bij_verzonnen_vindplaats() -> None:
    trace = [("get_lid", "geen enkele BWB-id hierin")]
    antwoord = "Zie <urn:bwb:BWBR9999999:artikel:1>."
    report = check_grounding(antwoord, trace)
    assert report.niveau == "ongegrond"
    assert report.grounded is False
    assert "urn:bwb:BWBR9999999:artikel:1" in report.unsupported


def test_ongegrond_bij_niet_letterlijk_citaat() -> None:
    trace = [("get_lid", "de daadwerkelijke brontekst van dit artikellid")]
    antwoord = 'De tekst zegt: "een compleet ander citaat van vijf woorden".'
    report = check_grounding(antwoord, trace)
    assert report.niveau == "ongegrond"
    assert len(report.niet_letterlijk) == 1


def test_onbepaald_zonder_vindplaats_of_citaat() -> None:
    trace = [("get_lid", "wat brontekst")]
    antwoord = "Dit onderwerp wordt geregeld in artikel 2 lid 1, kort samengevat."
    report = check_grounding(antwoord, trace)
    assert report.niveau == "onbepaald"


def test_korte_quote_onder_minimumlengte_wordt_niet_getoetst() -> None:
    # "belastingschuldige" alleen is een begrip/label, geen citaat van een passage (< 5 woorden).
    trace = [("get_lid", "iets heel anders")]
    antwoord = 'De term "belastingschuldige" komt hier voor.'
    report = check_grounding(antwoord, trace)
    assert report.niveau == "onbepaald"


def test_curate_sources_filtert_op_genoemde_regelingen() -> None:
    sources = [
        Source(label="a", uri="urn:bwb:BWBR0004770:artikel:2"),
        Source(label="b", uri="urn:bwb:BWBR0019242:artikel:1"),
    ]
    antwoord = "Zie <urn:bwb:BWBR0004770:artikel:2>."
    kept = curate_sources(sources, antwoord)
    assert len(kept) == 1
    assert kept[0].uri == "urn:bwb:BWBR0004770:artikel:2"


def test_curate_sources_valt_terug_op_volledige_lijst_zonder_bwb_id_in_antwoord() -> None:
    sources = [Source(label="a", uri="urn:bwb:BWBR0004770:artikel:2")]
    kept = curate_sources(sources, "Geen enkele regeling hier genoemd.")
    assert kept == sources
