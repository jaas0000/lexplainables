"""Gedeelde authenticatie via API_TOKEN-gate en X-User-Id-header (ADR-0003).

`huidige_beheerder` verifieert het machine-token van de BFF (twee bronnen: statische env-var
en DB-tokens uit `api_tokens`) en leest de gebruikersidentiteit uit de X-User-Id-header die
de BFF zet vanuit de Auth.js-sessie. De BFF is verantwoordelijk voor rolautorisatie.

`vereist_api_token` is een losse dependency voor routes die wel de token maar niet de
gebruikersidentiteit nodig hebben (bijv. /v1/auth/verify). De verificatievolgorde:
1. Statische `API_TOKEN` uit de omgeving (constant-time vergelijking) — bootstrap-pad.
2. DB-tokens uit `api_tokens`-tabel (SHA-256-hash-lookup) — intrekbaar, per beheerder.
Bij een DB-treffer wordt `laatste_gebruik` best-effort bijgeschreven.

`huidige_gebruiker` is een tijdelijke stand-in voor publieke routes (nog ongewijzigd).
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from ..db import get_engine
from ..features.api_tokens.store import verifieer_db_token

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


async def vereist_api_token(
    authorization: str | None = Header(None),
) -> None:
    """Verifieert het token uit de Authorization-header via twee bronnen.

    Bron 1: statische API_TOKEN (constant-time). Bron 2: DB-tokens (SHA-256-hash).
    Bij een DB-treffer: `laatste_gebruik` best-effort bijwerken.
    """
    if not authorization:
        raise _niet_geautoriseerd()

    token = authorization.removeprefix("Bearer ").strip()

    # 1. Statische token — bootstrap-pad, werkt ook zonder database.
    if API_TOKEN and hmac.compare_digest(token.encode(), API_TOKEN.encode()):
        return

    # 2. DB-tokens — owner-export uit api_tokens.store, DB-fouten worden daar afgevangen.
    if await verifieer_db_token(get_engine(), token):
        return

    raise _niet_geautoriseerd()


async def huidige_beheerder(
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
) -> GebruikerContext:
    """Verifieert API_TOKEN (statisch of DB) + leest gebruikersidentiteit uit X-User-Id-header."""
    await vereist_api_token(authorization)
    if not x_user_id:
        raise _niet_geautoriseerd()
    return GebruikerContext(gebruikersnaam=x_user_id, rol="beheerder")


def huidige_gebruiker(x_user_id: str = Header(..., alias="X-User-Id")) -> str:
    """Tijdelijke stand-in voor gebruikersauthenticatie op publieke routes."""
    return x_user_id
