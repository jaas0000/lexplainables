from __future__ import annotations

from pathlib import Path

from app.collect import collect
from app.models import Artikel, Verwijzing, VerwijzingSoort, Wet
from app.parser import ToestandParser

FIXTURE = Path(__file__).parent / "fixtures" / "sample_toestand.xml"


def test_collect_regeling_node() -> None:
    wet = ToestandParser().parse(FIXTURE)
    batch, summary = collect(wet)

    regeling = batch.nodes["Regeling"][0]
    assert regeling["ref_key"] == "BWBR0004770"
    assert regeling["citeertitel"] == "Invorderingswet 1990"
    assert summary.wetten == 1


def test_collect_artikel_ref_key_uit_jci() -> None:
    wet = ToestandParser().parse(FIXTURE)
    batch, _ = collect(wet)

    artikel1 = next(a for a in batch.nodes["Artikel"] if a["nummer"] == "1")
    assert artikel1["ref_key"] == "BWBR0004770#artikel=1"


def test_collect_lid_ref_key_uit_jci() -> None:
    wet = ToestandParser().parse(FIXTURE)
    batch, _ = collect(wet)

    # Lid 1 van artikel 1 heeft een jci met &lid=1.
    lid1 = next(
        li for li in batch.nodes["Lid"] if li["nummer"] == "1" and "rijksbelastingen" in li["tekst"]
    )
    assert lid1["ref_key"] == "BWBR0004770#artikel=1#lid=1"


def test_collect_tellingen_kloppen() -> None:
    wet = ToestandParser().parse(FIXTURE)
    _, summary = collect(wet)

    assert summary.hoofdstukken == 1
    assert summary.artikelen == 2
    assert summary.leden == 8
    assert summary.onderdelen == 32


def test_collect_verwijzing_met_jci_wordt_meegenomen() -> None:
    wet = ToestandParser().parse(FIXTURE)
    batch, _ = collect(wet)

    doelen = {v["to"] for v in batch.verwijzingen}
    assert "BWBR0005537#artikel=3:40" in doelen


def test_collect_ref_key_fallback_zonder_jci() -> None:
    """Zonder jci-metadata valt de ref_key terug op nummer/id (geen crash, geen None-string)."""
    wet = Wet(
        bwb_id="BWBR9999",
        citeertitel="Test",
        opschrift="Test",
        soort="wet",
        losse_artikelen=[Artikel(id="BWBR9999/Art1", nummer="1", label="Artikel 1", tekst="tekst")],
    )
    batch, _ = collect(wet)

    artikel = batch.nodes["Artikel"][0]
    assert artikel["ref_key"] == "BWBR9999#id=BWBR9999/Art1"


def test_collect_verwijzing_zonder_doc_wordt_overgeslagen() -> None:
    """Een verwijzing zonder jci-doc (geen betrouwbaar doel) levert geen graafrelatie op."""
    wet = Wet(
        bwb_id="BWBR9999",
        citeertitel="Test",
        opschrift="Test",
        soort="wet",
        losse_artikelen=[
            Artikel(
                id="BWBR9999/Art1",
                nummer="1",
                label="Artikel 1",
                tekst="tekst",
                verwijzingen=[Verwijzing(soort=VerwijzingSoort.INTERN, tekst="artikel 2")],
            )
        ],
    )
    batch, _ = collect(wet)

    assert batch.verwijzingen == []
