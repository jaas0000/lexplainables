"""`artikel_corpus`: gestructureerde artikeltekst uit de graaf — numerieke lid-sortering,
lid-filter, ongeldige vindplaats, bepaling-fallback voor decimale nummers.

Eigen tests (niet geport van de referentie se `tests/test_artikel.py` — niet gelezen), tegen
`agent/artikel.py`, dat zelf wél 1:1 geport is minus `haal_artikel_sync` (werkwijze-story 047).
"""

from __future__ import annotations

import pytest

from agent.artikel import OngeldigeVindplaats, artikel_corpus
from tests.fakes import FakeGraph


def _get_artikel_tsv(leden: list[tuple[str, str]]) -> str:
    header = "?tekst\t?jci\t?lid\t?lidnummer\t?lidtekst\t?onderdeel\t?onderdeeltekst"
    rijen = [f'\t\t\t"{nr}"\t"{tekst}"@nl\t\t' for nr, tekst in leden]
    return "\n".join([header, *rijen])


def test_leden_worden_numeriek_gesorteerd_niet_lexicaal() -> None:
    tsv = _get_artikel_tsv([("10", "tiende"), ("1", "eerste"), ("2", "tweede")])
    graph = FakeGraph(result=tsv)

    corpus = artikel_corpus("BWBR0004770", "2", graph)

    assert corpus.index("1. eerste") < corpus.index("2. tweede") < corpus.index("10. tiende")


def test_lid_filter_beperkt_tot_dat_ene_lid() -> None:
    tsv = _get_artikel_tsv([("1", "eerste"), ("2", "tweede")])
    graph = FakeGraph(result=tsv)

    corpus = artikel_corpus("BWBR0004770", "2", graph, lid="2")

    assert "tweede" in corpus
    assert "eerste" not in corpus


def test_lid_filter_tolereert_voorloopnullen() -> None:
    tsv = _get_artikel_tsv([("1", "eerste"), ("2", "tweede")])
    graph = FakeGraph(result=tsv)

    corpus = artikel_corpus("BWBR0004770", "2", graph, lid="02")

    assert corpus.strip() == "2. tweede"


def test_ongeldige_vindplaats_raist_voor_er_iets_gevraagd_wordt() -> None:
    graph = FakeGraph(result="")

    with pytest.raises(OngeldigeVindplaats):
        artikel_corpus("niet-een-bwb-id", "2", graph)
    assert graph.queries == []  # de check gebeurt vóór de eerste SPARQL


def test_ongeldig_artikelnummer_raist() -> None:
    graph = FakeGraph(result="")

    with pytest.raises(OngeldigeVindplaats):
        artikel_corpus("BWBR0004770", "!!!", graph)


def test_bepaling_fallback_bij_decimaal_nummer() -> None:
    """Een decimaal nummer ('9.1', circulaires/beleidsregels) faalt op het artikel/lid-IRI-
    patroon en valt terug op get_bepaling."""

    def antwoorden(query: str) -> str:
        if "?onderdelen" in query or "?lidnummer" in query:
            raise AssertionError("get_artikel/get_lid hoort hier niet aangeroepen te worden")
        return '?nummer\t?tekst\t?label\t?jci\n"9.1"\t"bepalingstekst"@nl\t\t'

    graph = FakeGraph(results=antwoorden)

    corpus = artikel_corpus("BWBR0004770", "9.1", graph)

    assert corpus == "bepalingstekst"


def test_geen_leden_maar_wel_artikeltekst_gebruikt_die_als_corpus() -> None:
    header = "?tekst\t?jci\t?lid\t?lidnummer\t?lidtekst\t?onderdeel\t?onderdeeltekst"
    tsv = f'{header}\n"heel artikel"@nl\t\t\t\t\t\t'
    graph = FakeGraph(result=tsv)

    corpus = artikel_corpus("BWBR0004770", "1", graph)

    assert corpus == "heel artikel"
