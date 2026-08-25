"""`agent/runs.py`'s `RunRegister`: het run-model (werkwijze-story 054).

Draait via `asyncio.run(...)` in gewone sync testfuncties — zelfde patroon als
`tests/test_checkpointer.py`. Oefent `RunRegister` rechtstreeks uit (geen HTTP), zodat de
concurrency-vorm (Condition-gebaseerd meekijken, selectief cappen, retentie) deterministisch
getest is, zonder te leunen op timing over de HTTP-laag heen.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest

from agent.runs import Run, RunBestaatAl, RunRegister


async def _stroom(events: list[dict]) -> AsyncIterator[dict]:
    for event in events:
        yield event


def _blokkerende_stroom(vrijgeven: asyncio.Event, na_vrijgave: list[dict]):
    async def maak(_run: Run) -> AsyncIterator[dict]:
        await vrijgeven.wait()
        for event in na_vrijgave:
            yield event

    return maak


def test_start_en_volg_tot_done() -> None:
    async def _run() -> None:
        register = RunRegister()
        run = register.start(
            conversation_id="gesprek-1",
            vraag="Een vraag",
            maak_stroom=lambda _r: _stroom([{"type": "token", "content": "hoi"}, {"type": "done"}]),
        )

        events = [e async for e in register.volg(run, 0)]

        assert [e["type"] for e in events] == ["token", "done"]
        assert events[0]["seq"] == 0
        assert events[1]["seq"] == 1
        assert run.status == "klaar"

    asyncio.run(_run())


def test_tweede_start_op_hetzelfde_gesprek_gooit_run_bestaat_al() -> None:
    async def _run() -> None:
        register = RunRegister()
        vrijgeven = asyncio.Event()
        run1 = register.start(
            conversation_id="gesprek-1",
            vraag="Eerste vraag",
            maak_stroom=_blokkerende_stroom(vrijgeven, [{"type": "done"}]),
        )
        await asyncio.sleep(0)  # laat de achtergrondtaak starten (nog niet vrijgegeven → loopt)

        with pytest.raises(RunBestaatAl) as exc:
            register.start(
                conversation_id="gesprek-1",
                vraag="Tweede vraag",
                maak_stroom=lambda _r: _stroom([{"type": "done"}]),
            )
        assert exc.value.run_id == run1.run_id

        vrijgeven.set()
        await run1.taak

    asyncio.run(_run())


def test_ander_gesprek_mag_wel_tegelijk_lopen() -> None:
    async def _run() -> None:
        register = RunRegister()
        vrijgeven = asyncio.Event()
        run1 = register.start(
            conversation_id="gesprek-1",
            vraag="Vraag",
            maak_stroom=_blokkerende_stroom(vrijgeven, [{"type": "done"}]),
        )
        await asyncio.sleep(0)

        run2 = register.start(
            conversation_id="gesprek-2",
            vraag="Andere vraag",
            maak_stroom=lambda _r: _stroom([{"type": "done"}]),
        )
        assert run2.run_id != run1.run_id

        vrijgeven.set()
        await run1.taak

    asyncio.run(_run())


def test_volg_levert_gat_event_bij_een_sprong_in_seq() -> None:
    async def _run() -> None:
        register = RunRegister()
        run = register.start(
            conversation_id="",
            vraag="Vraag",
            maak_stroom=lambda _r: _stroom(
                [{"type": "token", "content": "a"}, {"type": "token", "content": "b"}]
            ),
        )
        await run.taak

        events = [e async for e in register.volg(run, 1)]  # begin bij seq 1, sla seq 0 over

        assert events[0]["type"] == "token"
        assert events[0]["content"] == "b"

    asyncio.run(_run())


def test_cap_gooit_alleen_vluchtige_events_weg() -> None:
    async def _run() -> None:
        register = RunRegister(max_events=3)
        veel_tokens = [{"type": "token", "content": str(i)} for i in range(10)]
        run = register.start(
            conversation_id="",
            vraag="Vraag",
            maak_stroom=lambda _r: _stroom([*veel_tokens, {"type": "done"}]),
        )
        await run.taak

        assert len(run.events) <= 3
        assert any(e["type"] == "done" for e in run.events), "done mag nooit gesnoeid worden"
        assert run.weggevallen > 0

    asyncio.run(_run())


def test_ruim_op_verwijdert_pas_na_de_bewaartermijn() -> None:
    async def _run() -> None:
        register = RunRegister(bewaar_s=0.05)
        run = register.start(
            conversation_id="gesprek-1",
            vraag="Vraag",
            maak_stroom=lambda _r: _stroom([{"type": "done"}]),
        )
        await run.taak

        assert register.get(run.run_id) is not None, "meteen na afloop nog opvraagbaar"

        await asyncio.sleep(0.1)

        assert register.get(run.run_id) is None, "ná de bewaartermijn verdwenen"

    asyncio.run(_run())


def test_vraag_stop_geeft_status_gestopt() -> None:
    async def _run() -> None:
        register = RunRegister()

        async def stroom(run: Run) -> AsyncIterator[dict]:
            if run.stop_gevraagd:
                return
            yield {"type": "token", "content": "voor de stop"}

        run = register.start(conversation_id="", vraag="Vraag", maak_stroom=stroom)
        register.vraag_stop(run)
        await run.taak

        assert run.status == "gestopt"

    asyncio.run(_run())


def test_get_geeft_niets_terug_voor_een_andere_gebruiker() -> None:
    async def _run() -> None:
        register = RunRegister()
        run = register.start(
            conversation_id="",
            vraag="Vraag",
            maak_stroom=lambda _r: _stroom([{"type": "done"}]),
            user_id="alice",
        )
        await run.taak

        assert register.get(run.run_id, user_id="alice") is not None
        assert register.get(run.run_id, user_id="bob") is None
        assert register.get(run.run_id) is None  # geen header = ""

    asyncio.run(_run())


def test_actief_voor_geeft_de_laatst_afgeronde_run_terug() -> None:
    async def _run() -> None:
        register = RunRegister()
        run = register.start(
            conversation_id="gesprek-1",
            vraag="Vraag",
            maak_stroom=lambda _r: _stroom([{"type": "done"}]),
        )
        await run.taak

        gevonden = register.actief_voor("gesprek-1")

        assert gevonden is not None
        assert gevonden.run_id == run.run_id

    asyncio.run(_run())


def test_actief_voor_zonder_runs_geeft_niets() -> None:
    register = RunRegister()
    assert register.actief_voor("onbekend-gesprek") is None
