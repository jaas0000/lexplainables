"""De ene bron voor het berichten-domein (werkwijze-ADR-0011).

Twee entiteiten, elk met een SQLAlchemy Core `Table` (de databasetabel), Pydantic-modellen
(het contract dat de buitenwereld ziet) en een expliciete, met de hand geschreven
mapping-functie ertussen:

- `berichten` — release notes/aankondigingen, geschreven door een beheerder (draft →
  gepubliceerd), gelezen door analisten.
- `bericht_leesbewijzen` — per (bericht, gebruiker) of die het bericht al gezien heeft. Dit is
  al een eigen jointabel van dit domein, geen geleende kolom van een andere feature (in
  tegenstelling tot hoe `feedback` het oorspronkelijk deed, zie
  ../../../../docs/stories/001-feedback-indienen-en-beheren.md §Schemabeslissing) — hier is
  niets architecturaals te repareren, alleen netjes over te nemen.

Er zijn twee losse Read-contracten omdat er twee verschillende consumenten zijn: een analist
ziet een `gelezen`-vlag (per-gebruiker context) maar niet wie het bericht schreef, een beheerder
ziet `aangemaakt_door` maar geen per-gebruiker `gelezen`-status. Zie
../../../../docs/stories/002-berichten-lezen-en-beheren.md §Schemabeslissing voor de bewuste
vereenvoudiging (geen registratiemoment-filter) en de regel-8-afweging (geen gedeelde
`LeesbewijsStore`, wel gedeelde auth-stand-in).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
)

BerichtType = Literal["info", "update", "waarschuwing", "kritiek"]

metadata = MetaData()


# --- berichten ----------------------------------------------------------------------

berichten = Table(
    "berichten",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("titel", Text, nullable=False),
    Column("inhoud", Text, nullable=False),
    Column("type", String(16), nullable=False, default="info"),
    Column("versie", String(32), nullable=True),
    Column("gepubliceerd", Boolean, nullable=False, default=False),
    Column("gepubliceerd_op", DateTime(timezone=True), nullable=True),
    Column("aangemaakt_door", String(128), nullable=False),
    Column("created", DateTime(timezone=True), nullable=False),
    Column("updated", DateTime(timezone=True), nullable=False),
    Index("ix_berichten_gepubliceerd_created", "gepubliceerd", "created"),
)


class BerichtBase(BaseModel):
    titel: str = Field(..., min_length=1, max_length=256)
    inhoud: str = Field(..., min_length=1, max_length=10000)
    # Literal i.p.v. `str` + regex-pattern: een gesloten verzameling hoort als strikter type
    # vastgelegd te worden (ADR-0011, feature-bouwen regel 3 — "wees scherp op precisie").
    type: BerichtType = "info"
    versie: str | None = Field(default=None, max_length=32)


class BerichtCreate(BerichtBase):
    """Wat een beheerder mag sturen bij het aanmaken of bewerken van een bericht —
    `aangemaakt_door` komt niet van de client maar uit de auth-laag (zie router.py), en
    `gepubliceerd` is nooit client-instelbaar bij het aanmaken (altijd een concept, zie
    store.py `maak`). Bewerken hergebruikt bewust hetzelfde schema (zelfde velden, ander
    endpoint) in plaats van een bijna-identieke tweede class."""


class BerichtRead(BerichtBase):
    """Wat een analist terugkrijgt: alleen gepubliceerde berichten, met een per-gebruiker
    `gelezen`-vlag."""

    id: int
    gepubliceerd: bool
    gepubliceerd_op: datetime | None
    gelezen: bool
    created: datetime
    updated: datetime


class BerichtAdminRead(BerichtBase):
    """Wat een beheerder terugkrijgt: ook concepten, met wie het bericht aanmaakte — maar geen
    per-gebruiker `gelezen`-vlag (de admin-lijst is niet gebonden aan één gebruiker)."""

    id: int
    gepubliceerd: bool
    gepubliceerd_op: datetime | None
    aangemaakt_door: str
    created: datetime
    updated: datetime


def _basisvelden(rij) -> dict:
    """Velden die `BerichtRead` en `BerichtAdminRead` gemeenschappelijk hebben — expliciete
    mapping blijft (werkwijze-ADR-0011), maar de twee mappers hoeven deze 7 velden niet elk
    apart uit te schrijven."""
    return {
        "id": rij.id,
        "titel": rij.titel,
        "inhoud": rij.inhoud,
        "type": rij.type,
        "versie": rij.versie,
        "gepubliceerd": rij.gepubliceerd,
        "gepubliceerd_op": rij.gepubliceerd_op,
        "created": rij.created,
        "updated": rij.updated,
    }


def bericht_uit_rij(rij, *, gelezen: bool) -> BerichtRead:
    """Expliciete mapping tussen een databaserij van `berichten` en het analist-contract
    (werkwijze-ADR-0011) — geen impliciete/automatische ORM-mapping."""
    return BerichtRead(**_basisvelden(rij), gelezen=gelezen)


def bericht_admin_uit_rij(rij) -> BerichtAdminRead:
    """Expliciete mapping tussen een databaserij van `berichten` en het beheerder-contract
    (werkwijze-ADR-0011)."""
    return BerichtAdminRead(**_basisvelden(rij), aangemaakt_door=rij.aangemaakt_door)


# --- bericht_leesbewijzen ------------------------------------------------------------

bericht_leesbewijzen = Table(
    "bericht_leesbewijzen",
    metadata,
    Column("bericht_id", Integer, nullable=False),
    Column("userid", String(128), nullable=False),
    Column("gelezen_op", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("bericht_id", "userid"),
)

# Geen Pydantic-contract + mapping-functie voor deze tabel: `bericht_leesbewijzen` wordt nooit
# als geheel aan een client teruggegeven (geen GET-endpoint erop), alleen intern gebruikt door
# store.py om de `gelezen`-vlag/`ongelezen_aantal`/`markeer_alles_gelezen` te berekenen.
# ADR-0011's mapping-functie-eis geldt voor het contract dat de buitenwereld ziet — een tabel
# zonder extern contract heeft geen mapping-functie nodig (zelfde redenering als
# `feedback_leesbewijzen` in het feedback-domein).
