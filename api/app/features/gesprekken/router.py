"""Routelaag voor het gesprekken-domein (zie `__init__.py`).

Businessregels die niet uit de modellen volgen:
- Eigenaarschap: een gebruiker ziet en muteert alleen zijn eigen gesprekken — onbekend of
  andermans gesprek geeft een 404 (niet 403), zodat het bestaan niet lekt.
- `POST .../berichten` is idempotent op `run_id` (afgedwongen in de store, niet hier).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...db import get_engine
from ...shared.auth import GebruikerContext, huidige_beheerder
from .models import (
    Bericht,
    BerichtInvoer,
    Gesprek,
    GesprekAanmaken,
    GesprekHernoemen,
    GesprekSamenvatting,
)
from .store import GesprekStore, SqlAlchemyGesprekStore

router = APIRouter(prefix="/gesprekken", tags=["gesprekken"])


def get_store() -> GesprekStore:
    return SqlAlchemyGesprekStore(get_engine())


async def _laad_eigen_gesprek(gesprek_id: str, gebruiker: str, store: GesprekStore) -> Gesprek:
    gesprek = await store.laad_gesprek(gesprek_id)
    if gesprek is None or gesprek.gebruiker != gebruiker:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gesprek niet gevonden.")
    return gesprek


@router.post("", response_model=Gesprek, status_code=status.HTTP_201_CREATED)
async def maak_gesprek(
    body: GesprekAanmaken,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    store: GesprekStore = Depends(get_store),
) -> Gesprek:
    gesprek = Gesprek(
        id=uuid.uuid4().hex[:16], gebruiker=gebruiker.gebruikersnaam, titel=body.titel
    )
    return await store.maak_gesprek(gesprek)


@router.get("", response_model=list[GesprekSamenvatting])
async def lijst_gesprekken(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    store: GesprekStore = Depends(get_store),
) -> list[GesprekSamenvatting]:
    return await store.lijst_samenvattingen(gebruiker.gebruikersnaam, limit, offset)


@router.get("/{gesprek_id}", response_model=Gesprek)
async def haal_gesprek(
    gesprek_id: str,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    store: GesprekStore = Depends(get_store),
) -> Gesprek:
    return await _laad_eigen_gesprek(gesprek_id, gebruiker.gebruikersnaam, store)


@router.post("/{gesprek_id}/berichten", response_model=Bericht, status_code=status.HTTP_201_CREATED)
async def voeg_bericht_toe(
    gesprek_id: str,
    body: BerichtInvoer,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    store: GesprekStore = Depends(get_store),
) -> Bericht:
    await _laad_eigen_gesprek(gesprek_id, gebruiker.gebruikersnaam, store)
    return await store.voeg_bericht_toe(gesprek_id, body)


@router.patch("/{gesprek_id}", response_model=Gesprek)
async def hernoem_gesprek(
    gesprek_id: str,
    body: GesprekHernoemen,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    store: GesprekStore = Depends(get_store),
) -> Gesprek:
    await _laad_eigen_gesprek(gesprek_id, gebruiker.gebruikersnaam, store)
    await store.hernoem_gesprek(gesprek_id, body.titel)
    return await _laad_eigen_gesprek(gesprek_id, gebruiker.gebruikersnaam, store)


@router.delete("/{gesprek_id}", status_code=status.HTTP_204_NO_CONTENT)
async def verwijder_gesprek(
    gesprek_id: str,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    store: GesprekStore = Depends(get_store),
) -> None:
    await _laad_eigen_gesprek(gesprek_id, gebruiker.gebruikersnaam, store)
    await store.verwijder_gesprek(gesprek_id)
