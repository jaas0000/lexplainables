"""Store-abstractie voor het api_tokens-domein (werkwijze-ADR-0007).

`ApiTokenStore` beschrijft de operaties die router.py en shared/auth.py nodig hebben.
`SqlAlchemyApiTokenStore` is de enige implementatie (async SQLAlchemy Core).

Tokenformaat: `secrets.token_urlsafe(32)` (43 tekens, URL-veilig, hoge entropie).
Hash: SHA-256 van het plaintext-token (hex-digest). Prefix: eerste 8 tekens van de plaintext.
Het plaintext-token verlaat de server alleen bij aanmaken; daarna leeft alleen de hash in de DB.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from typing import Protocol

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared.tijd import nu
from .models import ApiTokenRead, api_tokens, token_uit_rij


def _hash(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


class ApiTokenStore(Protocol):
    async def lijst(self) -> list[ApiTokenRead]: ...

    async def maak(self, label: str, aangemaakt_door: str) -> tuple[ApiTokenRead, str]:
        """Maak een nieuw token. Geeft (read-zonder-geheim, plaintext-token)."""
        ...

    async def trek_in(self, token_id: str) -> None:
        """Trekk token in. Gooit 404 als onbekend of al ingetrokken."""
        ...

    async def verifieer(self, plaintext: str) -> str | None:
        """Hash en zoek op. Geeft token-id of None. Faalt nooit hard."""
        ...

    async def update_laatste_gebruik(self, token_id: str) -> None:
        """Schrijf laatste_gebruik best-effort. Gooit nooit een uitzondering."""
        ...


class SqlAlchemyApiTokenStore:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def lijst(self) -> list[ApiTokenRead]:
        stmt = (
            select(api_tokens)
            .where(api_tokens.c.actief.is_(True))
            .order_by(api_tokens.c.aangemaakt_op.desc())
        )
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [token_uit_rij(r) for r in rijen]

    async def maak(self, label: str, aangemaakt_door: str) -> tuple[ApiTokenRead, str]:
        plaintext = secrets.token_urlsafe(32)
        nu_ = nu()
        rij = {
            "id": uuid.uuid4().hex,
            "label": (label or "").strip()[:128],
            "token_hash": _hash(plaintext),
            "token_prefix": plaintext[:8],
            "scope": "beheerder",
            "actief": True,
            "aangemaakt_door": aangemaakt_door,
            "aangemaakt_op": nu_,
            "laatste_gebruik": None,
        }
        async with self._engine.begin() as conn:
            await conn.execute(api_tokens.insert().values(**rij))
        token_read = ApiTokenRead(
            id=rij["id"],
            label=rij["label"],
            token_prefix=rij["token_prefix"],
            scope=rij["scope"],
            actief=rij["actief"],
            aangemaakt_door=rij["aangemaakt_door"],
            aangemaakt_op=rij["aangemaakt_op"],
            laatste_gebruik=None,
        )
        return token_read, plaintext

    async def trek_in(self, token_id: str) -> None:
        async with self._engine.begin() as conn:
            res = await conn.execute(
                update(api_tokens)
                .where(api_tokens.c.id == token_id, api_tokens.c.actief.is_(True))
                .values(actief=False)
            )
        if res.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token niet gevonden of al ingetrokken.",
            )

    async def verifieer(self, plaintext: str) -> str | None:
        """Hash en zoek op in actieve tokens. Geeft token-id of None. Faalt nooit hard."""
        token_hash = _hash(plaintext)
        try:
            async with self._engine.connect() as conn:
                rij = (
                    await conn.execute(
                        select(api_tokens).where(
                            api_tokens.c.token_hash == token_hash,
                            api_tokens.c.actief.is_(True),
                        )
                    )
                ).first()
            if rij is None:
                return None
            return dict(rij._mapping)["id"]
        except Exception:  # noqa: BLE001 — DB-hapering mag geen 500 geven; behandel als geen treffer
            return None

    async def update_laatste_gebruik(self, token_id: str) -> None:
        """Schrijf laatste_gebruik. Faalt stil — best-effort, mag analyse nooit breken."""
        try:
            async with self._engine.begin() as conn:
                await conn.execute(
                    update(api_tokens)
                    .where(api_tokens.c.id == token_id)
                    .values(laatste_gebruik=nu())
                )
        except Exception:  # noqa: BLE001
            pass


async def verifieer_db_token(engine: AsyncEngine, token: str) -> bool:
    """Verifieer een plaintext-token tegen `api_tokens` en werk laatste_gebruik bij.

    Owner-export voor `shared/auth.py`: kapselt het volledige DB-verify-pad in zodat
    `shared/` niets uit `features/` hoeft te importeren buiten deze functie. Faalt nooit
    hard — bij een DB-hapering of onbekend token geeft de functie `False` terug, waarna
    de aanroeper mag doorschakelen naar een 401.
    """
    store = SqlAlchemyApiTokenStore(engine)
    token_id = await store.verifieer(token)
    if token_id is None:
        return False
    await store.update_laatste_gebruik(token_id)
    return True
