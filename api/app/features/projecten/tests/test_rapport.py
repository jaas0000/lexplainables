"""Gedragstests voor de rapport-endpoints (story 013).

Acceptatiecriteria:
- GET /v1/projecten/{id}/rapport → 200 met JSON als status 'klaar'
- GET /v1/projecten/{id}/rapport → 409 als status ≠ 'klaar'
- GET /v1/projecten/{id}/rapport → 404 als analyse onbekend
- GET /v1/projecten/{id}/rapport.md → 200 met juiste Content-Disposition
- GET /v1/projecten/{id}/rapport.md → 409 als status ≠ 'klaar'
"""

from __future__ import annotations

import asyncio

from app.features.projecten.store import SqlAlchemyAnalyseStore

GELDIGE_BRON = {"bwb_id": "BWBR0011823", "artikel": "9", "lid": "1"}

VOORBEELD_RAPPORT = {
    "naam": "Testanalyse",
    "bronnen": [
        {
            "bron_id": "br1",
            "label": "Wet inkomstenbelasting 2001 art. 9",
            "wet": "Wet inkomstenbelasting 2001",
            "bwbId": "BWBR0011823",
            "artikel": "9",
            "lid": "1",
            "versiedatum": "2024-01-01",
            "bronreferentie": "",
            "markeringen": [],
            "samenhang": "Samenhangende toelichting.",
        }
    ],
    "begrippen": [
        {
            "id": "bg1",
            "naam": "Inkomen",
            "definitie": "Inkomsten uit arbeid.",
            "klasse": "primair",
            "synoniemen": [],
            "voorbeeld": "",
        }
    ],
    "afleidingsregels": [
        {
            "id": "ar1",
            "naam": "Inkomensregel",
            "omschrijving": "Als X dan Y.",
        }
    ],
}


def _maak(client, *, naam: str = "Test-analyse", **extra) -> dict:
    body = {"naam": naam, "bronnen": [GELDIGE_BRON], **extra}
    resp = client.post("/v1/projecten", json=body)
    assert resp.status_code == 202, resp.json()
    return resp.json()


async def _stel_klaar_in_async(
    store: SqlAlchemyAnalyseStore, analyse_id: str, rapport: dict | None
) -> None:
    await store.zet_status(analyse_id, "klaar")
    if rapport is not None:
        await store.sla_rapport_op(analyse_id, rapport)


def _stel_klaar_in(
    store: SqlAlchemyAnalyseStore, analyse_id: str, rapport: dict | None = None
) -> None:
    """Hulpfunctie: zet status 'klaar' en sla rapport op (indien meegegeven)."""
    asyncio.run(_stel_klaar_in_async(store, analyse_id, rapport))


# ─── GET /rapport — 200 als klaar ─────────────────────────────────────────────


def test_rapport_200_als_klaar(client, store):
    data = _maak(client)
    _stel_klaar_in(store, data["id"], VOORBEELD_RAPPORT)

    resp = client.get(f"/v1/projecten/{data['id']}/rapport")
    assert resp.status_code == 200
    body = resp.json()
    assert body["naam"] == "Testanalyse"
    assert len(body["bronnen"]) == 1
    assert len(body["begrippen"]) == 1
    assert len(body["afleidingsregels"]) == 1


# ─── GET /rapport — 409 als niet klaar ────────────────────────────────────────


def test_rapport_409_als_wachtrij(client, store):
    data = _maak(client)
    # Status blijft 'wachtrij' (standaard bij aanmaken)
    resp = client.get(f"/v1/projecten/{data['id']}/rapport")
    assert resp.status_code == 409


def test_rapport_409_als_actief(client, store):
    data = _maak(client)
    asyncio.run(store.zet_status(data["id"], "actief"))
    resp = client.get(f"/v1/projecten/{data['id']}/rapport")
    assert resp.status_code == 409


def test_rapport_409_als_klaar_maar_rapport_leeg(client, store):
    """Status 'klaar' maar rapport-veld nog None → ook 409."""
    data = _maak(client)
    _stel_klaar_in(store, data["id"], rapport=None)  # geen rapport opslaan

    resp = client.get(f"/v1/projecten/{data['id']}/rapport")
    assert resp.status_code == 409


# ─── GET /rapport — 404 als onbekend ──────────────────────────────────────────


def test_rapport_404_als_onbekend(client, store):
    resp = client.get("/v1/projecten/onbekend-id/rapport")
    assert resp.status_code == 404


# ─── GET /rapport.md — 200 met Content-Disposition ────────────────────────────


def test_rapport_md_200_met_content_disposition(client, store):
    data = _maak(client)
    analyse_id = data["id"]
    _stel_klaar_in(store, analyse_id, VOORBEELD_RAPPORT)

    resp = client.get(f"/v1/projecten/{analyse_id}/rapport.md")
    assert resp.status_code == 200
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert f"rapport-{analyse_id}.md" in cd
    assert "# Testanalyse" in resp.text


# ─── GET /rapport.md — 409 als niet klaar ─────────────────────────────────────


def test_rapport_md_409_als_niet_klaar(client, store):
    data = _maak(client)
    resp = client.get(f"/v1/projecten/{data['id']}/rapport.md")
    assert resp.status_code == 409
