from __future__ import annotations

from pathlib import Path

import pytest

from app.parser import ParseError, ToestandParser

FIXTURES = Path(__file__).parent / "fixtures"
SCHEMA = Path(__file__).parent.parent / "schemas" / "toestand_2016-1.xsd"


def _schrijf(tmp_path: Path, xml: str) -> Path:
    pad = tmp_path / "toestand.xml"
    pad.write_text(xml, encoding="utf-8")
    return pad


# --------------------------------------------------------------------- validate()


def test_validate_geldig_document_geeft_true() -> None:
    parser = ToestandParser(schema_path=SCHEMA)
    assert parser.validate(FIXTURES / "sample_toestand.xml") is True


def test_validate_zonder_schema_path_geeft_false_geen_crash(tmp_path: Path) -> None:
    parser = ToestandParser(schema_path=None)
    pad = _schrijf(tmp_path, "<toestand bwb-id='X'><wetgeving/></toestand>")
    assert parser.validate(pad) is False


def test_validate_ongeldig_document_geeft_false(tmp_path: Path) -> None:
    parser = ToestandParser(schema_path=SCHEMA)
    pad = _schrijf(tmp_path, "<niet-toestand/>")
    assert parser.validate(pad) is False


# ------------------------------------------------------------------------- parse()


def test_parse_sample_toestand_kernvelden() -> None:
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    assert wet.bwb_id == "BWBR0004770"
    assert wet.citeertitel == "Invorderingswet 1990"
    assert wet.soort == "wet"
    assert wet.geldig_vanaf == "2026-01-01"


def test_parse_structuurdeel_en_artikelen() -> None:
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    assert len(wet.structuurdelen) == 1
    hoofdstuk = wet.structuurdelen[0]
    assert hoofdstuk.soort == "hoofdstuk"
    assert hoofdstuk.nummer == "I"
    assert hoofdstuk.titel == "Algemene bepalingen"
    assert [a.nummer for a in hoofdstuk.artikelen] == ["1", "2"]


def test_parse_lid_tekst_exclusief_meta_data() -> None:
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    artikel1 = wet.structuurdelen[0].artikelen[0]
    assert len(artikel1.leden) == 2
    lid1 = artikel1.leden[0]
    assert lid1.nummer == "1"
    assert lid1.tekst == "Deze wet geldt bij de invordering van rijksbelastingen."
    # Geen jci-verwijzingsstrings (uit <meta-data>) in de tekst.
    assert "jci1.3" not in lid1.tekst
    assert "verwijzing=" not in lid1.tekst


def test_parse_artikel_tekst_bevat_geen_lid_tekst() -> None:
    """Een artikel mét leden draagt zijn eigen tekst niet dubbel met die van zijn leden."""
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    artikel1 = wet.structuurdelen[0].artikelen[0]
    assert "Deze wet geldt bij de invordering" not in artikel1.tekst


def test_parse_lid_verwijzingen_extref() -> None:
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    lid2 = wet.structuurdelen[0].artikelen[0].leden[1]
    assert len(lid2.verwijzingen) == 7
    eerste = lid2.verwijzingen[0]
    assert eerste.soort.value == "extref"
    assert eerste.doel_bwb_id == "BWBR0005537"
    assert eerste.tekst == "artikel 3:40"
    assert eerste.doc == "jci1.3:c:BWBR0005537&artikel=3:40"


def test_parse_onderdelen_van_lijst() -> None:
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    lid1_artikel2 = wet.structuurdelen[0].artikelen[1].leden[0]
    assert [o.nummer for o in lid1_artikel2.onderdelen] == [
        "a.",
        "aa.",
        "b.",
        "c.",
        "d.",
        "e.",
        "f.",
        "g.",
        "h.",
        "i.",
        "j.",
        "k.",
        "l.",
        "m.",
        "n.",
        "o.",
        "p.",
        "q.",
        "r.",
        "s.",
        "t.",
    ]
    onderdeel_a = lid1_artikel2.onderdelen[0]
    assert "rijksbelastingen" in onderdeel_a.tekst
    assert len(onderdeel_a.verwijzingen) == 2


def test_parse_geneste_subonderdelen() -> None:
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    lid1_artikel2 = wet.structuurdelen[0].artikelen[1].leden[0]
    onderdeel_aa = lid1_artikel2.onderdelen[1]
    assert onderdeel_aa.nummer == "aa."
    assert [sub.nummer for sub in onderdeel_aa.subonderdelen] == ["1°.", "2°.", "3°.", "4°."]
    assert "Nederland" in onderdeel_aa.subonderdelen[2].tekst


def test_parse_artikel_verwijzingen_sluiten_lid_en_onderdeel_uit() -> None:
    """De verwijzingen van artikel 2 zelf (buiten zijn leden/onderdelen) zijn leeg — alle
    extref's in de fixture zitten binnen leden/onderdelen, niet direct op artikelniveau."""
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    artikel2 = wet.structuurdelen[0].artikelen[1]
    assert artikel2.verwijzingen == []


def test_parse_extref_tekst_blijft_leesbaar_in_lid() -> None:
    """Inline <extref>-verwijzingen leveren nog geen Verwijzing-object op (latere story), maar
    hun omringende tekst moet wel meekomen — anders verdwijnt een deel van de leestekst."""
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    lid2 = wet.structuurdelen[0].artikelen[0].leden[1]
    assert "artikel 3:40" in lid2.tekst
    assert "niet van toepassing" in lid2.tekst


# --------------------------------------------------------------------- edge cases


def test_parse_verkeerd_root_element_geeft_parse_error(tmp_path: Path) -> None:
    parser = ToestandParser()
    pad = _schrijf(tmp_path, "<niet-toestand/>")
    with pytest.raises(ParseError, match="Onverwacht root-element"):
        parser.parse(pad)


def test_parse_zonder_wetgeving_geeft_parse_error(tmp_path: Path) -> None:
    parser = ToestandParser()
    pad = _schrijf(tmp_path, "<toestand bwb-id='BWBR9999'/>")
    with pytest.raises(ParseError, match="Geen <wetgeving>"):
        parser.parse(pad)


def test_parse_zonder_wettekst_geeft_parse_error(tmp_path: Path) -> None:
    """Circulaires (<circulaire>/<circulaire-tekst>) zijn nog niet ondersteund."""
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='circulaire'>"
        "<citeertitel>Test</citeertitel>"
        "<circulaire><circulaire-tekst/></circulaire>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)
    with pytest.raises(ParseError, match="circulaires zijn nog niet ondersteund"):
        parser.parse(pad)


def test_parse_artikel_zonder_leden(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'>"
        "<kop><nr>1</nr></kop>"
        "<al>Losse artikeltekst zonder leden.</al>"
        "</artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    wet = parser.parse(pad)

    assert len(wet.losse_artikelen) == 1
    artikel = wet.losse_artikelen[0]
    assert artikel.tekst == "Losse artikeltekst zonder leden."
    assert artikel.leden == []
