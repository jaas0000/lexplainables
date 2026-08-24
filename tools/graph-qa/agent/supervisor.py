"""Supervisor van de antwoord-agent: kiest per vraag een specialist en beslist of de vraag
buiten de wetgeving valt.

Poort van `wetsanalyse-ai/tools/graph-qa/agent/supervisor.py`, ingekort (werkwijze-story 045
§Afwijkingen): geen `WORKERS:`-regel en geen antwoord-vs-annotatie-keuze — er is hier maar één
worker (de antwoord-agent uit story 044), dus niets om tussen te routeren of te ketenen.
"""

from __future__ import annotations

SUPERVISOR_SYSTEM = (
    "Je bent de supervisor van een juridische agent over een kennisgraaf met Nederlandse wet- en "
    "regelgeving (invordering/belastingen). Bepaal welke specialist de vraag moet beantwoorden. "
    "Antwoord in EXACT dit formaat, twee regels:\n"
    "SPECIALIST: <definitie|duiding|algemeen>\n"
    "PLAN: <1-2 zinnen aanpak, of AFWIJZEN als de vraag niet over Nederlandse wet- en regelgeving "
    "gaat>\n"
    "AFWIJZEN is alleen voor vragen die BUITEN de wetgeving vallen: het weer, actualiteit, "
    "programmeren, rekensommen, meningen. Gaat de vraag wél over een wet, een bepaling of een "
    "juridisch begrip, dan kies je een specialist — óók als je de genoemde regeling niet kent of "
    "denkt dat ze niet in de graaf zit. Dat is niet aan jou om te weten: je hebt geen tools en je "
    "hebt niet gekeken. De specialist zoekt het op en zegt zelf dat het niet in de kennisgraaf "
    "staat als hij niets vindt.\n"
    "SPECIALIST: 'definitie' voor begrip-/definitievragen, 'duiding' voor betekenis/structuur/"
    "samenhang van een bepaling, anders 'algemeen'."
)

_SPECIALISTEN = ("definitie", "duiding", "algemeen")


def parse_supervisor(text: str) -> tuple[str, str, bool]:
    """(specialist, plan, afwijzen).

    Onbekende/lege `SPECIALIST:`-waarde blijft op de default `"algemeen"` staan — een onverwacht
    modelantwoord mag nooit crashen, alleen degraderen naar de brede, generieke specialist.
    """
    specialist, plan = "algemeen", ""
    for line in text.splitlines():
        low = line.strip()
        up = low.upper()
        if up.startswith("SPECIALIST:"):
            val = low.split(":", 1)[1].strip().lower()
            if val in _SPECIALISTEN:
                specialist = val
        elif up.startswith("PLAN:"):
            plan = low.split(":", 1)[1].strip()
    if not plan:
        plan = text.strip()
    return specialist, plan, plan.strip().upper().startswith("AFWIJZEN")
