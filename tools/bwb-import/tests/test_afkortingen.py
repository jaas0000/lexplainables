from __future__ import annotations

from app.afkortingen import zoek_bwb_id


def test_bekende_afkorting_geeft_bwb_id() -> None:
    assert zoek_bwb_id("Awb", "3:2") == "BWBR0005537"
    assert zoek_bwb_id("IW", "10") == "BWBR0004770"


def test_bw_boek_uit_artikelnummer() -> None:
    assert zoek_bwb_id("BW", "6:162") == "BWBR0005289"
    assert zoek_bwb_id("BW", "3:1") == "BWBR0005291"


def test_bw_zonder_boeknummer_geeft_none() -> None:
    assert zoek_bwb_id("BW", "162") is None


def test_onbekende_afkorting_geeft_none() -> None:
    assert zoek_bwb_id("XYZ", "1") is None
