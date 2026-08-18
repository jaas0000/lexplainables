"""De ene bron voor het llm_profielen-domein (werkwijze-ADR-0011).

Een entiteit: `llm_profielen` — beheerbare LLM-configuratieprofielen. Per profiel een naam
(stabiele identifier), provider, model, API-instellingen en een optionele Fernet-versleutelde
API-sleutel. Eén profiel kan als standaard zijn gemarkeerd.

De API-sleutel verlaat de API nooit als plaintext: het Read-contract heeft `sleutel_ingesteld`
(bool) in plaats van de sleutel zelf (story 011 §acceptatiecriteria).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, Float, MetaData, String, Table, Text

metadata = MetaData()

llm_profielen = Table(
    "llm_profielen",
    metadata,
    Column("naam", String(128), primary_key=True),
    Column("provider", String(64), nullable=False),
    Column("model", String(128), nullable=False),
    Column("api_base", Text, nullable=False),
    Column("api_versie", String(64), nullable=True),
    Column("temperatuur", Float, nullable=False, default=0.0),
    Column("api_sleutel_enc", Text, nullable=True),  # Fernet-versleuteld; None = niet ingesteld
    Column("is_standaard", Boolean, nullable=False, default=False),
    Column("updated", DateTime(timezone=True), nullable=False),
)


class LlmProfielCreate(BaseModel):
    """Wat een beheerder meestuurt bij het aanmaken van een profiel."""

    naam: str = Field(..., min_length=1, max_length=128)
    provider: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=128)
    api_base: str = Field(..., min_length=1)
    api_versie: str | None = None
    temperatuur: float = 0.0
    api_sleutel: str | None = None
    is_standaard: bool = False


class LlmProfielUpdate(BaseModel):
    """Wat een beheerder meestuurt bij het bijwerken van een profiel.

    `naam` ontbreekt bewust: naam is de stabiele identifier en kan niet veranderen.
    `api_sleutel` leeg (None of "") → sleutel ongewijzigd laten (niet overschrijven).
    """

    provider: str = Field(..., min_length=1, max_length=64)
    model: str = Field(..., min_length=1, max_length=128)
    api_base: str = Field(..., min_length=1)
    api_versie: str | None = None
    temperatuur: float = 0.0
    api_sleutel: str | None = None
    is_standaard: bool = False


class LlmProfielRead(BaseModel):
    """Wat de API teruggeeft — de plaintext API-sleutel verlaat de API nooit."""

    naam: str
    provider: str
    model: str
    api_base: str
    api_versie: str | None
    temperatuur: float
    sleutel_ingesteld: bool
    is_standaard: bool
    updated: datetime


def llm_profiel_uit_rij(rij) -> LlmProfielRead:
    """Expliciete mapping tussen databaserij en het Read-contract (werkwijze-ADR-0011)."""
    return LlmProfielRead(
        naam=rij.naam,
        provider=rij.provider,
        model=rij.model,
        api_base=rij.api_base,
        api_versie=rij.api_versie,
        temperatuur=rij.temperatuur,
        sleutel_ingesteld=rij.api_sleutel_enc is not None,
        is_standaard=rij.is_standaard,
        updated=rij.updated,
    )
