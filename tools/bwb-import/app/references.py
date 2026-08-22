"""Herkenning van gestructureerde verwijzingen (`<intref>`/`<extref>`) tussen wetsartikelen, en
ontleding van jci-verwijzingen tot stabiele ref_keys (story 027).

Tekstuele fallback-detectie van ongetagde verwijzingen ("artikel 4", "artikel 6:162 BW") is
bewust niet in deze module — apart, kleiner stukje functionaliteit met een ander risicoprofiel
(regex-gebaseerde detectie, fout-positieven mogelijk), eigen story zodra dat nodig is.
"""

from __future__ import annotations

import re

from lxml import etree

from app.models import Verwijzing, VerwijzingSoort

# Onderdelen van een jci-verwijzing (bv. "jci1.3:c:BWBR0005537&artikel=3:40").
_JCI_BWB = re.compile(r":c:(BWBR\d+)")
_JCI_ARTIKEL = re.compile(r"[&?]artikel=([^&]+)")
_JCI_LID = re.compile(r"[&?]lid=([^&]+)")


def _normaliseer(tekst: str | None) -> str:
    return re.sub(r"\s+", " ", tekst or "").strip()


def jci_doel(doc: str | None) -> tuple[str | None, str | None, str | None]:
    """Ontleed een jci-`doc` tot `(bwb_id, artikelnummer, lidnummer)`.

    Versieparameters (`&z=`/`&g=`) worden genegeerd. Elk veld is `None` als het niet in de
    verwijzing voorkomt (bv. een verwijzing naar een heel hoofdstuk levert geen artikel/lid op).
    """
    if not doc:
        return (None, None, None)
    bwb = _JCI_BWB.search(doc)
    artikelen = _JCI_ARTIKEL.findall(doc)
    lidnrs = _JCI_LID.findall(doc)
    return (
        bwb.group(1) if bwb else None,
        artikelen[-1] if artikelen else None,
        lidnrs[-1] if lidnrs else None,
    )


def jci_to_ref_key(doc: str | None) -> str | None:
    """Vorm een stabiele artikelsleutel `{bwb}#artikel={nr}` uit een jci-doc.

    Geeft `None` als de verwijzing geen concreet artikel aanduidt (bv. naar een heel hoofdstuk),
    zodat er geen onterechte `verwijstNaar` ontstaat.
    """
    bwb, artikel, _ = jci_doel(doc)
    if not bwb or not artikel:
        return None
    return f"{bwb}#artikel={artikel}"


def jci_doel_ref_key(doc: str | None) -> tuple[str | None, str | None]:
    """Ontleed een jci-doc tot `(ref_key, doel_soort)` op elk niveau (artikel/lid/wet).

    Anders dan `jci_to_ref_key` (alleen artikel-niveau) resolveert deze ook lid- en
    hele-wet-doelen:
    - `&artikel=…`       -> `{bwb}#artikel={nr}` ("artikel")
    - `… &lid=…`         -> `…#lid={l}` ("lid")
    - alleen `:c:BWBR…`  -> `{bwb}` ("wet")
    """
    if not doc:
        return (None, None)
    bwb_match = _JCI_BWB.search(doc)
    if not bwb_match:
        return (None, None)
    bwb = bwb_match.group(1)

    artikelen = _JCI_ARTIKEL.findall(doc)
    if artikelen:
        ref_key, soort = f"{bwb}#artikel={artikelen[-1]}", "artikel"
        lidnrs = _JCI_LID.findall(doc)
        if lidnrs:
            ref_key, soort = f"{ref_key}#lid={lidnrs[-1]}", "lid"
        return (ref_key, soort)

    return (bwb, "wet")


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
