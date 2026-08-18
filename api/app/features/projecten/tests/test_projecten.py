"""Gedragstests voor het projecten-domein (feature-bouwen regel 6).

Alle tests gaan via de echte HTTP-laag (router + store + SQLite), zodat de acceptatiecriteria
van story 012 end-to-end gedekt zijn. Auth wordt overgeslagen via de conftest.py-override.

BackgroundTasks worden niet uitgevoerd door Starlette's TestClient — de background-job
(`_voer_analyse_uit`) hoeft hier niet getest te worden; de statusovergangen worden direct
via de store getest in `test_sse.py`.
"""

from __future__ import annotations

GELDIGE_BRON = {"bwb_id": "BWBR0011823", "artikel": "9", "lid": "1"}


def _maak(client, *, naam: str | None = "Test-analyse", bronnen=None, **extra) -> dict:
    body = {
        "naam": naam,
        "bronnen": bronnen or [GELDIGE_BRON],
        **extra,
    }
    resp = client.post("/v1/projecten", json=body)
    assert resp.status_code == 202, resp.json()
    return resp.json()


# ─── Aanmaken ──────────────────────────────────────────────────────────────────


def test_aanmaken_geeft_202_met_id(client):
    data = _maak(client)
    assert "id" in data
    assert data["status"] == "wachtrij"
    assert len(data["id"]) == 36  # UUID-formaat


def test_aanmaken_naam_optioneel(client):
    """Naam ontbreekt → naam wordt afgeleid uit de eerste bron."""
    data = _maak(client, naam=None)
    assert data["status"] == "wachtrij"
    # Detail moet een afgeleide naam bevatten
    detail = client.get(f"/v1/projecten/{data['id']}").json()
    assert "BWBR0011823" in detail["naam"]


def test_aanmaken_zonder_bronnen_geeft_422(client):
    resp = client.post("/v1/projecten", json={"bronnen": []})
    assert resp.status_code == 422


def test_aanmaken_met_begrippenlijst(client):
    data = _maak(
        client,
        begrippenlijst=[{"naam": "inkomen", "definitie": "Inkomsten uit arbeid."}],
    )
    detail = client.get(f"/v1/projecten/{data['id']}").json()
    assert detail["begrippenlijst"][0]["naam"] == "inkomen"


def test_aanmaken_human_in_the_loop_default_true(client):
    data = _maak(client)
    detail = client.get(f"/v1/projecten/{data['id']}").json()
    assert detail["human_in_the_loop"] is True


def test_aanmaken_human_in_the_loop_false(client):
    data = _maak(client, human_in_the_loop=False)
    detail = client.get(f"/v1/projecten/{data['id']}").json()
    assert detail["human_in_the_loop"] is False


# ─── Lijst ─────────────────────────────────────────────────────────────────────


def test_lijst_leeg(client):
    resp = client.get("/v1/projecten")
    assert resp.status_code == 200
    assert resp.json() == []


def test_lijst_gevuld(client):
    _maak(client, naam="Analyse A")
    _maak(client, naam="Analyse B")
    resp = client.get("/v1/projecten")
    assert resp.status_code == 200
    namen = [a["naam"] for a in resp.json()]
    assert "Analyse A" in namen
    assert "Analyse B" in namen


# ─── Detail ────────────────────────────────────────────────────────────────────


def test_detail_bestaand(client):
    data = _maak(client, naam="Detail-analyse", omschrijving="Test-context")
    resp = client.get(f"/v1/projecten/{data['id']}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["naam"] == "Detail-analyse"
    assert detail["omschrijving"] == "Test-context"
    # Status kan al verder zijn als de achtergrond-job vrijwel direct afloopt (sleep gepatchd)
    assert detail["status"] in ("wachtrij", "actief", "review", "klaar", "fout")
    assert detail["bronnen"][0]["bwb_id"] == "BWBR0011823"


def test_detail_onbekend_id_geeft_404(client):
    resp = client.get("/v1/projecten/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ─── Verwijderen ───────────────────────────────────────────────────────────────


def test_verwijder_bestaand(client):
    data = _maak(client)
    resp = client.delete(f"/v1/projecten/{data['id']}")
    assert resp.status_code == 204
    # Na verwijderen: 404 bij opvragen
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


# ─── SSE-endpoint ──────────────────────────────────────────────────────────────
# SSE-testen met human_in_the_loop=False zodat de achtergrond-job eindigt op "klaar"
# (terminale status) in plaats van "review" (niet-terminaal). De stroom sluit dan
# automatisch zodra de eerste terminale status is bereikt.


def test_events_endpoint_bestaat(client):
    """SSE-endpoint reageert zonder fout; volledige stream testen via E2E."""
    import json as _json

    # human_in_the_loop=False → background-job zet status op "klaar" (terminaal)
    data = _maak(client, human_in_the_loop=False)
    with client.stream("GET", f"/v1/projecten/{data['id']}/events") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        # Lees het eerste event: bevat in ieder geval een "status"-sleutel
        for line in resp.iter_lines():
            if line.startswith("data:"):
                payload = _json.loads(line[5:].strip())
                assert "status" in payload
                break


def test_events_onbekend_id_stuurt_fout_event(client):
    """SSE stuurt een fout-event voor een onbekend id en sluit de stroom."""
    import json as _json

    with client.stream("GET", "/v1/projecten/00000000-0000-0000-0000-000000000000/events") as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("data:"):
                payload = _json.loads(line[5:].strip())
                assert "fout" in payload
                break
