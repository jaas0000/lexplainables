"""De ene bron voor het api_tokens-domein (werkwijze-ADR-0011).

Tabel `api_tokens` — DB-backed programmatische tokens voor externe toegang (bijv. admin-MCP).
Alleen de SHA-256-hash van het plaintext-token wordt bewaard (tokens zijn hoge-entropie;
geen bcrypt nodig). Het prefix dient als herkenbare, niet-bruikbare identificatie in de UI.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, MetaData, Table, Text

metadata = MetaData()

api_tokens = Table(
    "api_tokens",
    metadata,
    Column("id", Text(), primary_key=True),
    Column("label", Text(), nullable=False, server_default=""),
    Column("token_hash", Text(), nullable=False),
    Column("token_prefix", Text(), nullable=False),
    Column("scope", Text(), nullable=False, server_default="beheerder"),
    Column("actief", Boolean(), nullable=False, server_default="1"),
    Column("aangemaakt_door", Text(), nullable=False, server_default=""),
    Column("aangemaakt_op", DateTime(timezone=True), nullable=False),
    Column("laatste_gebruik", DateTime(timezone=True), nullable=True),
)


class ApiTokenRead(BaseModel):
    id: str
    label: str
    token_prefix: str
    scope: str
    actief: bool
    aangemaakt_door: str
    aangemaakt_op: datetime
    laatste_gebruik: datetime | None


class ApiTokenAangemaakt(ApiTokenRead):
    """Eenmalige response bij aanmaken — bevat het plaintext-token."""

    token: str


class ApiTokenAanmakenVerzoek(BaseModel):
    label: str = Field(default="", max_length=128)


def token_uit_rij(rij) -> ApiTokenRead:
    """Mapping van een DB-rij naar ApiTokenRead (werkwijze-ADR-0011 §expliciete mapping)."""
    m = dict(rij._mapping)
    return ApiTokenRead(
        id=m["id"],
        label=m["label"],
        token_prefix=m["token_prefix"],
        scope=m["scope"],
        actief=bool(m["actief"]),
        aangemaakt_door=m["aangemaakt_door"],
        aangemaakt_op=m["aangemaakt_op"],
        laatste_gebruik=m["laatste_gebruik"],
    )
