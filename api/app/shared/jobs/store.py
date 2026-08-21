"""Store voor de async jobstore.

Vier operaties uit de publieke `__init__.py`, plus de reaper. Alle SQL is Postgres-specifiek
(ADR-0003) — met name `FOR UPDATE SKIP LOCKED` in `claim()` is wat de gelijktijdige-workers-
garantie levert: twee workers die tegelijk claim() aanroepen krijgen elk een andere job (of
`None`), nooit dezelfde.

Lease-model: een geclaimde job krijgt `status='bezig'` + een eigenaar + een verloopmoment. Als
de worker crasht (of trager is dan de lease), krijgt de reaper 'm terug op `wachtend`. De
`voltooi/faal`-operaties controleren de eigenaar zodat een oude worker die na een lease-verval
alsnog terug rapporteert de job niet meer kan afsluiten (die is dan al door een tweede worker
opgepakt).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import literal, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from ..observability import get_meter, get_tracer
from ..tijd import nu
from .models import Job, job_uit_rij, jobs

_tracer = get_tracer("app.shared.jobs.store")
# Tellers voor lifecycle-events — bezig_jobs kan later gecombineerd worden met een gauge/observer
# als een consumer periodiek naar de DB polt; voor nu volstaat een up-down-counter die claim/finish
# accuraat bijhoudt in-process (per replica).
_bezig_jobs = get_meter("app.shared.jobs.store").create_up_down_counter(
    "active_bezig_jobs",
    description="Aantal jobs in status 'bezig' (in-process, per replica).",
)


class JobNietGevonden(LookupError):
    """De opgegeven job bestaat niet — of de eigenaar klopt niet meer."""


class PostgresJobStore:
    """Implementatie tegen een async SQLAlchemy-engine (asyncpg, ADR-0003)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def plan(self, soort: str, payload: dict[str, Any]) -> Job:
        """Nieuwe job aanmaken in status `wachtend`."""
        moment = nu()
        job_id = uuid4()
        stmt = (
            pg_insert(jobs)
            .values(
                id=job_id,
                soort=soort,
                payload=payload,
                status="wachtend",
                pogingen=0,
                aangemaakt=moment,
                bijgewerkt=moment,
            )
            .returning(jobs)
        )
        async with self._engine.begin() as conn:
            rij = (await conn.execute(stmt)).one()
        return job_uit_rij(rij)

    async def claim(self, eigenaar: str, soort: str, lease_seconden: int = 300) -> Job | None:
        """Atomair een `wachtend`-job van deze soort claimen. Retourneert `None` als de
        wachtrij leeg is.

        De innerlijke `SELECT ... FOR UPDATE SKIP LOCKED` zorgt dat twee gelijktijdige
        workers nooit dezelfde rij pakken — een tweede caller ziet de rij die de eerste
        bezig-lockt overslagen worden en pakt de volgende (of `None`). Zonder `SKIP LOCKED`
        zouden ze op elkaar wachten.
        """
        with _tracer.start_as_current_span("jobs.claim") as span:
            span.set_attribute("job.soort", soort)
            moment = nu()
            verloopt = moment + timedelta(seconds=lease_seconden)
            binnenkant = (
                select(jobs.c.id)
                .where(jobs.c.status == "wachtend", jobs.c.soort == soort)
                .order_by(jobs.c.aangemaakt)
                .limit(1)
                .with_for_update(skip_locked=True)
            ).scalar_subquery()
            stmt = (
                update(jobs)
                .where(jobs.c.id == binnenkant)
                .values(
                    status="bezig",
                    lease_eigenaar=eigenaar,
                    lease_verloopt=verloopt,
                    pogingen=jobs.c.pogingen + 1,
                    bijgewerkt=moment,
                )
                .returning(jobs)
            )
            async with self._engine.begin() as conn:
                resultaat = await conn.execute(stmt)
                rij = resultaat.one_or_none()
            if rij is None:
                span.set_attribute("job.status", "leeg")
                return None
            span.set_attribute("job.status", "bezig")
            span.set_attribute("job.id", str(rij.id))
            _bezig_jobs.add(1, {"soort": soort})
            return job_uit_rij(rij)

    async def voltooi(self, job_id: UUID, eigenaar: str) -> Job:
        """Job → `klaar`. Faalt met `JobNietGevonden` als de eigenaar niet (meer) klopt
        (bijv. lease verlopen en door reaper heropend). Dat is bewust hard: een worker die
        z'n lease is kwijtgeraakt hoort niet stiekem "af te ronden" wat een ander misschien
        al opnieuw begonnen is."""
        with _tracer.start_as_current_span("jobs.voltooi") as span:
            span.set_attribute("job.id", str(job_id))
            stmt = (
                update(jobs)
                .where(
                    jobs.c.id == job_id,
                    jobs.c.status == "bezig",
                    jobs.c.lease_eigenaar == eigenaar,
                )
                .values(
                    status="klaar",
                    lease_eigenaar=None,
                    lease_verloopt=None,
                    bijgewerkt=nu(),
                )
                .returning(jobs)
            )
            async with self._engine.begin() as conn:
                rij = (await conn.execute(stmt)).one_or_none()
            if rij is None:
                span.set_attribute("job.status", "niet_gevonden")
                raise JobNietGevonden(
                    f"Job {job_id} bestaat niet, is niet bezig, of eigenaar {eigenaar} klopt niet."
                )
            span.set_attribute("job.status", "klaar")
            span.set_attribute("job.soort", rij.soort)
            _bezig_jobs.add(-1, {"soort": rij.soort})
            return job_uit_rij(rij)

    async def faal(self, job_id: UUID, eigenaar: str, fout: str) -> Job:
        """Job → `mislukt` met foutmelding. Zelfde eigenaar-check als `voltooi`."""
        with _tracer.start_as_current_span("jobs.faal") as span:
            span.set_attribute("job.id", str(job_id))
            stmt = (
                update(jobs)
                .where(
                    jobs.c.id == job_id,
                    jobs.c.status == "bezig",
                    jobs.c.lease_eigenaar == eigenaar,
                )
                .values(
                    status="mislukt",
                    fout=fout,
                    lease_eigenaar=None,
                    lease_verloopt=None,
                    bijgewerkt=nu(),
                )
                .returning(jobs)
            )
            async with self._engine.begin() as conn:
                rij = (await conn.execute(stmt)).one_or_none()
            if rij is None:
                span.set_attribute("job.status", "niet_gevonden")
                raise JobNietGevonden(
                    f"Job {job_id} bestaat niet, is niet bezig, of eigenaar {eigenaar} klopt niet."
                )
            span.set_attribute("job.status", "mislukt")
            span.set_attribute("job.soort", rij.soort)
            _bezig_jobs.add(-1, {"soort": rij.soort})
            return job_uit_rij(rij)

    async def haal(self, job_id: UUID) -> Job | None:
        """Read-only lookup — handig voor tests en voor consumers die de status willen zien."""
        stmt = select(jobs).where(jobs.c.id == job_id)
        async with self._engine.connect() as conn:
            rij = (await conn.execute(stmt)).one_or_none()
        return job_uit_rij(rij) if rij is not None else None

    async def heropen_verlopen_leases(self) -> int:
        """Reaper: `bezig`-jobs waarvan de lease is verlopen → `wachtend`. Retourneert het
        aantal heropende jobs. Wordt periodiek aangeroepen door de lifespan-taak in `main.py`."""
        # `text()` want SQLAlchemy Core kan `now()` niet standaard uitdrukken zonder dialect.
        stmt = (
            update(jobs)
            .where(jobs.c.status == "bezig", jobs.c.lease_verloopt < text("now()"))
            .values(
                status="wachtend",
                lease_eigenaar=None,
                lease_verloopt=None,
                bijgewerkt=literal(nu()),
            )
        )
        async with self._engine.begin() as conn:
            resultaat = await conn.execute(stmt)
        return resultaat.rowcount or 0
