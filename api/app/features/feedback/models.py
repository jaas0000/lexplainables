"""De ene bron voor het feedback-domein (werkwijze-ADR-0011).

Twee entiteiten, elk met een SQLAlchemy Core `Table` (de databasetabel), Pydantic-modellen
(het contract dat de buitenwereld ziet) en een expliciete, met de hand geschreven
mapping-functie ertussen:

- `user_feedback` — één rij per ingediend feedbackitem, onwijzigbaar (append-only).
- `feedback_leesbewijzen` — per beheerder tot welk tijdstip die de feedbackpagina heeft
  gezien. Dit is een EIGEN tabel van dit domein, geen kolom op een users-tabel: het
  feedback-domein bezit zijn eigen "wie heeft dit gezien"-data (vertical slicing,
  werkwijze-ADR-0001) in plaats van een kolom van het identiteits-/toegangsdomein te lenen —
  zie ../../../../docs/stories/001-feedback-indienen-en-beheren.md §Schemabeslissing voor de
  volledige afweging.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, Index, Integer, MetaData, String, Table, Text

Categorie = Literal["verbeteridee", "probleemmelding", "compliment", "vraag"]

metadata = MetaData()


def nu() -> datetime:
    """Huidig moment, tz-aware (UTC). Openbaar zodat store.py en tests hetzelfde tijdsbegrip
    delen in plaats van elk hun eigen `datetime.now(UTC)`-aanroep te doen."""
    return datetime.now(UTC)


# --- user_feedback --------------------------------------------------------------

user_feedback = Table(
    "user_feedback",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("client_id", String(128), nullable=False),
    Column("userid", String(128), nullable=False),
    Column("categorie", String(32), nullable=False),
    Column("tekst", Text, nullable=False),
    Column("pagina", Text, nullable=True),
    Column("created", DateTime(timezone=True), nullable=False),
    Index("ix_user_feedback_created", "created"),
)


class FeedbackBase(BaseModel):
    # Literal i.p.v. `str` + regex-pattern: een gesloten verzameling hoort als strikter type
    # vastgelegd te worden, niet als losse string met een validatie-side-effect (ADR-0011,
    # feature-bouwen regel 3 — "wees scherp op precisie"). Genereert bovendien een echte
    # `enum` in het OpenAPI-schema in plaats van een format-pattern.
    categorie: Categorie
    tekst: str = Field(..., min_length=1, max_length=4000)
    pagina: str | None = Field(None, max_length=500)


class FeedbackCreate(FeedbackBase):
    """Wat een client mag sturen bij het indienen van feedback — client_id/userid komen niet
    van de client zelf maar uit de auth-laag (zie router.py), dus staan hier bewust niet bij."""


class FeedbackRead(FeedbackBase):
    """Wat een beheerder terugkrijgt bij het opvragen van feedback."""

    id: int
    client_id: str
    userid: str
    created: datetime


def feedback_uit_rij(rij) -> FeedbackRead:
    """Expliciete mapping tussen een databaserij van `user_feedback` en het Pydantic-contract
    (werkwijze-ADR-0011) — geen impliciete/automatische ORM-mapping."""
    return FeedbackRead(
        id=rij.id,
        client_id=rij.client_id,
        userid=rij.userid,
        categorie=rij.categorie,
        tekst=rij.tekst,
        pagina=rij.pagina,
        created=rij.created,
    )


# --- feedback_leesbewijzen -------------------------------------------------------

feedback_leesbewijzen = Table(
    "feedback_leesbewijzen",
    metadata,
    Column("admin_userid", String(128), primary_key=True),
    Column("gezien_tot", DateTime(timezone=True), nullable=False),
)

# Geen Pydantic-contract + mapping-functie voor deze tabel: `feedback_leesbewijzen` wordt nooit
# als geheel aan een client teruggegeven (geen GET-endpoint erop), alleen intern gebruikt door
# store.py om `ongelezen_aantal`/`markeer_gezien` te berekenen. ADR-0011's mapping-functie-eis
# geldt voor het contract dat de buitenwereld ziet — een tabel zonder extern contract heeft
# geen mapping-functie nodig, alleen de kale kolomwaarde die de store zelf leest.
