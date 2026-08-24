"""`_verwerk`/`_parse_elementen`: brongetrouwheid, klasse-validatie, ontdubbeling via
`sleutel_van`, id-behoud.

Eigen tests (niet geport van de referentie se `tests/test_annotatie.py` — niet gelezen), tegen
`agent/annotatie.py`, dat zelf wél 1:1 geport is voor de kernfuncties (werkwijze-story 047).
"""

from __future__ import annotations

import json

from agent.annotatie import _parse_elementen, _verwerk

_CORPUS = (
    "1. Degene die aangifte doet, is verplicht de gegevens waarheidsgetrouw te verstrekken.\n\n"
    "2. Bij gebreke daarvan kan de inspecteur een boete opleggen."
)


def test_parse_elementen_volledige_json() -> None:
    tekst = json.dumps(
        {"elementen": [{"klasse": "Rechtssubject", "tekst": "Degene die aangifte doet"}]}
    )
    assert _parse_elementen(tekst) == [
        {"klasse": "Rechtssubject", "tekst": "Degene die aangifte doet"}
    ]


def test_parse_elementen_met_code_fence() -> None:
    tekst = (
        "```json\n"
        + json.dumps({"elementen": [{"klasse": "Rechtsfeit", "tekst": "aangifte doet"}]})
        + "\n```"
    )
    assert _parse_elementen(tekst) == [{"klasse": "Rechtsfeit", "tekst": "aangifte doet"}]


def test_parse_elementen_met_omringende_proza() -> None:
    payload = json.dumps({"elementen": [{"klasse": "Rechtsfeit", "tekst": "aangifte doet"}]})
    tekst = f"Hier is de analyse:\n\n{payload}\n\nDat waren de elementen."
    assert _parse_elementen(tekst) == [{"klasse": "Rechtsfeit", "tekst": "aangifte doet"}]


def test_parse_elementen_salvaget_afgekapte_respons() -> None:
    # Twee complete elementen, dan een afgekapt derde object (geen sluit-accolade) — de fast-path
    # faalt (ongeldige JSON), de salvage-weg levert de twee complete elementen.
    tekst = (
        '{"elementen": ['
        '{"klasse": "Rechtssubject", "tekst": "Degene die aangifte doet"}, '
        '{"klasse": "Rechtsfeit", "tekst": "aangifte doet"}, '
        '{"klasse": "Voorwaarde", "tekst": "bij gebr'
    )
    gered = _parse_elementen(tekst)
    assert {"klasse": "Rechtssubject", "tekst": "Degene die aangifte doet"} in gered
    assert {"klasse": "Rechtsfeit", "tekst": "aangifte doet"} in gered
    assert len(gered) == 2


def test_parse_elementen_verwart_genest_alternatief_niet_met_een_element() -> None:
    tekst = json.dumps(
        {
            "elementen": [
                {
                    "klasse": "Rechtsfeit",
                    "tekst": "aangifte doet",
                    "alternatieven": [{"klasse": "Rechtssubject", "motivatie": "twijfel"}],
                }
            ]
        }
    )
    gered = _parse_elementen(tekst)
    assert len(gered) == 1
    assert gered[0]["klasse"] == "Rechtsfeit"


def test_verwerk_grondt_geldig_fragment() -> None:
    tekst = json.dumps(
        {
            "elementen": [
                {"klasse": "Rechtssubject", "tekst": "Degene die aangifte doet", "lid": "1"}
            ]
        }
    )
    voorstellen, verworpen = _verwerk(tekst, _CORPUS, "BWBR0004770", "10")

    assert verworpen == []
    assert len(voorstellen) == 1
    v = voorstellen[0]
    assert v.grounded is True
    assert v.klasse == "Rechtssubject"
    assert v.vindplaats == "BWBR0004770 art. 10 lid 1"
    assert len(v.id) == 12  # toegekend, niet leeg


def test_verwerk_behoudt_aangeboden_id() -> None:
    tekst = json.dumps(
        {
            "elementen": [
                {
                    "id": "bestaand-id12",
                    "klasse": "Rechtssubject",
                    "tekst": "Degene die aangifte doet",
                }
            ]
        }
    )
    voorstellen, _ = _verwerk(tekst, _CORPUS, "BWBR0004770", "10")

    assert voorstellen[0].id == "bestaand-id12"


def test_verwerk_verwerpt_ongeldige_klasse() -> None:
    tekst = json.dumps(
        {"elementen": [{"klasse": "Bestaat-Niet", "tekst": "Degene die aangifte doet"}]}
    )
    voorstellen, verworpen = _verwerk(tekst, _CORPUS, "BWBR0004770", "10")

    assert voorstellen == []
    assert len(verworpen) == 1
    assert verworpen[0].reden == "ongeldige_klasse"


def test_verwerk_verwerpt_niet_letterlijk_fragment() -> None:
    tekst = json.dumps(
        {"elementen": [{"klasse": "Rechtssubject", "tekst": "een verzonnen fragment"}]}
    )
    voorstellen, verworpen = _verwerk(tekst, _CORPUS, "BWBR0004770", "10")

    assert voorstellen == []
    assert len(verworpen) == 1
    assert verworpen[0].reden == "niet_letterlijk"


def test_verwerk_ontdubbelt_identiek_fragment_binnen_een_ronde() -> None:
    tekst = json.dumps(
        {
            "elementen": [
                {"klasse": "Rechtssubject", "tekst": "Degene die aangifte doet", "lid": "1"},
                {"klasse": "Rechtssubject", "tekst": "Degene die aangifte doet", "lid": "1"},
            ]
        }
    )
    voorstellen, _ = _verwerk(tekst, _CORPUS, "BWBR0004770", "10")

    assert len(voorstellen) == 1


def test_verwerk_zelfde_fragment_andere_klasse_wordt_alternatief() -> None:
    tekst = json.dumps(
        {
            "elementen": [
                {"klasse": "Rechtssubject", "tekst": "Degene die aangifte doet", "lid": "1"},
                {
                    "klasse": "Rechtsobject",
                    "tekst": "Degene die aangifte doet",
                    "lid": "1",
                    "toelichting": "zou ook object kunnen zijn",
                },
            ]
        }
    )
    voorstellen, _ = _verwerk(tekst, _CORPUS, "BWBR0004770", "10")

    assert len(voorstellen) == 1
    assert voorstellen[0].klasse == "Rechtssubject"
    assert len(voorstellen[0].alternatieven) == 1
    assert voorstellen[0].alternatieven[0].klasse == "Rechtsobject"


def test_verwerk_scope_lid_overschrijft_het_modelveld() -> None:
    tekst = json.dumps(
        {
            "elementen": [
                {"klasse": "Rechtssubject", "tekst": "Degene die aangifte doet", "lid": "1"}
            ]
        }
    )
    voorstellen, _ = _verwerk(tekst, _CORPUS, "BWBR0004770", "10", scope_lid="1")

    assert voorstellen[0].lid == "1"
    assert voorstellen[0].vindplaats == "BWBR0004770 art. 10 lid 1"
