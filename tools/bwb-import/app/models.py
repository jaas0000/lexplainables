"""Dataclasses voor het BWB-domeinmodel.

Dekt tot nu toe: SRU-discovery (`ToestandRef`, story 024), de kernstructuur van een
wet-besluit-document (`Wet`/`Structuurdeel`/`Artikel`/`Lid`, story 025), onderdelen (genestelde
`<lijst>/<li>`) + gestructureerde verwijzingen (`Onderdeel`/`Verwijzing`, story 026), de
`jci`-identiteit per node + import-tellingen (`ImportSummary`/`ImportResult`, story 027), en de
`label_id`/`locatie_wti`-join-sleutels voor WTI-verrijking (story 030).
Illustraties, voetnoten, definities, tabellen, ondertekenaars, bijlagen en circulaires komen in
latere stories.
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
    locatie_wti: str | None = None


class VerwijzingSoort(StrEnum):
    """Interne verwijzing (binnen dezelfde wet) of externe (andere regeling).

    De string-waarde is de brontag — handig bij debuggen/logging. Een `extref` naar de eigen wet
    telt als `INTERN` (zie `references.extract_references`), ongeacht de brontag.
    """

    INTERN = "intref"
    EXTERN = "extref"


@dataclass(slots=True)
class Verwijzing:
    """Een gestructureerde verwijzing (`<intref>`/`<extref>`) vanuit een tekstdeel."""

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
    jci: str | None = None
    verwijzingen: list[Verwijzing] = field(default_factory=list)
    subonderdelen: list[Onderdeel] = field(default_factory=list)


@dataclass(slots=True)
class Lid:
    """Een lid binnen een artikel."""

    id: str
    nummer: str
    tekst: str
    jci: str | None = None
    verwijzingen: list[Verwijzing] = field(default_factory=list)
    onderdelen: list[Onderdeel] = field(default_factory=list)


@dataclass(slots=True)
class Artikel:
    """Een artikel; `leden` is leeg als de tekst direct in het artikel staat (geen leden)."""

    id: str
    nummer: str
    label: str
    tekst: str
    jci: str | None = None
    label_id: str | None = None  # WTI-join-sleutel (label-id-attribuut)
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
    jci: str | None = None
    label_id: str | None = None  # WTI-join-sleutel (label-id-attribuut)
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
    label_id: str | None = None  # WTI-join-sleutel (label-id van <wetgeving>)
    structuurdelen: list[Structuurdeel] = field(default_factory=list)
    losse_artikelen: list[Artikel] = field(default_factory=list)


@dataclass(slots=True)
class ImportSummary:
    """Telling van geïmporteerde elementen, getoond na een import."""

    bwb_id: str
    wetten: int = 0
    hoofdstukken: int = 0
    titeldelen: int = 0
    afdelingen: int = 0
    paragrafen: int = 0
    artikelen: int = 0
    leden: int = 0
    onderdelen: int = 0
    relaties: int = 0

    def as_dict(self) -> dict[str, int | str]:
        return {
            "bwb_id": self.bwb_id,
            "wetten": self.wetten,
            "hoofdstukken": self.hoofdstukken,
            "titeldelen": self.titeldelen,
            "afdelingen": self.afdelingen,
            "paragrafen": self.paragrafen,
            "artikelen": self.artikelen,
            "leden": self.leden,
            "onderdelen": self.onderdelen,
            "relaties": self.relaties,
        }


@dataclass(slots=True)
class ImportResult:
    """Uitkomst van één wet binnen een (batch-)import."""

    bwb_id: str
    ok: bool
    overzicht: ImportSummary | None = None
    fout: str | None = None

    def as_dict(self) -> dict:
        return {
            "bwb_id": self.bwb_id,
            "status": "ok" if self.ok else "fout",
            "overzicht": self.overzicht.as_dict() if self.overzicht else None,
            "fout": self.fout,
        }
