from __future__ import annotations

from pathlib import Path

import pytest

from app import main
from app.config import Settings
from app.models import ImportSummary

FIXTURE = Path(__file__).parent / "fixtures" / "sample_toestand.xml"


class FakeWriter:
    """Vervangt `GraphDbWriter`: geen HTTP, registreert aanroepen voor assertions."""

    def __init__(self) -> None:
        self.constraints_calls = 0
        self.ontology_calls = 0
        self.geschreven: list[str] = []
        self.fail_bwb_id: str | None = None

    def ensure_constraints(self) -> None:
        self.constraints_calls += 1

    def write_ontology(self) -> None:
        self.ontology_calls += 1

    def write_wet(self, wet) -> ImportSummary:  # noqa: ANN001
        if wet.bwb_id == self.fail_bwb_id:
            raise RuntimeError(f"gesimuleerde fout voor {wet.bwb_id}")
        self.geschreven.append(wet.bwb_id)
        return ImportSummary(bwb_id=wet.bwb_id, wetten=1, artikelen=2)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        schemas_dir=tmp_path,
        sru_base_url="https://sru.test/Search",
        validate_xsd=False,
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
