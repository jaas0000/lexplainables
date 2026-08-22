"""Dataclasses voor het BWB-domeinmodel.

Deze eerste story dekt alleen `ToestandRef` (SRU-discovery-resultaat). Het volledige
documentmodel (wet/hoofdstuk/afdeling/artikel/lid/onderdeel) komt in de parser-story.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ToestandRef:
    """Eén toestand (versie) van een regeling, zoals de SRU-discovery 'm teruggeeft."""

    bwb_id: str
    locatie_toestand: str
    geldig_vanaf: str | None = None
    geldig_tot: str | None = None
