"""Auth-router: credential-verificatie en accountbeheer achter API_TOKEN-gate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.db import get_engine
from app.shared.auth import GebruikerContext, huidige_beheerder, vereist_api_token

from .models import MijnProfiel, VerifyRequest, VerifyResult, WachtwoordWijzigenVerzoek
from .store import haal_gebruiker, verifieer_credentials, wijzig_eigen_wachtwoord

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/verify", response_model=VerifyResult, dependencies=[Depends(vereist_api_token)])
async def verify(request: VerifyRequest, engine=Depends(get_engine)) -> VerifyResult:
    return await verifieer_credentials(engine, request.gebruikersnaam, request.wachtwoord)


@router.get("/me", response_model=MijnProfiel)
async def me(
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> MijnProfiel:
    """Geeft de eigen accountgegevens terug van de ingelogde gebruiker."""
    return await haal_gebruiker(engine, gebruiker.gebruikersnaam)


@router.post("/wijzig-wachtwoord", status_code=status.HTTP_204_NO_CONTENT)
async def wijzig_wachtwoord(
    verzoek: WachtwoordWijzigenVerzoek,
    gebruiker: GebruikerContext = Depends(huidige_beheerder),
    engine=Depends(get_engine),
) -> None:
    """Wijzigt het eigen wachtwoord. Geeft 400 als het huidige wachtwoord onjuist is."""
    await wijzig_eigen_wachtwoord(
        engine,
        gebruiker.gebruikersnaam,
        verzoek.huidig_wachtwoord,
        verzoek.nieuw_wachtwoord,
    )
