"""Gedragstests voor het berichten-domein (feature-bouwen regel 6: gedrag, niet vorm — vorm is
al gegarandeerd door models.py/ADR-0011). Elke test gaat via de echte HTTP-laag (router +
store + SQLite), niet via losse functieaanroepen, zodat de acceptatiecriteria uit
docs/stories/002-berichten-lezen-en-beheren.md end-to-end gedekt zijn."""

from __future__ import annotations

import sqlite3

GEBRUIKER = {"X-User-Id": "analist-1"}


def _maak(client, titel: str = "Nieuwe functie", type: str = "update") -> dict:
    body = {"titel": titel, "inhoud": "Er is iets veranderd.", "type": type}
    response = client.post("/v1/admin/berichten", json=body)
    assert response.status_code == 201
    return response.json()


def _maak_en_publiceer(client, titel: str = "Nieuwe functie") -> dict:
    bericht = _maak(client, titel)
    response = client.patch(
        f"/v1/admin/berichten/{bericht['id']}/publicatie",
        json={"gepubliceerd": True},
    )
    assert response.status_code == 200
    return response.json()


def test_aanmaken_is_altijd_concept(client):
    bericht = _maak(client, "Concept-bericht")
    assert bericht["gepubliceerd"] is False
    assert bericht["gepubliceerd_op"] is None

    # Een analist ziet een ongepubliceerd concept niet.
    lijst = client.get("/v1/berichten", headers=GEBRUIKER).json()
    assert lijst["totaal"] == 0

    # De beheerder ziet het concept wel terug in de admin-lijst.
    admin_lijst = client.get("/v1/admin/berichten", headers={}).json()
    assert admin_lijst["totaal"] == 1
    assert admin_lijst["items"][0]["id"] == bericht["id"]


def test_aanmaken_met_ongeldig_type_geeft_422(client):
    response = client.post(
        "/v1/admin/berichten",
        json={"titel": "X", "inhoud": "Y", "type": "onbekend"},
        headers={},
    )
    assert response.status_code == 422


def test_bewerken(client):
    bericht = _maak(client, "Oude titel")

    response = client.put(
        f"/v1/admin/berichten/{bericht['id']}",
        json={"titel": "Nieuwe titel", "inhoud": "Bijgewerkte inhoud.", "type": "info"},
        headers={},
    )
    assert response.status_code == 200
    bijgewerkt = response.json()
    assert bijgewerkt["titel"] == "Nieuwe titel"
    assert bijgewerkt["inhoud"] == "Bijgewerkte inhoud."


def test_bewerken_onbekend_id_geeft_404(client):
    response = client.put(
        "/v1/admin/berichten/999",
        json={"titel": "X", "inhoud": "Y", "type": "info"},
        headers={},
    )
    assert response.status_code == 404


def test_publiceren_en_depubliceren(client):
    bericht = _maak(client)

    gepubliceerd = client.patch(
        f"/v1/admin/berichten/{bericht['id']}/publicatie",
        json={"gepubliceerd": True},
        headers={},
    ).json()
    assert gepubliceerd["gepubliceerd"] is True
    assert gepubliceerd["gepubliceerd_op"] is not None

    # Nu zichtbaar voor de analist.
    lijst = client.get("/v1/berichten", headers=GEBRUIKER).json()
    assert lijst["totaal"] == 1

    gedepubliceerd = client.patch(
        f"/v1/admin/berichten/{bericht['id']}/publicatie",
        json={"gepubliceerd": False},
        headers={},
    ).json()
    assert gedepubliceerd["gepubliceerd"] is False
    assert gedepubliceerd["gepubliceerd_op"] is None

    # Weer onzichtbaar voor de analist.
    lijst = client.get("/v1/berichten", headers=GEBRUIKER).json()
    assert lijst["totaal"] == 0


def test_publicatie_onbekend_id_geeft_404(client):
    response = client.patch(
        "/v1/admin/berichten/999/publicatie", json={"gepubliceerd": True}, headers={}
    )
    assert response.status_code == 404


def test_verwijderen_onbekend_id_geeft_404(client):
    response = client.delete("/v1/admin/berichten/999", headers={})
    assert response.status_code == 404


def test_lijst_met_paginering_en_gelezen_vlag(client):
    for i in range(3):
        _maak_en_publiceer(client, f"Bericht {i}")

    eerste_pagina = client.get(
        "/v1/berichten", params={"offset": 0, "limit": 2}, headers=GEBRUIKER
    ).json()
    assert eerste_pagina["totaal"] == 3
    assert len(eerste_pagina["items"]) == 2
    assert all(item["gelezen"] is False for item in eerste_pagina["items"])
    # Nieuwste (laatst gepubliceerde) eerst.
    assert eerste_pagina["items"][0]["titel"] == "Bericht 2"

    client.post("/v1/berichten/lees-alles", headers=GEBRUIKER)

    na_lezen = client.get("/v1/berichten", headers=GEBRUIKER).json()
    assert all(item["gelezen"] is True for item in na_lezen["items"])


def test_lijst_ongelezen_filter(client):
    _maak_en_publiceer(client, "Bericht A")
    _maak_en_publiceer(client, "Bericht B")

    client.post("/v1/berichten/lees-alles", headers=GEBRUIKER)
    _maak_en_publiceer(client, "Bericht C")

    alleen_ongelezen = client.get(
        "/v1/berichten", params={"ongelezen": True}, headers=GEBRUIKER
    ).json()
    assert alleen_ongelezen["totaal"] == 1
    assert alleen_ongelezen["items"][0]["titel"] == "Bericht C"


def test_ongelezen_aantal_voor_en_na_lees_alles(client):
    _maak_en_publiceer(client, "Bericht A")
    _maak_en_publiceer(client, "Bericht B")

    aantal = client.get("/v1/berichten/ongelezen-aantal", headers=GEBRUIKER).json()
    assert aantal["aantal"] == 2

    response = client.post("/v1/berichten/lees-alles", headers=GEBRUIKER)
    assert response.status_code == 204

    aantal = client.get("/v1/berichten/ongelezen-aantal", headers=GEBRUIKER).json()
    assert aantal["aantal"] == 0

    # Een nieuw gepubliceerd bericht telt weer mee.
    _maak_en_publiceer(client, "Bericht C")
    aantal = client.get("/v1/berichten/ongelezen-aantal", headers=GEBRUIKER).json()
    assert aantal["aantal"] == 1


def test_lees_alles_is_idempotent(client):
    _maak_en_publiceer(client, "Bericht A")

    eerste = client.post("/v1/berichten/lees-alles", headers=GEBRUIKER)
    tweede = client.post("/v1/berichten/lees-alles", headers=GEBRUIKER)
    assert eerste.status_code == 204
    assert tweede.status_code == 204

    aantal = client.get("/v1/berichten/ongelezen-aantal", headers=GEBRUIKER).json()
    assert aantal["aantal"] == 0


def test_verwijderen_cascadeert_leesbewijzen(client, db_pad):
    bericht = _maak_en_publiceer(client, "Te verwijderen bericht")
    client.post("/v1/berichten/lees-alles", headers=GEBRUIKER)

    # Er staat nu een leesbewijs voor dit bericht.
    conn = sqlite3.connect(db_pad)
    voor = conn.execute(
        "SELECT COUNT(*) FROM bericht_leesbewijzen WHERE bericht_id = ?", (bericht["id"],)
    ).fetchone()[0]
    conn.close()
    assert voor == 1

    response = client.delete(f"/v1/admin/berichten/{bericht['id']}", headers={})
    assert response.status_code == 204

    conn = sqlite3.connect(db_pad)
    na = conn.execute(
        "SELECT COUNT(*) FROM bericht_leesbewijzen WHERE bericht_id = ?", (bericht["id"],)
    ).fetchone()[0]
    conn.close()
    assert na == 0

    admin_lijst = client.get("/v1/admin/berichten", headers={}).json()
    assert admin_lijst["totaal"] == 0
