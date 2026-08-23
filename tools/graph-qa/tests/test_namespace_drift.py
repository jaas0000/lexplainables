"""Drift-guard: de IRI-ruimte van de graaf, over de componentgrenzen heen (werkwijze-story 041).

Waarom deze test bestaat. De basis-IRI wordt geschreven door de importer (`tools/bwb-import`) en
gelezen door graph-qa. Die twee leven in verschillende venv's, dus er is geen compiler die ze aan
elkaar houdt — en het faalgedrag is stil: loopt graph-qa's filterwaarde uit de pas met wat de
importer wegschrijft, dan matcht `STRSTARTS` niets en krijgt de jurist een leeg antwoord in
plaats van een foutmelding.

`tools/bwb-import` wordt als **bestand** gelezen, niet geïmporteerd — zijn venv is hier niet
beschikbaar (ADR-0002: geen gedeelde import over een servicegrens). We vergelijken de defaults in
de broncode, niet de runtime-waarde: die hangt van de omgeving af en zou de test
machine-afhankelijk maken.

Poort van `wetsanalyse-ai/tools/graph-qa/tests/test_namespace_drift.py`, aangepast: geen
frontend-check (dit project se frontend leest geen graaf-IRI's rechtstreeks — dat gebeurt in
`api/`, zie de vervolgpunt-notitie in de story-doc).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WORTEL = Path(__file__).resolve().parents[3]
RDF_VOCAB = WORTEL / "tools" / "bwb-import" / "app" / "rdf_vocab.py"
NAMESPACE = WORTEL / "tools" / "graph-qa" / "agent" / "namespace.py"


def _literal(pad: Path, patroon: str) -> str:
    tekst = pad.read_text(encoding="utf-8")
    treffer = re.search(patroon, tekst)
    assert treffer, f"{pad.name}: patroon niet gevonden — is de constante hernoemd? ({patroon})"
    return treffer.group(1)


@pytest.mark.parametrize(
    "naam, patroon_importer, patroon_agent",
    [
        (
            "basis",
            r'DEFAULT_BASE_IRI\s*=\s*"([^"]+)"',
            r'BASIS\s*=\s*os\.getenv\([^)]*\)\s*or\s*"([^"]+)"',
        ),
        (
            "ontologie",
            r'DEFAULT_ONTOLOGY_IRI\s*=\s*"([^"]+)"',
            r'ONTOLOGIE\s*=\s*os\.getenv\([^)]*\)\s*or\s*"([^"]+)"',
        ),
    ],
)
def test_agent_volgt_de_importer(naam: str, patroon_importer: str, patroon_agent: str) -> None:
    importer = _literal(RDF_VOCAB, patroon_importer)
    agent = _literal(NAMESPACE, patroon_agent)
    assert agent == importer, (
        f"{naam}-IRI loopt uiteen: de importer schrijft {importer!r}, graph-qa zoekt {agent!r}. "
        "Dat levert geen fout op maar een leeg antwoord — pas beide aan, of geef graph-qa "
        "GRAPHDB_BASE_IRI/GRAPHDB_ONTOLOGY_IRI mee."
    )
