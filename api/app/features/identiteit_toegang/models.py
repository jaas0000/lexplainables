"""De ene bron voor het identiteit_toegang-domein (werkwijze-ADR-0011).

Tabel `gebruikers` (migraties 0003, 0006, 0014). Zelfde patroon als `api_tokens/models.py`:
een SQLAlchemy Core `Table`, de publieke Pydantic-contracten, en expliciete mapping-functies
tussen een databaserij en die contracten.

`_GebruikerRij` is bewust geen publiek contract: het draagt `id`/`wachtwoord_hash`/
`totp_secret_enc`, velden die nooit in een API-response horen. `GebruikerRead`/`MijnProfiel`
zijn de publieke afgeleiden daarvan (zie `naar_read`/`naar_mijn_profiel`).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

import sqlalchemy as sa
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, String, Table, Text

_GEBRUIKERSNAAM_RE = re.compile(r"^[a-z0-9._-]{3,64}$")

metadata = MetaData()

gebruikers = Table(
    "gebruikers",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("gebruikersnaam", String(64), nullable=False, unique=True),
    Column("wachtwoord_hash", Text, nullable=False),
    Column("rol", String(16), nullable=False, server_default="beheerder"),
    Column("actief", Boolean, nullable=False, server_default=sa.true()),
    Column("aangemaakt_op", DateTime(timezone=True), nullable=False),
    Column("email", Text, nullable=False, server_default=""),
    Column("totp_secret_enc", Text, nullable=True),
    Column("totp_ingeschakeld", Boolean, nullable=False, server_default=sa.false()),
)


# --- Intern: volledige rij (nooit direct naar buiten) --------------------------------


class _GebruikerRij(BaseModel):
    id: int
    gebruikersnaam: str
    wachtwoord_hash: str
    rol: str
    actief: bool
    aangemaakt_op: datetime
    email: str
    totp_secret_enc: str | None
    totp_ingeschakeld: bool


def gebruiker_uit_rij(rij) -> _GebruikerRij:
    """Mapping van een databaserij naar `_GebruikerRij` (werkwijze-ADR-0011 §expliciete mapping)."""
    m = dict(rij._mapping)
    return _GebruikerRij(
        id=m["id"],
        gebruikersnaam=m["gebruikersnaam"],
        wachtwoord_hash=m["wachtwoord_hash"],
        rol=m["rol"],
        actief=m["actief"],
        aangemaakt_op=m["aangemaakt_op"],
        email=m["email"],
        totp_secret_enc=m["totp_secret_enc"],
        totp_ingeschakeld=m["totp_ingeschakeld"],
    )


# --- Publieke contracten ---------------------------------------------------------------


class SetupStatus(BaseModel):
    needs_setup: bool


class SetupVerzoek(BaseModel):
    gebruikersnaam: str = Field(max_length=64)
    email: str = Field(max_length=320)
    wachtwoord: str = Field(min_length=8, max_length=512)

    @field_validator("gebruikersnaam")
    @classmethod
    def gebruikersnaam_patroon(cls, v: str) -> str:
        if not _GEBRUIKERSNAAM_RE.match(v):
            raise ValueError(
                "Gebruikersnaam moet 3–64 tekens lang zijn en alleen a–z, 0–9, "
                "punt, underscore of koppelteken bevatten."
            )
        return v


class GebruikerInfo(BaseModel):
    gebruikersnaam: str
    email: str
    rol: str


class GebruikerRead(BaseModel):
    gebruikersnaam: str
    rol: str
    actief: bool
    aangemaakt_op: datetime


def naar_read(g: _GebruikerRij) -> GebruikerRead:
    return GebruikerRead(
        gebruikersnaam=g.gebruikersnaam,
        rol=g.rol,
        actief=g.actief,
        aangemaakt_op=g.aangemaakt_op,
    )


class GebruikerCreate(BaseModel):
    gebruikersnaam: str = Field(max_length=64)
    wachtwoord: str = Field(min_length=8)
    rol: Literal["beheerder", "analist"] = Field(default="analist")


class GebruikerPatch(BaseModel):
    rol: Literal["beheerder", "analist"] | None = None
    actief: bool | None = None

    @model_validator(mode="after")
    def _minstens_een_veld(self) -> GebruikerPatch:
        if self.rol is None and self.actief is None:
            raise ValueError("Geef ten minste 'rol' of 'actief' op.")
        return self


class TijdelijkWachtwoord(BaseModel):
    gebruikersnaam: str
    tijdelijk_wachtwoord: str


class VerifyRequest(BaseModel):
    gebruikersnaam: str
    wachtwoord: str
    totp: str | None = Field(default=None, max_length=16)


class VerifyResult(BaseModel):
    ok: bool
    gebruikersnaam: str = ""
    rol: str = ""
    # `""` bij ok=True, `"invalid"` bij foute credentials/TOTP, `"totp_required"` als het
    # wachtwoord klopt maar 2FA aan staat zonder meegestuurde `totp`.
    code: str = ""


class TotpBeginResultaat(BaseModel):
    """Retour van POST /v1/auth/2fa/begin — de `otpauth://`-URI voor de QR-code."""

    otpauth_uri: str


class TotpCodeVerzoek(BaseModel):
    """Body van POST /v1/auth/2fa/activeer en /uitschakel."""

    totp: str = Field(min_length=6, max_length=16)


class MijnProfiel(BaseModel):
    """Eigen accountgegevens — teruggegeven door GET /v1/auth/me.

    `actief` is er expliciet zodat een consument (bijv. de frontend Auth.js live-rol-check,
    fase 2b.3) na een periodieke fetch direct kan zien of het account nog geldig is. De
    endpoint retourneert 401 op een inactieve gebruiker, dus in de praktijk komt hier alleen
    `actief=true` binnen — het veld is de expliciete tegenpool van die 401.
    """

    naam: str
    gebruikersnaam: str
    rol: str
    actief: bool
    totp_ingeschakeld: bool


def naar_mijn_profiel(g: _GebruikerRij) -> MijnProfiel:
    return MijnProfiel(
        naam=g.gebruikersnaam,
        gebruikersnaam=g.gebruikersnaam,
        rol=g.rol,
        actief=g.actief,
        totp_ingeschakeld=g.totp_ingeschakeld,
    )


class WachtwoordWijzigenVerzoek(BaseModel):
    """Verzoek om het eigen wachtwoord te wijzigen — body van POST /v1/auth/wijzig-wachtwoord."""

    huidig_wachtwoord: str = Field(max_length=512)
    nieuw_wachtwoord: str = Field(min_length=8, max_length=512)
