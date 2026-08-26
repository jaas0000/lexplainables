"""Gedragstests voor het annotatie-domein (feature-bouwen regel 6: gedrag, niet vorm).

Dekt de acceptatiecriteria uit docs/stories/022-annotatie-backend.md:
- Document aanmaken / ophalen / verwijderen
- Elementen zetten (validatie: ongeldige klasse, lege tekst)
- Beslissing registreren (alle typen, validatie van vereiste velden)
- Auditlog bijhouden en opvragen
- Client-scoping (andermans document → 404)
"""

from __future__ import annotations

import app.features.annotatie.router as annotatie_router
from app.features.annotatie.graphdb import GraphDbNietBereikbaar, WetsartikelNietGevonden
from app.features.annotatie.models import Wetsartikel, WetsartikelLid
from app.main import app
from app.shared.auth import huidige_gebruiker

HDRS_A = {"X-User-Id": "analist-A"}
HDRS_B = {"X-User-Id": "analist-B"}

_DOC_BODY = {
    "werkgebied": "sociaal",
    "bwb_id": "BWBR0001234",
    "artikel": "3",
    "lid": "1",
}

_GELDIG_ELEMENT = {
    "klasse": "Rechtssubject",
    "tekst": "de belastingplichtige",
    "toelichting": "Subject dat de plicht draagt.",
    "vindplaats": "art. 3 lid 1",
}

_ONGELDIG_ELEMENT_KLASSE = {
    "klasse": "OnbekendType",
    "tekst": "iets",
}

_ELEMENT_LEGE_TEKST = {
    "klasse": "Rechtssubject",
    "tekst": "   ",
}


# --- helpers -----------------------------------------------------------------------


def _maak(client, body: dict = _DOC_BODY) -> dict:
    resp = client.post("/v1/annotatie/documenten", json=body, headers=HDRS_A)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _zet_elementen(client, slug: str, elementen: list[dict]) -> dict:
    resp = client.put(
        f"/v1/annotatie/documenten/{slug}/elementen",
        json={"elementen": elementen},
        headers=HDRS_A,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- acceptatiecriteria ------------------------------------------------------------


def test_document_aanmaken_en_ophalen(client):
    doc = _maak(client)
    assert doc["slug"]
    assert doc["werkgebied"] == "sociaal"
    assert doc["status"] == "voorgesteld"
    assert doc["elementen"] == []

    resp = client.get(f"/v1/annotatie/documenten/{doc['slug']}", headers=HDRS_A)
    assert resp.status_code == 200
    assert resp.json()["slug"] == doc["slug"]


def test_lijst_eigen_documenten(client):
    _maak(client)
    _maak(client, {**_DOC_BODY, "artikel": "4"})

    resp = client.get("/v1/annotatie/documenten", headers=HDRS_A)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


def test_document_verwijderen(client):
    doc = _maak(client)
    slug = doc["slug"]

    resp = client.delete(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A)
    assert resp.status_code == 204

    resp2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A)
    assert resp2.status_code == 404


def test_elementen_zetten_geldig(client):
    doc = _maak(client)
    slug = doc["slug"]

    resultaat = _zet_elementen(client, slug, [_GELDIG_ELEMENT])
    assert resultaat["aanvaard"] == 1
    assert resultaat["verworpen"] == 0

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    assert len(doc2["elementen"]) == 1
    assert doc2["elementen"][0]["klasse"] == "Rechtssubject"


def test_elementen_ongeldige_klasse_overgeslagen(client):
    doc = _maak(client)
    slug = doc["slug"]

    resultaat = _zet_elementen(client, slug, [_GELDIG_ELEMENT, _ONGELDIG_ELEMENT_KLASSE])
    assert resultaat["aanvaard"] == 1
    assert resultaat["verworpen"] == 1


def test_elementen_lege_tekst_overgeslagen(client):
    doc = _maak(client)
    slug = doc["slug"]

    resultaat = _zet_elementen(client, slug, [_GELDIG_ELEMENT, _ELEMENT_LEGE_TEKST])
    assert resultaat["aanvaard"] == 1
    assert resultaat["verworpen"] == 1


def test_beslissing_goedkeuren(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    element_id = doc2["elementen"][0]["id"]

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/{element_id}/beslissing",
        json={"type": "goedkeuren"},
        headers=HDRS_A,
    )
    assert resp.status_code == 200
    doc3 = resp.json()
    assert doc3["elementen"][0]["levenscyclus"] == "human_goedgekeurd"
    assert doc3["status"] == "klaar"


def test_beslissing_bewerken_met_reden_en_wijziging(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    element_id = doc2["elementen"][0]["id"]

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/{element_id}/beslissing",
        json={
            "type": "bewerken",
            "reden": "fout_tekst",
            "wijziging": {"tekst": "de nieuwe belastingplichtige"},
        },
        headers=HDRS_A,
    )
    assert resp.status_code == 200
    doc3 = resp.json()
    assert doc3["elementen"][0]["levenscyclus"] == "bewerkt"
    assert doc3["elementen"][0]["tekst"] == "de nieuwe belastingplichtige"


def test_beslissing_bewerken_zonder_reden_geeft_422(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    element_id = doc2["elementen"][0]["id"]

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/{element_id}/beslissing",
        json={"type": "bewerken", "wijziging": {"tekst": "x"}},
        headers=HDRS_A,
    )
    assert resp.status_code == 422


def test_beslissing_bewerken_zonder_wijziging_geeft_422(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    element_id = doc2["elementen"][0]["id"]

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/{element_id}/beslissing",
        json={"type": "bewerken", "reden": "fout_tekst"},
        headers=HDRS_A,
    )
    assert resp.status_code == 422


def test_beslissing_afwijzen_met_reden(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    element_id = doc2["elementen"][0]["id"]

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/{element_id}/beslissing",
        json={"type": "afwijzen", "reden": "dubbeling"},
        headers=HDRS_A,
    )
    assert resp.status_code == 200
    assert resp.json()["elementen"][0]["levenscyclus"] == "afgewezen"


def test_beslissing_afwijzen_zonder_reden_geeft_422(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    element_id = doc2["elementen"][0]["id"]

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/{element_id}/beslissing",
        json={"type": "afwijzen"},
        headers=HDRS_A,
    )
    assert resp.status_code == 422


def test_beslissing_element_niet_gevonden_geeft_404(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/onbekend-id/beslissing",
        json={"type": "goedkeuren"},
        headers=HDRS_A,
    )
    assert resp.status_code == 404


def test_auditlog_bijgehouden(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    audit = client.get(f"/v1/annotatie/documenten/{slug}/audit", headers=HDRS_A).json()["items"]
    acties = [r["actie"] for r in audit]
    assert "document-aangemaakt" in acties
    assert "elementen-voorgesteld" in acties


def test_auditlog_na_beslissing(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    element_id = doc2["elementen"][0]["id"]

    client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/{element_id}/beslissing",
        json={"type": "goedkeuren"},
        headers=HDRS_A,
    )

    audit = client.get(f"/v1/annotatie/documenten/{slug}/audit", headers=HDRS_A).json()["items"]
    acties = [r["actie"] for r in audit]
    assert "beslissing-goedkeuren" in acties


def test_client_scoping_andermans_document_geeft_404(client):
    """Andermans document is niet zichtbaar — 404, geen 403."""
    doc = _maak(client)
    slug = doc["slug"]

    # Andere gebruiker probeert het document te lezen.
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-B"
    resp = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_B)
    # Restore
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-A"

    assert resp.status_code == 404


def test_client_scoping_lijst_isoleert_gebruikers(client):
    """Een gebruiker ziet alleen zijn eigen documenten in de lijst."""
    _maak(client)  # document van analist-A

    # Maak een document als analist-B.
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-B"
    _maak(client)
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-A"

    lijst_a = client.get("/v1/annotatie/documenten", headers=HDRS_A).json()["items"]
    assert len(lijst_a) == 1

    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-B"
    lijst_b = client.get("/v1/annotatie/documenten", headers=HDRS_B).json()["items"]
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-A"
    assert len(lijst_b) == 1


def test_document_met_optioneel_lid(client):
    body = {"werkgebied": "fiscaal", "bwb_id": "BWBR0009999", "artikel": "7"}
    doc = _maak(client, body)
    assert doc["lid"] == ""


def test_gedeeltelijk_gereviewd_status(client):
    """Twee elementen: één goedgekeurd → gedeeltelijk_gereviewd."""
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT, {**_GELDIG_ELEMENT, "tekst": "tweede"}])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    eerste_id = doc2["elementen"][0]["id"]

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/{eerste_id}/beslissing",
        json={"type": "goedkeuren"},
        headers=HDRS_A,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "gedeeltelijk_gereviewd"


# --- wetsartikeltekst (story 037) ---------------------------------------------------


def test_wetsartikel_geeft_tekst_en_leden(client, monkeypatch):
    doc = _maak(client)

    async def fake_haal_op(bwb_id: str, artikel: str) -> Wetsartikel:
        assert (bwb_id, artikel) == (doc["bwb_id"], doc["artikel"])
        return Wetsartikel(
            bwb_id=bwb_id,
            artikel=artikel,
            opschrift="Belastingplicht",
            tekst="De belasting wordt geheven van...",
            leden=[WetsartikelLid(nummer="1", tekst="Eerste lid.")],
        )

    monkeypatch.setattr(annotatie_router, "haal_wetsartikel_op", fake_haal_op)

    resp = client.get(f"/v1/annotatie/documenten/{doc['slug']}/wetsartikel", headers=HDRS_A)
    assert resp.status_code == 200
    body = resp.json()
    assert body["opschrift"] == "Belastingplicht"
    assert body["leden"] == [{"nummer": "1", "tekst": "Eerste lid.", "onderdelen": []}]


def test_wetsartikel_andermans_document_geeft_404(client):
    doc = _maak(client)

    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-B"
    resp = client.get(f"/v1/annotatie/documenten/{doc['slug']}/wetsartikel", headers=HDRS_B)
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-A"

    assert resp.status_code == 404


def test_wetsartikel_niet_in_graaf_geeft_404(client, monkeypatch):
    doc = _maak(client)

    async def fake_haal_op(bwb_id: str, artikel: str) -> Wetsartikel:
        raise WetsartikelNietGevonden("niet gevonden")

    monkeypatch.setattr(annotatie_router, "haal_wetsartikel_op", fake_haal_op)

    resp = client.get(f"/v1/annotatie/documenten/{doc['slug']}/wetsartikel", headers=HDRS_A)
    assert resp.status_code == 404


def test_wetsartikel_graphdb_onbereikbaar_geeft_502(client, monkeypatch):
    doc = _maak(client)

    async def fake_haal_op(bwb_id: str, artikel: str) -> Wetsartikel:
        raise GraphDbNietBereikbaar("geen verbinding")

    monkeypatch.setattr(annotatie_router, "haal_wetsartikel_op", fake_haal_op)

    resp = client.get(f"/v1/annotatie/documenten/{doc['slug']}/wetsartikel", headers=HDRS_A)
    assert resp.status_code == 502


# --- merge-en-bevries-semantiek (PUT .../elementen is geen volledige vervanging) ---------------


def test_zet_elementen_tweede_ronde_voegt_toe_zonder_eerste_te_verliezen(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    tweede_element = {"klasse": "Rechtsobject", "tekst": "de aanslag", "toelichting": ""}
    _zet_elementen(client, slug, [tweede_element])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    teksten = {e["tekst"] for e in doc2["elementen"]}
    assert teksten == {"de belastingplichtige", "de aanslag"}


def test_zet_elementen_zelfde_sleutel_vervangt_zonder_beslissing(client):
    """Zonder jurist-beslissing mag een agent-ronde een element gewoon bijwerken (nieuwe
    toelichting, zelfde tekst+lid → zelfde sleutel), zolang het id maar behouden blijft."""
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])
    origineel_id = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()[
        "elementen"
    ][0]["id"]

    bijgewerkt = {**_GELDIG_ELEMENT, "toelichting": "Aangescherpte toelichting."}
    _zet_elementen(client, slug, [bijgewerkt])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    assert len(doc2["elementen"]) == 1
    assert doc2["elementen"][0]["id"] == origineel_id
    assert doc2["elementen"][0]["toelichting"] == "Aangescherpte toelichting."


def test_zet_elementen_bevriest_een_door_jurist_beoordeeld_element(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])
    element_id = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()["elementen"][
        0
    ]["id"]

    client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/{element_id}/beslissing",
        json={"type": "goedkeuren"},
        headers=HDRS_A,
    )

    # Een nieuwe agent-ronde probeert hetzelfde fragment (zelfde sleutel) opnieuw voor te
    # stellen — dat voorstel mag het al goedgekeurde element niet aanraken.
    nieuw_voorstel = {**_GELDIG_ELEMENT, "toelichting": "Een heel ander voorstel."}
    _zet_elementen(client, slug, [nieuw_voorstel])

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    assert len(doc2["elementen"]) == 1
    assert doc2["elementen"][0]["id"] == element_id
    assert doc2["elementen"][0]["levenscyclus"] == "human_goedgekeurd"
    assert doc2["elementen"][0]["toelichting"] == "Subject dat de plicht draagt."


def test_zet_elementen_met_run_info_slaat_laatste_run_op(client):
    doc = _maak(client)
    slug = doc["slug"]

    resp = client.put(
        f"/v1/annotatie/documenten/{slug}/elementen",
        json={
            "elementen": [_GELDIG_ELEMENT],
            "run": {
                "model": "claude-sonnet-4-6",
                "provider": "azure-foundry",
                "agent_versie": "0.1.0",
                "critic_rondes": 1,
                "stop_reden": "",
            },
        },
        headers=HDRS_A,
    )
    assert resp.status_code == 200

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    assert doc2["laatste_run"]["model"] == "claude-sonnet-4-6"
    assert doc2["laatste_run"]["critic_rondes"] == 1


def test_beslissing_laat_laatste_run_ongemoeid(client):
    doc = _maak(client)
    slug = doc["slug"]
    client.put(
        f"/v1/annotatie/documenten/{slug}/elementen",
        json={
            "elementen": [_GELDIG_ELEMENT],
            "run": {"model": "claude-sonnet-4-6"},
        },
        headers=HDRS_A,
    )
    element_id = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()["elementen"][
        0
    ]["id"]

    client.post(
        f"/v1/annotatie/documenten/{slug}/elementen/{element_id}/beslissing",
        json={"type": "goedkeuren"},
        headers=HDRS_A,
    )

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    assert doc2["laatste_run"]["model"] == "claude-sonnet-4-6"


# --- jurist voegt eigen elementen toe / verwijdert ze (wetsanalyse-migratie-vervolg) -----------


def test_element_zelf_toevoegen_door_jurist(client):
    doc = _maak(client)
    slug = doc["slug"]

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/elementen",
        json=_GELDIG_ELEMENT,
        headers=HDRS_A,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["elementen"]) == 1
    element = body["elementen"][0]
    assert element["herkomst"] == "mens"
    assert element["levenscyclus"] == "human_goedgekeurd"


def test_element_toevoegen_ongeldige_klasse_geeft_422(client):
    doc = _maak(client)
    resp = client.post(
        f"/v1/annotatie/documenten/{doc['slug']}/elementen",
        json=_ONGELDIG_ELEMENT_KLASSE,
        headers=HDRS_A,
    )
    assert resp.status_code == 422


def test_eigen_element_verwijderen(client):
    doc = _maak(client)
    slug = doc["slug"]
    aangemaakt = client.post(
        f"/v1/annotatie/documenten/{slug}/elementen", json=_GELDIG_ELEMENT, headers=HDRS_A
    ).json()
    element_id = aangemaakt["elementen"][0]["id"]

    resp = client.delete(f"/v1/annotatie/documenten/{slug}/elementen/{element_id}", headers=HDRS_A)
    assert resp.status_code == 204

    doc2 = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()
    assert doc2["elementen"] == []


def test_verwijderen_van_agent_element_geeft_409(client):
    """Alleen je eigen (`herkomst == "mens"`) markeringen kun je verwijderen; een agent-voorstel
    (`PUT .../elementen`, `herkomst == "agent"`) verwerp je via de beslissing-endpoint
    (`afwijzen`) — ook als het in je eigen document staat."""
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])
    element_id = client.get(f"/v1/annotatie/documenten/{slug}", headers=HDRS_A).json()["elementen"][
        0
    ]["id"]

    resp = client.delete(f"/v1/annotatie/documenten/{slug}/elementen/{element_id}", headers=HDRS_A)
    assert resp.status_code == 409


def test_element_verwijderen_onbekend_element_geeft_404(client):
    doc = _maak(client)
    resp = client.delete(
        f"/v1/annotatie/documenten/{doc['slug']}/elementen/onbekend", headers=HDRS_A
    )
    assert resp.status_code == 404


# --- afronden/heropenen bevriest het document (wetsanalyse-migratie-vervolg) -------------------


def test_status_accorderen_bevriest_document(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/status",
        json={"geaccordeerd": True},
        headers=HDRS_A,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "geaccordeerd"

    # Elk ander schrijfpad weigert nu met 409.
    assert (
        client.put(
            f"/v1/annotatie/documenten/{slug}/elementen",
            json={"elementen": [_GELDIG_ELEMENT]},
            headers=HDRS_A,
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/v1/annotatie/documenten/{slug}/elementen",
            json=_GELDIG_ELEMENT,
            headers=HDRS_A,
        ).status_code
        == 409
    )


def test_status_heropenen_herstelt_bewerkbaarheid(client):
    doc = _maak(client)
    slug = doc["slug"]
    client.post(
        f"/v1/annotatie/documenten/{slug}/status", json={"geaccordeerd": True}, headers=HDRS_A
    )

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/status",
        json={"geaccordeerd": False},
        headers=HDRS_A,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "voorgesteld"  # geen elementen → terug naar de basisstatus

    # Weer bewerkbaar.
    resultaat = _zet_elementen(client, slug, [_GELDIG_ELEMENT])
    assert resultaat["aanvaard"] == 1


# --- export (wetsanalyse-migratie-vervolg) ------------------------------------------------------


def test_export_json(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/export", params={"formaat": "json"}, headers=HDRS_A
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert body["document"]["slug"] == slug
    assert len(body["document"]["elementen"]) == 1
    assert "audit" in body


def test_export_csv(client):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/export", params={"formaat": "csv"}, headers=HDRS_A
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    regels = resp.text.splitlines()
    assert regels[0] == "klasse,tekst,lid,levenscyclus,toelichting,vindplaats"
    assert "de belastingplichtige" in regels[1]


def test_export_pdf(client, monkeypatch):
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    async def fake_haal_op(bwb_id: str, artikel: str) -> Wetsartikel:
        return Wetsartikel(bwb_id=bwb_id, artikel=artikel, opschrift=None, tekst="Wettekst.")

    monkeypatch.setattr(annotatie_router, "haal_wetsartikel_op", fake_haal_op)

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/export", params={"formaat": "pdf"}, headers=HDRS_A
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_export_zonder_wetsartikel_werkt_toch(client, monkeypatch):
    """De graaf is onbereikbaar of het artikel staat er niet in — de export faalt niet, hij
    laat gewoon het wettekst-blok weg."""
    doc = _maak(client)
    slug = doc["slug"]
    _zet_elementen(client, slug, [_GELDIG_ELEMENT])

    async def fake_haal_op(bwb_id: str, artikel: str) -> Wetsartikel:
        raise GraphDbNietBereikbaar("graaf onbereikbaar")

    monkeypatch.setattr(annotatie_router, "haal_wetsartikel_op", fake_haal_op)

    resp = client.post(
        f"/v1/annotatie/documenten/{slug}/export", params={"formaat": "pdf"}, headers=HDRS_A
    )
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")


def test_export_andermans_document_geeft_404(client):
    doc = _maak(client)

    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-B"
    resp = client.post(
        f"/v1/annotatie/documenten/{doc['slug']}/export",
        params={"formaat": "json"},
    )
    app.dependency_overrides[huidige_gebruiker] = lambda: "analist-A"

    assert resp.status_code == 404
