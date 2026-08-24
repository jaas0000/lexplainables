"""Bron-provenance uit de tool-executietrace.

Poort van `wetsanalyse-ai/tools/graph-qa/tests/test_provenance.py`, 1:1 (werkwijze-story 044).
"""

from __future__ import annotations

from agent.provenance import citations_in, collect_sources, first_bwb, iter_refs


def test_first_bwb_vindt_bwb_id() -> None:
    assert first_bwb("zie BWBR0004770 art. 2") == "BWBR0004770"
    assert first_bwb("geen vindplaats hier") is None


def test_iter_refs_herkent_iri_jci_en_kale_bwb_id() -> None:
    tekst = (
        "Zie <urn:bwb:BWBR0004770:artikel:2> en jci1.3:c:BWBR0004770&artikel=2, "
        "ook los BWBR0019242 wordt genoemd."
    )
    refs = list(iter_refs(tekst))
    uris = [r[0] for r in refs]
    assert "urn:bwb:BWBR0004770:artikel:2" in uris
    assert any(u.startswith("jci1.3:c:BWBR0004770") for u in uris)
    assert "BWBR0019242" in uris


def test_iter_refs_ontdubbelt_kale_bwb_id_binnen_iri() -> None:
    # BWBR0004770 zit al in de IRI hierboven — de kale losse variant mag niet nog eens verschijnen.
    tekst = "<urn:bwb:BWBR0004770:artikel:2>"
    refs = list(iter_refs(tekst))
    assert len(refs) == 1


def test_citations_in_is_platte_urilijst() -> None:
    tekst = "<urn:bwb:BWBR0004770:artikel:2> en BWBR0019242"
    assert citations_in(tekst) == [
        "urn:bwb:BWBR0004770:artikel:2",
        "BWBR0019242",
    ]


def test_collect_sources_bouwt_ontdubbelde_lijst() -> None:
    entries = [
        ("get_artikel", "<urn:bwb:BWBR0004770:artikel:2> tekst"),
        ("get_lid", "<urn:bwb:BWBR0004770:artikel:2> nogmaals dezelfde bron"),
        ("search_wetgeving", ""),  # lege tool-resultaten leveren niets op
    ]
    sources = collect_sources(entries)
    assert len(sources) == 1
    assert sources[0].uri == "urn:bwb:BWBR0004770:artikel:2"
    assert sources[0].origin_tool == "get_artikel"
