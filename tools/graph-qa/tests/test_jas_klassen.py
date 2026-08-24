"""Drift-guard: `JAS_KLASSEN` moet de 13 canonieke namen + volgorde volgen uit
`api/references/jas-klassen-referentie.md` (de "enige toegestane klassen" van dit project).

Eigen tests (niet geport van de referentie se `tests/test_jas_klassen.py` — niet gelezen, en
sowieso tegen een andere bron: hier de markdown-referentie van dit project, niet
wetsanalyse-ai's `docs/wetsanalyse-rijk/H2-JAS.md`), tegen `agent/jas_klassen.py` (werkwijze-
story 047).
"""

from __future__ import annotations

import re
from pathlib import Path

from agent.jas_klassen import GELDIGE_JAS_KLASSEN, JAS_KLASSEN, JAS_KLASSEN_VOLGORDE

_MARKDOWN = Path(__file__).resolve().parents[3] / "api" / "references" / "jas-klassen-referentie.md"
_KOP_RE = re.compile(r"^## \d+\.\s+(.+)$", re.MULTILINE)


def _namen_uit_markdown() -> tuple[str, ...]:
    tekst = _MARKDOWN.read_text(encoding="utf-8")
    return tuple(_KOP_RE.findall(tekst))


def test_markdown_referentie_bestaat_en_heeft_dertien_koppen() -> None:
    namen = _namen_uit_markdown()
    assert len(namen) == 13, f"verwacht 13 genummerde koppen in {_MARKDOWN}, kreeg {len(namen)}"


def test_jas_klassen_volgorde_matcht_de_markdown_referentie() -> None:
    assert _namen_uit_markdown() == JAS_KLASSEN_VOLGORDE


def test_dertien_klassen_geen_meer_geen_minder() -> None:
    assert len(JAS_KLASSEN) == 13
    assert len(GELDIGE_JAS_KLASSEN) == 13


def test_geldige_jas_klassen_is_afgeleid_van_de_volgorde() -> None:
    assert frozenset(JAS_KLASSEN_VOLGORDE) == GELDIGE_JAS_KLASSEN


def test_elke_klasse_heeft_alle_velden_gevuld() -> None:
    for k in JAS_KLASSEN:
        assert k.naam.strip()
        assert k.omschrijving.strip()
        assert k.vraag.strip()
        assert k.uitdrukkingswijze.strip()
