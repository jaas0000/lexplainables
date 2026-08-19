"""De ene bron voor het projecten-domein (werkwijze-ADR-0011).

Één entiteit: `analyses` — analyses aangemaakt door ingelogde gebruikers. Per analyse:
bronartikelen, status, voortgangsinfo en optionele configuratie (model-profiel,
human-in-the-loop, begrippenlijst).

Status-levenscyclus: wachtrij → actief → review (optioneel) → klaar
                                      ↘ fout
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

AnalyseStatus = Literal["wachtrij", "actief", "review", "klaar", "fout"]

# Statussen waarna geen verdere overgang meer volgt; SSE sluit de stroom zodra een van
# deze bereikt wordt.
TERMINAL_STATUSSEN: frozenset[str] = frozenset({"klaar", "fout"})

metadata = MetaData()

analyses = Table(
    "analyses",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("naam", String(256), nullable=True),
    Column("status", String(32), nullable=False),
    Column("bronnen", JSON, nullable=False),  # list[BronKeuze] als JSON
    Column("model_profiel", String(128), nullable=True),
    Column("omschrijving", Text, nullable=True),
    Column("analysefocus", Text, nullable=True),
    Column("human_in_the_loop", Boolean, nullable=False),
    Column("begrippenlijst", JSON, nullable=True),  # list[BegripInvoer] als JSON of None
    Column("huidige_fase", Text, nullable=True),
    Column("foutmelding", Text, nullable=True),
    Column("rapport", JSON, nullable=True),  # eindrapport na act3 (migratie 0009)
    Column("aangemaakt", DateTime(timezone=True), nullable=False),
    Column("bijgewerkt", DateTime(timezone=True), nullable=False),
    Column("gebruiker_id", String(128), nullable=False),
    Index("ix_analyses_gebruiker_id", "gebruiker_id"),
    Index("ix_analyses_bijgewerkt", "bijgewerkt"),
)

# llm_calls-tabel: vastgelegde LLM-verkeer (capture-toggle, migratie 0009).
llm_calls_metadata = MetaData()

llm_calls = Table(
    "llm_calls",
    llm_calls_metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("analyse_id", String(36), nullable=False),
    Column("activiteit", String(32), nullable=False),
    Column("bron_id", String(32), nullable=True),
    Column("system_prompt", Text, nullable=False),
    Column("user_prompt", Text, nullable=False),
    Column("ruwe_respons", Text, nullable=False),
    Column("model", String(128), nullable=False),
    Column("tokens_in", Integer, nullable=False),
    Column("tokens_out", Integer, nullable=False),
    Column("aangemaakt", DateTime(timezone=True), nullable=False),
    Index("ix_llm_calls_analyse_id", "analyse_id"),
)


# ─── Pydantic-modellen (contract) ────────────────────────────────────────────


class BronKeuze(BaseModel):
    """Één bronartikel: wet-id, artikelnummer en optioneel lidnummer."""

    bwb_id: str
    artikel: str
    lid: str | None = None


class BegripInvoer(BaseModel):
    """Eén begrip uit een eventuele bestaande begrippenlijst."""

    naam: str
    definitie: str | None = None


class AnalyseAanmaken(BaseModel):
    """Wat een ingelogde gebruiker meestuurt bij het aanmaken van een analyse."""

    naam: str | None = None
    bronnen: list[BronKeuze] = Field(..., min_length=1, max_length=50)
    omschrijving: str | None = None
    analysefocus: str | None = None
    begrippenlijst: list[BegripInvoer] | None = None
    model_profiel: str | None = None
    human_in_the_loop: bool = True


class AangemaaktAcceptatie(BaseModel):
    """Directe bevestiging na aanmaken — 202 Accepted, analyse loopt asynchroon."""

    id: str
    status: AnalyseStatus


class AnalyseOverzicht(BaseModel):
    """Samenvatting voor de analyselijst."""

    id: str
    naam: str  # nooit None in het read-contract; afgeleid als de gebruiker geen naam gaf
    bronnen: list[BronKeuze]
    status: AnalyseStatus
    bijgewerkt: datetime


class AnalyseDetail(AnalyseOverzicht):
    """Volledige detailweergave van één analyse."""

    omschrijving: str | None
    analysefocus: str | None
    model_profiel: str | None
    human_in_the_loop: bool
    begrippenlijst: list[BegripInvoer] | None
    huidige_fase: str | None
    foutmelding: str | None
    rapport: dict | None  # eindrapport (gevuld na status 'klaar')


class LlmCallRead(BaseModel):
    """Vastgelegde LLM-aanroep, leesbaar via GET /v1/projecten/{id}/llm-calls."""

    id: int
    analyse_id: str
    activiteit: str
    bron_id: str | None
    system_prompt: str
    user_prompt: str
    ruwe_respons: str
    model: str
    tokens_in: int
    tokens_out: int
    aangemaakt: datetime


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
    """Expliciete mapping databaserij → AnalyseDetail (werkwijze-ADR-0011).

    Bouwt voort op analyse_overzicht_uit_rij om naam- en bronnen-afleiding niet te
    dupliceren.
    """
    overzicht = analyse_overzicht_uit_rij(rij)
    begrippen = [BegripInvoer(**b) for b in rij.begrippenlijst] if rij.begrippenlijst else None
    return AnalyseDetail(
        **overzicht.model_dump(),
        omschrijving=rij.omschrijving,
        analysefocus=rij.analysefocus,
        model_profiel=rij.model_profiel,
        human_in_the_loop=rij.human_in_the_loop,
        begrippenlijst=begrippen,
        huidige_fase=rij.huidige_fase,
        foutmelding=rij.foutmelding,
        rapport=rij.rapport,
    )
