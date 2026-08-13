"""Auth-router: credential-verificatie achter API_TOKEN-gate."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db import get_engine
from app.shared.auth import vereist_api_token

from .models import VerifyRequest, VerifyResult
from .store import verifieer_credentials

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/verify", response_model=VerifyResult, dependencies=[Depends(vereist_api_token)])
async def verify(request: VerifyRequest, engine=Depends(get_engine)) -> VerifyResult:
    return await verifieer_credentials(engine, request.gebruikersnaam, request.wachtwoord)
