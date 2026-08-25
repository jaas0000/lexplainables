"""De ene bron voor het gesprekken-domein (zie `__init__.py`).

Twee tabellen:
- `gesprekken` — één rij per gesprek, gescoped op `gebruiker`.
- `gesprek_berichten` — append-only; de heterogene beurt-payload (tekst/denk/bronnen/
  annotatieverwijzing) staat in de JSON-kolom `inhoud`, niet als losse kolommen — dezelfde
  reden als `annotatie_documenten.elementen`: de vorm verschilt per rol (`user` heeft alleen
  `tekst`, `assistant` kan `denk`/`bronnen`/`annotatie_slug` erbij hebben) en een vaste
  kolomset zou voor de ene rol altijd leeg zijn.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, Index, Integer, MetaData, Table, Text

metadata = MetaData()


class Rol(StrEnum):
    user = "user"
    assistant = "assistant"


class Bericht(BaseModel):
    """Eén beurt in het gesprek. `annotatie_titel` is het leesbare label van het
    annotatiedocument op het moment van de beurt — het bericht beschrijft zichzelf, zodat het
    gesprek leesbaar blijft als het document later verwijderd wordt (geen foreign key)."""

    id: int | None = None
    rol: Rol
    tekst: str = ""
    denk: str = ""
    bronnen: list[dict] = Field(default_factory=list)
    annotatie_slug: str = ""
    annotatie_titel: str = ""
    ontbrekend: list[dict] = Field(default_factory=list)
    # Idempotentiesleutel: dezelfde agent-run mag maar één assistent-bericht opleveren.
    run_id: str = ""
    aangemaakt: str = ""


class Gesprek(BaseModel):
    id: str
    gebruiker: str
    titel: str = ""
    berichten: list[Bericht] = Field(default_factory=list)
    aangemaakt: str = ""
    bijgewerkt: str = ""


# --- Input-/uitvoercontracten --------------------------------------------------------


class GesprekAanmaken(BaseModel):
    titel: str = ""


class GesprekHernoemen(BaseModel):
    titel: str


class BerichtInvoer(BaseModel):
    rol: Rol
    tekst: str = ""
    denk: str = ""
    bronnen: list[dict] = Field(default_factory=list)
    annotatie_slug: str = ""
    annotatie_titel: str = ""
    ontbrekend: list[dict] = Field(default_factory=list)
    run_id: str = ""


class GesprekSamenvatting(BaseModel):
    """Lichte lijst-weergave voor een gesprekgeschiedenis-overzicht."""

    id: str
    titel: str = ""
    aantal_berichten: int = 0
    bijgewerkt: str = ""


# --- SQLAlchemy Core tables ------------------------------------------------------------

gesprekken = Table(
    "gesprekken",
    metadata,
    Column("id", Text, primary_key=True),
    Column("gebruiker", Text, nullable=False),
    Column("titel", Text, nullable=False, default=""),
    Column("aangemaakt", DateTime(timezone=True), nullable=False),
    Column("bijgewerkt", DateTime(timezone=True), nullable=False),
    Index("ix_gesprekken_gebruiker", "gebruiker"),
)

gesprek_berichten = Table(
    "gesprek_berichten",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gesprek_id", Text, nullable=False),
    Column("rol", Text, nullable=False),
    Column("inhoud", JSON, nullable=False, default=dict),
    Column("aangemaakt", DateTime(timezone=True), nullable=False),
    Index("ix_gesprek_berichten_gesprek_id", "gesprek_id"),
)


# --- Mapping-functies ------------------------------------------------------------------


def _inhoud_uit(inv: BerichtInvoer) -> dict:
    """De heterogene beurt-payload → de JSON-kolom (weglaten wat leeg is houdt de rij compact)."""
    inhoud: dict = {}
    if inv.tekst:
        inhoud["tekst"] = inv.tekst
    if inv.denk:
        inhoud["denk"] = inv.denk
    if inv.bronnen:
        inhoud["bronnen"] = inv.bronnen
    if inv.annotatie_slug:
        inhoud["annotatie_slug"] = inv.annotatie_slug
    if inv.annotatie_titel:
        inhoud["annotatie_titel"] = inv.annotatie_titel
    if inv.ontbrekend:
        inhoud["ontbrekend"] = inv.ontbrekend
    if inv.run_id:
        inhoud["run_id"] = inv.run_id
    return inhoud


def bericht_uit_rij(rij) -> Bericht:
    inhoud = rij.inhoud or {}
    return Bericht(
        id=rij.id,
        rol=Rol(rij.rol),
        tekst=inhoud.get("tekst", ""),
        denk=inhoud.get("denk", ""),
        bronnen=inhoud.get("bronnen") or [],
        annotatie_slug=inhoud.get("annotatie_slug", ""),
        annotatie_titel=inhoud.get("annotatie_titel", ""),
        ontbrekend=inhoud.get("ontbrekend") or [],
        run_id=inhoud.get("run_id", ""),
        aangemaakt=rij.aangemaakt.isoformat(),
    )


def samenvatting_uit_rij(rij) -> GesprekSamenvatting:
    return GesprekSamenvatting(
        id=rij.id,
        titel=rij.titel,
        aantal_berichten=rij.aantal_berichten or 0,
        bijgewerkt=rij.bijgewerkt.isoformat(),
    )
