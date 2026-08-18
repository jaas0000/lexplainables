"""Auth-router en admin-router voor gebruikersbeheer.

auth-router: credential-verificatie en accountbeheer achter API_TOKEN-gate.
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
    MijnProfiel,
    TijdelijkWachtwoord,
    VerifyRequest,
    VerifyResult,
    WachtwoordWijzigenVerzoek,
)
from .store import (
    GELDIGE_ROLLEN,
    GebruikerNietActief,
    GebruikerNietGevonden,
    GebruikersnaamAlInGebruik,
    LaatsteBeheerder,
    WachtwoordOnjuist,
    haal_gebruiker,
    lijst_gebruikers,
    maak_gebruiker_admin,
    reset_wachtwoord,
    verifieer_credentials,
    verwijder_gebruiker,
    wijzig_eigen_wachtwoord,
    wijzig_gebruiker,
)

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin/gebruikers", tags=["gebruikers-admin"])


@router.post("/verify", response_model=VerifyResult, dependencies=[Depends(vereist_api_token)])
async def verify(request: VerifyRequest, engine=Depends(get_engine)) -> VerifyResult:
    return await verifieer_credentials(engine, request.gebruikersnaam, request.wachtwoord)


@router.get("/me", response_model=MijnProfiel)
async def me(
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> MijnProfiel:
    """Geeft de eigen accountgegevens terug van de ingelogde gebruiker."""
    try:
        return await haal_gebruiker(engine, gebruiker.gebruikersnaam)
    except GebruikerNietActief as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account niet (meer) actief.",
        ) from exc


@router.post("/wijzig-wachtwoord", status_code=status.HTTP_204_NO_CONTENT)
async def wijzig_wachtwoord(
    verzoek: WachtwoordWijzigenVerzoek,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> None:
    """Wijzigt het eigen wachtwoord. Geeft 400 als het huidige wachtwoord onjuist is."""
    try:
        await wijzig_eigen_wachtwoord(
            engine,
            gebruiker.gebruikersnaam,
            verzoek.huidig_wachtwoord,
            verzoek.nieuw_wachtwoord,
        )
    except GebruikerNietActief as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account niet (meer) actief.",
        ) from exc
    except WachtwoordOnjuist as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Huidig wachtwoord klopt niet.",
        ) from exc


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
