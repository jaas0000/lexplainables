"""`agent/agent.py`'s `answer_stream()`: het SSE-event-contract (werkwijze-story 051).

Draait via `asyncio.run(...)` in gewone sync testfuncties — geen pytest-asyncio-plugin nodig,
zelfde patroon als `tests/test_checkpointer.py`.
"""

from __future__ import annotations

import asyncio

from agent.agent import _foutmelding, answer_stream
from tests.fakes import FakeGraph, FakeLLM, make_settings, response, text_block


def _supervisor_ok(specialist: str = "algemeen", plan: str = "beantwoord de vraag"):
    return response([text_block(f"SPECIALIST: {specialist}\nPLAN: {plan}")], "end_turn")


def _events(llm: FakeLLM, graph: FakeGraph, question: str, **kwargs) -> list[dict]:
    async def _run() -> list[dict]:
        settings = make_settings()
        out = []
        async for event in answer_stream(
            question, settings=settings, llm=llm, graph=graph, **kwargs
        ):
            out.append(event)
        return out

    return asyncio.run(_run())


def test_gelukkig_pad_levert_tokens_sources_grounding_done() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok(),
            response([text_block("Dit volgt uit de algemene systematiek van de wet.")], "end_turn"),
        ]
    )
    graph = FakeGraph(result="")

    events = _events(llm, graph, "Een algemene vraag")

    token_events = [e for e in events if e["type"] == "token"]
    assert token_events, "geen enkel token-event geëmit"
    herbouwd = "".join(e["content"] for e in token_events)
    assert herbouwd == "Dit volgt uit de algemene systematiek van de wet."

    types = [e["type"] for e in events]
    assert types[-2:] == ["grounding", "done"]
    assert "sources" in types
    assert graph.closed, "graph.close() hoort in de finally te lopen"


def test_conversation_id_gaat_vlak_voor_done() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok(),
            response([text_block("Antwoord.")], "end_turn"),
        ]
    )
    graph = FakeGraph(result="")

    events = _events(llm, graph, "Een vraag", conversation_id="gesprek-1")

    assert events[-1] == {"type": "done"}
    assert events[-2] == {"type": "conversation_id", "conversation_id": "gesprek-1"}


def test_afgewezen_vraag_levert_toch_done_zonder_crash() -> None:
    llm = FakeLLM([_supervisor_ok("algemeen", "AFWIJZEN")])
    graph = FakeGraph(result="")

    events = _events(llm, graph, "Wat is het weer vandaag?")

    assert events[-1] == {"type": "done"}
    # Geen tokens (afwijzen streamt geen antwoord) — wel sources/grounding met hun defaults.
    assert not [e for e in events if e["type"] == "token"]
    sources = next(e for e in events if e["type"] == "sources")
    assert sources["sources"] == []
    grounding = next(e for e in events if e["type"] == "grounding")
    assert grounding["grounded"] is True


def test_onverwachte_fout_geeft_gesaniteerde_melding() -> None:
    class _KapotteLLM:
        def create(self, **kwargs):
            raise RuntimeError("interne details die niet naar de client mogen lekken")

        def stream(self, **kwargs):
            raise RuntimeError("interne details die niet naar de client mogen lekken")

    graph = FakeGraph(result="")

    events = _events(_KapotteLLM(), graph, "Een vraag")

    assert events == [
        {
            "type": "error",
            "message": (
                "Er ging iets mis bij het beantwoorden. Probeer het opnieuw; blijft het "
                "misgaan, dan staat de oorzaak in het server-log."
            ),
        }
    ]
    assert graph.closed


def test_foutmelding_herkent_provider_uitzonderingen_op_naam() -> None:
    class RateLimitError(Exception):
        pass

    class APIConnectionError(Exception):
        pass

    assert "overbelast" in _foutmelding(RateLimitError())
    assert "niet bereiken" in _foutmelding(APIConnectionError())
    assert "Er ging iets mis" in _foutmelding(ValueError())
