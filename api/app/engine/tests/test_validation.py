"""Tests voor shared/validation.py (story 024).

Dekt schema_check_act2, schema_check_act3, brongetrouwheid_check.
"""

from __future__ import annotations

from app.engine.validation import (
    GELDIGE_JAS_KLASSEN,
    brongetrouwheid_check,
    schema_check_act2,
    schema_check_act3,
)

# ─── schema_check_act2 ──────────────────────────────────────────────────────


def test_act2_geldig():
    data = {
        "markeringen": [
            {
                "id": "m1",
                "formulering": "heeft recht op toeslag",
                "klasse": "Rechtsbetrekking",
                "vindplaats": "lid 1",
                "toelichting": "Rechthebbende–Staat",
            }
        ],
        "samenhang": "Artikel regelt recht op toeslag.",
    }
    assert schema_check_act2(data) == []


def test_act2_ontbrekende_markeringen():
    fouten = schema_check_act2({})
    assert any("markeringen" in f for f in fouten)


def test_act2_ontbrekend_veld():
    data = {
        "markeringen": [{"id": "m1", "klasse": "Rechtsfeit", "vindplaats": "lid 1"}],
        "samenhang": "x",
    }
    fouten = schema_check_act2(data)
    assert any("formulering" in f for f in fouten)


def test_act2_ongeldige_klasse():
    data = {
        "markeringen": [
            {
                "id": "m1",
                "formulering": "tekst",
                "klasse": "VerzonneneKlasse",
                "vindplaats": "lid 1",
                "toelichting": "x",
            }
        ],
        "samenhang": "x",
    }
    fouten = schema_check_act2(data)
    assert any("VerzonneneKlasse" in f for f in fouten)


def test_act2_dubbel_id():
    data = {
        "markeringen": [
            {"id": "m1", "formulering": "a", "klasse": "Rechtsfeit", "vindplaats": "lid 1"},
            {"id": "m1", "formulering": "b", "klasse": "Rechtssubject", "vindplaats": "lid 2"},
        ],
        "samenhang": "x",
    }
    fouten = schema_check_act2(data)
    assert any("meerdere keren" in f for f in fouten)


def test_act2_ontbrekende_samenhang():
    data = {
        "markeringen": [
            {
                "id": "m1",
                "formulering": "tekst",
                "klasse": "Rechtssubject",
                "vindplaats": "lid 1",
                "toelichting": "x",
            }
        ],
        "samenhang": "",
    }
    fouten = schema_check_act2(data)
    assert any("samenhang" in f for f in fouten)


# ─── schema_check_act3 ──────────────────────────────────────────────────────


def test_act3_geldig():
    data = {
        "begrippen": [
            {
                "id": "b1",
                "naam": "toeslag",
                "klasse": "Rechtsbetrekking",
                "definitie": "financiële tegemoetkoming",
                "is_interpretatie": False,
                "vindplaatsen": [{"bron_id": "br1", "lid": "1"}],
                "markering_ids": ["m1"],
            }
        ],
        "afleidingsregels": [],
    }
    assert schema_check_act3(data) == []


def test_act3_ontbrekende_begrippen():
    fouten = schema_check_act3({"afleidingsregels": []})
    assert any("begrippen" in f for f in fouten)


def test_act3_ongeldige_klasse():
    data = {
        "begrippen": [
            {
                "id": "b1",
                "naam": "x",
                "klasse": "Nep",
                "definitie": "y",
            }
        ],
        "afleidingsregels": [],
    }
    fouten = schema_check_act3(data)
    assert any("Nep" in f for f in fouten)


# ─── brongetrouwheid_check ──────────────────────────────────────────────────


def test_brongetrouwheid_citaat_aanwezig():
    leden = [{"lid": "1", "tekst": "De belastingplichtige heeft recht op een aftrek."}]
    markeringen = [{"id": "m1", "formulering": "heeft recht op een aftrek"}]
    assert brongetrouwheid_check(leden, markeringen) == []


def test_brongetrouwheid_citaat_afwezig():
    leden = [{"lid": "1", "tekst": "De belastingplichtige heeft recht op een aftrek."}]
    markeringen = [{"id": "m1", "formulering": "heeft recht op een toeslag"}]
    overtredingen = brongetrouwheid_check(leden, markeringen)
    assert len(overtredingen) == 1
    assert "m1" in overtredingen[0]


def test_brongetrouwheid_nfkc_normalisatie():
    """Unicode-whitespace en ligaturen moeten worden genormaliseerd."""

    tekst = "De belastingplichtige heeft recht."  # non-breaking space
    leden = [{"lid": "1", "tekst": tekst}]
    formulering = "belastingplichtige heeft recht"  # gewone spatie
    markeringen = [{"id": "m1", "formulering": formulering}]
    # Na NFKC-normalisatie zijn beide gelijk
    assert brongetrouwheid_check(leden, markeringen) == []


def test_brongetrouwheid_meerdere_leden():
    leden = [
        {"lid": "1", "tekst": "Artikel bepaalt de hoogte."},
        {"lid": "2", "tekst": "De hoogte bedraagt tien procent."},
    ]
    markeringen = [
        {"id": "m1", "formulering": "bepaalt de hoogte"},
        {"id": "m2", "formulering": "bedraagt tien procent"},
    ]
    assert brongetrouwheid_check(leden, markeringen) == []


def test_brongetrouwheid_leeg_formulering_genegeerd():
    """Lege formulering wordt niet gecontroleerd."""
    leden = [{"lid": "1", "tekst": "Tekst."}]
    markeringen = [{"id": "m1", "formulering": ""}]
    assert brongetrouwheid_check(leden, markeringen) == []


# ─── GELDIGE_JAS_KLASSEN ────────────────────────────────────────────────────


def test_geldige_klassen_telt_13():
    assert len(GELDIGE_JAS_KLASSEN) == 13
