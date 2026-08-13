"""Routelaag voor het berichten-domein — wat niet uit de vorm volgt (stack-profiel.md
§Feature-eenheid): auth-checks en validatie voorbij het schema. De schemaclasses (models.py)
leggen vast WAT een bericht is; ze leggen niet vast WIE iets mag — dat is gedrag, geen vorm.

Auth (`huidige_gebruiker`/`huidige_beheerder`) is een gedeelde, sterk vereenvoudigde stand-in —
zie ../../shared/auth.py voor de volledige toelichting (werkwijze-ADR-0009, feature-bouwen
regel 8).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ...db import get_engine
from ...shared.auth import huidige_beheerder, huidige_gebruiker
from .models import BerichtAdminRead, BerichtCreate, BerichtRead
from .store import BerichtenStore, BerichtNietGevonden, SqlAlchemyBerichtenStore


def get_store() -> BerichtenStore:
    """FastAPI-dependency die de router aan een concrete store koppelt (werkwijze-ADR-0007).
    Tests overschrijven dit (`app.dependency_overrides[get_store]`) met een store op een eigen,
    kortlevende engine — de routercode zelf blijft daarbij ongewijzigd."""
    return SqlAlchemyBerichtenStore(get_engine())


router = APIRouter(prefix="/berichten", tags=["berichten"])
admin_router = APIRouter(prefix="/admin/berichten", tags=["berichten-admin"])


class OngelezenAantalOut(BaseModel):
    aantal: int


class BerichtenPaginaOut(BaseModel):
    items: list[BerichtRead]
    totaal: int


class AdminBerichtenPaginaOut(BaseModel):
    items: list[BerichtAdminRead]
    totaal: int


class BerichtPublicatieIn(BaseModel):
    gepubliceerd: bool


# --- analist-endpoints ---------------------------------------------------------------


@router.get("/ongelezen-aantal", response_model=OngelezenAantalOut)
async def get_ongelezen_aantal(
    userid: str = Depends(huidige_gebruiker),
    store: BerichtenStore = Depends(get_store),
) -> OngelezenAantalOut:
    return OngelezenAantalOut(aantal=await store.ongelezen_aantal(userid))


@router.post("/lees-alles", status_code=status.HTTP_204_NO_CONTENT)
async def post_lees_alles(
    userid: str = Depends(huidige_gebruiker),
    store: BerichtenStore = Depends(get_store),
) -> None:
    await store.markeer_alles_gelezen(userid)


@router.get("", response_model=BerichtenPaginaOut)
async def lijst_berichten(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    ongelezen: bool = Query(False),
    userid: str = Depends(huidige_gebruiker),
    store: BerichtenStore = Depends(get_store),
) -> BerichtenPaginaOut:
    items, totaal = await asyncio.gather(
        store.lijst(userid, offset, limit, ongelezen_only=ongelezen),
        store.totaal(userid, ongelezen_only=ongelezen),
    )
    return BerichtenPaginaOut(items=items, totaal=totaal)


# --- admin-endpoints -------------------------------------------------------------------


@admin_router.get("", response_model=AdminBerichtenPaginaOut)
async def lijst_alle_berichten(
    offset: int = Query(0, ge=0),
    # Ruimer dan de analist-default (20): de admin-lijst toont ook concepten en dient een
    # beheeroverzicht, geen doorlopend leesscherm — overgenomen redenering uit het externe
    # project (daar roept een extern tool dit endpoint ongepagineerd aan).
    limit: int = Query(100, ge=1, le=500),
    _admin_userid: str = Depends(huidige_beheerder),
    store: BerichtenStore = Depends(get_store),
) -> AdminBerichtenPaginaOut:
    items, totaal = await asyncio.gather(store.lijst_admin(offset, limit), store.totaal_admin())
    return AdminBerichtenPaginaOut(items=items, totaal=totaal)


@admin_router.post("", response_model=BerichtAdminRead, status_code=status.HTTP_201_CREATED)
async def maak_bericht(
    body: BerichtCreate,
    admin_userid: str = Depends(huidige_beheerder),
    store: BerichtenStore = Depends(get_store),
) -> BerichtAdminRead:
    return await store.maak(body.titel, body.inhoud, body.type, body.versie, admin_userid)


@admin_router.put("/{bericht_id}", response_model=BerichtAdminRead)
async def bewerk_bericht(
    bericht_id: int,
    body: BerichtCreate,
    _admin_userid: str = Depends(huidige_beheerder),
    store: BerichtenStore = Depends(get_store),
) -> BerichtAdminRead:
    try:
        return await store.bewerk(bericht_id, body.titel, body.inhoud, body.type, body.versie)
    except BerichtNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@admin_router.patch("/{bericht_id}/publicatie", response_model=BerichtAdminRead)
async def zet_publicatie(
    bericht_id: int,
    body: BerichtPublicatieIn,
    _admin_userid: str = Depends(huidige_beheerder),
    store: BerichtenStore = Depends(get_store),
) -> BerichtAdminRead:
    try:
        return await store.zet_publicatie(bericht_id, body.gepubliceerd)
    except BerichtNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@admin_router.delete("/{bericht_id}", status_code=status.HTTP_204_NO_CONTENT)
async def verwijder_bericht(
    bericht_id: int,
    _admin_userid: str = Depends(huidige_beheerder),
    store: BerichtenStore = Depends(get_store),
) -> None:
    try:
        await store.verwijder(bericht_id)
    except BerichtNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
