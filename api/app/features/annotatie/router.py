"""Routelaag voor het annotatie-domein (stack-profiel.md §Feature-eenheid, story 022).

Businessregels die niet uit de modellen volgen:
- Client-scoping: een gebruiker ziet en bewerkt alleen zijn eigen documenten — een onbekend of
  andermans document geeft een 404 (niet 403) om het bestaan niet te lekken.
- Elementenvalidatie bij PUT: ongeldige JAS-klasse of lege tekst → element overgeslagen (niet
  de hele batch afgewezen). De response meldt hoeveel elementen verworpen zijn.
- Beslissingsvalidatie: `bewerken` vereist `reden` én `wijziging`; `afwijzen` vereist `reden`
  (afgedwongen door `BeslissingInvoer.model_validator` in models.py → automatisch 422).
- Levenscyclus na beslissing: `goedkeuren` → `human_goedgekeurd`; `bewerken` → `bewerkt`;
  `afwijzen` → `afgewezen`; `opmerking` → levenscyclus ongewijzigd.
- Documentstatus na beslissing: herberekend op basis van levenscyclus-verdeling van alle
  elementen — volledig beslist → `klaar`; gedeeltelijk → `gedeeltelijk_gereviewd`.

Gebruikt `GELDIGE_JAS_KLASSEN` uit `shared/validation.py` (zie feature-bouwen regel 8;
terugverwijzing: annotatie gebruikt `shared/validation.py`, zie daar).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ...db import get_engine
from ...shared.auth import huidige_gebruiker
from ...shared.tijd import nu
from ...shared.validation import GELDIGE_JAS_KLASSEN
from .models import (
    AnnotatieDocument,
    AnnotatieElement,
    AuditRegel,
    Beslissing,
    BeslissingInvoer,
    BeslissingType,
    DocumentAanmaken,
    DocumentSamenvatting,
    DocumentStatus,
    ElementenInvoer,
    Levenscyclus,
)
from .store import (
    AnnotatieStore,
    DocumentNietGevonden,
    SqlAlchemyAnnotatieStore,
)

router = APIRouter(prefix="/annotatie/documenten", tags=["annotatie"])


def get_store() -> AnnotatieStore:
    """FastAPI-dependency die de router aan een concrete store koppelt (werkwijze-ADR-0007)."""
    return SqlAlchemyAnnotatieStore(get_engine())


# --- Response-modellen -------------------------------------------------------------


class ElementenZettenOut(BaseModel):
    aanvaard: int
    verworpen: int


class DocumentenLijstOut(BaseModel):
    items: list[DocumentSamenvatting]


class AuditlogOut(BaseModel):
    items: list[AuditRegel]


# --- Helpers -----------------------------------------------------------------------


async def _laad_eigen_document(
    slug: str, client_id: str, store: AnnotatieStore
) -> AnnotatieDocument:
    """Laad document en controleer eigenaarschap — 404 als niet gevonden of van iemand anders."""
    doc = await store.laad_document(slug)
    if doc is None or doc.client_id != client_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document niet gevonden.")
    return doc


def _bereken_status(elementen: list[AnnotatieElement]) -> DocumentStatus:
    """Herbereken documentstatus op basis van de levenscyclus-verdeling van alle elementen."""
    if not elementen:
        return DocumentStatus.voorgesteld
    beslist = {Levenscyclus.human_goedgekeurd, Levenscyclus.bewerkt, Levenscyclus.afgewezen}
    aantal_beslist = sum(1 for e in elementen if e.levenscyclus in beslist)
    if aantal_beslist == len(elementen):
        return DocumentStatus.klaar
    if aantal_beslist > 0:
        return DocumentStatus.gedeeltelijk_gereviewd
    return DocumentStatus.voorgesteld


_LEVENSCYCLUS_NA_BESLISSING: dict[BeslissingType, Levenscyclus | None] = {
    BeslissingType.goedkeuren: Levenscyclus.human_goedgekeurd,
    BeslissingType.bewerken: Levenscyclus.bewerkt,
    BeslissingType.afwijzen: Levenscyclus.afgewezen,
    BeslissingType.opmerking: None,  # geen levenscyclus-overgang bij opmerking
}


# --- Endpoints ---------------------------------------------------------------------


@router.post("", response_model=AnnotatieDocument, status_code=status.HTTP_201_CREATED)
async def maak_document(
    body: DocumentAanmaken,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> AnnotatieDocument:
    slug = uuid.uuid4().hex[:16]
    doc = AnnotatieDocument(
        slug=slug,
        client_id=client_id,
        werkgebied=body.werkgebied,
        bwb_id=body.bwb_id,
        artikel=body.artikel,
        lid=body.lid or "",
        aangemaakt="",  # store vult dit in
        bijgewerkt="",
    )
    result = await store.maak_document(doc)
    await store.schrijf_audit(
        slug,
        client_id,
        actor=client_id,
        actie="document-aangemaakt",
        detail={"werkgebied": body.werkgebied, "bwb_id": body.bwb_id, "artikel": body.artikel},
    )
    return result


@router.get("", response_model=DocumentenLijstOut)
async def lijst_documenten(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> DocumentenLijstOut:
    items = await store.lijst_documenten_samenvatting(client_id, limit=limit, offset=offset)
    return DocumentenLijstOut(items=items)


@router.get("/{slug}", response_model=AnnotatieDocument)
async def get_document(
    slug: str,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> AnnotatieDocument:
    return await _laad_eigen_document(slug, client_id, store)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def verwijder_document(
    slug: str,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> None:
    # Eerst eigenaarschap verifiëren, dan verwijderen.
    await _laad_eigen_document(slug, client_id, store)
    # Bewust try/except: een TOCTOU-race (gelijktijdige delete) geeft anders een 500.
    try:
        await store.verwijder_document(slug)
    except DocumentNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.put("/{slug}/elementen", response_model=ElementenZettenOut)
async def zet_elementen(
    slug: str,
    body: ElementenInvoer,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> ElementenZettenOut:
    """Vervangt de elementenlijst volledig.

    Ongeldige JAS-klasse of lege tekst → element overgeslagen.
    """
    await _laad_eigen_document(slug, client_id, store)

    aanvaard: list[AnnotatieElement] = []
    verworpen = 0
    for invoer in body.elementen:
        if not invoer.tekst.strip():
            verworpen += 1
            continue
        if invoer.klasse not in GELDIGE_JAS_KLASSEN:
            verworpen += 1
            continue
        element_id = uuid.uuid4().hex[:12]
        aanvaard.append(
            AnnotatieElement(
                id=element_id,
                klasse=invoer.klasse,
                tekst=invoer.tekst,
                lid=invoer.lid,
                toelichting=invoer.toelichting,
                vindplaats=invoer.vindplaats,
                span=invoer.span,
                herkomst=client_id,
                alternatieven=invoer.alternatieven,
                aandacht=invoer.aandacht,
                critic=invoer.critic,
            )
        )

    await store.vervang_elementen(slug, aanvaard, DocumentStatus.voorgesteld)
    await store.schrijf_audit(
        slug,
        client_id,
        actor=client_id,
        actie="elementen-voorgesteld",
        detail={"aanvaard": len(aanvaard), "verworpen": verworpen},
    )
    return ElementenZettenOut(aanvaard=len(aanvaard), verworpen=verworpen)


@router.post(
    "/{slug}/elementen/{element_id}/beslissing",
    response_model=AnnotatieDocument,
)
async def registreer_beslissing(
    slug: str,
    element_id: str,
    body: BeslissingInvoer,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> AnnotatieDocument:
    """Registreert een human-beslissing op één element. Valideert type-specifieke vereisten
    (afgedwongen door `BeslissingInvoer` validator → 422 bij ontbrekende velden)."""
    doc = await _laad_eigen_document(slug, client_id, store)

    # Zoek het element op in de lijst.
    element_idx = next((i for i, e in enumerate(doc.elementen) if e.id == element_id), None)
    if element_idx is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Element '{element_id}' niet gevonden.")

    tijdstip = nu().isoformat()
    beslissing = Beslissing(
        type=body.type,
        actor=client_id,
        tijd=tijdstip,
        reden=body.reden,
        opmerking=body.opmerking,
        wijziging=body.wijziging.model_dump(exclude_none=True) if body.wijziging else {},
    )

    element = doc.elementen[element_idx]
    element.beslissingen.append(beslissing)

    nieuwe_lc = _LEVENSCYCLUS_NA_BESLISSING[body.type]
    if nieuwe_lc is not None:
        element.levenscyclus = nieuwe_lc

    # Pas eventuele wijzigingen toe op het element zelf (bij type 'bewerken').
    if body.type == BeslissingType.bewerken and body.wijziging:
        w = body.wijziging
        if w.klasse is not None:
            element.klasse = w.klasse
        if w.tekst is not None:
            element.tekst = w.tekst
        if w.toelichting is not None:
            element.toelichting = w.toelichting
        if w.lid is not None:
            element.lid = w.lid

    nieuwe_status = _bereken_status(doc.elementen)
    await store.vervang_elementen(slug, doc.elementen, nieuwe_status)
    await store.schrijf_audit(
        slug,
        client_id,
        actor=client_id,
        actie=f"beslissing-{body.type.value}",
        element_id=element_id,
        detail={
            "reden": body.reden.value if body.reden else None,
            "opmerking": body.opmerking,
        },
    )

    # Return de in-memory staat (elementen al bijgewerkt) — vermijdt een extra SELECT.
    return doc.model_copy(update={"status": nieuwe_status, "bijgewerkt": nu().isoformat()})


@router.get("/{slug}/audit", response_model=AuditlogOut)
async def get_audit(
    slug: str,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> AuditlogOut:
    await _laad_eigen_document(slug, client_id, store)
    regels = await store.lees_audit(slug)
    return AuditlogOut(items=regels)
