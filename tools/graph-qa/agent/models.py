"""Pydantic-modellen voor de agent-loop.

Getrimd tot wat de antwoord-agent-loop (stories 044-046), de annotatieketen (stories 047-048) en
de HTTP-laag (stories 053-054, `ChatRequest`/`RunStart`) gebruiken — geen `AgentDoel`/
`ChatContext`/`ArtikelResult` (bestaan nog niet in `answer_stream()`, zie story 050 §Afwijkingen
punt 3), en van de annotatie-modellen bewust geen `AgentRun`; die hoort bij de story die
`emit_node` bouwt.

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


class ChatRequest(BaseModel):
    """Body van `POST /v1/chat` en `POST /v1/runs` (stories 053-054). Geen `modus`/`context`/
    `doel` — die bestaan nog niet in `answer_stream()`."""

    question: str
    conversation_id: str | None = None


class RunStart(BaseModel):
    """Wat een client van het run-model te zien krijgt — matcht `agent.runs.Run.samenvatting()`
    (story 054)."""

    run_id: str
    conversation_id: str
    vraag: str
    status: Literal["loopt", "klaar", "gestopt", "mislukt"]
    volgende_seq: int
    weggevallen: int


# --- Annotatie (stories 047-048: enkele ronde + critic) ------------------------------------


class AnnotatieAlternatief(BaseModel):
    """Een kandidaat-klasse bij twijfel, met korte motivatie (disambiguatie)."""

    klasse: str
    motivatie: str = ""


class CriticRonde(BaseModel):
    """Wat de Critic in één pas van dit element vond, en wat hij ermee wilde.

    Dit is drie dingen tegelijk: het geheugen van de Critic in een volgende ronde (`_stand_van`),
    het spoor dat de jurist op de kaart terugziet, en de reden dat een latere patch-stap kan zien
    of een punt al eens is gemaakt.
    """

    ronde: int
    aandacht: str = ""  # groen | geel | rood
    motivatie: str = ""
    actie: str = "behoud"  # behoud | vervang | verwijder
    # Is de instructie ook uitgevoerd? Een latere patch-story zet dit. Zonder dit verschilt "de
    # Critic vroeg erom" niet van "het is ook gebeurd" — en dat verschil moet een auditspoor
    # kunnen laten zien.
    toegepast: bool = False
    voorstel_klasse: str = ""
    voorstel_tekst: str = ""


class AnnotatieVoorstel(BaseModel):
    """Eén door de agent voorgesteld JAS-annotatie-element voor een artikel.

    `tekst` is een letterlijk fragment uit de artikeltekst; `grounded`/`vindplaats` worden
    server-side ingevuld door de brongetrouwheid-check (nooit door het model). `aandacht`/
    `critic`/`critic_rondes` worden door `critic_node` (story 048) gezet — bij `annoteer_node`'s
    eigen output blijven ze op hun default.
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
    aandacht: str = ""  # "" | groen | geel | rood — gezet door critic_node
    critic: str = ""  # korte Critic-motivatie bij het aandacht-niveau
    critic_rondes: list[CriticRonde] = []  # het heen-en-weer per ronde; leeg tot de eerste pas


class CriticOordeel(BaseModel):
    """Wat de Critic van één voorstel vindt, inclusief wat de annoteerder ermee moet doen.

    Zonder `actie`/`voorstel_*` is een herzieningsronde onmogelijk: dan weet de annoteerder wél
    dat er iets mis is, maar niet wat.
    """

    aandacht: str = ""  # groen | geel | rood
    motivatie: str = ""
    actie: str = "behoud"  # behoud | vervang | verwijder
    voorstel_klasse: str = ""
    voorstel_tekst: str = ""


class OntbrekendItem(BaseModel):
    """Een door de Critic vermoed ontbrekend element: een JAS-klasse die waarschijnlijk óók in de
    tekst zit maar niet is gemarkeerd. `tekst` is optioneel — staat er een letterlijk fragment
    bij, dan kan een latere herzieningsronde het element daadwerkelijk toevoegen in plaats van
    alleen een klasse te noemen."""

    klasse: str
    reden: str = ""
    tekst: str = ""


class VerworpenFragment(BaseModel):
    """Een voorstel dat de grondingscheck niet haalde.

    Anders alleen geteld en weggegooid. Juist deze informatie laat een latere herzieningsronde
    zichzelf corrigeren: "dit citaat staat niet letterlijk in de tekst" is een aanwijzing, geen
    fout."""

    klasse: str
    tekst: str
    reden: str  # ongeldige_klasse | niet_letterlijk
