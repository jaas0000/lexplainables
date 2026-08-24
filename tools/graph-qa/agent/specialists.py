"""Specialisten voor het supervisor-patroon.

Een specialist is een **declaratieve config**: een focus-prompt bovenop `SYSTEM_PROMPT` + een
toegestane tool-subset. De supervisor (`agent/supervisor.py`) kiest er één per vraag; `agent_node`
draait daarna de gewone agent↔tools-lus met die config. Uitbreiden = een entry toevoegen.

Poort van `wetsanalyse-ai/tools/graph-qa/agent/specialists.py`, zonder de `retrieval`-specialist
(die hoort bij de annotatie-ophaal-agent, die hier nog niet bestaat — werkwijze-story 045
§Afwijkingen).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Specialist:
    system: str
    tools: frozenset[str] | None  # None = alle tools


SPECIALISTS: dict[str, Specialist] = {
    "definitie": Specialist(
        system=(
            "Je bent de DEFINITIE-specialist. Je herleidt en verklaart juridische begrippen. "
            "Begin bij resolve_begrip en de definitieartikelen; citeer de brondefinitie letterlijk "
            "met vindplaats en benoem of het een wettelijke definitie of interpretatie is.\n"
            "Begripsbepalingen staan doorgaans in artikel 1 of 2 van een regeling; haal die beide "
            "in één beurt op in plaats van na elkaar. Het definitie-artikel zelf bevat vaak alleen "
            "de aanhef ('Deze wet verstaat onder:') — de definities zitten in de onderdelen van "
            "het lid, die get_lid meelevert. Citeer de vindplaats van het ONDERDEEL (…&o=k), niet "
            "die van het hele lid."
        ),
        tools=frozenset(
            {
                "resolve_begrip",
                "search_wetgeving",
                "semantic_search",
                "get_artikel",
                "get_lid",
                "graph_schema",
                "raw_sparql",
            }
        ),
    ),
    "duiding": Specialist(
        system=(
            "Je bent de DUIDINGS-specialist. Je legt de betekenis, structuur en samenhang van een "
            "bepaling uit. Gebruik get_context voor de bepaling met haar structuur en "
            "verwijzingen, en follow_verwijzingen/referenced_by om kruisverwijzingen te volgen."
        ),
        tools=frozenset(
            {
                "get_context",
                "get_artikel",
                "get_lid",
                "follow_verwijzingen",
                "referenced_by",
                "search_wetgeving",
                "semantic_search",
                "graph_schema",
                "raw_sparql",
            }
        ),
    ),
    "algemeen": Specialist(system="", tools=None),
}

DEFAULT = "algemeen"


def get(name: str | None) -> Specialist:
    """Specialist op naam; valt terug op 'algemeen' bij onbekend/leeg."""
    return SPECIALISTS.get((name or "").strip().lower(), SPECIALISTS[DEFAULT])
