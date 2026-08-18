"""Auth-router: credential-verificatie en setup-flow achter API_TOKEN-gate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_engine
from app.shared.auth import vereist_api_token

from .models import GebruikerInfo, SetupStatus, SetupVerzoek, VerifyRequest, VerifyResult
from .store import GebruikerFout, maak_eerste_beheerder, tabel_leeg, verifieer_credentials

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
