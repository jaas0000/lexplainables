"""De ene bron voor het wetcatalogus-domein (werkwijze-ADR-0011).

Puur Pydantic — geen SQLAlchemy-tabel. De wetcatalogus bevat statische seed-data
voor de eerste PoC (story 010 §Acceptatiecriteria): de wetten staan hardcoded in
store.py. Er is geen databasetabel nodig totdat de catalogus beheerbaar moet zijn
via een admin-interface.
"""

from __future__ import annotations

from pydantic import BaseModel


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
