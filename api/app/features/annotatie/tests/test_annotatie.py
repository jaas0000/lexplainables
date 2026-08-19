"""Gedragstests voor het annotatie-domein (feature-bouwen regel 6: gedrag, niet vorm).

Dekt de acceptatiecriteria uit docs/stories/022-annotatie-backend.md:
- Document aanmaken / ophalen / verwijderen
- Elementen zetten (validatie: ongeldige klasse, lege tekst)
- Beslissing registreren (alle typen, validatie van vereiste velden)
- Auditlog bijhouden en opvragen
- Client-scoping (andermans document → 404)
"""

from __future__ import annotations

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
