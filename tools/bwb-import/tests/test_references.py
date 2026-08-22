from __future__ import annotations

from lxml import etree

from app.models import VerwijzingSoort
from app.references import (
    detect_textual_references,
    extract_references,
    jci_doel,
    jci_doel_ref_key,
    jci_to_ref_key,
)


def test_intref_geeft_soort_intern() -> None:
    xml = '<al>zie <intref verwijzing-id="1" bwb-ng-variabel-deel="/Art2">artikel 2</intref>.</al>'
    element = etree.fromstring(xml)

    verwijzingen = extract_references(element, eigen_bwb_id="BWBR0004770")

    assert len(verwijzingen) == 1
    ref = verwijzingen[0]
    assert ref.soort == VerwijzingSoort.INTERN
    assert ref.tekst == "artikel 2"
    assert ref.doel_bwb_id is None
    assert ref.doel_pad == "/Art2"
    assert ref.verwijzing_id == "1"


def test_extref_naar_andere_wet_geeft_soort_extern() -> None:
    xml = (
        '<al>zie <extref bwb-id="BWBR0005537" doc="jci1.3:c:BWBR0005537&amp;artikel=1">'
        "artikel 1 Awb</extref>.</al>"
    )
    element = etree.fromstring(xml)

    verwijzingen = extract_references(element, eigen_bwb_id="BWBR0004770")

    assert verwijzingen[0].soort == VerwijzingSoort.EXTERN
    assert verwijzingen[0].doel_bwb_id == "BWBR0005537"
    assert verwijzingen[0].doc == "jci1.3:c:BWBR0005537&artikel=1"


def test_extref_naar_eigen_wet_geeft_soort_intern() -> None:
    """De brontag zegt 'extern', maar het doel is de eigen wet -> intern."""
    xml = '<al>zie <extref bwb-id="BWBR0004770">artikel 2</extref>.</al>'
    element = etree.fromstring(xml)

    verwijzingen = extract_references(element, eigen_bwb_id="BWBR0004770")

    assert verwijzingen[0].soort == VerwijzingSoort.INTERN


def test_verwijzingen_niet_uit_meta_data() -> None:
    xml = (
        "<lid><al>gewone tekst</al>"
        '<meta-data><jcis><intref bwb-ng-variabel-deel="/Art1">art 1</intref></jcis></meta-data>'
        "</lid>"
    )
    element = etree.fromstring(xml)

    assert extract_references(element, eigen_bwb_id="BWBR1") == []


def test_extra_excl_sluit_geneste_lid_uit() -> None:
    xml = (
        "<artikel>"
        '<al>artikel-tekst met <intref bwb-ng-variabel-deel="/A">a</intref></al>'
        '<lid><al>lid-tekst met <intref bwb-ng-variabel-deel="/B">b</intref></al></lid>'
        "</artikel>"
    )
    element = etree.fromstring(xml)

    op_artikel_niveau = extract_references(
        element, eigen_bwb_id="BWBR1", extra_excl=" and not(ancestor::lid)"
    )

    assert len(op_artikel_niveau) == 1
    assert op_artikel_niveau[0].doel_pad == "/A"


# --------------------------------------------------------------------- jci-ontleding


def test_jci_doel_artikel_en_lid() -> None:
    doc = "jci1.3:c:BWBR0004770&hoofdstuk=I&artikel=1&lid=1&z=2026-01-01&g=2026-01-01"
    assert jci_doel(doc) == ("BWBR0004770", "1", "1")


def test_jci_doel_alleen_wet() -> None:
    assert jci_doel("jci1.3:c:BWBR0004770") == ("BWBR0004770", None, None)


def test_jci_doel_leeg() -> None:
    assert jci_doel(None) == (None, None, None)


def test_jci_to_ref_key_met_artikel() -> None:
    doc = "jci1.3:c:BWBR0005537&artikel=3:40"
    assert jci_to_ref_key(doc) == "BWBR0005537#artikel=3:40"


def test_jci_to_ref_key_zonder_artikel_geeft_none() -> None:
    """Een verwijzing naar een heel hoofdstuk heeft geen concreet artikel-doel."""
    doc = "jci1.3:c:BWBR0005537&hoofdstuk=6"
    assert jci_to_ref_key(doc) is None


def test_jci_doel_ref_key_artikel() -> None:
    doc = "jci1.3:c:BWBR0004770&hoofdstuk=I&artikel=1&z=2026-01-01"
    assert jci_doel_ref_key(doc) == ("BWBR0004770#artikel=1", "artikel")


def test_jci_doel_ref_key_lid() -> None:
    doc = "jci1.3:c:BWBR0004770&hoofdstuk=I&artikel=1&lid=1&z=2026-01-01"
    assert jci_doel_ref_key(doc) == ("BWBR0004770#artikel=1#lid=1", "lid")


def test_jci_doel_ref_key_alleen_wet() -> None:
    assert jci_doel_ref_key("jci1.3:c:BWBR0004770") == ("BWBR0004770", "wet")


def test_jci_doel_ref_key_geen_bwb_id_geeft_none() -> None:
    assert jci_doel_ref_key("niet-een-jci-string") == (None, None)


# ----------------------------------------------------- tekstuele fallback-detectie (story 036)


def test_detect_textual_references_met_bekende_afkorting() -> None:
    treffers = detect_textual_references(
        "zie artikel 3:2 Awb voor de procedure", eigen_bwb_id="BWBR0004770"
    )

    assert len(treffers) == 1
    treffer = treffers[0]
    assert treffer.soort == VerwijzingSoort.TEKSTUEEL
    assert treffer.doel_bwb_id == "BWBR0005537"
    assert treffer.doel_artikel == "3:2"
    assert treffer.tekst == "artikel 3:2 Awb"


def test_detect_textual_references_zonder_afkorting_is_intern() -> None:
    treffers = detect_textual_references("zoals bedoeld in artikel 12", eigen_bwb_id="BWBR0004770")

    assert len(treffers) == 1
    assert treffers[0].doel_bwb_id == "BWBR0004770"
    assert treffers[0].doel_artikel == "12"


def test_detect_textual_references_onbekende_afkorting_wordt_overgeslagen() -> None:
    """Onbekende afkortingen worden nooit gegokt — geen treffer, niet als intern behandeld."""
    treffers = detect_textual_references("zie artikel 5 XYZ", eigen_bwb_id="BWBR0004770")

    assert treffers == []


def test_detect_textual_references_meerdere_treffers() -> None:
    tekst = "zie artikel 3 en artikel 4 van deze wet"
    treffers = detect_textual_references(tekst, eigen_bwb_id="BWBR0004770")

    assert [t.doel_artikel for t in treffers] == ["3", "4"]


def test_detect_textual_references_bw_boek() -> None:
    treffers = detect_textual_references(
        "aansprakelijk op grond van artikel 6:162 BW", eigen_bwb_id="X"
    )

    assert treffers[0].doel_bwb_id == "BWBR0005289"
    assert treffers[0].doel_artikel == "6:162"
