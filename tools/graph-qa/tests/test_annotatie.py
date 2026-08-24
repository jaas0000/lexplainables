"""`_verwerk`/`_parse_elementen`: brongetrouwheid, klasse-validatie, ontdubbeling via
`sleutel_van`, id-behoud. `_verwerk_critic`/`demp_zelfweerspreking`/`vervang_ids_door_citaat`:
Critic-JSON-parsing, normalisatie, zelfweerspreking-demping, id-naar-citaat.

Eigen tests (niet geport van de referentie se `tests/test_annotatie.py` — niet gelezen), tegen
`agent/annotatie.py`, dat zelf wél 1:1 geport is voor de kernfuncties (werkwijze-stories 047-048).
"""

from __future__ import annotations

import json

from agent.annotatie import (
    _parse_elementen,
    _verwerk,
    _verwerk_critic,
    demp_zelfweerspreking,
    openstaand_voorstel,
    pas_critic_toe,
    vervang_ids_door_citaat,
)

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


# ---- _verwerk_critic (story 048) -------------------------------------------------------------


def test_verwerk_critic_koppelt_op_id() -> None:
    tekst = json.dumps(
        {
            "oordelen": [
                {"id": "abc123456789", "aandacht": "groen", "motivatie": "prima", "actie": "behoud"}
            ],
            "ontbrekend": [],
        }
    )
    oordelen, ontbrekend = _verwerk_critic(tekst, ["abc123456789"])

    assert ontbrekend == []
    assert oordelen["abc123456789"].aandacht == "groen"
    assert oordelen["abc123456789"].actie == "behoud"


def test_verwerk_critic_index_terugval_bij_ontbrekend_id() -> None:
    tekst = json.dumps({"oordelen": [{"index": 0, "aandacht": "geel", "actie": "behoud"}]})
    oordelen, _ = _verwerk_critic(tekst, ["idA"])

    assert oordelen["idA"].aandacht == "geel"


def test_verwerk_critic_onbekende_aandacht_genegeerd() -> None:
    tekst = json.dumps({"oordelen": [{"id": "idA", "aandacht": "blauw", "actie": "behoud"}]})
    oordelen, _ = _verwerk_critic(tekst, ["idA"])

    assert oordelen == {}


def test_verwerk_critic_verwijder_zonder_rood_degradeert_naar_vervang() -> None:
    tekst = json.dumps(
        {
            "oordelen": [
                {
                    "id": "idA",
                    "aandacht": "geel",
                    "actie": "verwijder",
                    "voorstel_klasse": "Rechtsobject",
                }
            ]
        }
    )
    oordelen, _ = _verwerk_critic(tekst, ["idA"])

    assert oordelen["idA"].actie == "vervang"


def test_verwerk_critic_vervang_zonder_voorstel_degradeert_naar_behoud() -> None:
    tekst = json.dumps({"oordelen": [{"id": "idA", "aandacht": "rood", "actie": "vervang"}]})
    oordelen, _ = _verwerk_critic(tekst, ["idA"])

    assert oordelen["idA"].actie == "behoud"


def test_verwerk_critic_ongeldige_voorstel_klasse_wordt_leeggemaakt() -> None:
    tekst = json.dumps(
        {
            "oordelen": [
                {
                    "id": "idA",
                    "aandacht": "geel",
                    "actie": "vervang",
                    "voorstel_klasse": "Onzin",
                    "voorstel_tekst": "iets",
                }
            ]
        }
    )
    oordelen, _ = _verwerk_critic(tekst, ["idA"])

    assert oordelen["idA"].voorstel_klasse == ""
    assert oordelen["idA"].voorstel_tekst == "iets"
    assert oordelen["idA"].actie == "vervang"  # voorstel_tekst alleen is genoeg


def test_verwerk_critic_ontbrekend_geldige_klasse_behouden_ongeldige_genegeerd() -> None:
    tekst = json.dumps(
        {
            "oordelen": [],
            "ontbrekend": [
                {"klasse": "Rechtssubject", "reden": "mist", "tekst": "iets"},
                {"klasse": "Onzin", "reden": "x"},
            ],
        }
    )
    _, ontbrekend = _verwerk_critic(tekst, [])

    assert len(ontbrekend) == 1
    assert ontbrekend[0].klasse == "Rechtssubject"


# ---- demp_zelfweerspreking (story 048) -------------------------------------------------------


def test_demp_zelfweerspreking_dempt_teruggedraaide_eigen_correctie() -> None:
    voorstel = {
        "klasse": "Rechtsbetrekking",  # het resultaat van de al toegepaste ronde-1-correctie
        "alternatieven": [],
        "critic_rondes": [
            {
                "ronde": 1,
                "aandacht": "rood",
                "actie": "vervang",
                "voorstel_klasse": "Rechtsbetrekking",
                "toegepast": True,
            },
            {
                "ronde": 2,
                "aandacht": "rood",
                "actie": "vervang",
                "voorstel_klasse": "Rechtsobject",  # draait de eigen correctie terug
                "motivatie": "toch geen Rechtsbetrekking",
                "toegepast": False,
            },
        ],
    }
    gedempt = demp_zelfweerspreking([voorstel])

    assert gedempt == 1
    assert voorstel["aandacht"] == "geel"
    assert voorstel["critic_rondes"][-1]["aandacht"] == "geel"
    assert any(a["klasse"] == "Rechtsobject" for a in voorstel["alternatieven"])


def test_demp_zelfweerspreking_laat_eerste_ronde_ongemoeid() -> None:
    voorstel = {
        "klasse": "Rechtsobject",
        "alternatieven": [],
        "critic_rondes": [
            {
                "ronde": 1,
                "aandacht": "rood",
                "voorstel_klasse": "Rechtsbetrekking",
                "toegepast": False,
            }
        ],
    }
    gedempt = demp_zelfweerspreking([voorstel])

    assert gedempt == 0
    assert "aandacht" not in voorstel or voorstel.get("aandacht") != "geel"


def test_demp_zelfweerspreking_laat_ongerelateerd_oordeel_ongemoeid() -> None:
    voorstel = {
        "klasse": "Rechtsbetrekking",
        "alternatieven": [],
        "critic_rondes": [
            {
                "ronde": 1,
                "aandacht": "rood",
                "voorstel_klasse": "Rechtsbetrekking",
                "toegepast": True,
            },
            {
                "ronde": 2,
                "aandacht": "geel",  # geen rood eindoordeel — niets om te dempen
                "voorstel_klasse": "Rechtsobject",
                "toegepast": False,
            },
        ],
    }
    gedempt = demp_zelfweerspreking([voorstel])

    assert gedempt == 0


# ---- vervang_ids_door_citaat (story 048) -----------------------------------------------------


def test_vervang_ids_door_citaat_bekend_id() -> None:
    voorstellen = [{"id": "abc123456789", "tekst": "een kort fragment"}]
    resultaat = vervang_ids_door_citaat("zie [abc123456789] voor context", voorstellen)

    assert "abc123456789" not in resultaat
    assert "'een kort fragment'" in resultaat


def test_vervang_ids_door_citaat_onbekend_id() -> None:
    voorstellen = [{"id": "abc123456789", "tekst": "iets"}]
    resultaat = vervang_ids_door_citaat("zie [999999999999] voor context", voorstellen)

    assert "een ander element" in resultaat


def test_vervang_ids_door_citaat_kapt_lange_tekst_af() -> None:
    lange_tekst = "x" * 60
    voorstellen = [{"id": "abc123456789", "tekst": lange_tekst}]
    resultaat = vervang_ids_door_citaat("zie [abc123456789]", voorstellen)

    assert "…" in resultaat
    assert lange_tekst not in resultaat


def test_vervang_ids_door_citaat_lege_motivatie_blijft_leeg() -> None:
    assert vervang_ids_door_citaat("", [{"id": "abc123456789", "tekst": "iets"}]) == ""


# ---- pas_critic_toe (story 049) ---------------------------------------------------------------


def _voorstel(**overrides: object) -> dict:
    basis = {
        "id": "elementid01",
        "klasse": "Rechtssubject",
        "tekst": "Degene die aangifte doet",
        "alternatieven": [],
        "critic_rondes": [],
    }
    basis.update(overrides)
    return basis


def test_pas_critic_toe_rood_vervang_wijzigt_klasse_en_tekst() -> None:
    voorstel = _voorstel(critic_rondes=[{"ronde": 1}])
    feedback = [
        {
            "id": "elementid01",
            "aandacht": "rood",
            "actie": "vervang",
            "voorstel_klasse": "Rechtsfeit",
            "voorstel_tekst": "aangifte doet",
        }
    ]
    uit, telling, rest = pas_critic_toe([voorstel], feedback, _CORPUS)

    assert telling.toegepast == 1
    assert rest == []
    assert uit[0]["klasse"] == "Rechtsfeit"
    assert uit[0]["tekst"] == "aangifte doet"
    assert uit[0]["critic_rondes"][-1]["toegepast"] is True
    assert uit[0]["aandacht"] == ""  # opnieuw te beoordelen


def test_pas_critic_toe_geel_vervang_wordt_alternatief_niet_hoofdklasse() -> None:
    voorstel = _voorstel()
    feedback = [
        {
            "id": "elementid01",
            "aandacht": "geel",
            "actie": "vervang",
            "voorstel_klasse": "Rechtsfeit",
            "motivatie": "twijfel",
        }
    ]
    uit, telling, rest = pas_critic_toe([voorstel], feedback, _CORPUS)

    assert telling.alternatief == 1
    assert uit[0]["klasse"] == "Rechtssubject"  # ongewijzigd
    assert any(a["klasse"] == "Rechtsfeit" for a in uit[0]["alternatieven"])


def test_pas_critic_toe_laat_jurist_markering_ongemoeid() -> None:
    voorstel = _voorstel(van_jurist=True)
    feedback = [
        {
            "id": "elementid01",
            "aandacht": "rood",
            "actie": "vervang",
            "voorstel_klasse": "Rechtsfeit",
        }
    ]
    uit, telling, rest = pas_critic_toe([voorstel], feedback, _CORPUS)

    assert telling.toegepast == 0
    assert uit[0]["klasse"] == "Rechtssubject"


def test_pas_critic_toe_rood_vervang_niet_letterlijk_gaat_naar_rest() -> None:
    voorstel = _voorstel(critic_rondes=[{"ronde": 1}])
    feedback = [
        {
            "id": "elementid01",
            "aandacht": "rood",
            "actie": "vervang",
            "voorstel_tekst": "een verzonnen fragment",
        }
    ]
    uit, telling, rest = pas_critic_toe([voorstel], feedback, _CORPUS)

    assert telling.toegepast == 0
    assert len(rest) == 1
    assert uit[0]["tekst"] == "Degene die aangifte doet"  # ongewijzigd


def test_pas_critic_toe_zonder_feedback_laat_voorstel_ongemoeid() -> None:
    voorstel = _voorstel()
    uit, telling, rest = pas_critic_toe([voorstel], [], _CORPUS)

    assert telling.toegepast == 0
    assert telling.alternatief == 0
    assert uit == [voorstel]


# ---- openstaand_voorstel (story 049) -----------------------------------------------------------


def test_openstaand_voorstel_niet_uitgevoerde_eindronde() -> None:
    voorstel = _voorstel(
        critic_rondes=[
            {
                "actie": "vervang",
                "toegepast": False,
                "voorstel_klasse": "Rechtsfeit",
                "voorstel_tekst": "aangifte doet",
                "motivatie": "beter zo",
            }
        ]
    )
    klasse, tekst, reden = openstaand_voorstel(voorstel, _CORPUS)

    assert klasse == "Rechtsfeit"
    assert tekst == "aangifte doet"
    assert reden == "beter zo"


def test_openstaand_voorstel_toegepast_levert_niets() -> None:
    voorstel = _voorstel(
        critic_rondes=[{"actie": "vervang", "toegepast": True, "voorstel_klasse": "Rechtsfeit"}]
    )
    assert openstaand_voorstel(voorstel, _CORPUS) == ("", "", "")


def test_openstaand_voorstel_zonder_geschiedenis_levert_niets() -> None:
    assert openstaand_voorstel(_voorstel(), _CORPUS) == ("", "", "")
