"""Fernet-versleuteling voor secrets die via de admin-UI in de database terechtkomen.

Symmetrisch (Fernet/AES-128-CBC + HMAC) met één master key, gelezen uit het bestand waarnaar
`FERNET_KEY_FILE` wijst (werkwijze-ADR-0006 — nooit een platte env-var-waarde). De master key
zelf staat nooit in de database, alleen in dat bestand. Ontbreekt de master key, dan mislukt het
opslaan van een API-sleutel expliciet (fail-closed — nooit plaintext bewaren).

Genereer een geldige Fernet-key met:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Gedeelde module (feature-bouwen regel 8): heeft geen natuurlijke eigenaar-feature —
versleuteling is een infrastructurele zorg, niet gebonden aan één domein.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


class CryptoFout(RuntimeError):
    """Versleutelen/ontsleutelen lukt niet — master key ontbreekt of is ongeldig."""


@lru_cache
def _fernet():
    from cryptography.fernet import Fernet

    pad = os.environ.get("FERNET_KEY_FILE")
    sleutel = Path(pad).read_text(encoding="utf-8").strip() if pad else ""
    if not sleutel:
        return None
    try:
        return Fernet(sleutel.encode("utf-8"))
    except (ValueError, TypeError) as e:
        raise CryptoFout(
            "FERNET_KEY_FILE bevat geen geldige Fernet-key (32 url-safe base64-bytes)."
        ) from e


def encrypt(plaintext: str) -> str:
    """Versleutel een string. Gooit `CryptoFout` als er geen FERNET_KEY_FILE is."""
    f = _fernet()
    if f is None:
        raise CryptoFout(
            "Geen FERNET_KEY_FILE geconfigureerd; kan API-sleutel niet versleuteld opslaan."
        )
    return f.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    """Ontsleutel een Fernet-token. Gooit `CryptoFout` bij ontbrekende of verkeerde key."""
    f = _fernet()
    if f is None:
        raise CryptoFout(
            "Geen FERNET_KEY_FILE geconfigureerd; kan opgeslagen API-sleutel niet ontsleutelen."
        )
    from cryptography.fernet import InvalidToken

    try:
        return f.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise CryptoFout(
            "Kan opgeslagen API-sleutel niet ontsleutelen "
            "(verkeerde of geroteerde FERNET_KEY_FILE?)."
        ) from e
