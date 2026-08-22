"""Herkenning van gestructureerde verwijzingen (`<intref>`/`<extref>`) tussen wetsartikelen.

Tekstuele fallback-detectie van ongetagde verwijzingen ("artikel 4", "artikel 6:162 BW") is
bewust niet in deze module — apart, kleiner stukje functionaliteit met een ander risicoprofiel
(regex-gebaseerde detectie, fout-positieven mogelijk), eigen story zodra dat nodig is.
"""

from __future__ import annotations

import re

from lxml import etree

from app.models import Verwijzing, VerwijzingSoort


def _normaliseer(tekst: str | None) -> str:
    return re.sub(r"\s+", " ", tekst or "").strip()


def extract_references(
    element: etree._Element,
    *,
    eigen_bwb_id: str,
    base: str = ".//*",
    extra_excl: str = "",
) -> list[Verwijzing]:
    """Haal gestructureerde verwijzingen uit `element`.

    `base` bepaalt het zoekbereik (bv. `"./al//*"` voor alleen de directe alinea's van een
    onderdeel, zodat geneste sub-onderdelen niet meetellen); `extra_excl` voegt extra
    xpath-voorwaarden toe (bv. `" and not(ancestor::lid)"` om geneste niveaus uit te sluiten,
    zodat een artikel niet de verwijzingen van zijn eigen leden dubbel meetelt).

    Verwijzingen komen nooit uit `<meta-data>`-subtrees. Een `extref` naar de eigen wet
    (`bwb-id` == `eigen_bwb_id`) telt als `INTERN`, ongeacht de brontag.
    """
    xpath = f"{base}[self::intref or self::extref][not(ancestor::meta-data){extra_excl}]"
    verwijzingen: list[Verwijzing] = []
    for ref in element.xpath(xpath):
        doel_bwb = ref.get("bwb-id")
        is_intern = ref.tag == "intref" or doel_bwb == eigen_bwb_id
        verwijzingen.append(
            Verwijzing(
                soort=VerwijzingSoort.INTERN if is_intern else VerwijzingSoort.EXTERN,
                tekst=_normaliseer("".join(ref.itertext())),
                doel_bwb_id=doel_bwb,
                doel_pad=ref.get("bwb-ng-variabel-deel"),
                doc=ref.get("doc"),
                verwijzing_id=ref.get("verwijzing-id"),
            )
        )
    return verwijzingen
