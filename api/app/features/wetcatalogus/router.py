"""Routelaag voor het wetcatalogus-domein — feature-bouwen regel 5.

Story 010: analist-endpoints (GET /v1/wetten, GET /v1/wetten/{bwb_id}/structuur).
Story 020: admin-endpoints (GET/PUT/DELETE /v1/admin/wetten,
POST /v1/admin/wetten/{bwb_id}/resolve).

Resolve-endpoint: delegeert de MCP-aanroep aan `shared/wettenbank.haal_citeertitel_op` en
vertaalt `WettenbankNietBereikbaar` → 502, `WettenbankNietGevonden` → 404.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...db import get_engine
from ...shared.auth import GebruikerContext, huidige_beheerder, huidige_gebruiker
from ...shared.wettenbank import (
    WettenbankNietBereikbaar,
    WettenbankNietGevonden,
    haal_citeertitel_op,
)
from .models import ResolveResultaat, WetCreate, WetKeuze, WetRead, WetStructuur
from .store import DatabaseWetcatalogusStore, WetcatalogusStore, WetNietGevonden

router = APIRouter(prefix="/wetten", tags=["wetcatalogus"])
admin_router = APIRouter(prefix="/admin/wetten", tags=["wetcatalogus-admin"])


def get_store() -> WetcatalogusStore:
    """FastAPI-dependency — tests overschrijven dit via `app.dependency_overrides[get_store]`."""
    return DatabaseWetcatalogusStore(get_engine())


# --- analist-endpoints (story 010 — ongewijzigd qua contract) -----------------


@router.get("", response_model=list[WetKeuze])
async def lijst_wetten(
    _gebruiker: str = Depends(huidige_gebruiker),
    store: WetcatalogusStore = Depends(get_store),
) -> list[WetKeuze]:
    """Lijst van beschikbare wetten (bwb-id + naam). Vereist een ingelogde gebruiker."""
    return await store.lijst()


@router.get("/{bwb_id}/structuur", response_model=WetStructuur)
async def get_wet_structuur(
    bwb_id: str,
    _gebruiker: str = Depends(huidige_gebruiker),
    store: WetcatalogusStore = Depends(get_store),
) -> WetStructuur:
    """Artikel-structuur van één wet. Geeft 404 bij een onbekend bwb_id."""
    try:
        return await store.structuur(bwb_id)
    except WetNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


# --- admin-endpoints (story 020) ----------------------------------------------


@admin_router.get("", response_model=list[WetRead])
async def admin_lijst_wetten(
    _beheerder: GebruikerContext = Depends(huidige_beheerder),
    store: WetcatalogusStore = Depends(get_store),
) -> list[WetRead]:
    """Lijst catalogus-items inclusief beheermetadata. Alleen voor beheerders."""
    return await store.lijst_met_metadata()


@admin_router.put("/{bwb_id}", response_model=WetRead)
async def admin_upsert_wet(
    bwb_id: str,
    body: WetCreate,
    beheerder: GebruikerContext = Depends(huidige_beheerder),
    store: WetcatalogusStore = Depends(get_store),
) -> WetRead:
    """Voeg een wet toe of werk bestaande bij. Beheerder-only."""
    return await store.upsert(bwb_id, naam=body.naam, bijgewerkt_door=beheerder.gebruikersnaam)


@admin_router.delete("/{bwb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_verwijder_wet(
    bwb_id: str,
    _beheerder: GebruikerContext = Depends(huidige_beheerder),
    store: WetcatalogusStore = Depends(get_store),
) -> None:
    """Verwijder een wet uit de catalogus. Geeft 404 als het bwb-id onbekend is."""
    try:
        await store.verwijder(bwb_id)
    except WetNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@admin_router.post("/{bwb_id}/resolve", response_model=ResolveResultaat)
async def admin_resolve_wet(
    bwb_id: str,
    _beheerder: GebruikerContext = Depends(huidige_beheerder),
) -> ResolveResultaat:
    """Haal de officiële citeertitel van een wet op via de Wettenbank-MCP.

    Geeft 502 als de MCP tijdelijk niet bereikbaar is.
    Geeft 404 als het bwb-id onbekend is bij de Wettenbank.
    """
    try:
        naam = await haal_citeertitel_op(bwb_id)
    except WettenbankNietBereikbaar as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Wettenbank tijdelijk niet bereikbaar.",
        ) from exc
    except WettenbankNietGevonden as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Wet niet gevonden in de Wettenbank.",
        ) from exc
    return ResolveResultaat(naam=naam)
