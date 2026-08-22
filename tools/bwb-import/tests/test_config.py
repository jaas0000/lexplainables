from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings


def test_from_env_gebruikt_defaults_zonder_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "BWB_DATA_DIR",
        "BWB_SRU_URL",
        "GRAPHDB_URL",
        "GRAPHDB_REPOSITORY",
        "GRAPHDB_USER",
        "GRAPHDB_PASSWORD_FILE",
    ):
        monkeypatch.delenv(var, raising=False)

    settings = Settings.from_env()

    assert settings.sru_base_url == "https://zoekservice.overheid.nl/sru/Search"
    assert settings.graphdb_repository == "inning"
    assert settings.graphdb_password is None


def test_graphdb_password_komt_uit_bestand_niet_uit_env_waarde(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret_file = tmp_path / "graphdb_password"
    secret_file.write_text("geheim-wachtwoord\n")
    monkeypatch.setenv("GRAPHDB_PASSWORD_FILE", str(secret_file))

    settings = Settings.from_env()

    assert settings.graphdb_password == "geheim-wachtwoord"
