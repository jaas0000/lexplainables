"""Gedragstests voor de jobstore (feature-bouwen regel 6: gedrag, niet vorm).

Alle tests draaien tegen de echte Postgres (ADR-0003) via de `store`-fixture — met name de
lease/claim-mechanismen zijn Postgres-specifiek (`FOR UPDATE SKIP LOCKED`) en horen thuis in
een echte-DB-test, niet in een mock.
"""

from __future__ import annotations

import asyncio

import pytest

from app.shared.jobs.store import JobNietGevonden


async def test_plan_maakt_wachtend_job(store):
    job = await store.plan("annotatie", {"artikel": "9"})
    assert job.status == "wachtend"
    assert job.soort == "annotatie"
    assert job.payload == {"artikel": "9"}
    assert job.lease_eigenaar is None
    assert job.pogingen == 0


async def test_claim_pakt_wachtend_job_op(store):
    gepland = await store.plan("annotatie", {"artikel": "9"})
    geclaimd = await store.claim(eigenaar="worker-1", soort="annotatie")
    assert geclaimd is not None
    assert geclaimd.id == gepland.id
    assert geclaimd.status == "bezig"
    assert geclaimd.lease_eigenaar == "worker-1"
    assert geclaimd.lease_verloopt is not None
    assert geclaimd.pogingen == 1


async def test_claim_op_lege_wachtrij_geeft_none(store):
    resultaat = await store.claim(eigenaar="worker-1", soort="annotatie")
    assert resultaat is None


async def test_claim_scopet_op_soort(store):
    await store.plan("analyse", {"x": 1})
    resultaat = await store.claim(eigenaar="worker-1", soort="annotatie")
    assert resultaat is None  # er staat wél iets in, maar niet met de gevraagde soort


async def test_claim_pakt_oudste_eerst(store):
    eerst = await store.plan("annotatie", {"nummer": 1})
    await store.plan("annotatie", {"nummer": 2})
    geclaimd = await store.claim(eigenaar="worker-1", soort="annotatie")
    assert geclaimd is not None
    assert geclaimd.id == eerst.id


async def test_claim_is_atomisch_bij_gelijktijdige_workers(store):
    """Twee workers die tegelijk claim() aanroepen krijgen ieder een andere job (of None),
    nooit dezelfde. Dit is het hele punt van `FOR UPDATE SKIP LOCKED`."""
    await store.plan("annotatie", {"n": 1})
    await store.plan("annotatie", {"n": 2})
    resultaten = await asyncio.gather(
        store.claim(eigenaar="worker-A", soort="annotatie"),
        store.claim(eigenaar="worker-B", soort="annotatie"),
    )
    ids = {r.id for r in resultaten if r is not None}
    assert len(ids) == 2  # twee verschillende jobs
    assert {r.lease_eigenaar for r in resultaten} == {"worker-A", "worker-B"}


async def test_voltooi_zet_status_op_klaar(store):
    await store.plan("annotatie", {})
    geclaimd = await store.claim(eigenaar="worker-1", soort="annotatie")
    assert geclaimd is not None
    voltooid = await store.voltooi(geclaimd.id, eigenaar="worker-1")
    assert voltooid.status == "klaar"
    assert voltooid.lease_eigenaar is None
    assert voltooid.lease_verloopt is None


async def test_voltooi_door_verkeerde_eigenaar_faalt(store):
    """Als een worker z'n lease heeft verloren (bijv. door de reaper), mag 'ie de job niet
    stiekem toch afsluiten — die is misschien al opnieuw opgepakt door een tweede worker."""
    await store.plan("annotatie", {})
    geclaimd = await store.claim(eigenaar="worker-1", soort="annotatie")
    assert geclaimd is not None
    with pytest.raises(JobNietGevonden):
        await store.voltooi(geclaimd.id, eigenaar="andere-worker")


async def test_faal_zet_status_op_mislukt_met_fout(store):
    await store.plan("annotatie", {})
    geclaimd = await store.claim(eigenaar="worker-1", soort="annotatie")
    assert geclaimd is not None
    gefaald = await store.faal(geclaimd.id, eigenaar="worker-1", fout="verbindingsprobleem")
    assert gefaald.status == "mislukt"
    assert gefaald.fout == "verbindingsprobleem"
    assert gefaald.lease_eigenaar is None


async def test_faal_door_verkeerde_eigenaar_faalt(store):
    await store.plan("annotatie", {})
    geclaimd = await store.claim(eigenaar="worker-1", soort="annotatie")
    assert geclaimd is not None
    with pytest.raises(JobNietGevonden):
        await store.faal(geclaimd.id, eigenaar="andere-worker", fout="whatever")


async def test_haal_leest_bestaande_job(store):
    gepland = await store.plan("annotatie", {"x": 1})
    gelezen = await store.haal(gepland.id)
    assert gelezen is not None
    assert gelezen.id == gepland.id


async def test_haal_onbekende_id_geeft_none(store):
    import uuid

    assert await store.haal(uuid.uuid4()) is None


async def test_reaper_heropent_verlopen_leases(store):
    """Een `bezig`-job met een `lease_verloopt` in het verleden hoort door reap() weer op
    `wachtend` te komen (met de eigenaar weggehaald), zodat een tweede worker 'm kan pakken."""
    gepland = await store.plan("annotatie", {})
    geclaimd = await store.claim(eigenaar="worker-1", soort="annotatie", lease_seconden=300)
    assert geclaimd is not None

    # Forceer verlopen lease door direct in de DB de lease-tijd te backdaten.
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from app.shared.jobs.models import jobs

    async with store._engine.begin() as conn:
        await conn.execute(
            update(jobs)
            .where(jobs.c.id == gepland.id)
            .values(lease_verloopt=datetime.now(UTC) - timedelta(minutes=5))
        )

    aantal = await store.heropen_verlopen_leases()
    assert aantal == 1

    heropend = await store.haal(gepland.id)
    assert heropend is not None
    assert heropend.status == "wachtend"
    assert heropend.lease_eigenaar is None
    assert heropend.lease_verloopt is None


async def test_reaper_laat_actieve_leases_ongemoeid(store):
    """Een `bezig`-job met een geldige lease mag NIET heropend worden."""
    await store.plan("annotatie", {})
    await store.claim(eigenaar="worker-1", soort="annotatie", lease_seconden=300)

    aantal = await store.heropen_verlopen_leases()
    assert aantal == 0


async def test_reaper_maakt_werk_opnieuw_claimbaar(store):
    """End-to-end: eerste worker crash-simulatie → reaper → tweede worker pakt job op."""
    gepland = await store.plan("annotatie", {"artikel": "9"})
    eerste = await store.claim(eigenaar="worker-1", soort="annotatie")
    assert eerste is not None

    # Simuleer crash: lease verloopt (backdate) en reaper draait.
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from app.shared.jobs.models import jobs

    async with store._engine.begin() as conn:
        await conn.execute(
            update(jobs)
            .where(jobs.c.id == gepland.id)
            .values(lease_verloopt=datetime.now(UTC) - timedelta(minutes=5))
        )
    await store.heropen_verlopen_leases()

    # Tweede worker kan de job nu claimen.
    tweede = await store.claim(eigenaar="worker-2", soort="annotatie")
    assert tweede is not None
    assert tweede.id == gepland.id
    assert tweede.lease_eigenaar == "worker-2"
    assert tweede.pogingen == 2  # eerste claim +1, tweede claim +1
