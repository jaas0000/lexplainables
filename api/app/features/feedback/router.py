"""Routelaag voor het feedback-domein — wat niet uit de vorm volgt (stack-profiel.md
§Feature-eenheid): auth-checks en validatie voorbij het schema. De schemaclasses (models.py)
leggen vast WAT feedback is; ze leggen niet vast WIE iets mag — dat is gedrag, geen vorm.

Auth hieronder is een STERK VEREENVOUDIGDE stand-in voor het echte, twee-gescheiden-schema's-
auth-systeem van deze werkwijze (werkwijze-ADR-0009: gebruikerssessies vs. service-/admin-
bearer-tokens). Deze demo simuleert beide met een simpele header, zonder sessies/JWT/bcrypt —
het punt van deze referentie-implementatie is de featurestructuur (vertical slicing,
store-abstractie, migraties), niet een volledig auth-domein namaken (dat is voorzien als latere
stap, zie `BACKLOG.md` §Referentie-implementatie).
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from ...db import get_engine
from .models import FeedbackCreate, FeedbackRead
from .store import FeedbackNietGevonden, FeedbackStore, SqlAlchemyFeedbackStore


def huidige_gebruiker(x_user_id: str = Header(..., alias="X-User-Id")) -> str:
    """Vereenvoudigde stand-in voor gebruikersauthenticatie (ADR-0009): een ingelogde
    gebruiker wordt hier gesimuleerd via een header in plaats van een echte sessie."""
    return x_user_id


def huidige_beheerder(x_admin_id: str = Header(..., alias="X-Admin-Id")) -> str:
    """Vereenvoudigde stand-in voor service-/adminauthenticatie (ADR-0009): een aparte header
    in plaats van een bearer-token, om hetzelfde principe (twee gescheiden mechanismen) te
    tonen zonder een echt tokensysteem te bouwen."""
    return x_admin_id


def get_store() -> FeedbackStore:
    """FastAPI-dependency die de router aan een concrete store koppelt (werkwijze-ADR-0007).
    Tests overschrijven dit (`app.dependency_overrides[get_store]`) met een store op een eigen,
    kortlevende engine — de routercode zelf blijft daarbij ongewijzigd."""
    return SqlAlchemyFeedbackStore(get_engine())


router = APIRouter(prefix="/feedback", tags=["feedback"])
admin_router = APIRouter(prefix="/admin/feedback", tags=["feedback-admin"])


class FeedbackBevestigd(BaseModel):
    id: int


class OngelezenFeedbackOut(BaseModel):
    aantal: int


class MarkeerGezienIn(BaseModel):
    tot: datetime | None = None


class FeedbackPaginaOut(BaseModel):
    items: list[FeedbackRead]
    totaal: int


@router.post("", response_model=FeedbackBevestigd, status_code=status.HTTP_201_CREATED)
async def dien_feedback_in(
    body: FeedbackCreate,
    userid: str = Depends(huidige_gebruiker),
    store: FeedbackStore = Depends(get_store),
) -> FeedbackBevestigd:
    # client_id komt in het echte project uit een client-bearer-token (require_client). Deze
    # demo simuleert één vaste client — multi-tenancy is geen onderdeel van dit bewijs-van-
    # concept (zie de story).
    feedback = await store.dien_in(
        client_id="demo-client",
        userid=userid,
        categorie=body.categorie,
        tekst=body.tekst,
        pagina=body.pagina,
    )
    return FeedbackBevestigd(id=feedback.id)


@admin_router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def verwijder_feedback(
    feedback_id: int,
    _admin_userid: str = Depends(huidige_beheerder),
    store: FeedbackStore = Depends(get_store),
) -> None:
    try:
        await store.verwijder(feedback_id)
    except FeedbackNietGevonden as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@admin_router.get("/ongelezen-aantal", response_model=OngelezenFeedbackOut)
async def get_ongelezen_aantal(
    admin_userid: str = Depends(huidige_beheerder),
    store: FeedbackStore = Depends(get_store),
) -> OngelezenFeedbackOut:
    return OngelezenFeedbackOut(aantal=await store.ongelezen_aantal(admin_userid))


@admin_router.post("/markeer-gezien", status_code=status.HTTP_204_NO_CONTENT)
async def markeer_gezien(
    body: MarkeerGezienIn = MarkeerGezienIn(),
    admin_userid: str = Depends(huidige_beheerder),
    store: FeedbackStore = Depends(get_store),
) -> None:
    await store.markeer_gezien(admin_userid, body.tot)


@admin_router.get("", response_model=FeedbackPaginaOut)
async def lijst_feedback(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _admin_userid: str = Depends(huidige_beheerder),
    store: FeedbackStore = Depends(get_store),
) -> FeedbackPaginaOut:
    items = await store.lijst(offset, limit)
    totaal = await store.totaal()
    return FeedbackPaginaOut(items=items, totaal=totaal)
