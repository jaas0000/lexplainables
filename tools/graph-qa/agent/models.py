"""Pydantic-modellen voor de agent-loop.

Getrimd tot wat de antwoord-agent-loop (stories 044-046) en de enkele-ronde-annotatie (story 047)
gebruiken — geen `ChatRequest`/`AgentDoel`/`ChatContext`/`ArtikelResult`, en van de
annotatie-modellen bewust geen `CriticRonde`/`CriticOordeel`/`OntbrekendItem`/`AgentRun`; die
horen bij de stories die de API-laag resp. de critic/patch/herzie/emit-keten bouwen.

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


# --- Annotatie (story 047: enkele ronde, geen critic) --------------------------------------


class AnnotatieAlternatief(BaseModel):
    """Een kandidaat-klasse bij twijfel, met korte motivatie (disambiguatie)."""

    klasse: str
    motivatie: str = ""


class AnnotatieVoorstel(BaseModel):
    """Eén door de agent voorgesteld JAS-annotatie-element voor een artikel.

    `tekst` is een letterlijk fragment uit de artikeltekst; `grounded`/`vindplaats` worden
    server-side ingevuld door de brongetrouwheid-check (nooit door het model). Bewust **zonder**
    `aandacht`/`critic`/`critic_rondes` — die velden hoort de Critic-node te zetten (een latere
    story); ze hebben hier nog geen consument.
    """

    # Stabiel id, hier toegekend (niet door het model). Een latere revisieronde matcht erop; op
    # positie koppelen breekt zodra een herziening iets toevoegt of weglaat.
    id: str = ""
    klasse: str
    tekst: str
    lid: str = ""
    toelichting: str = ""
    alternatieven: list[AnnotatieAlternatief] = []
    grounded: bool = False
    vindplaats: str = ""  # bwbId/artikel/lid-notatie


class VerworpenFragment(BaseModel):
    """Een voorstel dat de grondingscheck niet haalde.

    Anders alleen geteld en weggegooid. Juist deze informatie laat een latere herzieningsronde
    zichzelf corrigeren: "dit citaat staat niet letterlijk in de tekst" is een aanwijzing, geen
    fout."""

    klasse: str
    tekst: str
    reden: str  # ongeldige_klasse | niet_letterlijk
