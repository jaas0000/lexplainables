"""De ene bron voor het annotatie-domein (werkwijze-ADR-0011, story 022).

Twee tabellen:
- `annotatie_documenten` — annotatie-werkdocument per (werkgebied, bwb_id, artikel, lid).
  De `elementen`-kolom slaat een lijst van `AnnotatieElement`-objecten op als JSON; de store
  serialiseert en deserialiseert via `model_dump()` / `model_validate()`.
- `annotatie_audit` — append-only auditlog; tijdlijn = ORDER BY id (BIGINT autoincrement).

Gebruikt `GELDIGE_JAS_KLASSEN` uit `shared/validation.py` (tweede onafhankelijke gebruiker naast
`engine/validation.py` — vandaar naar `shared/` verplaatst, zie feature-bouwen regel 8).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
)

metadata = MetaData()


# --- Enums --------------------------------------------------------------------------


class DocumentStatus(StrEnum):
    voorgesteld = "voorgesteld"
    gedeeltelijk_gereviewd = "gedeeltelijk_gereviewd"
    klaar = "klaar"


class Levenscyclus(StrEnum):
    voorgesteld = "voorgesteld"
    critic_gecheckt = "critic_gecheckt"
    human_goedgekeurd = "human_goedgekeurd"
    bewerkt = "bewerkt"
    afgewezen = "afgewezen"


class BeslissingType(StrEnum):
    goedkeuren = "goedkeuren"
    bewerken = "bewerken"
    afwijzen = "afwijzen"
    opmerking = "opmerking"


class BeoordelingsReden(StrEnum):
    onduidelijk = "onduidelijk"
    fout_klasse = "fout_klasse"
    fout_tekst = "fout_tekst"
    dubbeling = "dubbeling"
    overig = "overig"


class Aandacht(StrEnum):
    groen = "groen"
    geel = "geel"
    rood = "rood"


# --- Pydantic-contracten (geneste structuren in de JSON-kolom) -----------------------


class Alternatief(BaseModel):
    klasse: str
    tekst: str
    toelichting: str


class CriticRonde(BaseModel):
    """Wat de Critic (graph-qa) in één pas van dit element vond — het geheugen van de Critic
    over meerdere rondes heen, en het spoor voor de jurist. Poort van graph-qa's
    `agent.models.CriticRonde` (zie `tools/graph-qa/agent/models.py`)."""

    ronde: int
    aandacht: str = ""
    motivatie: str = ""
    actie: str = "behoud"
    toegepast: bool = False
    voorstel_klasse: str = ""
    voorstel_tekst: str = ""


class RunInfo(BaseModel):
    """Herkomst van een agent-run — welk model/versie deze elementen voorstelde. Poort van
    graph-qa's `run`-event (`emit_node`, zie `tools/graph-qa/agent/orchestrator.py`)."""

    model: str = ""
    provider: str = ""
    agent_versie: str = ""
    critic_rondes: int = 0
    stop_reden: str = ""


class Beslissing(BaseModel):
    type: BeslissingType
    actor: str
    tijd: str
    reden: BeoordelingsReden | None = None
    opmerking: str | None = None
    wijziging: dict = Field(default_factory=dict)


class AnnotatieElement(BaseModel):
    id: str
    klasse: str
    tekst: str
    lid: str = ""
    toelichting: str = ""
    vindplaats: str = ""
    span: dict | None = None
    herkomst: str = ""
    levenscyclus: Levenscyclus = Levenscyclus.voorgesteld
    alternatieven: list[Alternatief] = Field(default_factory=list)
    aandacht: Aandacht | None = None
    critic: str | None = None
    critic_rondes: list[CriticRonde] = Field(default_factory=list)
    beslissingen: list[Beslissing] = Field(default_factory=list)
    diff: dict = Field(default_factory=dict)


class AnnotatieDocument(BaseModel):
    slug: str
    client_id: str
    werkgebied: str
    bwb_id: str
    artikel: str
    lid: str = ""
    status: DocumentStatus = DocumentStatus.voorgesteld
    elementen: list[AnnotatieElement] = Field(default_factory=list)
    laatste_run: RunInfo | None = None
    aangemaakt: str
    bijgewerkt: str


class AuditRegel(BaseModel):
    id: int
    document_slug: str
    client_id: str
    actor: str
    actie: str
    element_id: str | None
    detail: dict
    tijdstip: str


# --- Input-contracten ---------------------------------------------------------------


class DocumentAanmaken(BaseModel):
    werkgebied: str = Field(..., min_length=1)
    bwb_id: str = Field(..., min_length=1)
    artikel: str = Field(..., min_length=1)
    lid: str | None = None


class ElementInvoer(BaseModel):
    id: str = ""
    klasse: str
    tekst: str
    lid: str = ""
    toelichting: str = ""
    vindplaats: str = ""
    span: dict | None = None
    alternatieven: list[Alternatief] = Field(default_factory=list)
    aandacht: Aandacht | None = None
    critic: str | None = None
    critic_rondes: list[CriticRonde] = Field(default_factory=list)


class ElementenInvoer(BaseModel):
    """`PUT .../elementen` is altijd de agent se schrijfpad (zelfde aanname als de referentie —
    een jurist beslist via de losse `beslissing`-endpoint, nooit via een rauwe PUT). Vandaar
    merge-niet-vervang-semantiek in de router: bestaande, al door een jurist beoordeelde
    elementen blijven ongemoeid ("bevroren"), alleen nieuwe/nog-niet-beoordeelde voorstellen
    worden overschreven of toegevoegd."""

    elementen: list[ElementInvoer]
    run: RunInfo | None = None


class WijzigingInvoer(BaseModel):
    klasse: str | None = None
    tekst: str | None = None
    toelichting: str | None = None
    lid: str | None = None


class BeslissingInvoer(BaseModel):
    type: BeslissingType
    reden: BeoordelingsReden | None = None
    opmerking: str | None = None
    wijziging: WijzigingInvoer | None = None

    @model_validator(mode="after")
    def _valideer_vereiste_velden(self) -> BeslissingInvoer:
        """`bewerken` vereist `reden` én `wijziging`; `afwijzen` vereist `reden`."""
        if self.type in (BeslissingType.bewerken, BeslissingType.afwijzen) and self.reden is None:
            raise ValueError("'reden' is verplicht bij type 'bewerken' of 'afwijzen'.")
        if self.type == BeslissingType.bewerken and self.wijziging is None:
            raise ValueError("'wijziging' is verplicht bij type 'bewerken'.")
        return self


class WetsartikelOnderdeel(BaseModel):
    nummer: str | None
    tekst: str


class WetsartikelLid(BaseModel):
    nummer: str | None
    tekst: str
    onderdelen: list[WetsartikelOnderdeel] = Field(default_factory=list)


class Wetsartikel(BaseModel):
    bwb_id: str
    artikel: str
    opschrift: str | None
    tekst: str
    onderdelen: list[WetsartikelOnderdeel] = Field(default_factory=list)
    leden: list[WetsartikelLid] = Field(default_factory=list)


class DocumentSamenvatting(BaseModel):
    slug: str
    bwb_id: str
    artikel: str
    lid: str
    werkgebied: str
    status: DocumentStatus
    aantal_elementen: int
    bijgewerkt: str


# --- SQLAlchemy Core tables ---------------------------------------------------------

annotatie_documenten = Table(
    "annotatie_documenten",
    metadata,
    Column("slug", Text, primary_key=True),
    Column("client_id", Text, nullable=False),
    Column("werkgebied", Text, nullable=False),
    Column("bwb_id", Text, nullable=False),
    Column("artikel", Text, nullable=False),
    Column("lid", Text, nullable=False, default=""),
    Column("status", Text, nullable=False, default="voorgesteld"),
    Column("elementen", JSON, nullable=False, default=list),
    Column("laatste_run", JSON, nullable=True),
    Column("aangemaakt", DateTime(timezone=True), nullable=False),
    Column("bijgewerkt", DateTime(timezone=True), nullable=False),
    Index("ix_annotatie_documenten_client_id", "client_id"),
)

annotatie_audit = Table(
    "annotatie_audit",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("document_slug", Text, nullable=False),
    Column("client_id", Text, nullable=False),
    Column("actor", Text, nullable=False),
    Column("actie", Text, nullable=False),
    Column("element_id", Text, nullable=True),
    Column("detail", JSON, nullable=False, default=dict),
    Column("tijdstip", DateTime(timezone=True), nullable=False),
    Index("ix_annotatie_audit_document_slug", "document_slug"),
)


# --- Mapping-functies (werkwijze-ADR-0011) -------------------------------------------


def document_uit_rij(rij) -> AnnotatieDocument:
    """Expliciete mapping van een databaserij naar het volledige `AnnotatieDocument`-contract."""
    elementen_raw = rij.elementen or []
    return AnnotatieDocument(
        slug=rij.slug,
        client_id=rij.client_id,
        werkgebied=rij.werkgebied,
        bwb_id=rij.bwb_id,
        artikel=rij.artikel,
        lid=rij.lid or "",
        status=DocumentStatus(rij.status),
        elementen=[AnnotatieElement.model_validate(e) for e in elementen_raw],
        laatste_run=RunInfo.model_validate(rij.laatste_run) if rij.laatste_run else None,
        aangemaakt=rij.aangemaakt.isoformat(),
        bijgewerkt=rij.bijgewerkt.isoformat(),
    )


def samenvatting_uit_rij(rij) -> DocumentSamenvatting:
    """Expliciete mapping van een databaserij naar het `DocumentSamenvatting`-contract."""
    elementen_raw = rij.elementen or []
    return DocumentSamenvatting(
        slug=rij.slug,
        bwb_id=rij.bwb_id,
        artikel=rij.artikel,
        lid=rij.lid or "",
        werkgebied=rij.werkgebied,
        status=DocumentStatus(rij.status),
        aantal_elementen=len(elementen_raw),
        bijgewerkt=rij.bijgewerkt.isoformat(),
    )


def audit_uit_rij(rij) -> AuditRegel:
    """Expliciete mapping van een databaserij naar het `AuditRegel`-contract."""
    return AuditRegel(
        id=rij.id,
        document_slug=rij.document_slug,
        client_id=rij.client_id,
        actor=rij.actor,
        actie=rij.actie,
        element_id=rij.element_id,
        detail=rij.detail or {},
        tijdstip=rij.tijdstip.isoformat(),
    )
