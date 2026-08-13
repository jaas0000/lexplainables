"""Gedeelde authenticatie via API_TOKEN-gate en X-User-Id-header (ADR-0003).

`huidige_beheerder` verifieert het machine-token van de BFF (constant-time vergelijking)
en leest de gebruikersidentiteit uit de X-User-Id-header die de BFF zet vanuit de
Auth.js-sessie. De BFF is verantwoordelijk voor rolautorisatie.

`vereist_api_token` is een losse dependency voor routes die wel de token maar niet de
gebruikersidentiteit nodig hebben (bijv. /v1/auth/verify).

`huidige_gebruiker` is een tijdelijke stand-in voor publieke routes (nog ongewijzigd).
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

API_TOKEN = os.environ.get("API_TOKEN", "")


class GebruikerContext(BaseModel):
    gebruikersnaam: str
    # rol is een toekomstig extensiepunt (X-Role-header zodra meerdere rollen nodig zijn).
    # Huidige waarde is altijd "beheerder" — de BFF draagt de rolautorisatie, niet de API.
    rol: str


def _niet_geautoriseerd(detail: str = "Niet geautoriseerd.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def vereist_api_token(
    authorization: str | None = Header(None),
) -> None:
    """Verifieert de API_TOKEN uit de Authorization-header (constant-time)."""
    if not API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API-token niet geconfigureerd.",
        )
    if not authorization:
        raise _niet_geautoriseerd()
    token = authorization.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token.encode(), API_TOKEN.encode()):
        raise _niet_geautoriseerd()


def huidige_beheerder(
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> GebruikerContext:
    """Verifieert API_TOKEN + leest gebruikersidentiteit uit X-User-Id-header."""
    vereist_api_token(authorization)
    if not x_user_id:
        raise _niet_geautoriseerd()
    return GebruikerContext(gebruikersnaam=x_user_id, rol="beheerder")


def huidige_gebruiker(x_user_id: str = Header(..., alias="X-User-Id")) -> str:
    """Tijdelijke stand-in voor gebruikersauthenticatie op publieke routes."""
    return x_user_id
