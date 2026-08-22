from __future__ import annotations

from lxml import etree

from app.models import VerwijzingSoort
from app.references import extract_references


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
