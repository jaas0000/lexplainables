from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from app import main
from app.config import Settings
from app.models import ImportSummary, ToestandRef
from app.wti_parser import WtiInfo

FIXTURE = Path(__file__).parent / "fixtures" / "sample_toestand.xml"


class FakeWriter:
    """Vervangt `GraphDbWriter`: geen HTTP, registreert aanroepen voor assertions."""

    def __init__(self) -> None:
        self.constraints_calls = 0
        self.ontology_calls = 0
        self.geschreven: list[str] = []
        self.fail_bwb_id: str | None = None
        self.laatste_wti: WtiInfo | None = None

    def ensure_constraints(self) -> None:
        self.constraints_calls += 1

    def write_ontology(self) -> None:
        self.ontology_calls += 1

    def ensure_fts_connector(self) -> None:
        pass

    def write_wet(self, wet, wti: WtiInfo | None = None) -> ImportSummary:  # noqa: ANN001
        if wet.bwb_id == self.fail_bwb_id:
            raise RuntimeError(f"gesimuleerde fout voor {wet.bwb_id}")
        self.geschreven.append(wet.bwb_id)
        self.laatste_wti = wti
        return ImportSummary(bwb_id=wet.bwb_id, wetten=1, artikelen=2)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        schemas_dir=tmp_path,
        sru_base_url="https://sru.test/Search",
        validate_xsd=False,
        import_wti=False,
        detect_tekstuele_refs=True,
        graphdb_url="http://graphdb.test",
        graphdb_repository="inning",
        graphdb_user=None,
        graphdb_password=None,
        service_api_key=None,
    )


@pytest.fixture(autouse=True)
def _geen_echte_download(monkeypatch: pytest.MonkeyPatch) -> None:
    """Elke test in dit bestand downloadt "BWBR0004770" via de echte fixture, geen netwerk."""
    monkeypatch.setattr(
        main.BwbDownloader,
        "latest_toestand",
        lambda self, bwb_id: ToestandRef(bwb_id=bwb_id, locatie_toestand=str(FIXTURE)),
    )
    monkeypatch.setattr(
        main.BwbDownloader, "download_toestand", lambda self, bwb_id, ref=None: FIXTURE
    )


def test_run_import_schrijft_naar_writer(settings: Settings) -> None:
    fake = FakeWriter()
    summary = main.run_import("BWBR0004770", settings, writer=fake)

    assert summary.artikelen == 2
    assert fake.geschreven == ["BWBR0004770"]
    # writer meegegeven -> prepare() (constraints + ontologie) wordt hier niet nogmaals gedraaid.
    assert fake.constraints_calls == 0


def test_run_import_zonder_writer_draait_prepare(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeWriter()
    monkeypatch.setattr(main, "maak_writer", lambda s: fake)

    main.run_import("BWBR0004770", settings)

    assert fake.constraints_calls == 1
    assert fake.ontology_calls == 1


def test_run_imports_batch_gaat_door_na_fout(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeWriter()
    fake.fail_bwb_id = "BWBR0004770"
    monkeypatch.setattr(main, "maak_writer", lambda s: fake)

    resultaten = main.run_imports(["BWBR0004770"], settings)

    assert len(resultaten) == 1
    assert resultaten[0].ok is False
    assert "gesimuleerde fout" in (resultaten[0].fout or "")
    # prepare() draait precies één keer voor de hele batch, niet per wet.
    assert fake.constraints_calls == 1


def test_main_exit_code_1_bij_fout(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeWriter()
    fake.fail_bwb_id = "BWBR0004770"
    monkeypatch.setattr(main, "maak_writer", lambda s: fake)
    monkeypatch.setattr(main.Settings, "from_env", classmethod(lambda cls: settings))

    exit_code = main.main(["BWBR0004770"])

    assert exit_code == 1


def test_main_exit_code_0_bij_succes(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeWriter()
    monkeypatch.setattr(main, "maak_writer", lambda s: fake)
    monkeypatch.setattr(main.Settings, "from_env", classmethod(lambda cls: settings))

    exit_code = main.main(["BWBR0004770"])

    assert exit_code == 0


def test_run_import_wti_download_fout_breekt_import_niet(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Best-effort: een falende WTI-download logt een waarschuwing maar de wet zelf importeert
    gewoon door — de kernwettekst is altijd waardevoller dan de verrijking."""
    fake = FakeWriter()
    wti_settings = replace(settings, import_wti=True)
    monkeypatch.setattr(
        main.BwbDownloader,
        "download_wti",
        lambda self, ref: (_ for _ in ()).throw(RuntimeError("WTI-download mislukt")),
    )

    summary = main.run_import("BWBR0004770", wti_settings, writer=fake)

    assert fake.geschreven == ["BWBR0004770"]
    assert fake.laatste_wti is None
    assert summary.artikelen == 2


def test_run_import_met_wti_geeft_wti_door_aan_writer(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = FakeWriter()
    wti_settings = replace(settings, import_wti=True)
    wti_fixture = Path(__file__).parent / "fixtures" / "sample_wti.xml"
    monkeypatch.setattr(main.BwbDownloader, "download_wti", lambda self, ref: wti_fixture)

    main.run_import("BWBR0004770", wti_settings, writer=fake)

    assert fake.laatste_wti is not None
    assert fake.laatste_wti.citeertitels == ["Invorderingswet 1990"]
