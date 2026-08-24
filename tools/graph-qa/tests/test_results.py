"""`parse_select`: SPARQL Query Results TSV → rijen.

Eigen tests (niet geport van de referentie se `tests/test_results.py` — niet gelezen), tegen
`agent/graph/results.py`, dat zelf wél 1:1 geport is (werkwijze-story 047).
"""

from __future__ import annotations

import json

from agent.graph.results import parse_select


def test_lege_invoer_geeft_lege_lijst() -> None:
    assert parse_select("") == []
    assert parse_select("   ") == []


def test_alleen_header_geeft_lege_lijst() -> None:
    assert parse_select("?tekst\t?jci") == []


def test_parseert_iri_en_literal_met_taal() -> None:
    tsv = '?tekst\t?jci\n"Hallo daar"@nl\t<https://example.org/1>'
    assert parse_select(tsv) == [{"tekst": "Hallo daar", "jci": "https://example.org/1"}]


def test_lege_cel_is_unbound_string() -> None:
    tsv = "?tekst\t?jci\n\t<https://example.org/1>"
    assert parse_select(tsv) == [{"tekst": "", "jci": "https://example.org/1"}]


def test_ontsnapte_tab_en_newline_in_literal() -> None:
    tsv = '?tekst\n"regel een\\nregel twee\\tmet tab"'
    rows = parse_select(tsv)
    assert rows == [{"tekst": "regel een\nregel twee\tmet tab"}]


def test_json_string_omhulde_tsv_wordt_gepeld() -> None:
    """De GraphDB-MCP levert de TSV JSON-string-encoded — precies de vorm die live is
    waargenomen tegen de echte MCP-server."""
    kale_tsv = '?nummer\t?tekst\n"1"\t"Deze wet verstaat onder:"@nl'
    omhuld = json.dumps(kale_tsv)
    assert parse_select(omhuld) == [{"nummer": "1", "tekst": "Deze wet verstaat onder:"}]


def test_meerdere_rijen() -> None:
    tsv = '?nummer\t?tekst\n"1"\t"eerste"@nl\n"2"\t"tweede"@nl'
    assert parse_select(tsv) == [
        {"nummer": "1", "tekst": "eerste"},
        {"nummer": "2", "tekst": "tweede"},
    ]
