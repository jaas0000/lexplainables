"""Dataclasses voor het BWB-domeinmodel.

Dekt tot nu toe: SRU-discovery (`ToestandRef`, story 024), de kernstructuur van een
wet-besluit-document (`Wet`/`Structuurdeel`/`Artikel`/`Lid`, story 025), en onderdelen (genestelde
`<lijst>/<li>`) + gestructureerde verwijzingen (`Onderdeel`/`Verwijzing`, story 026). Illustraties,
voetnoten, definities, tabellen, ondertekenaars, bijlagen en circulaires komen in latere stories —
zie docs/project/stories/026-bwb-import-onderdelen-en-verwijzingen.md §Buiten scope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(slots=True)
class ToestandRef:
    """Eén toestand (versie) van een regeling, zoals de SRU-discovery 'm teruggeeft."""

    bwb_id: str
    locatie_toestand: str
    geldig_vanaf: str | None = None
    geldig_tot: str | None = None


class VerwijzingSoort(StrEnum):
    """Interne verwijzing (binnen dezelfde wet) of externe (andere regeling).

    De string-waarde is de brontag — handig bij debuggen/logging. Een `extref` naar de eigen wet
    telt als `INTERN` (zie `references.extract_references`), ongeacht de brontag.
    """

    INTERN = "intref"
    EXTERN = "extref"


@dataclass(slots=True)
class Verwijzing:
    """Een gestructureerde verwijzing (`<intref>`/`<extref>`) vanuit een tekstdeel.

    Alleen de rauwe velden uit de XML — jci-ontleding (naar een graafrelatie) is een taak voor de
    GraphDB-writer-story, niet voor de parser (zie story 026 §Buiten scope).
    """

    soort: VerwijzingSoort
    tekst: str
    doel_bwb_id: str | None = None
    doel_pad: str | None = None  # bwb-ng-variabel-deel van het doel
    doc: str | None = None  # jci-verwijzing, bv. "jci1.3:c:BWBR0004770&artikel=4"
    verwijzing_id: str | None = None  # bron-id van de <intref>/<extref>


@dataclass(slots=True)
class Onderdeel:
    """Een onderdeel (`<li>`) binnen een `<lijst>`; bv. een definitie of opsommingspunt. Kan
    genest zijn (sub-lijsten, bv. "aa." met een genest "1°./2°./…")."""

    id: str
    nummer: str  # uit <li.nr>, bv. "a." of "1°."
    tekst: str
    verwijzingen: list[Verwijzing] = field(default_factory=list)
    subonderdelen: list[Onderdeel] = field(default_factory=list)


@dataclass(slots=True)
class Lid:
    """Een lid binnen een artikel."""

    id: str
    nummer: str
    tekst: str
    verwijzingen: list[Verwijzing] = field(default_factory=list)
    onderdelen: list[Onderdeel] = field(default_factory=list)


@dataclass(slots=True)
class Artikel:
    """Een artikel; `leden` is leeg als de tekst direct in het artikel staat (geen leden)."""

    id: str
    nummer: str
    label: str
    tekst: str
    leden: list[Lid] = field(default_factory=list)
    verwijzingen: list[Verwijzing] = field(default_factory=list)
    onderdelen: list[Onderdeel] = field(default_factory=list)


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
