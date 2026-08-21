"""Gedragstests voor het projecten-domein (feature-bouwen regel 6).

Alle tests gaan via de echte HTTP-laag (router + store + SQLite), zodat de acceptatiecriteria
end-to-end gedekt zijn. Auth wordt overgeslagen via de conftest.py-override.
"""

from __future__ import annotations

GELDIGE_BRON = {"bwb_id": "BWBR0011823", "artikel": "9", "lid": "1"}


def _maak(client, *, naam: str | None = "Test-werkgebied", bronnen=None, **extra) -> dict:
    body = {
        "naam": naam,
        "bronnen": bronnen or [GELDIGE_BRON],
        **extra,
    }
    resp = client.post("/v1/projecten", json=body)
    assert resp.status_code == 201, resp.json()
    return resp.json()


# ─── Aanmaken ──────────────────────────────────────────────────────────────────


def test_aanmaken_geeft_201_met_id(client):
    data = _maak(client)
    assert "id" in data
    assert data["status"] == "nieuw"
    assert len(data["id"]) == 36  # UUID-formaat


def test_aanmaken_naam_optioneel(client):
    """Naam ontbreekt → naam wordt afgeleid uit de eerste bron."""
    data = _maak(client, naam=None)
    assert data["status"] == "nieuw"
    detail = client.get(f"/v1/projecten/{data['id']}").json()
    assert "BWBR0011823" in detail["naam"]


def test_aanmaken_zonder_bronnen_geeft_422(client):
    resp = client.post("/v1/projecten", json={"bronnen": []})
    assert resp.status_code == 422


def test_aanmaken_met_omschrijving(client):
    data = _maak(client, omschrijving="Context bij dit werkgebied.")
    detail = client.get(f"/v1/projecten/{data['id']}").json()
    assert detail["omschrijving"] == "Context bij dit werkgebied."


# ─── Lijst ─────────────────────────────────────────────────────────────────────


def test_lijst_leeg(client):
    resp = client.get("/v1/projecten")
    assert resp.status_code == 200
    assert resp.json() == []


def test_lijst_gevuld(client):
    _maak(client, naam="Werkgebied A")
    _maak(client, naam="Werkgebied B")
    resp = client.get("/v1/projecten")
    assert resp.status_code == 200
    namen = [a["naam"] for a in resp.json()]
    assert "Werkgebied A" in namen
    assert "Werkgebied B" in namen


# ─── Detail ────────────────────────────────────────────────────────────────────


def test_detail_bestaand(client):
    data = _maak(client, naam="Detail-werkgebied", omschrijving="Test-context")
    resp = client.get(f"/v1/projecten/{data['id']}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["naam"] == "Detail-werkgebied"
    assert detail["omschrijving"] == "Test-context"
    assert detail["status"] == "nieuw"
    assert detail["bronnen"][0]["bwb_id"] == "BWBR0011823"


def test_detail_onbekend_id_geeft_404(client):
    resp = client.get("/v1/projecten/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ─── Verwijderen ───────────────────────────────────────────────────────────────


def test_verwijder_bestaand(client):
    data = _maak(client)
    resp = client.delete(f"/v1/projecten/{data['id']}")
    assert resp.status_code == 204
    assert client.get(f"/v1/projecten/{data['id']}").status_code == 404


def test_verwijder_onbekend_id_geeft_404(client):
    resp = client.delete("/v1/projecten/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_verwijder_verdwijnt_uit_lijst(client):
    a = _maak(client, naam="Verwijder-me")
    _maak(client, naam="Houd-me")
    client.delete(f"/v1/projecten/{a['id']}")
    namen = [x["naam"] for x in client.get("/v1/projecten").json()]
    assert "Verwijder-me" not in namen
    assert "Houd-me" in namen
