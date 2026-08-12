"""Gedragstests voor het feedback-domein (feature-bouwen regel 6: gedrag, niet vorm — vorm is
al gegarandeerd door models.py/ADR-0011). Elke test gaat via de echte HTTP-laag (router +
store + SQLite), niet via losse functieaanroepen, zodat de acceptatiecriteria uit
docs/stories/001-feedback-indienen-en-beheren.md end-to-end gedekt zijn."""

from __future__ import annotations

GEBRUIKER = {"X-User-Id": "analist-1"}
BEHEERDER = {"X-Admin-Id": "beheerder-1"}


def _dien_in(client, tekst: str, categorie: str = "vraag", pagina: str | None = None) -> int:
    body = {"categorie": categorie, "tekst": tekst}
    if pagina is not None:
        body["pagina"] = pagina
    response = client.post("/v1/feedback", json=body, headers=GEBRUIKER)
    assert response.status_code == 201
    return response.json()["id"]


def test_indienen_en_admin_ziet_het_terug(client):
    feedback_id = _dien_in(client, "Het zoekveld werkt niet lekker.", categorie="probleemmelding")

    response = client.get("/v1/admin/feedback", headers=BEHEERDER)
    assert response.status_code == 200
    data = response.json()
    assert data["totaal"] == 1
    item = data["items"][0]
    assert item["id"] == feedback_id
    assert item["categorie"] == "probleemmelding"
    assert item["tekst"] == "Het zoekveld werkt niet lekker."
    assert item["userid"] == "analist-1"


def test_indienen_met_ongeldige_categorie_geeft_422(client):
    response = client.post(
        "/v1/feedback",
        json={"categorie": "onbekend", "tekst": "iets"},
        headers=GEBRUIKER,
    )
    assert response.status_code == 422


def test_verwijderen(client):
    feedback_id = _dien_in(client, "Weg met dit item.")

    response = client.delete(f"/v1/admin/feedback/{feedback_id}", headers=BEHEERDER)
    assert response.status_code == 204

    lijst = client.get("/v1/admin/feedback", headers=BEHEERDER).json()
    assert lijst["totaal"] == 0


def test_verwijderen_onbekend_id_geeft_404(client):
    response = client.delete("/v1/admin/feedback/999", headers=BEHEERDER)
    assert response.status_code == 404


def test_paginering(client):
    for i in range(3):
        _dien_in(client, f"Item {i}")

    eerste_pagina = client.get(
        "/v1/admin/feedback", params={"offset": 0, "limit": 2}, headers=BEHEERDER
    ).json()
    assert eerste_pagina["totaal"] == 3
    assert len(eerste_pagina["items"]) == 2
    # Nieuwste eerst: het laatst ingediende item ("Item 2") staat vooraan.
    assert eerste_pagina["items"][0]["tekst"] == "Item 2"

    tweede_pagina = client.get(
        "/v1/admin/feedback", params={"offset": 2, "limit": 2}, headers=BEHEERDER
    ).json()
    assert len(tweede_pagina["items"]) == 1
    assert tweede_pagina["items"][0]["tekst"] == "Item 0"


def test_ongelezen_aantal_voor_en_na_markeer_gezien(client):
    # Vóór ooit gemarkeerd te hebben: alles telt als ongelezen (zie de store-docstring).
    _dien_in(client, "Eerste item.")
    _dien_in(client, "Tweede item.")
    aantal = client.get("/v1/admin/feedback/ongelezen-aantal", headers=BEHEERDER).json()
    assert aantal["aantal"] == 2

    response = client.post("/v1/admin/feedback/markeer-gezien", json={}, headers=BEHEERDER)
    assert response.status_code == 204
    aantal = client.get("/v1/admin/feedback/ongelezen-aantal", headers=BEHEERDER).json()
    assert aantal["aantal"] == 0

    # Na het markeren komt er nieuwe feedback bij: die telt weer mee.
    _dien_in(client, "Derde item, na het markeren.")
    aantal = client.get("/v1/admin/feedback/ongelezen-aantal", headers=BEHEERDER).json()
    assert aantal["aantal"] == 1


def test_markeer_gezien_met_expliciete_tot_beschermt_tegen_race_conditie(client):
    """Simuleert: de beheerder laadt de feedbackpagina en ziet 'm tot en met item A. Terwijl
    hij naar het scherm kijkt, komt item B binnen — vóórdat hij op "gezien"-klikt. Markeert hij
    met de expliciete created-timestamp van A (wat de UI zou meesturen), dan blijft B
    onterecht-ongezien. Zou hij in plaats daarvan zonder `tot` markeren (het huidige moment),
    dan zou B ten onrechte als gezien meetellen — dat is precies de bug die de expliciete `tot`
    voorkomt."""
    _dien_in(client, "Item A, gezien bij het laden.")
    item_a = client.get("/v1/admin/feedback", headers=BEHEERDER).json()["items"][0]
    tot_bij_laden = item_a["created"]

    # Item B komt binnen ná het laden, vóór het markeren.
    _dien_in(client, "Item B, komt binnen tussen laden en markeren.")

    response = client.post(
        "/v1/admin/feedback/markeer-gezien", json={"tot": tot_bij_laden}, headers=BEHEERDER
    )
    assert response.status_code == 204

    aantal = client.get("/v1/admin/feedback/ongelezen-aantal", headers=BEHEERDER).json()
    assert aantal["aantal"] == 1  # item B telt terecht nog als ongelezen
