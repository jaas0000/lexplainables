"""Routelaag voor het wetcatalogus-domein — feature-bouwen regel 5: auth-checks en
businesslogica die niet uit de vorm (models.py) volgen.

Auth: alle endpoints vereisen een ingelogde gebruiker (`huidige_gebruiker`). Geen
rolbeperking — zowel analisten als beheerders mogen de catalogus raadplegen (story 010 §Auth).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...shared.auth import huidige_gebruiker
from .models import WetKeuze, WetStructuur
from .store import HardgecodeerdeWetcatalogusStore, WetcatalogusStore, WetNietGevonden

router = APIRouter(prefix="/wetten", tags=["wetcatalogus"])


def get_store() -> WetcatalogusStore:
    """FastAPI-dependency — tests overschrijven dit via `app.dependency_overrides[get_store]`."""
    return HardgecodeerdeWetcatalogusStore()


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
