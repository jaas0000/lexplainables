"""Routelaag voor het projecten-domein.

Elke request vereist authenticatie via `huidige_beheerder` (API_TOKEN + X-User-Id-header
vanuit de BFF). De rolfilter (analist ziet alleen eigen, beheerder ziet alles) staat in
`store.py`, niet hier (werkwijze-ADR-0007).

Een werkgebied bevat naam + bronnen (bwb_id/artikel/lid) + optionele omschrijving. De
LLM-calls-log per werkgebied is een read-only endpoint (blijft nuttig voor annotatie-runs die
LLM-calls hebben vastgelegd via `runtime_config.capture_llm_calls`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...db import get_engine
from ...shared.auth import GebruikerContext, huidige_beheerder
from ..llm_calls.dependencies import get_llm_calls_store
from ..llm_calls.models import LlmCallRead
from ..llm_calls.store import SqlAlchemyLlmCallsStore
from .models import (
    AangemaaktAcceptatie,
    AnalyseAanmaken,
    AnalyseDetail,
    AnalyseOverzicht,
)
from .store import (
    AnalyseNietGevonden,
    AnalyseStore,
    SqlAlchemyAnalyseStore,
)


def get_store() -> AnalyseStore:
    """FastAPI-dependency die de router aan een concrete store koppelt (werkwijze-ADR-0007)."""
    return SqlAlchemyAnalyseStore(get_engine())


router = APIRouter(prefix="/projecten", tags=["projecten"])


@router.post(
    "",
    response_model=AangemaaktAcceptatie,
    status_code=status.HTTP_201_CREATED,
)
async def maak_analyse(
    body: AnalyseAanmaken,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    store: AnalyseStore = Depends(get_store),
) -> AangemaaktAcceptatie:
    """Maak een nieuw werkgebied aan."""
    analyse = await store.maak(
        gebruiker_id=ctx.gebruikersnaam,
        naam=body.naam,
        bronnen=body.bronnen,
        omschrijving=body.omschrijving,
    )
    return AangemaaktAcceptatie(id=analyse.id, status=analyse.status)


@router.get("", response_model=list[AnalyseOverzicht])
async def lijst_analyses(
    ctx: GebruikerContext = Depends(huidige_beheerder),
    store: AnalyseStore = Depends(get_store),
) -> list[AnalyseOverzicht]:
    """Geef alle werkgebieden terug die de ingelogde gebruiker mag zien."""
    return await store.lijst(ctx.gebruikersnaam, is_beheerder=ctx.rol == "beheerder")


@router.get("/{analyse_id}", response_model=AnalyseDetail)
async def detail_analyse(
    analyse_id: str,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    store: AnalyseStore = Depends(get_store),
) -> AnalyseDetail:
    """Geef het detail van één werkgebied terug."""
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
    """Verwijder een werkgebied (eigen of, voor een beheerder, elke)."""
    try:
        await store.verwijder(analyse_id, ctx.gebruikersnaam, ctx.rol == "beheerder")
    except AnalyseNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/{analyse_id}/llm-calls", response_model=list[LlmCallRead])
async def lijst_llm_calls(
    analyse_id: str,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    llm_store: SqlAlchemyLlmCallsStore = Depends(get_llm_calls_store),
) -> list[LlmCallRead]:
    """Geef alle vastgelegde LLM-calls voor een werkgebied terug (alleen beheerders).

    Lege lijst als capture uitgeschakeld was of het werkgebied onbekend is — geen 404.
    """
    return await llm_store.lijst_calls(analyse_id)
