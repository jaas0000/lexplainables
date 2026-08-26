"""Routelaag voor het annotatie-domein (stack-profiel.md §Feature-eenheid, story 022).

Businessregels die niet uit de modellen volgen:
- Client-scoping: een gebruiker ziet en bewerkt alleen zijn eigen documenten — een onbekend of
  andermans document geeft een 404 (niet 403) om het bestaan niet te lekken.
- Elementenvalidatie bij PUT: ongeldige JAS-klasse of lege tekst → element overgeslagen (niet
  de hele batch afgewezen). De response meldt hoeveel elementen verworpen zijn.
- PUT is een merge, geen vervanging: `_merge_elementen` matcht op (tekst, lid) — een reeds door
  de jurist beoordeeld element blijft bevroren, ook als een latere agent-ronde er een nieuw
  voorstel voor doet (poort van graph-qa's eigen ontdubbel-/bevries-regels, zie
  `agent.annotatie.sleutel_van` in `tools/graph-qa`).
- Beslissingsvalidatie: `bewerken` vereist `reden` én `wijziging`; `afwijzen` vereist `reden`
  (afgedwongen door `BeslissingInvoer.model_validator` in models.py → automatisch 422).
- Levenscyclus na beslissing: `goedkeuren` → `human_goedgekeurd`; `bewerken` → `bewerkt`;
  `afwijzen` → `afgewezen`; `opmerking` → levenscyclus ongewijzigd.
- Documentstatus na beslissing: herberekend op basis van levenscyclus-verdeling van alle
  elementen — volledig beslist → `klaar`; gedeeltelijk → `gedeeltelijk_gereviewd`.
- Wetsartikeltekst (story 037): opgehaald uit GraphDB via `graphdb.py`, niet uit Postgres.
  Artikel niet in de graaf → 404; GraphDB onbereikbaar → 502 (onderscheiden van het generieke
  "document niet gevonden"-404 hierboven).

Gebruikt `GELDIGE_JAS_KLASSEN` uit `shared/validation.py` (zie feature-bouwen regel 8;
terugverwijzing: annotatie gebruikt `shared/validation.py`, zie daar).
"""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ...db import get_engine
from ...shared.auth import huidige_gebruiker
from ...shared.tijd import nu
from ...shared.validation import GELDIGE_JAS_KLASSEN
from .export import Exportformaat, bouw_export
from .graphdb import GraphDbNietBereikbaar, WetsartikelNietGevonden, haal_wetsartikel_op
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
    MensElementInvoer,
    StatusInvoer,
    Wetsartikel,
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


def _vereis_niet_afgerond(doc: AnnotatieDocument) -> None:
    """Zolang de jurist het document expliciet heeft geaccordeerd (`POST .../status`) weigert
    elk ander schrijfpad — agent-write-back (PUT elementen) incluis — met een 409. Dit endpoint
    (en heropenen via dezelfde route) is de enige uitweg én de enige ingang."""
    if doc.status == DocumentStatus.geaccordeerd:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Deze annotatie is afgerond. Heropen hem om te wijzigen.",
        )


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


_WS = re.compile(r"\s+")

# Levenscycli waarin een jurist al een oordeel heeft geveld — een agent-run mag deze elementen
# niet overschrijven (zie `_merge_elementen`).
_BESLIST = {Levenscyclus.human_goedgekeurd, Levenscyclus.bewerkt, Levenscyclus.afgewezen}


def _sleutel_van(tekst: str, lid: str) -> tuple[str, str]:
    """Identiteit van een markering los van zijn id: fragment + lid, bewust zonder klasse — een
    herziening mag herclassificeren en moet dan hetzelfde element treffen.

    Dezelfde regel als graph-qa's `agent.annotatie.sleutel_van` (`tools/graph-qa/agent/
    annotatie.py`) — drie implementaties (graph-qa, hier, de werkplek-UI zodra die 'm nodig
    heeft) horen op precies deze normalisatie uit te komen, anders ziet de jurist dezelfde
    markering dubbel."""
    return (_WS.sub(" ", tekst or "").strip().lower(), (lid or "").strip())


def _merge_elementen(
    bestaand: list[AnnotatieElement], voorstellen: list[AnnotatieElement]
) -> list[AnnotatieElement]:
    """Merge nieuwe agent-voorstellen met de bestaande elementenlijst.

    Een reeds door een jurist beoordeeld element (`_BESLIST`) is bevroren: een nieuw voorstel
    met dezelfde sleutel wordt genegeerd, het bestaande element blijft ongewijzigd staan. Een
    nog-niet-beoordeeld element met dezelfde sleutel wordt vervangen (het oudste id wint, zodat
    een eerder toegekend id — en de beslissingen die daaraan hangen — niet verweest raakt). Een
    element waarvoor geen nieuw voorstel meer binnenkomt blijft gewoon staan (de agent-run is
    geen volledige vervanging, alleen een aanvulling/correctie)."""
    per_sleutel: dict[tuple[str, str], AnnotatieElement] = {
        _sleutel_van(e.tekst, e.lid): e for e in bestaand
    }
    for voorstel in voorstellen:
        sleutel = _sleutel_van(voorstel.tekst, voorstel.lid)
        oud = per_sleutel.get(sleutel)
        if oud is not None and oud.levenscyclus in _BESLIST:
            continue  # bevroren — de jurist had hier al een oordeel over
        if oud is not None:
            voorstel = voorstel.model_copy(update={"id": oud.id})
        per_sleutel[sleutel] = voorstel
    return list(per_sleutel.values())


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
    """Merget nieuwe agent-voorstellen met de bestaande elementenlijst (`_merge_elementen`) —
    geen volledige vervanging. Een reeds door de jurist beoordeeld element blijft bevroren, ook
    als een latere agent-ronde er een nieuw voorstel voor doet (poort van de referentie-api se
    merge-gedrag, story 056-vervolg — werkwijze: nieuwe architectuureis van lexplainables t.o.v.
    de vroegere volledige-vervanging-semantiek).

    Ongeldige JAS-klasse of lege tekst → element overgeslagen (niet de hele batch afgewezen).
    """
    doc = await _laad_eigen_document(slug, client_id, store)
    _vereis_niet_afgerond(doc)

    voorstellen: list[AnnotatieElement] = []
    verworpen = 0
    for invoer in body.elementen:
        if not invoer.tekst.strip():
            verworpen += 1
            continue
        if invoer.klasse not in GELDIGE_JAS_KLASSEN:
            verworpen += 1
            continue
        voorstellen.append(
            AnnotatieElement(
                id=uuid.uuid4().hex[:12],
                klasse=invoer.klasse,
                tekst=invoer.tekst,
                lid=invoer.lid,
                toelichting=invoer.toelichting,
                vindplaats=invoer.vindplaats,
                span=invoer.span,
                herkomst="agent",
                alternatieven=invoer.alternatieven,
                aandacht=invoer.aandacht,
                critic=invoer.critic,
                critic_rondes=invoer.critic_rondes,
            )
        )

    gemerged = _merge_elementen(doc.elementen, voorstellen)
    nieuwe_status = _bereken_status(gemerged)
    await store.vervang_elementen(slug, gemerged, nieuwe_status, laatste_run=body.run)
    await store.schrijf_audit(
        slug,
        client_id,
        actor=client_id,
        actie="elementen-voorgesteld",
        detail={
            "voorgesteld": len(voorstellen),
            "verworpen": verworpen,
            "totaal_na_merge": len(gemerged),
        },
    )
    return ElementenZettenOut(aanvaard=len(voorstellen), verworpen=verworpen)


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
    _vereis_niet_afgerond(doc)

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


@router.post(
    "/{slug}/elementen",
    response_model=AnnotatieDocument,
    status_code=status.HTTP_201_CREATED,
)
async def voeg_element_toe(
    slug: str,
    body: MensElementInvoer,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> AnnotatieDocument:
    """Eén element dat de jurist zelf aanmaakt (een tekstselectie in het documentpaneel) — apart
    van `PUT`, want dat is de uitkomst van een agent-ronde en dit komt er los bij zonder de rest
    te raken. Meteen `human_goedgekeurd`: de jurist hoeft zijn eigen markering niet nog eens goed
    te keuren."""
    doc = await _laad_eigen_document(slug, client_id, store)
    _vereis_niet_afgerond(doc)

    if body.klasse not in GELDIGE_JAS_KLASSEN:
        raise HTTPException(422, f"Onbekende JAS-klasse: {body.klasse}")

    element_id = uuid.uuid4().hex[:12]
    nieuw_element = AnnotatieElement(
        id=element_id,
        klasse=body.klasse,
        tekst=body.tekst,
        lid=body.lid,
        toelichting=body.toelichting,
        vindplaats=body.vindplaats,
        span=body.span,
        herkomst="mens",
        levenscyclus=Levenscyclus.human_goedgekeurd,
    )
    nieuwe_elementen = [*doc.elementen, nieuw_element]
    nieuwe_status = _bereken_status(nieuwe_elementen)
    await store.vervang_elementen(slug, nieuwe_elementen, nieuwe_status)
    await store.schrijf_audit(
        slug,
        client_id,
        actor=client_id,
        actie="element-toegevoegd",
        element_id=element_id,
        detail={"klasse": body.klasse, "tekst": body.tekst, "lid": body.lid},
    )
    return doc.model_copy(update={"elementen": nieuwe_elementen, "status": nieuwe_status})


@router.delete("/{slug}/elementen/{element_id}", status_code=status.HTTP_204_NO_CONTENT)
async def verwijder_element(
    slug: str,
    element_id: str,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> None:
    """Verwijder een EIGEN markering (`herkomst == "mens"`). Een agent-voorstel (`herkomst ==
    "agent"`, gezet door `PUT .../elementen`) verdwijnt niet via deze route: die verwerp je via
    de beslissing-endpoint (`afwijzen`), zodat het auditspoor laat zien dát er een voorstel was
    en wat ermee gebeurde. Documenteigenaarschap is al door `_laad_eigen_document` afgedwongen —
    dit is dus geen tweede identiteitscheck, maar een origin-type-check binnen je eigen
    document."""
    doc = await _laad_eigen_document(slug, client_id, store)
    _vereis_niet_afgerond(doc)

    element = next((e for e in doc.elementen if e.id == element_id), None)
    if element is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Element '{element_id}' niet gevonden.")
    if element.herkomst != "mens":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Alleen je eigen markeringen kun je verwijderen; verwerp een agent-voorstel.",
        )

    nieuwe_elementen = [e for e in doc.elementen if e.id != element_id]
    nieuwe_status = _bereken_status(nieuwe_elementen)
    await store.vervang_elementen(slug, nieuwe_elementen, nieuwe_status)
    await store.schrijf_audit(
        slug,
        client_id,
        actor=client_id,
        actie="element-verwijderd",
        element_id=element_id,
        detail={"klasse": element.klasse, "tekst": element.tekst},
    )


@router.post("/{slug}/status", response_model=AnnotatieDocument)
async def zet_status(
    slug: str,
    body: StatusInvoer,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> AnnotatieDocument:
    """De annotatie afronden of weer heropenen — een expliciete handeling van de jurist, geen
    afgeleide van "alle elementen beslist" (dat is niet hetzelfde als tevreden zijn: er kan nog
    een agent-ronde komen). Heropenen kan altijd; een knop die niet terug kan is een knop die
    niemand durft te gebruiken. Zie `_vereis_niet_afgerond` voor het schrijf-slot dat hierdoor
    ontstaat."""
    doc = await _laad_eigen_document(slug, client_id, store)

    nieuwe_status = (
        DocumentStatus.geaccordeerd if body.geaccordeerd else _bereken_status(doc.elementen)
    )
    await store.vervang_elementen(slug, doc.elementen, nieuwe_status)
    await store.schrijf_audit(
        slug,
        client_id,
        actor=client_id,
        actie="document-afgerond" if body.geaccordeerd else "document-heropend",
        detail={"aantal_elementen": len(doc.elementen)},
    )
    return doc.model_copy(update={"status": nieuwe_status})


@router.post("/{slug}/export")
async def exporteer_document(
    slug: str,
    formaat: Exportformaat = Query(Exportformaat.pdf),
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
):
    """Het hele document als bestand: de markeringen als tabel plus het volledige spoor. Werkt
    in elke fase — een document dat nog in review is exporteert gewoon, met de telling "te
    beoordelen" in de kop, zodat een concept nooit als eindproduct kan worden gelezen.

    Anders dan de referentie: die kreeg de wettekst per lid van de client meegestuurd (haar `api`
    had geen graafverbinding). Lexplainables' `annotatie`-domein heeft dat wél (`graphdb.py`,
    story 037) en haalt de wettekst dus zelf op — ontbreekt hij (artikel niet in de graaf, of de
    graaf onbereikbaar), dan exporteert het document gewoon zonder wettekst-blok in plaats van
    de hele export te laten falen."""
    doc = await _laad_eigen_document(slug, client_id, store)
    audit = await store.lees_audit(slug)
    try:
        wetsartikel = await haal_wetsartikel_op(doc.bwb_id, doc.artikel)
    except (WetsartikelNietGevonden, GraphDbNietBereikbaar):
        wetsartikel = None
    return bouw_export(doc, audit, wetsartikel, formaat=formaat)


@router.get("/{slug}/audit", response_model=AuditlogOut)
async def get_audit(
    slug: str,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> AuditlogOut:
    await _laad_eigen_document(slug, client_id, store)
    regels = await store.lees_audit(slug)
    return AuditlogOut(items=regels)


@router.get("/{slug}/wetsartikel", response_model=Wetsartikel)
async def get_wetsartikel(
    slug: str,
    client_id: str = Depends(huidige_gebruiker),
    store: AnnotatieStore = Depends(get_store),
) -> Wetsartikel:
    """Wetsartikeltekst uit GraphDB voor het `bwb_id`/`artikel` van dit document (story 037)."""
    doc = await _laad_eigen_document(slug, client_id, store)
    try:
        return await haal_wetsartikel_op(doc.bwb_id, doc.artikel)
    except WetsartikelNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except GraphDbNietBereikbaar as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
