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


def test_parse_wet_brondata_en_aanhef_uit_fixture() -> None:
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    assert wet.vast_deel_url == "http://wetten.overheid.nl/id/BWBR0004770/2026-01-01/0"
    assert wet.publicatiejaar == "2018"
    assert wet.publicatienr == "75"
    assert wet.dossier == "34753"
    assert wet.ondertekeningsdatum == "2018-02-21"
    assert wet.uitgiftedatum == "2018-03-16"
    assert wet.aanhef is not None
    assert "Beatrix" in wet.aanhef
    assert wet.considerans is not None
    assert "Alzo Wij" in wet.considerans


def test_parse_wet_brondata_ontbrekend_geeft_none(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'><kop><nr>1</nr></kop><al>Tekst.</al></artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    wet = parser.parse(pad)

    assert wet.publicatiejaar is None
    assert wet.publicatienr is None
    assert wet.dossier is None
    assert wet.ondertekeningsdatum is None
    assert wet.uitgiftedatum is None
    assert wet.aanhef is None
    assert wet.considerans is None


def test_parse_ondertekenaars_uit_fixture() -> None:
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    assert len(wet.ondertekenaars) == 3
    eerste = wet.ondertekenaars[0]
    assert eerste.functie == "De Staatssecretaris van Financiën,"
    assert eerste.achternaam == "M. J. J. van Amelsvoort"
    assert eerste.voornaam is None


def test_parse_ondertekenaars_dedupliceert(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit>"
        "<aanhef>"
        "<ondertekening><functie>De Minister</functie><naam><achternaam>Jansen</achternaam>"
        "</naam></ondertekening>"
        "<ondertekening><functie>De Minister</functie><naam><achternaam>Jansen</achternaam>"
        "</naam></ondertekening>"
        "<ondertekening/>"
        "</aanhef>"
        "<wettekst>"
        "<artikel label='Artikel 1'><kop><nr>1</nr></kop><al>Tekst.</al></artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    wet = parser.parse(pad)

    assert len(wet.ondertekenaars) == 1
    assert wet.ondertekenaars[0].achternaam == "Jansen"


def test_parse_artikel_provenance_uit_fixture() -> None:
    """Artikel 2 in de fixture draagt echte provenance-attributen."""
    parser = ToestandParser()
    wet = parser.parse(FIXTURES / "sample_toestand.xml")

    artikel2 = wet.structuurdelen[0].artikelen[1]
    assert artikel2.bron == "Stb.2016-163"
    assert artikel2.effect == "wijziging"
    assert artikel2.status == "goed"
    assert artikel2.inwerking == "2016-05-01"


def test_parse_artikel_provenance_ontbrekend_geeft_none(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'>"
        "<kop><nr>1</nr></kop>"
        "<al>Tekst.</al>"
        "</artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    artikel = parser.parse(pad).losse_artikelen[0]

    assert artikel.inwerking is None
    assert artikel.bron is None
    assert artikel.effect is None
    assert artikel.status is None
    assert artikel.terugwerkend_tot is None
    assert artikel.wijzigingsbronnen == []


def test_parse_wijzigingsbronnen_en_terugwerkende_kracht(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'>"
        "<kop><nr>1</nr></kop>"
        "<al>Tekst.</al>"
        "<meta-data>"
        "<brondata><inwerkingtreding>"
        "<terugwerkend.datum isodatum='2020-01-01'/>"
        "</inwerkingtreding></brondata>"
        "<juncto><publicatie soort='Stb'>"
        "<publicatiejaar>2021</publicatiejaar><publicatienr>42</publicatienr>"
        "</publicatie></juncto>"
        "</meta-data>"
        "</artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    artikel = parser.parse(pad).losse_artikelen[0]

    assert artikel.terugwerkend_tot == "2020-01-01"
    assert artikel.wijzigingsbronnen == ["Stb.2021-42"]


def test_parse_voetnoten_op_artikel(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'>"
        "<kop><nr>1</nr></kop>"
        "<al>Tekst met noot<noot>Dit is een voetnoot.</noot>.</al>"
        "</artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    artikel = parser.parse(pad).losse_artikelen[0]

    assert artikel.voetnoten == ["Dit is een voetnoot."]
    assert "Dit is een voetnoot" not in artikel.tekst


def test_parse_definieert_begrippen_op_lid(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'>"
        "<kop><nr>1</nr></kop>"
        "<lid><lidnr>1</lidnr>"
        "<al><nadruk type='cur'>belastingschuldige:</nadruk> degene die belasting is "
        "verschuldigd.</al>"
        "</lid>"
        "</artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    lid = parser.parse(pad).losse_artikelen[0].leden[0]

    assert lid.definieert_begrippen == ["belastingschuldige"]


def test_parse_cursief_zonder_dubbele_punt_is_geen_definitie(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'>"
        "<kop><nr>1</nr></kop>"
        "<lid><lidnr>1</lidnr>"
        "<al><nadruk type='cur'>nadruk zonder definitie</nadruk> in de tekst.</al>"
        "</lid>"
        "</artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    lid = parser.parse(pad).losse_artikelen[0].leden[0]

    assert lid.definieert_begrippen == []


def test_parse_illustratie_op_artikel(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'>"
        "<kop><nr>1</nr></kop>"
        "<al>Zie de afbeelding.</al>"
        "<plaatje><illustratie id='IL1' naam='123.png' formaat='png' breedte='100px' "
        "hoogte='50px' alt='een schema'/></plaatje>"
        "</artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    artikel = parser.parse(pad).losse_artikelen[0]

    assert len(artikel.illustraties) == 1
    il = artikel.illustraties[0]
    assert il.id == "IL1"
    assert il.naam == "123.png"
    assert il.formaat == "png"
    assert il.alt == "een schema"


def test_parse_illustratie_zonder_id_of_naam_geeft_lege_id(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'>"
        "<kop><nr>1</nr></kop>"
        "<al>Tekst.</al>"
        "<plaatje><illustratie formaat='png'/></plaatje>"
        "</artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    artikel = parser.parse(pad).losse_artikelen[0]

    assert artikel.illustraties[0].id == ""


def test_parse_tabel_gerenderd_als_tekst(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'>"
        "<kop><nr>1</nr></kop>"
        "<al>Onderstaande tabel geldt.</al>"
        "<table><tgroup><tbody>"
        "<row><entry>Categorie</entry><entry>Tarief</entry></row>"
        "<row><entry>A</entry><entry>21%</entry></row>"
        "</tbody></tgroup></table>"
        "</artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    artikel = parser.parse(pad).losse_artikelen[0]

    assert "Onderstaande tabel geldt." in artikel.tekst
    assert "Categorie | Tarief" in artikel.tekst
    assert "A | 21%" in artikel.tekst


def test_parse_lege_tabel_levert_niets_op(tmp_path: Path) -> None:
    parser = ToestandParser()
    xml = (
        "<toestand bwb-id='BWBR9999'>"
        "<wetgeving soort='wet'>"
        "<citeertitel>Test</citeertitel>"
        "<wet-besluit><wettekst>"
        "<artikel label='Artikel 1'>"
        "<kop><nr>1</nr></kop>"
        "<al>Tekst zonder relevante tabel.</al>"
        "<table><tgroup><tbody><row><entry/><entry/></row></tbody></tgroup></table>"
        "</artikel>"
        "</wettekst></wet-besluit>"
        "</wetgeving>"
        "</toestand>"
    )
    pad = _schrijf(tmp_path, xml)

    artikel = parser.parse(pad).losse_artikelen[0]

    assert artikel.tekst == "Tekst zonder relevante tabel."


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
