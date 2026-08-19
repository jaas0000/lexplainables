"""Routelaag voor het projecten-domein — businesslogica voorbij het schema.

Alle endpoints vereisen authenticatie via `huidige_beheerder` (API_TOKEN + X-User-Id-header
vanuit de BFF). De rolfilter (analist vs. beheerder) staat in `store.py`, niet hier
(story 012 §Auth/rollen, werkwijze-ADR-0007).

SSE (`GET /v1/projecten/{id}/events`): stuurt `data: <json>\\n\\n`-events met de huidige
status en fase. De stroom sluit zodra een terminale status (klaar/fout) bereikt is.

Human-in-the-loop:
  - `POST /v1/projecten/{id}/akkoord` — zet status terug op 'actief' (background-job gaat door).
  - `POST /v1/projecten/{id}/afwijzen` — zet status op 'fout' (background-job stopt).
"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ...db import get_engine
from ...engine.orchestrator import voer_analyse_uit
from ...shared.auth import GebruikerContext, huidige_beheerder
from .models import (
    TERMINAL_STATUSSEN,
    AangemaaktAcceptatie,
    AnalyseAanmaken,
    AnalyseDetail,
    AnalyseOverzicht,
    LlmCallRead,
)
from .store import (
    AnalyseNietGevonden,
    AnalyseStore,
    SqlAlchemyAnalyseStore,
    SqlAlchemyLlmCallsStore,
)


def get_store() -> AnalyseStore:
    """FastAPI-dependency die de router aan een concrete store koppelt (werkwijze-ADR-0007)."""
    return SqlAlchemyAnalyseStore(get_engine())


def get_llm_calls_store() -> SqlAlchemyLlmCallsStore:
    """FastAPI-dependency voor de LLM-calls store (werkwijze-ADR-0007)."""
    return SqlAlchemyLlmCallsStore(get_engine())


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
    taken.add_task(_voer_analyse_uit, analyse.id, store)
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


async def _vereist_review_status(
    store: AnalyseStore, analyse_id: str, ctx: GebruikerContext
) -> None:
    """Guard: raise 404 als analyse niet bestaat, 409 als status != 'review'."""
    try:
        detail = await store.detail(analyse_id, ctx.gebruikersnaam, ctx.rol == "beheerder")
    except AnalyseNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    if detail.status != "review":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Analyse staat niet in review-status (huidige status: {detail.status}).",
        )


@router.post("/{analyse_id}/akkoord", status_code=status.HTTP_204_NO_CONTENT)
async def akkoord_analyse(
    analyse_id: str,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    store: AnalyseStore = Depends(get_store),
) -> None:
    """Human-in-the-loop: geef akkoord na act2-review.

    Zet de status terug op 'actief' zodat de background-job doorgaat naar act3.
    Geeft 404 als de analyse niet bestaat, 409 als de analyse niet in 'review' staat.
    """
    await _vereist_review_status(store, analyse_id, ctx)
    await store.zet_status(analyse_id, "actief", "Review akkoord — verdergaan met act 3")


@router.post("/{analyse_id}/afwijzen", status_code=status.HTTP_204_NO_CONTENT)
async def afwijzen_analyse(
    analyse_id: str,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    store: AnalyseStore = Depends(get_store),
) -> None:
    """Human-in-the-loop: wijs de analyse af na act2-review.

    Zet de status op 'fout' zodat de background-job stopt.
    Geeft 404 als de analyse niet bestaat, 409 als de analyse niet in 'review' staat.
    """
    await _vereist_review_status(store, analyse_id, ctx)
    await store.zet_status(analyse_id, "fout", foutmelding="Analyse afgewezen door gebruiker.")


@router.get("/{analyse_id}/llm-calls", response_model=list[LlmCallRead])
async def lijst_llm_calls(
    analyse_id: str,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    llm_store: SqlAlchemyLlmCallsStore = Depends(get_llm_calls_store),
) -> list[LlmCallRead]:
    """Geef alle vastgelegde LLM-calls voor een analyse terug (alleen beheerders).

    Lege lijst als capture uitgeschakeld was of de analyse onbekend is — geen 404.
    """
    return await llm_store.lijst_calls(analyse_id)


async def _voer_analyse_uit(analyse_id: str, store: AnalyseStore) -> None:
    """Achtergrond-job: voert de echte LLM-orkestratie uit (story 024).

    Delegeert naar engine.orchestrator.voer_analyse_uit met de engine uit get_engine().
    De store wordt meegegeven zodat tests de dependency-override doorgeven.
    """
    await voer_analyse_uit(analyse_id, store, get_engine())
