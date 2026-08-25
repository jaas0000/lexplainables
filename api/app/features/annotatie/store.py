"""Store-abstractie voor het annotatie-domein (werkwijze-ADR-0007, story 022).

`AnnotatieStore` beschrijft de operaties die router.py nodig heeft. `SqlAlchemyAnnotatieStore`
is de enige huidige implementatie (async SQLAlchemy Core). Tests draaien 'm tegen een eigen,
kortlevende SQLite-engine — dezelfde implementatie, geen aparte fake.

De `elementen`-kolom slaat Pydantic-objecten op als JSON (lijsten van dicts); de store
serialiseert via `.model_dump()` en deserialiseert via `model_validate()` — de mapping-functies
in models.py verwerken dat.

Aparte `AnnotatieStore` (niet gedeeld met projecten-store) zodat de domein-grenzen helder
blijven (implementatienoot in de story).
"""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from ...shared.tijd import nu
from .models import (
    AnnotatieDocument,
    AnnotatieElement,
    AuditRegel,
    DocumentSamenvatting,
    DocumentStatus,
    RunInfo,
    annotatie_audit,
    annotatie_documenten,
    audit_uit_rij,
    document_uit_rij,
    samenvatting_uit_rij,
)


class DocumentNietGevonden(LookupError):
    """Onbekend of andermans document — altijd een 404 (niet 403, om bestaan niet te lekken)."""


class ElementNietGevonden(LookupError):
    """Element-id niet aangetroffen in de `elementen`-lijst van het document."""


class AnnotatieStore(Protocol):
    async def maak_document(self, doc: AnnotatieDocument) -> AnnotatieDocument: ...

    async def laad_document(self, slug: str) -> AnnotatieDocument | None: ...

    async def lijst_documenten_samenvatting(
        self, client_id: str, limit: int, offset: int
    ) -> list[DocumentSamenvatting]: ...

    async def verwijder_document(self, slug: str) -> None: ...

    async def vervang_elementen(
        self,
        slug: str,
        elementen: list[AnnotatieElement],
        status: DocumentStatus,
        *,
        laatste_run: RunInfo | None = None,
    ) -> None: ...

    async def schrijf_audit(
        self,
        slug: str,
        client_id: str,
        actor: str,
        actie: str,
        *,
        element_id: str | None = None,
        detail: dict | None = None,
    ) -> None: ...

    async def lees_audit(self, slug: str) -> list[AuditRegel]: ...


class SqlAlchemyAnnotatieStore:
    """Implementatie tegen een async SQLAlchemy-engine.

    SQLite in tests, PostgreSQL in productie.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def maak_document(self, doc: AnnotatieDocument) -> AnnotatieDocument:
        moment = nu()
        async with self._engine.begin() as conn:
            result = await conn.execute(
                insert(annotatie_documenten)
                .values(
                    slug=doc.slug,
                    client_id=doc.client_id,
                    werkgebied=doc.werkgebied,
                    bwb_id=doc.bwb_id,
                    artikel=doc.artikel,
                    lid=doc.lid,
                    status=doc.status.value,
                    elementen=[],
                    aangemaakt=moment,
                    bijgewerkt=moment,
                )
                .returning(annotatie_documenten)
            )
            rij = result.one()
        return document_uit_rij(rij)

    async def laad_document(self, slug: str) -> AnnotatieDocument | None:
        async with self._engine.connect() as conn:
            rij = (
                await conn.execute(
                    select(annotatie_documenten).where(annotatie_documenten.c.slug == slug)
                )
            ).first()
        return document_uit_rij(rij) if rij is not None else None

    async def lijst_documenten_samenvatting(
        self, client_id: str, limit: int, offset: int
    ) -> list[DocumentSamenvatting]:
        stmt = (
            select(annotatie_documenten)
            .where(annotatie_documenten.c.client_id == client_id)
            .order_by(annotatie_documenten.c.bijgewerkt.desc())
            .offset(offset)
            .limit(limit)
        )
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [samenvatting_uit_rij(rij) for rij in rijen]

    async def verwijder_document(self, slug: str) -> None:
        """Verwijdert het document én alle bijbehorende audit-regels in één transactie."""
        async with self._engine.begin() as conn:
            await conn.execute(
                delete(annotatie_audit).where(annotatie_audit.c.document_slug == slug)
            )
            result = await conn.execute(
                delete(annotatie_documenten)
                .where(annotatie_documenten.c.slug == slug)
                .returning(annotatie_documenten.c.slug)
            )
            if result.first() is None:
                raise DocumentNietGevonden(f"Document '{slug}' bestaat niet.")

    async def vervang_elementen(
        self,
        slug: str,
        elementen: list[AnnotatieElement],
        status: DocumentStatus,
        *,
        laatste_run: RunInfo | None = None,
    ) -> None:
        """Vervangt de volledige `elementen`-JSON en werkt `status` en `bijgewerkt` bij.

        `laatste_run` wordt alleen bijgewerkt als 'ie meegegeven is — een jurist-beslissing
        (`registreer_beslissing`) roept dit ook aan, maar zonder een nieuwe agent-run; die mag
        de vorige run-provenance niet wissen.
        """
        elementen_json = [e.model_dump() for e in elementen]
        waarden: dict[str, object] = {
            "elementen": elementen_json,
            "status": status.value,
            "bijgewerkt": nu(),
        }
        if laatste_run is not None:
            waarden["laatste_run"] = laatste_run.model_dump()
        async with self._engine.begin() as conn:
            await conn.execute(
                update(annotatie_documenten)
                .where(annotatie_documenten.c.slug == slug)
                .values(**waarden)
            )

    async def schrijf_audit(
        self,
        slug: str,
        client_id: str,
        actor: str,
        actie: str,
        *,
        element_id: str | None = None,
        detail: dict | None = None,
    ) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                insert(annotatie_audit).values(
                    document_slug=slug,
                    client_id=client_id,
                    actor=actor,
                    actie=actie,
                    element_id=element_id,
                    detail=detail or {},
                    tijdstip=nu(),
                )
            )

    async def lees_audit(self, slug: str) -> list[AuditRegel]:
        stmt = (
            select(annotatie_audit)
            .where(annotatie_audit.c.document_slug == slug)
            .order_by(annotatie_audit.c.id)
        )
        async with self._engine.connect() as conn:
            rijen = (await conn.execute(stmt)).all()
        return [audit_uit_rij(rij) for rij in rijen]
