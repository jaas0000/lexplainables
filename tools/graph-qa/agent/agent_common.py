"""Kleine helper gedeeld door de wrapper (`agent.py`) en de orkestrator (`orchestrator.py`) —
een eigen module i.p.v. de een uit de ander te importeren, om een importcirkel te vermijden.
"""

from __future__ import annotations


class BeurtGestopt(Exception):
    """De jurist heeft om stoppen gevraagd; de graaf hoort geen nieuwe node meer te betreden.

    Bewust een exception en géén taak-annulering. De nodes zijn synchroon; een lopende LLM- of
    MCP-call halverwege afbreken laat de MCP-verbinding in een inconsistente staat achter. Dit
    stopt dus netjes op een **nodegrens**, met een consistente checkpointer-state.

    Gevolg voor de gebruiker: stoppen kost tijd, want de lopende stap maakt zichzelf eerst af —
    dat hoort de UI te tonen in plaats van te doen alsof het meteen klaar is.
    """
