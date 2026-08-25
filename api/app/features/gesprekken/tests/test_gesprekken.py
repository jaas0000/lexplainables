"""Gedragstests voor het gesprekken-domein — CRUD, eigenaarschap, en `run_id`-idempotentie."""

from __future__ import annotations

from app.main import app
from app.shared.auth import huidige_beheerder

from .conftest import GEBRUIKER_A, GEBRUIKER_B


def test_maak_gesprek_en_haal_op(client) -> None:
    aangemaakt = client.post("/v1/gesprekken", json={"titel": "Een gesprek"})
    assert aangemaakt.status_code == 201
    gesprek = aangemaakt.json()
    assert gesprek["titel"] == "Een gesprek"
    assert gesprek["berichten"] == []

    opgehaald = client.get(f"/v1/gesprekken/{gesprek['id']}")
    assert opgehaald.status_code == 200
    assert opgehaald.json()["id"] == gesprek["id"]


def test_onbekend_gesprek_geeft_404(client) -> None:
    resp = client.get("/v1/gesprekken/onbekend")
    assert resp.status_code == 404


def test_andermans_gesprek_geeft_404(client) -> None:
    aangemaakt = client.post("/v1/gesprekken", json={"titel": "Privé"})
    gesprek_id = aangemaakt.json()["id"]

    app.dependency_overrides[huidige_beheerder] = lambda: GEBRUIKER_B
    try:
        resp = client.get(f"/v1/gesprekken/{gesprek_id}")
    finally:
        app.dependency_overrides[huidige_beheerder] = lambda: GEBRUIKER_A

    assert resp.status_code == 404


def test_lijst_toont_alleen_eigen_gesprekken_nieuwste_eerst(client) -> None:
    eerste = client.post("/v1/gesprekken", json={"titel": "Eerste"}).json()
    tweede = client.post("/v1/gesprekken", json={"titel": "Tweede"}).json()

    app.dependency_overrides[huidige_beheerder] = lambda: GEBRUIKER_B
    try:
        client.post("/v1/gesprekken", json={"titel": "Van B"})
    finally:
        app.dependency_overrides[huidige_beheerder] = lambda: GEBRUIKER_A

    lijst = client.get("/v1/gesprekken").json()
    ids = [g["id"] for g in lijst]
    assert eerste["id"] in ids
    assert tweede["id"] in ids
    assert all(g["titel"] != "Van B" for g in lijst)
    # Nieuwste-eerst: `tweede` is later aangemaakt/bijgewerkt dan `eerste`.
    assert ids.index(tweede["id"]) < ids.index(eerste["id"])


def test_bericht_toevoegen_verschijnt_in_gesprek(client) -> None:
    gesprek_id = client.post("/v1/gesprekken", json={}).json()["id"]

    resp = client.post(
        f"/v1/gesprekken/{gesprek_id}/berichten",
        json={"rol": "user", "tekst": "Wat is een belastingschuldige?"},
    )
    assert resp.status_code == 201
    bericht = resp.json()
    assert bericht["rol"] == "user"
    assert bericht["tekst"] == "Wat is een belastingschuldige?"

    gesprek = client.get(f"/v1/gesprekken/{gesprek_id}").json()
    assert len(gesprek["berichten"]) == 1


def test_bericht_op_onbekend_gesprek_geeft_404(client) -> None:
    resp = client.post("/v1/gesprekken/onbekend/berichten", json={"rol": "user", "tekst": "Hoi"})
    assert resp.status_code == 404


def test_zelfde_run_id_levert_niet_twee_berichten_op(client) -> None:
    gesprek_id = client.post("/v1/gesprekken", json={}).json()["id"]

    eerste = client.post(
        f"/v1/gesprekken/{gesprek_id}/berichten",
        json={"rol": "assistant", "tekst": "Antwoord", "run_id": "run-1"},
    ).json()
    tweede = client.post(
        f"/v1/gesprekken/{gesprek_id}/berichten",
        json={"rol": "assistant", "tekst": "Ander antwoord", "run_id": "run-1"},
    ).json()

    assert eerste["id"] == tweede["id"]
    assert tweede["tekst"] == "Antwoord"  # het eerste bericht wint, niet het tweede

    gesprek = client.get(f"/v1/gesprekken/{gesprek_id}").json()
    assert len(gesprek["berichten"]) == 1


def test_annotatieverwijzing_op_bericht(client) -> None:
    gesprek_id = client.post("/v1/gesprekken", json={}).json()["id"]

    bericht = client.post(
        f"/v1/gesprekken/{gesprek_id}/berichten",
        json={
            "rol": "assistant",
            "annotatie_slug": "abc123",
            "annotatie_titel": "BWBR0004770 — art. 1",
        },
    ).json()

    assert bericht["annotatie_slug"] == "abc123"
    assert bericht["annotatie_titel"] == "BWBR0004770 — art. 1"


def test_hernoem_gesprek(client) -> None:
    gesprek_id = client.post("/v1/gesprekken", json={"titel": "Oud"}).json()["id"]

    resp = client.patch(f"/v1/gesprekken/{gesprek_id}", json={"titel": "Nieuw"})
    assert resp.status_code == 200
    assert resp.json()["titel"] == "Nieuw"


def test_verwijder_gesprek(client) -> None:
    gesprek_id = client.post("/v1/gesprekken", json={}).json()["id"]

    resp = client.delete(f"/v1/gesprekken/{gesprek_id}")
    assert resp.status_code == 204

    assert client.get(f"/v1/gesprekken/{gesprek_id}").status_code == 404


def test_zonder_auth_geeft_401() -> None:
    from fastapi.testclient import TestClient

    with TestClient(app) as kaal_client:
        resp = kaal_client.post("/v1/gesprekken", json={"titel": "x"})

    assert resp.status_code == 401
