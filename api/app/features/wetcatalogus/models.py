"""De ene bron voor het wetcatalogus-domein (werkwijze-ADR-0011).

Story 020 breidt story 010 uit: de catalogus is nu database-backed via een
SQLAlchemy Core Table. Bestaande modellen (WetKeuze, ArtikelKeuze, WetStructuur)
zijn ongewijzigd; WetCreate, WetRead en ResolveResultaat zijn nieuw.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, MetaData, Table, Text

metadata = MetaData()

wet_catalogus = Table(
    "wet_catalogus",
    metadata,
    Column("bwb_id", Text, primary_key=True),
    Column("naam", Text, nullable=False),
    Column("bijgewerkt_door", Text, nullable=False, server_default=""),
    Column("bijgewerkt", DateTime(timezone=True), nullable=False),
)


# --- bestaande modellen (story 010 — ongewijzigd) ----------------------------


class WetKeuze(BaseModel):
    """Één beschikbare wet — bwb-id + leesbare naam."""

    bwb_id: str
    naam: str


class ArtikelKeuze(BaseModel):
    """Één artikel binnen een wet — artikelnummer + padnotatie (hoofdstuk / artikel)."""

    artikel: str
    pad: str


class WetStructuur(BaseModel):
    """Artikel-structuur van één wet."""

    bwb_id: str
    artikelen: list[ArtikelKeuze]


# --- nieuwe modellen (story 020) ----------------------------------------------


class WetCreate(BaseModel):
    """Wat een beheerder meestuurt bij het aanmaken of bijwerken van een wet."""

    bwb_id: str = Field(..., min_length=1)
    naam: str = Field(..., min_length=1, max_length=256)


class WetRead(BaseModel):
    """Wat de admin-API teruggeeft — inclusief beheermetadata."""

    bwb_id: str
    naam: str
    bijgewerkt_door: str
    bijgewerkt: str  # ISO-8601-string; datetime blijft intern, string verlaat de API


class ResolveResultaat(BaseModel):
    """Resultaat van een resolve-aanroep: de officiële citeertitel."""

    naam: str


def wet_uit_rij(rij) -> WetRead:
    """Expliciete mapping tussen databaserij en het Read-contract (werkwijze-ADR-0011)."""
    bijgewerkt = rij.bijgewerkt
    if hasattr(bijgewerkt, "isoformat"):
        bijgewerkt_str = bijgewerkt.isoformat()
    else:
        bijgewerkt_str = str(bijgewerkt)
    return WetRead(
        bwb_id=rij.bwb_id,
        naam=rij.naam,
        bijgewerkt_door=rij.bijgewerkt_door,
        bijgewerkt=bijgewerkt_str,
    )
