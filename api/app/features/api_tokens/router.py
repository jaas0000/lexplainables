"""Routelaag voor het api_tokens-domein — auth-checks en endpoint-koppeling.

Alle drie endpoints zijn beheerder-only (`huidige_beheerder`). De store bevat de tokenlogica
(aanmaken, intrekken, verifiëren). Aangemaakt_door wordt gezet vanuit de beheerder-context.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...db import get_engine
from ...shared.auth import GebruikerContext, huidige_beheerder
from .models import ApiTokenAangemaakt, ApiTokenAanmakenVerzoek, ApiTokenRead
from .store import SqlAlchemyApiTokenStore


def get_store() -> SqlAlchemyApiTokenStore:
    """FastAPI-dependency die de router aan een concrete store koppelt (werkwijze-ADR-0007)."""
    return SqlAlchemyApiTokenStore(get_engine())


admin_router = APIRouter(prefix="/admin/api-tokens", tags=["api-tokens-admin"])


@admin_router.get("", response_model=list[ApiTokenRead])
async def lijst_tokens(
    beheerder: GebruikerContext = Depends(huidige_beheerder),
    store: SqlAlchemyApiTokenStore = Depends(get_store),
) -> list[ApiTokenRead]:
    """Lijst alle actieve API-tokens. Bevat nooit het plaintext-token."""
    return await store.lijst()


@admin_router.post("", response_model=ApiTokenAangemaakt, status_code=status.HTTP_201_CREATED)
async def maak_token(
    body: ApiTokenAanmakenVerzoek,
    beheerder: GebruikerContext = Depends(huidige_beheerder),
    store: SqlAlchemyApiTokenStore = Depends(get_store),
) -> ApiTokenAangemaakt:
    """Maak een nieuw API-token. Het plaintext-token is eenmalig zichtbaar in de response."""
    token_read, plaintext = await store.maak(body.label, beheerder.gebruikersnaam)
    return ApiTokenAangemaakt(**token_read.model_dump(), token=plaintext)


@admin_router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def trek_token_in(
    token_id: str,
    beheerder: GebruikerContext = Depends(huidige_beheerder),
    store: SqlAlchemyApiTokenStore = Depends(get_store),
) -> Response:
    """Trek een token in. 404 als het token onbekend is of al ingetrokken was."""
    await store.trek_in(token_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
