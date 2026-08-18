"""Auth-router: credential-verificatie, setup-flow en accountbeheer achter API_TOKEN-gate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_engine
from app.shared.auth import GebruikerContext, huidige_beheerder, vereist_api_token

from .models import (
    GebruikerInfo,
    MijnProfiel,
    SetupStatus,
    SetupVerzoek,
    VerifyRequest,
    VerifyResult,
    WachtwoordWijzigenVerzoek,
)
from .store import (
    GebruikerFout,
    GebruikerNietActief,
    WachtwoordOnjuist,
    haal_gebruiker,
    maak_eerste_beheerder,
    tabel_leeg,
    verifieer_credentials,
    wijzig_eigen_wachtwoord,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/setup-status",
    response_model=SetupStatus,
    dependencies=[Depends(vereist_api_token)],
)
async def setup_status(engine=Depends(get_engine)) -> SetupStatus:
    """Geeft aan of er al een beheerder bestaat (needs_setup = False als inrichtbaar)."""
    leeg = await tabel_leeg(engine)
    return SetupStatus(needs_setup=leeg)


@router.post(
    "/setup",
    response_model=GebruikerInfo,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(vereist_api_token)],
)
async def setup(body: SetupVerzoek, engine=Depends(get_engine)) -> GebruikerInfo:
    """Maakt de eerste beheerder aan. Retourneert 409 als de tabel al niet leeg is."""
    try:
        return await maak_eerste_beheerder(engine, body.gebruikersnaam, body.email, body.wachtwoord)
    except GebruikerFout as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


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
