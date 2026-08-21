"""Schema + contract voor de jobstore.

Eén tabel: `jobs`. Payload is `JSONB` zodat elk feature zijn eigen structuur meegeeft zonder
schema-migratie. Zie `__init__.py` voor de context en `store.py` voor het gedrag.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID

JobStatus = Literal["wachtend", "bezig", "klaar", "mislukt"]

metadata = MetaData()

jobs = Table(
    "jobs",
    metadata,
    Column("id", PgUUID(as_uuid=True), primary_key=True),
    Column("soort", Text(), nullable=False),
    Column("payload", JSONB(), nullable=False),
    Column("status", Text(), nullable=False, server_default="wachtend"),
    Column("lease_eigenaar", Text(), nullable=True),
    Column("lease_verloopt", DateTime(timezone=True), nullable=True),
    Column("fout", Text(), nullable=True),
    Column("pogingen", Integer(), nullable=False, server_default="0"),
    Column("aangemaakt", DateTime(timezone=True), nullable=False),
    Column("bijgewerkt", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "status IN ('wachtend', 'bezig', 'klaar', 'mislukt')", name="jobs_status_geldig"
    ),
    Index("ix_jobs_status_soort", "status", "soort"),
    Index("ix_jobs_status_lease", "status", "lease_verloopt"),
)


class Job(BaseModel):
    """Wat een consumer ziet nadat 'ie een job heeft geclaimd of gepland."""

    id: UUID
    soort: str
    payload: dict[str, Any]
    status: JobStatus
    lease_eigenaar: str | None
    lease_verloopt: datetime | None
    fout: str | None
    pogingen: int
    aangemaakt: datetime
    bijgewerkt: datetime


def job_uit_rij(rij) -> Job:
    """Expliciete mapping tussen een databaserij en het Pydantic-contract (ADR-0011)."""
    return Job(
        id=rij.id,
        soort=rij.soort,
        payload=rij.payload,
        status=rij.status,
        lease_eigenaar=rij.lease_eigenaar,
        lease_verloopt=rij.lease_verloopt,
        fout=rij.fout,
        pogingen=rij.pogingen,
        aangemaakt=rij.aangemaakt,
        bijgewerkt=rij.bijgewerkt,
    )
