"""Gebruikersmodel en auth-contracten (ADR-0003)."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from pydantic import field_validator
from sqlmodel import Field, SQLModel

_GEBRUIKERSNAAM_RE = re.compile(r"^[a-z0-9._-]{3,64}$")


class GebruikerBase(SQLModel):
    gebruikersnaam: str = Field(max_length=64)
    rol: str = Field(default="beheerder")
    actief: bool = Field(default=True)


class Gebruiker(GebruikerBase, table=True):
    __tablename__ = "gebruikers"
    id: int | None = Field(default=None, primary_key=True)
    wachtwoord_hash: str
    email: str = Field(default="", max_length=320)
    aangemaakt_op: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SetupStatus(SQLModel):
    needs_setup: bool


class SetupVerzoek(SQLModel):
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


class GebruikerInfo(SQLModel):
    gebruikersnaam: str
    email: str
    rol: str


class VerifyRequest(SQLModel):
    gebruikersnaam: str
    wachtwoord: str


class VerifyResult(SQLModel):
    ok: bool
    gebruikersnaam: str = ""
    rol: str = ""
