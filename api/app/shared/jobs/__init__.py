"""Async jobstore met lease-mechanisme (fase 1 story 3 van de wetsanalyse-migratie).

Wat: generieke Postgres-jobstore die meerdere features (annotatie-generatie in fase 4,
mogelijk analyse-orkestratie later) kunnen benutten voor async achtergrondwerk.
Waarom: `shared/`-module, geen feature — er is geen domein achter "jobs"; het is
infrastructuur voor lang-lopend werk dat een worker crash moet overleven en gelijktijdige
consumers moet uitsluiten (werkwijze-ADR-0008, project-ADR-0007).
Grens: geen scheduling (cron-achtig), geen prioriteiten, geen exponential backoff. Bewust
minimaal — genoeg voor "atomair claim → uitvoeren → voltooien of falen", niet meer.

Publieke API:
- `plan(engine, soort, payload)` — nieuwe job in status `wachtend`
- `claim(engine, eigenaar, soort, lease_seconden)` — atomisch `wachtend`-job → `bezig`
- `voltooi(engine, job_id, eigenaar)` — `bezig` → `klaar`
- `faal(engine, job_id, eigenaar, fout)` — `bezig` → `mislukt`
- `heropen_verlopen_leases(engine)` — reaper: `bezig` met verlopen lease → `wachtend`

Zie `store.py` voor het lease-patroon. De reaper draait als lifespan-taak in `main.py`.
"""

from app.shared.jobs.models import Job, JobStatus, jobs, metadata
from app.shared.jobs.store import PostgresJobStore

__all__ = ["Job", "JobStatus", "PostgresJobStore", "jobs", "metadata"]
