"""Gedeelde authenticatie via Keycloak JWKS (ADR-0002).

`huidige_beheerder` verifieert een Keycloak-JWT via het JWKS-endpoint en levert een
`GebruikerContext` op. De JWKS worden gecached en elke 5 minuten ververst, zodat de
verificatie niet bij elke request het netwerk op gaat.

`huidige_gebruiker` is nog een tijdelijke stand-in (header-based); vervangen in een
latere story zodra ook de gebruikersroutes Keycloak-auth krijgen.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "wetsanalyse")
_ALGORITHM = "RS256"
_JWKS_TTL = 300

_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0.0
_jwks_lock = asyncio.Lock()

_bearer = HTTPBearer(auto_error=False)


class GebruikerContext(BaseModel):
    gebruikersnaam: str
    rol: str


async def _haal_jwks_op() -> dict[str, Any]:
    global _jwks_cache, _jwks_fetched_at
    now = time.monotonic()
    if _jwks_cache and (now - _jwks_fetched_at) < _JWKS_TTL:
        return _jwks_cache
    async with _jwks_lock:
        if _jwks_cache and (time.monotonic() - _jwks_fetched_at) < _JWKS_TTL:
            return _jwks_cache
        jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=5.0)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_fetched_at = time.monotonic()
    return _jwks_cache


def _niet_geautoriseerd(detail: str = "Niet geautoriseerd.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def huidige_beheerder(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> GebruikerContext:
    if not credentials:
        raise _niet_geautoriseerd()
    # Valideer JWT-structuur vóórdat we het netwerk op gaan voor JWKS.
    try:
        jwt.get_unverified_header(credentials.credentials)
    except JWTError as exc:
        raise _niet_geautoriseerd("Ongeldig token.") from exc
    try:
        jwks = await _haal_jwks_op()
        payload = jwt.decode(
            credentials.credentials,
            jwks,
            algorithms=[_ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        bericht = str(exc).lower()
        if "expired" in bericht:
            raise _niet_geautoriseerd("Token verlopen.") from exc
        raise _niet_geautoriseerd("Ongeldig token.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authenticatieservice tijdelijk niet beschikbaar.",
        ) from exc

    rollen = payload.get("realm_access", {}).get("roles", [])
    if "beheerder" not in rollen:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Onvoldoende rechten.",
        )

    return GebruikerContext(
        gebruikersnaam=payload.get("preferred_username", "onbekend"),
        rol="beheerder",
    )


def huidige_gebruiker(x_user_id: str = Header(..., alias="X-User-Id")) -> str:
    """Tijdelijke stand-in voor gebruikersauthenticatie — wordt in een latere story
    vervangen door Keycloak-JWT-verificatie."""
    return x_user_id
