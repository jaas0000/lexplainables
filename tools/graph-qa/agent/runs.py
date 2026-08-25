"""Het run-register: een beurt is een object van de server, geen HTTP-request (werkwijze-story
054).

`POST /v1/chat` (story 053) koppelt de beurt aan de verbinding: valt de client weg, dan sneuvelt
de stream — ook al draait het werk zelf gewoon door (de LangGraph-nodes zijn synchroon, dus een
lopende LLM-call maakt zichzelf af in de executor). Hier wordt dat omgedraaid: de **run** draait
als achtergrondtaak met een eigen event-log; een client *kijkt* mee en kan opnieuw aanhaken.
Losraken is dus geen annuleren — stoppen is een aparte, expliciete handeling (`vraag_stop`, die
via `stop_check`/`BeurtGestopt`, story 052, de graaf op een nodegrens laat uitstappen).

Poort van `wetsanalyse-ai/tools/graph-qa/agent/runs.py`, met één aanpassing: `VLUCHTIGE_TYPES` is
hier alleen `{"token"}` — lexplainables' agent heeft nog geen `reason`/`status`-narratie (die
hoort bij de annotatieketen-route, die nog niet op `answer_stream()`/HTTP is aangesloten, zie
`docs/project/stories/054-graph-qa-runs-model.md` §Afwijkingen).

Aannames die je moet kennen voordat je dit uitbreidt:

- **Eén proces, één replica.** Het register leeft in het geheugen. Komt er ooit een tweede
  replica, dan moet dit naar een gedeelde store.
- **Een herstart wist het register.** Bewust: hervatten-vanaf-checkpoint vraagt async nodes.
- **Alleen de run-taak schrijft.** Een abonnee die aanhaakt lokt nooit een schrijfactie uit —
  aanhaken is dus per definitie veilig en idempotent.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("graph_qa.runs")

# Hoeveel events er hoogstens in de log blijven staan.
MAX_EVENTS = 4000

# Hoe lang een afgeronde run nog opvraagbaar blijft.
BEWAAR_NA_AFLOOP_S = 600.0

# Welke events bij het cappen mogen sneuvelen — betekenisvolle events (`sources`, `grounding`,
# `conversation_id`, `done`, `error`) blijven altijd staan.
VLUCHTIGE_TYPES = frozenset({"token"})


class RunBestaatAl(Exception):
    """Er loopt al een run voor dit gesprek. Draagt het actieve run_id, zodat de aanroeper kan
    aanhaken in plaats van een tweede run te starten.

    Geen UI-nettigheid maar een gegevensbeschermer: `thread_id == conversation_id`, dus twee
    gelijktijdige lussen zouden door elkaar heen in dezelfde checkpointer-thread schrijven.
    """

    def __init__(self, run_id: str) -> None:
        super().__init__(f"Er loopt al een run voor dit gesprek: {run_id}")
        self.run_id = run_id


@dataclass
class Run:
    """Eén beurt, met alles wat een late kijker nodig heeft om hem te begrijpen."""

    run_id: str
    conversation_id: str
    user_id: str = ""
    vraag: str = ""
    status: str = "loopt"  # loopt | klaar | gestopt | mislukt
    # Elk event draagt zijn EIGEN `seq`, toegekend bij het toevoegen — een identiteit, geen
    # positie. `_cap` snoeit selectief, dus "de eerste N zijn weg" klopt niet: daarmee zou een
    # aanhaker betekenisvolle events dubbel krijgen.
    events: list[dict[str, Any]] = field(default_factory=list)
    weggevallen: int = 0
    geproduceerd: int = 0
    gestart: float = field(default_factory=time.monotonic)
    eind_op: float | None = None
    stop_gevraagd: bool = False
    taak: asyncio.Task[None] | None = None
    _wakker: asyncio.Condition = field(default_factory=asyncio.Condition)

    @property
    def loopt(self) -> bool:
        return self.status == "loopt"

    @property
    def volgende_seq(self) -> int:
        return self.geproduceerd

    def samenvatting(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "conversation_id": self.conversation_id,
            "vraag": self.vraag,
            "status": self.status,
            "volgende_seq": self.volgende_seq,
            "weggevallen": self.weggevallen,
        }


class RunRegister:
    """Houdt de lopende en recent afgeronde runs bij, één per gesprek."""

    def __init__(
        self, *, max_events: int = MAX_EVENTS, bewaar_s: float = BEWAAR_NA_AFLOOP_S
    ) -> None:
        self._runs: dict[str, Run] = {}
        self._max_events = max_events
        self._bewaar_s = bewaar_s

    # -- opvragen ------------------------------------------------------------------------------

    def get(self, run_id: str, *, user_id: str = "") -> Run | None:
        """De run, of niets als hij niet van deze gebruiker is — een 404, geen lek."""
        self._ruim_op()
        run = self._runs.get(run_id)
        if run is None or run.user_id != user_id:
            return None
        return run

    def actief_voor(self, conversation_id: str, *, user_id: str = "") -> Run | None:
        """De lopende run van dit gesprek, of de laatst afgeronde die nog binnen de
        bewaartermijn valt — beide zijn een geldige reden om aan te haken."""
        self._ruim_op()
        kandidaten = [
            r
            for r in self._runs.values()
            if r.conversation_id == conversation_id and r.user_id == user_id
        ]
        if not kandidaten:
            return None
        lopend = [r for r in kandidaten if r.loopt]
        return sorted(lopend or kandidaten, key=lambda r: r.gestart)[-1]

    # -- starten -------------------------------------------------------------------------------

    def start(
        self,
        *,
        conversation_id: str,
        vraag: str,
        maak_stroom: Callable[[Run], AsyncIterator[dict[str, Any]]],
        user_id: str = "",
    ) -> Run:
        """Registreer een run en zet hem als achtergrondtaak weg.

        `maak_stroom` krijgt de Run mee zodat de driver een stopverzoek kan zien; hij levert de
        eventstroom (in de praktijk `answer_stream`). De taak hangt bewust **niet** aan de
        request-scope — dat is de hele omkering.
        """
        self._ruim_op()
        if conversation_id:
            # Bewust project-breed (niet per user_id): twee beurten op één thread_id schrijven
            # door elkaar in de checkpointer, ongeacht wie ze start.
            bestaand = next(
                (
                    r
                    for r in self._runs.values()
                    if r.conversation_id == conversation_id and r.loopt
                ),
                None,
            )
            if bestaand is not None:
                raise RunBestaatAl(bestaand.run_id)

        run = Run(
            run_id=uuid.uuid4().hex, conversation_id=conversation_id, user_id=user_id, vraag=vraag
        )
        self._runs[run.run_id] = run
        run.taak = asyncio.create_task(self._draai(run, maak_stroom))
        return run

    async def _draai(
        self, run: Run, maak_stroom: Callable[[Run], AsyncIterator[dict[str, Any]]]
    ) -> None:
        try:
            async for event in maak_stroom(run):
                await self._voeg_toe(run, event)
            nieuwe_status = "gestopt" if run.stop_gevraagd else "klaar"
        except asyncio.CancelledError:
            await self._rond_af(run, "gestopt")
            raise
        except Exception:
            # De stroom saniteert zijn fouten al naar een `error`-event; komt er tóch een
            # exception doorheen, dan is dat een defect in de driver en hoort het in het log.
            logger.exception("run mislukt", extra={"run_id": run.run_id})
            await self._voeg_toe(
                run,
                {
                    "type": "error",
                    "message": "Er ging iets mis bij het beantwoorden. Probeer het opnieuw.",
                },
            )
            nieuwe_status = "mislukt"
        await self._rond_af(run, nieuwe_status)

    async def _rond_af(self, run: Run, status: str) -> None:
        run.status = status
        run.eind_op = time.monotonic()
        async with run._wakker:
            run._wakker.notify_all()

    async def _voeg_toe(self, run: Run, event: dict[str, Any]) -> None:
        run.events.append({**event, "seq": run.geproduceerd})
        run.geproduceerd += 1
        self._cap(run)
        async with run._wakker:
            run._wakker.notify_all()

    def _cap(self, run: Run) -> None:
        """Snoei de log als hij te lang wordt — maar gooi alleen vluchtige events weg."""
        if len(run.events) <= self._max_events:
            return
        teveel = len(run.events) - self._max_events
        behouden: list[dict[str, Any]] = []
        gedropt = 0
        for event in run.events:
            if gedropt < teveel and event.get("type") in VLUCHTIGE_TYPES:
                gedropt += 1
                continue
            behouden.append(event)
        run.events = behouden
        run.weggevallen += gedropt

    # -- stoppen -------------------------------------------------------------------------------

    def vraag_stop(self, run: Run) -> None:
        """Vraag om te stoppen. Bewust een vlag en géén `task.cancel()` — zie `stop_check`
        (story 052): de nodes zijn synchroon, dus de run stopt op de eerstvolgende nodegrens."""
        run.stop_gevraagd = True

    # -- meekijken -----------------------------------------------------------------------------

    async def volg(self, run: Run, vanaf: int = 0) -> AsyncIterator[dict[str, Any]]:
        """Lever de events vanaf `vanaf` en volg daarna live mee.

        Elke abonnee houdt zijn eigen cursor en wacht op een `Condition` — geen `asyncio.Queue`,
        want die kun je maar één keer leegdrinken en er kunnen meerdere kijkers tegelijk zijn.
        Losraken van deze generator laat de run ongemoeid.

        De toestandscontrole staat bewust onder dezelfde lock als de `notify_all`: anders kan de
        run afronden tussen "nog niet klaar" en het wachten, en blijft een kijker hangen op een
        run die al klaar is.
        """
        cursor = vanaf
        while True:
            for event in [e for e in run.events if e.get("seq", 0) >= cursor]:
                seq = int(event.get("seq", cursor))
                if seq > cursor:
                    yield {"type": "gat", "weggevallen": seq - cursor}
                yield event
                cursor = seq + 1
            async with run._wakker:
                if cursor >= run.geproduceerd and not run.loopt:
                    return
                if cursor >= run.geproduceerd:
                    # `cursor` is geen for-lus-variabele die ná deze aanroep nog verandert vóór de
                    # lambda geëvalueerd wordt — hij wordt binnen dezelfde `while`-iteratie meteen
                    # en synchroon gebruikt door `wait_for`, geen uitgestelde closure over een
                    # stale waarde.
                    await run._wakker.wait_for(
                        lambda: cursor < run.geproduceerd or not run.loopt  # noqa: B023
                    )

    # -- opruimen ------------------------------------------------------------------------------

    def _ruim_op(self) -> None:
        nu = time.monotonic()
        verlopen = [
            run_id
            for run_id, run in self._runs.items()
            if run.eind_op is not None and nu - run.eind_op > self._bewaar_s
        ]
        for run_id in verlopen:
            del self._runs[run_id]
