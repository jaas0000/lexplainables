from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import service
from app.models import ImportResult, ImportSummary


@pytest.fixture(autouse=True)
def _geen_echte_settings_uit_omgeving(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("GRAPHDB_URL", "GRAPHDB_REPOSITORY", "BWB_SERVICE_API_KEY_FILE"):
        monkeypatch.delenv(var, raising=False)


def test_health() -> None:
    client = TestClient(service.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_import_enkele_wet(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_import(bwb_id, settings):  # noqa: ANN001
        assert bwb_id == "BWBR0004770"
        return ImportSummary(bwb_id=bwb_id, wetten=1, artikelen=2)

    monkeypatch.setattr(service, "run_import", fake_run_import)

    with TestClient(service.app) as client:
        resp = client.post("/import", json={"bwb_id": "BWBR0004770"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["overzicht"]["artikelen"] == 2


def test_import_mislukt_geeft_500(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_import(bwb_id, settings):  # noqa: ANN001
        raise RuntimeError("kapot")

    monkeypatch.setattr(service, "run_import", fake_run_import)

    with TestClient(service.app) as client:
        resp = client.post("/import", json={"bwb_id": "BWBR0004770"})

    assert resp.status_code == 500
    assert "kapot" in resp.json()["detail"]


def test_import_batch_gedeeltelijk_geslaagd(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_imports(bwb_ids, settings):  # noqa: ANN001
        return [
            ImportResult(bwb_id="BWBR1", ok=True, overzicht=ImportSummary(bwb_id="BWBR1")),
            ImportResult(bwb_id="BWBR2", ok=False, fout="mislukt"),
        ]

    monkeypatch.setattr(service, "run_imports", fake_run_imports)

    with TestClient(service.app) as client:
        resp = client.post("/import", json={"bwb_ids": ["BWBR1", "BWBR2"]})

    assert resp.status_code == 200
    assert resp.json()["status"] == "gedeeltelijk"


def test_import_zonder_bwb_id_geeft_422() -> None:
    with TestClient(service.app) as client:
        resp = client.post("/import", json={})
    assert resp.status_code == 422


def test_import_lege_bwb_ids_geeft_422() -> None:
    with TestClient(service.app) as client:
        resp = client.post("/import", json={"bwb_ids": []})
    assert resp.status_code == 422


def test_import_verkeerde_api_key_geeft_401(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ANN001
    secret_file = tmp_path / "bwb_api_key"
    secret_file.write_text("juiste-sleutel")
    monkeypatch.setenv("BWB_SERVICE_API_KEY_FILE", str(secret_file))

    def fake_run_import(bwb_id, settings):  # noqa: ANN001
        return ImportSummary(bwb_id=bwb_id)

    monkeypatch.setattr(service, "run_import", fake_run_import)

    with TestClient(service.app) as client:
        fout = client.post("/import", json={"bwb_id": "BWBR1"}, headers={"X-API-Key": "verkeerd"})
        goed = client.post(
            "/import", json={"bwb_id": "BWBR1"}, headers={"X-API-Key": "juiste-sleutel"}
        )

    assert fout.status_code == 401
    assert goed.status_code == 200
