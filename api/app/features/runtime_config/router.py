"""Routelaag voor het runtime_config-domein — auth-checks en endpoint-koppeling.

Beide endpoints zijn beheerder-only (`huidige_beheerder`). De store handhaaft
businessregels (TTL-cache, standaardwaarden, upsert).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...db import get_engine
from ...shared.auth import huidige_beheerder
from .models import AppInstellingen, AppInstellingenPatch
from .store import RuntimeConfigStore


def get_store() -> RuntimeConfigStore:
    """FastAPI-dependency die de router aan een concrete store koppelt (werkwijze-ADR-0007)."""
    return RuntimeConfigStore(get_engine())


admin_router = APIRouter(prefix="/admin/instellingen", tags=["runtime-config-admin"])


@admin_router.get("", response_model=AppInstellingen)
async def lees_instellingen(
    _beheerder=Depends(huidige_beheerder),
    store: RuntimeConfigStore = Depends(get_store),
) -> AppInstellingen:
    return await store.lees_alle()


@admin_router.put("", response_model=AppInstellingen)
async def pas_instellingen_aan(
    body: AppInstellingenPatch,
    _beheerder=Depends(huidige_beheerder),
    store: RuntimeConfigStore = Depends(get_store),
) -> AppInstellingen:
    return await store.schrijf(body)
