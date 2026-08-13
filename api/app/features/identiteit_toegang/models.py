"""Gebruikersmodel en auth-contracten (ADR-0003)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class GebruikerBase(SQLModel):
    gebruikersnaam: str = Field(max_length=64)
    rol: str = Field(default="beheerder")
    actief: bool = Field(default=True)


class Gebruiker(GebruikerBase, table=True):
    __tablename__ = "gebruikers"
    id: int | None = Field(default=None, primary_key=True)
    wachtwoord_hash: str
    aangemaakt_op: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VerifyRequest(SQLModel):
    gebruikersnaam: str
    wachtwoord: str


class VerifyResult(SQLModel):
    ok: bool
    gebruikersnaam: str = ""
    rol: str = ""
