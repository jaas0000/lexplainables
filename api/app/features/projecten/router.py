"""Routelaag voor het projecten-domein — businesslogica voorbij het schema.

Alle endpoints vereisen authenticatie via `huidige_beheerder` (API_TOKEN + X-User-Id-header
vanuit de BFF). De rolfilter (analist vs. beheerder) staat in `store.py`, niet hier
(story 012 §Auth/rollen, werkwijze-ADR-0007).

SSE (`GET /v1/projecten/{id}/events`): stuurt `data: <json>\\n\\n`-events met de huidige
status en fase. De stroom sluit zodra een terminale status (klaar/fout) bereikt is.
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ...db import get_engine
from ...shared.auth import GebruikerContext, huidige_beheerder
from .models import (
    TERMINAL_STATUSSEN,
    AangemaaktAcceptatie,
    AnalyseAanmaken,
    AnalyseDetail,
    AnalyseOverzicht,
)
from .store import AnalyseNietGevonden, AnalyseStore, SqlAlchemyAnalyseStore


def get_store() -> AnalyseStore:
    """FastAPI-dependency die de router aan een concrete store koppelt (werkwijze-ADR-0007)."""
    return SqlAlchemyAnalyseStore(get_engine())


router = APIRouter(prefix="/projecten", tags=["projecten"])


@router.post(
    "",
    response_model=AangemaaktAcceptatie,
    status_code=status.HTTP_202_ACCEPTED,
)
async def maak_analyse(
    body: AnalyseAanmaken,
    taken: BackgroundTasks,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    store: AnalyseStore = Depends(get_store),
) -> AangemaaktAcceptatie:
    """Maak een nieuwe analyse aan en start de achtergrond-job (202 Accepted)."""
    analyse = await store.maak(
        gebruiker_id=ctx.gebruikersnaam,
        naam=body.naam,
        bronnen=body.bronnen,
        omschrijving=body.omschrijving,
        analysefocus=body.analysefocus,
        begrippenlijst=body.begrippenlijst,
        model_profiel=body.model_profiel,
        human_in_the_loop=body.human_in_the_loop,
    )
    taken.add_task(_voer_analyse_uit, analyse.id, body.human_in_the_loop, store)
    return AangemaaktAcceptatie(id=analyse.id, status=analyse.status)


@router.get("", response_model=list[AnalyseOverzicht])
async def lijst_analyses(
    ctx: GebruikerContext = Depends(huidige_beheerder),
    store: AnalyseStore = Depends(get_store),
) -> list[AnalyseOverzicht]:
    """Geef alle analyses terug die de ingelogde gebruiker mag zien."""
    return await store.lijst(ctx.gebruikersnaam, is_beheerder=ctx.rol == "beheerder")


@router.get("/{analyse_id}", response_model=AnalyseDetail)
async def detail_analyse(
    analyse_id: str,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    store: AnalyseStore = Depends(get_store),
) -> AnalyseDetail:
    """Geef het detail van één analyse terug."""
    try:
        return await store.detail(analyse_id, ctx.gebruikersnaam, ctx.rol == "beheerder")
    except AnalyseNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.delete("/{analyse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def verwijder_analyse(
    analyse_id: str,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    store: AnalyseStore = Depends(get_store),
) -> None:
    """Verwijder een analyse (eigen of, voor een beheerder, elke analyse)."""
    try:
        await store.verwijder(analyse_id, ctx.gebruikersnaam, ctx.rol == "beheerder")
    except AnalyseNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/{analyse_id}/events")
async def analyse_events(
    analyse_id: str,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    store: AnalyseStore = Depends(get_store),
) -> StreamingResponse:
    """SSE-stroom: stuurt status-updates tot de analyse terminaal is (klaar/fout)."""
    is_beheerder = ctx.rol == "beheerder"

    async def sse_generator():
        while True:
            try:
                analyse = await store.detail(analyse_id, ctx.gebruikersnaam, is_beheerder)
            except AnalyseNietGevonden:
                yield f"data: {json.dumps({'fout': 'Analyse niet gevonden.'})}\n\n"
                break
            data = json.dumps(
                {
                    "status": analyse.status,
                    "huidige_fase": analyse.huidige_fase,
                    "foutmelding": analyse.foutmelding,
                }
            )
            yield f"data: {data}\n\n"
            if analyse.status in TERMINAL_STATUSSEN:
                break
            await asyncio.sleep(1)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


async def _voer_analyse_uit(
    analyse_id: str, human_in_the_loop: bool, store: AnalyseStore | None = None
) -> None:
    """PoC-placeholder-job: simuleert een analyse met statusovergangen.

    Echte analyselogica (MCP-aanroepen, LLM-orchestratie) komt in story 013+. Deze
    implementatie simuleert de tijdvertraging en statusovergangen zodat de SSE-stroom
    en de frontend al te testen zijn.

    `store` wordt meegegeven vanuit de router zodat tests de dependency-override (test-engine)
    doorvoeren in de achtergrond-job — anders roept de job `get_engine()` aan op de
    globale engine en vindt de tabel niet in de test-database.
    """
    if store is None:
        store = SqlAlchemyAnalyseStore(get_engine())
    try:
        await asyncio.sleep(2)
        await store.zet_status(analyse_id, "actief", "Bronnen ophalen")
        await asyncio.sleep(3)
        if human_in_the_loop:
            await store.zet_status(analyse_id, "review", "Wacht op goedkeuring")
        else:
            await store.zet_status(analyse_id, "actief", "Rapport samenstellen")
            await asyncio.sleep(2)
            await store.zet_status(analyse_id, "klaar")
    except Exception as exc:  # noqa: BLE001
        await store.zet_status(analyse_id, "fout", foutmelding=str(exc))
