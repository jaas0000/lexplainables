"""Gedeelde brongetrouwheids-primitieven: is een fragment letterlijk in een tekst aanwezig?

Zowel `grounding.py` (het antwoord tegen de tool-trace) als `annotatie.py` (een JAS-voorstel tegen
de opgehaalde artikeltekst) stellen dezelfde eis — geen twee losse implementaties die stil uit
elkaar kunnen lopen. Verhuisd hierheen zodra `annotatie.py` (story 047) een tweede consument werd;
tot dan stond dit tijdelijk in `grounding.py` (`feature-bouwen` regel 8: pas delen ná een tweede
consument).
"""

from __future__ import annotations

import re

_WS = re.compile(r"\s+")


def normaliseer(s: str) -> str:
    """Collapse witruimte, zodat een fragment ondanks layout-verschillen matcht."""
    return _WS.sub(" ", s or "").strip()


def komt_letterlijk_voor(corpus: str, fragment: str) -> bool:
    """Staat dit fragment letterlijk in de opgehaalde tekst? (witruimte-ongevoelig)."""
    norm = normaliseer(fragment)
    return bool(norm) and normaliseer(corpus).find(norm) >= 0
