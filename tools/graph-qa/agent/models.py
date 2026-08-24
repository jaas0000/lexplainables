"""Pydantic-modellen voor de agent-loop.

Getrimd tot wat story 044 (de minimale antwoord-agent-loop) gebruikt — geen `ChatRequest`/
`AgentDoel`/`ChatContext`/annotatie-modellen/`ArtikelResult`; die horen bij de stories die de
API-laag, de annotatieketen resp. het documentpaneel bouwen.

Poort van `wetsanalyse-ai/tools/graph-qa/agent/models.py`, 1:1 voor de hier opgenomen klassen.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Source(BaseModel):
    label: str
    uri: str
    # Herkomst-velden (additief; een toekomstige BFF zou alleen label + uri hoeven te lezen).
    iri: str | None = None
    jci: str | None = None
    origin_tool: str | None = None


# SSE-events (nog niet aangesloten op een streamende laag in deze story, maar wel het contract dat
# een latere API-story zal uitsturen — hier al in de vorm van de referentie, zodat orchestrator.py
# en de API-laag straks dezelfde vocabulaire delen).
class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    content: str


class SourcesEvent(BaseModel):
    type: Literal["sources"] = "sources"
    sources: list[Source]


class GroundingEvent(BaseModel):
    """De uitkomst van de brongetrouwheidstoets op het antwoord.

    `niveau` is fijner dan `grounded` en is de waarde om te tonen: "onbepaald" betekent dat het
    antwoord geen enkele vindplaats of citaat noemde en er dus niets te controleren viel. Dat als
    "gegrond" presenteren zou schijnzekerheid zijn.
    """

    type: Literal["grounding"] = "grounding"
    grounded: bool
    cited: int = 0
    unsupported: list[str] = []
    # Als citaat gepresenteerde tekst die niet letterlijk in de opgehaalde tekst staat.
    niet_letterlijk: list[str] = []
    niveau: Literal["gegrond", "onbepaald", "ongegrond"] = "gegrond"


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str
