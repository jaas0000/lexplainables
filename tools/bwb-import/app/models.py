"""Dataclasses voor het BWB-domeinmodel.

Dekt tot nu toe: SRU-discovery (`ToestandRef`, story 024) en de kernstructuur van een
wet-besluit-document (`Wet`/`Structuurdeel`/`Artikel`/`Lid`, story 025). Onderdelen/lijsten,
verwijzingen, illustraties, voetnoten, tabellen, ondertekenaars, bijlagen en circulaires komen in
latere stories — zie docs/project/stories/025-bwb-import-xsd-en-kernparser.md §Buiten scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ToestandRef:
    """Eén toestand (versie) van een regeling, zoals de SRU-discovery 'm teruggeeft."""

    bwb_id: str
    locatie_toestand: str
    geldig_vanaf: str | None = None
    geldig_tot: str | None = None


@dataclass(slots=True)
class Lid:
    """Een lid binnen een artikel."""

    id: str
    nummer: str
    tekst: str


@dataclass(slots=True)
class Artikel:
    """Een artikel; `leden` is leeg als de tekst direct in het artikel staat (geen leden)."""

    id: str
    nummer: str
    label: str
    tekst: str
    leden: list[Lid] = field(default_factory=list)


@dataclass(slots=True)
class Structuurdeel:
    """Een structuurdeel (hoofdstuk/titeldeel/afdeling/paragraaf), generiek genest."""

    id: str
    soort: str
    nummer: str
    label: str
    titel: str
    subdelen: list[Structuurdeel] = field(default_factory=list)
    artikelen: list[Artikel] = field(default_factory=list)


@dataclass(slots=True)
class Wet:
    """Een regeling (wet, besluit of ministeriële regeling — geen circulaires, zie story 025)."""

    bwb_id: str
    citeertitel: str
    opschrift: str
    soort: str
    geldig_vanaf: str | None = None
    structuurdelen: list[Structuurdeel] = field(default_factory=list)
    losse_artikelen: list[Artikel] = field(default_factory=list)
