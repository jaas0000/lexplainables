"""De ene bron voor het projecten-domein (werkwijze-ADR-0011).

Één entiteit: `analyses` — het werkgebied dat een ingelogde gebruiker aanmaakt om vervolgens
in de werkplek te annoteren. Per werkgebied: naam, bronartikelen, optionele omschrijving en
metadata (aangemaakt, bijgewerkt, gebruiker).

Legacy: de JAS-pipeline (act2/act3, review-flow, rapport) is verwijderd (migratie 0012);
alleen annotatie blijft als analyse-stap. Zie `docs/project/migratie-wetsanalyse.md`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Index,
    MetaData,
    String,
    Table,
    Text,
)

AnalyseStatus = Literal["nieuw"]

metadata = MetaData()

analyses = Table(
    "analyses",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("naam", String(256), nullable=True),
    Column("status", String(32), nullable=False),
    Column("bronnen", JSON, nullable=False),
    Column("omschrijving", Text, nullable=True),
    Column("aangemaakt", DateTime(timezone=True), nullable=False),
    Column("bijgewerkt", DateTime(timezone=True), nullable=False),
    Column("gebruiker_id", String(128), nullable=False),
    Index("ix_analyses_gebruiker_id", "gebruiker_id"),
    Index("ix_analyses_bijgewerkt", "bijgewerkt"),
)

# ─── Pydantic-modellen (contract) ────────────────────────────────────────────


class BronKeuze(BaseModel):
    """Één bronartikel: wet-id, artikelnummer en optioneel lidnummer."""

    bwb_id: str
    artikel: str
    lid: str | None = None


class AnalyseAanmaken(BaseModel):
    """Wat een ingelogde gebruiker meestuurt bij het aanmaken van een werkgebied."""

    naam: str | None = None
    bronnen: list[BronKeuze] = Field(..., min_length=1, max_length=50)
    omschrijving: str | None = None


class AangemaaktAcceptatie(BaseModel):
    """Directe bevestiging na aanmaken van een werkgebied."""

    id: str
    status: AnalyseStatus


class AnalyseOverzicht(BaseModel):
    """Samenvatting voor de werkgebied-lijst."""

    id: str
    naam: str  # nooit None in het read-contract; afgeleid als de gebruiker geen naam gaf
    bronnen: list[BronKeuze]
    status: AnalyseStatus
    bijgewerkt: datetime


class AnalyseDetail(AnalyseOverzicht):
    """Volledige detailweergave van één werkgebied."""

    omschrijving: str | None


# ─── Mapping-functies (werkwijze-ADR-0011) ────────────────────────────────────


def _naam_afleiden(bronnen: list[dict]) -> str:
    """Leidt een weergavenaam af uit de eerste bron als de gebruiker geen naam gaf."""
    if not bronnen:
        return "Naamloos"
    b = bronnen[0]
    lid_suffix = f" lid {b['lid']}" if b.get("lid") else ""
    return f"{b['bwb_id']} art. {b['artikel']}{lid_suffix}"


def analyse_overzicht_uit_rij(rij) -> AnalyseOverzicht:
    """Expliciete mapping databaserij → AnalyseOverzicht (werkwijze-ADR-0011)."""
    naam = rij.naam or _naam_afleiden(rij.bronnen or [])
    bronnen = [BronKeuze(**b) for b in (rij.bronnen or [])]
    return AnalyseOverzicht(
        id=rij.id,
        naam=naam,
        bronnen=bronnen,
        status=rij.status,
        bijgewerkt=rij.bijgewerkt,
    )


def analyse_detail_uit_rij(rij) -> AnalyseDetail:
    """Expliciete mapping databaserij → AnalyseDetail (werkwijze-ADR-0011)."""
    overzicht = analyse_overzicht_uit_rij(rij)
    return AnalyseDetail(
        **overzicht.model_dump(),
        omschrijving=rij.omschrijving,
    )
