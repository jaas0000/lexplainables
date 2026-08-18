"""Routelaag voor het llm_profielen-domein — businesslogica en auth-checks.

Alle endpoints zijn beheerder-only (`huidige_beheerder`). De store handhaaft de
businessregels (naam-uniciteit, standaard-flip, enig-profiel-beveiliging).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...db import get_engine
from ...shared.auth import huidige_beheerder
from ...shared.crypto import CryptoFout
from .models import LlmProfielCreate, LlmProfielRead, LlmProfielUpdate
from .store import (
    EnigeProfielFout,
    LlmProfielenStore,
    NaamConflictFout,
    ProfielNietGevonden,
    SqlAlchemyLlmProfielenStore,
)


def get_store() -> LlmProfielenStore:
    """FastAPI-dependency die de router aan een concrete store koppelt (werkwijze-ADR-0007)."""
    return SqlAlchemyLlmProfielenStore(get_engine())


admin_router = APIRouter(prefix="/admin/profielen", tags=["llm-profielen-admin"])


@admin_router.get("", response_model=list[LlmProfielRead])
async def lijst_profielen(
    _beheerder=Depends(huidige_beheerder),
    store: LlmProfielenStore = Depends(get_store),
) -> list[LlmProfielRead]:
    return await store.lijst()


@admin_router.post("", response_model=LlmProfielRead, status_code=status.HTTP_201_CREATED)
async def maak_profiel(
    body: LlmProfielCreate,
    _beheerder=Depends(huidige_beheerder),
    store: LlmProfielenStore = Depends(get_store),
) -> LlmProfielRead:
    try:
        return await store.maak(
            naam=body.naam,
            provider=body.provider,
            model=body.model,
            api_base=body.api_base,
            api_versie=body.api_versie,
            temperatuur=body.temperatuur,
            api_sleutel=body.api_sleutel,
            is_standaard=body.is_standaard,
        )
    except NaamConflictFout as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except CryptoFout as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@admin_router.put("/{naam}", response_model=LlmProfielRead)
async def bewerk_profiel(
    naam: str,
    body: LlmProfielUpdate,
    _beheerder=Depends(huidige_beheerder),
    store: LlmProfielenStore = Depends(get_store),
) -> LlmProfielRead:
    try:
        return await store.bewerk(
            naam=naam,
            provider=body.provider,
            model=body.model,
            api_base=body.api_base,
            api_versie=body.api_versie,
            temperatuur=body.temperatuur,
            api_sleutel=body.api_sleutel,
            is_standaard=body.is_standaard,
        )
    except ProfielNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except CryptoFout as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@admin_router.delete("/{naam}", status_code=status.HTTP_204_NO_CONTENT)
async def verwijder_profiel(
    naam: str,
    _beheerder=Depends(huidige_beheerder),
    store: LlmProfielenStore = Depends(get_store),
) -> None:
    try:
        await store.verwijder(naam)
    except ProfielNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except EnigeProfielFout as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
