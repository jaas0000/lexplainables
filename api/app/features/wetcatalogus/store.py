"""Store-abstractie voor het wetcatalogus-domein (werkwijze-ADR-0007).

`WetcatalogusStore` beschrijft de operaties die router.py nodig heeft.
`HardgecodeerdeWetcatalogusStore` is de enige huidige implementatie — statische seed-data
voor de eerste PoC (story 010 §Acceptatiecriteria: "wetten zijn geseed in de database of
hardcoded in de router"). Geen SQLAlchemy-engine nodig.
"""

from __future__ import annotations

from typing import Protocol

from .models import ArtikelKeuze, WetKeuze, WetStructuur

# Statische seed-data (mockup: frontend/app/mockup/wetcatalogus/page.tsx)
_WETTEN: list[WetKeuze] = [
    WetKeuze(bwb_id="BWBR0011823", naam="Wet werk en bijstand"),
    WetKeuze(bwb_id="BWBR0015703", naam="Wet structuur uitvoeringsorganisatie werk en inkomen"),
    WetKeuze(bwb_id="BWBR0020183", naam="Participatiewet"),
]

_STRUCTUUR: dict[str, list[ArtikelKeuze]] = {
    "BWBR0011823": [
        ArtikelKeuze(artikel="1", pad="Hoofdstuk 1 / Artikel 1"),
        ArtikelKeuze(artikel="2", pad="Hoofdstuk 1 / Artikel 2"),
        ArtikelKeuze(artikel="3", pad="Hoofdstuk 1 / Artikel 3"),
        ArtikelKeuze(artikel="11", pad="Hoofdstuk 2 / Artikel 11"),
        ArtikelKeuze(artikel="17", pad="Hoofdstuk 2 / Artikel 17"),
        ArtikelKeuze(artikel="31", pad="Hoofdstuk 3 / Artikel 31"),
    ],
    "BWBR0015703": [
        ArtikelKeuze(artikel="1", pad="Hoofdstuk 1 / Artikel 1"),
        ArtikelKeuze(artikel="7", pad="Hoofdstuk 2 / Artikel 7"),
        ArtikelKeuze(artikel="30", pad="Hoofdstuk 4 / Artikel 30"),
    ],
    "BWBR0020183": [
        ArtikelKeuze(artikel="1", pad="Hoofdstuk 1 / Artikel 1"),
        ArtikelKeuze(artikel="8a", pad="Hoofdstuk 2 / Artikel 8a"),
        ArtikelKeuze(artikel="10", pad="Hoofdstuk 2 / Artikel 10"),
        ArtikelKeuze(artikel="44", pad="Hoofdstuk 3 / Artikel 44"),
    ],
}


class WetNietGevonden(LookupError):
    """Onbekend bwb_id."""


class WetcatalogusStore(Protocol):
    async def lijst(self) -> list[WetKeuze]: ...

    async def structuur(self, bwb_id: str) -> WetStructuur: ...


class HardgecodeerdeWetcatalogusStore:
    """Statische implementatie — geen database. Vervanging door een SQLAlchemy-variant
    zodra de catalogus beheerbaar wordt (story n.n.b.)."""

    async def lijst(self) -> list[WetKeuze]:
        return list(_WETTEN)

    async def structuur(self, bwb_id: str) -> WetStructuur:
        if bwb_id not in _STRUCTUUR:
            raise WetNietGevonden(f"Wet {bwb_id!r} niet gevonden.")
        return WetStructuur(bwb_id=bwb_id, artikelen=list(_STRUCTUUR[bwb_id]))
