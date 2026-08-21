"""Acceptatiecriteria-tests voor het api_tokens-domein (story 018).

Tests:
- Aanmaken → token zichtbaar in response, niet in lijst
- Lijst toont token_prefix, niet het plaintext-token
- Intrekken → token werkt niet meer (404 bij herhaling)
- DB-token accepteer in auth-laag (integratietest)
"""

from __future__ import annotations

import pytest

from app.features.api_tokens.store import SqlAlchemyApiTokenStore

# ---------------------------------------------------------------------------
# Aanmaken
# ---------------------------------------------------------------------------


def test_aanmaken_geeft_token_in_response(client):
    """Het plaintext-token zit éénmalig in de aanmaak-response."""
    res = client.post("/v1/admin/api-tokens", json={"label": "mijn-token"})
    assert res.status_code == 201
    data = res.json()
    assert "token" in data
    assert len(data["token"]) > 8
    assert data["label"] == "mijn-token"
    assert data["actief"] is True


def test_aanmaken_zonder_label(client):
    """Label is optioneel; een leeg label is geldig."""
    res = client.post("/v1/admin/api-tokens", json={})
    assert res.status_code == 201
    assert res.json()["label"] == ""


def test_aanmaken_token_niet_in_lijst(client):
    """Het plaintext-token mag nooit in de lijst verschijnen."""
    res = client.post("/v1/admin/api-tokens", json={"label": "test"})
    assert res.status_code == 201
    plaintext = res.json()["token"]

    lijst = client.get("/v1/admin/api-tokens").json()
    assert len(lijst) == 1
    item = lijst[0]
    assert "token" not in item
    assert "token_hash" not in item
    # Prefix is de eerste 8 tekens en mag verschijnen
    assert item["token_prefix"] == plaintext[:8]
    # Maar de volledige plaintext staat nergens in het listitem
    for waarde in item.values():
        assert plaintext not in str(waarde)


# ---------------------------------------------------------------------------
# Lijst
# ---------------------------------------------------------------------------


def test_lijst_toont_prefix_niet_plaintext(client):
    """Lijst-response bevat token_prefix maar nooit het volledige token."""
    res = client.post("/v1/admin/api-tokens", json={"label": "prefix-test"})
    plaintext = res.json()["token"]

    lijst = client.get("/v1/admin/api-tokens").json()
    assert len(lijst) == 1
    item = lijst[0]
    assert item["token_prefix"] == plaintext[:8]
    assert "token" not in item


def test_lijst_is_leeg_bij_start(client):
    lijst = client.get("/v1/admin/api-tokens").json()
    assert lijst == []


# ---------------------------------------------------------------------------
# Intrekken
# ---------------------------------------------------------------------------


def test_intrekken_geeft_204(client):
    res = client.post("/v1/admin/api-tokens", json={"label": "weg"})
    token_id = res.json()["id"]

    del_res = client.delete(f"/v1/admin/api-tokens/{token_id}")
    assert del_res.status_code == 204


def test_ingetrokken_token_verschijnt_niet_in_lijst(client):
    """Na intrekken staat het token niet meer in de actieve lijst."""
    res = client.post("/v1/admin/api-tokens", json={"label": "weg"})
    token_id = res.json()["id"]

    client.delete(f"/v1/admin/api-tokens/{token_id}")

    lijst = client.get("/v1/admin/api-tokens").json()
    assert all(item["id"] != token_id for item in lijst)


def test_intrekken_onbekend_id_geeft_404(client):
    """Onbekend of al ingetrokken token-id geeft 404."""
    res = client.delete("/v1/admin/api-tokens/bestaat-niet")
    assert res.status_code == 404


def test_intrekken_tweemaal_geeft_404(client):
    """Intrekken is niet idempotent — tweede poging geeft 404."""
    res = client.post("/v1/admin/api-tokens", json={"label": "tweemaal"})
    token_id = res.json()["id"]

    client.delete(f"/v1/admin/api-tokens/{token_id}")
    res2 = client.delete(f"/v1/admin/api-tokens/{token_id}")
    assert res2.status_code == 404


# ---------------------------------------------------------------------------
# Auth-integratietest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_token_wordt_geaccepteerd_in_auth(auth_client):
    """Een DB-token wordt geaccepteerd door vereist_api_token (integratietest).

    API_TOKEN is leeg zodat alleen de DB-check het overnemen kan.
    """
    test_client, store = auth_client
    token_read, plaintext = await store.maak("mcp-token", "test-beheerder")

    # GET zonder token → 401
    res = test_client.get("/v1/admin/api-tokens")
    assert res.status_code == 401

    # GET met DB-token + X-User-Id → 200
    res = test_client.get(
        "/v1/admin/api-tokens",
        headers={
            "Authorization": f"Bearer {plaintext}",
            "X-User-Id": "test-beheerder",
        },
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_ingetrokken_db_token_wordt_geweigerd(auth_client):
    """Een ingetrokken DB-token geeft 401."""
    test_client, store = auth_client
    token_read, plaintext = await store.maak("weg-token", "test-beheerder")
    await store.trek_in(token_read.id)

    res = test_client.get(
        "/v1/admin/api-tokens",
        headers={
            "Authorization": f"Bearer {plaintext}",
            "X-User-Id": "test-beheerder",
        },
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_verifieer_update_laatste_gebruik(tmp_path):
    """update_laatste_gebruik schrijft de timestamp best-effort zonder uitzondering."""
    from app.features.api_tokens.models import metadata
    from conftest import maak_test_engine

    engine = maak_test_engine(metadata, tmp_path=tmp_path)
    store = SqlAlchemyApiTokenStore(engine)

    token_read, plaintext = await store.maak("ltu", "beheerder")
    token_id = await store.verifieer(plaintext)
    assert token_id == token_read.id

    # Mag niet gooien
    await store.update_laatste_gebruik(token_id)
    await engine.dispose()
