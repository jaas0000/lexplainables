"""Auth-router en admin-router voor gebruikersbeheer.

auth-router: credential-verificatie achter API_TOKEN-gate.
admin_router: beheerder-only CRUD voor gebruikersaccounts (werkwijze-ADR-0003).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_engine
from app.shared.auth import GebruikerContext, huidige_beheerder, vereist_api_token

from .models import (
    GebruikerCreate,
    GebruikerPatch,
    GebruikerRead,
    TijdelijkWachtwoord,
    VerifyRequest,
    VerifyResult,
)
from .store import (
    GELDIGE_ROLLEN,
    GebruikerNietGevonden,
    GebruikersnaamAlInGebruik,
    LaatsteBeheerder,
    lijst_gebruikers,
    maak_gebruiker_admin,
    reset_wachtwoord,
    verifieer_credentials,
    verwijder_gebruiker,
    wijzig_gebruiker,
)

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin/gebruikers", tags=["gebruikers-admin"])


@router.post("/verify", response_model=VerifyResult, dependencies=[Depends(vereist_api_token)])
async def verify(request: VerifyRequest, engine=Depends(get_engine)) -> VerifyResult:
    return await verifieer_credentials(engine, request.gebruikersnaam, request.wachtwoord)


# ---- Admin-endpoints -------------------------------------------------------


@admin_router.get("", response_model=list[GebruikerRead])
async def haal_gebruikers_op(
    _ctx: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> list[GebruikerRead]:
    return await lijst_gebruikers(engine)


@admin_router.post("", response_model=GebruikerRead, status_code=status.HTTP_201_CREATED)
async def maak_gebruiker_aan(
    body: GebruikerCreate,
    _ctx: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> GebruikerRead:
    if body.rol not in GELDIGE_ROLLEN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ongeldige rol '{body.rol}'. Kies uit: {sorted(GELDIGE_ROLLEN)}.",
        )
    try:
        return await maak_gebruiker_admin(engine, body.gebruikersnaam, body.wachtwoord, body.rol)
    except GebruikersnaamAlInGebruik as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Gebruikersnaam '{body.gebruikersnaam}' is al in gebruik.",
        ) from exc


@admin_router.patch("/{gebruikersnaam}", response_model=GebruikerRead)
async def wijzig_gebruiker_endpoint(
    gebruikersnaam: str,
    body: GebruikerPatch,
    _ctx: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> GebruikerRead:
    if body.rol is not None and body.rol not in GELDIGE_ROLLEN:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ongeldige rol '{body.rol}'. Kies uit: {sorted(GELDIGE_ROLLEN)}.",
        )
    try:
        return await wijzig_gebruiker(engine, gebruikersnaam, rol=body.rol, actief=body.actief)
    except GebruikerNietGevonden as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gebruiker niet gevonden."
        ) from exc
    except LaatsteBeheerder as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kan de laatste actieve beheerder niet deactiveren of degraderen.",
        ) from exc


@admin_router.post("/{gebruikersnaam}/reset-wachtwoord", response_model=TijdelijkWachtwoord)
async def reset_wachtwoord_endpoint(
    gebruikersnaam: str,
    _ctx: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> TijdelijkWachtwoord:
    try:
        return await reset_wachtwoord(engine, gebruikersnaam)
    except GebruikerNietGevonden as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gebruiker niet gevonden."
        ) from exc


@admin_router.delete("/{gebruikersnaam}", status_code=status.HTTP_204_NO_CONTENT)
async def verwijder_gebruiker_endpoint(
    gebruikersnaam: str,
    ctx: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> None:
    try:
        await verwijder_gebruiker(engine, gebruikersnaam, ingelogd_als=ctx.gebruikersnaam)
    except GebruikerNietGevonden as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gebruiker niet gevonden."
        ) from exc
    except LaatsteBeheerder as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kan de laatste actieve beheerder niet verwijderen.",
        ) from exc
