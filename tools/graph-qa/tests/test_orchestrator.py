"""De minimale antwoord-agent-loop: gelukkig pad, ongegrond-correctie, onbepaald, max-turns-vangnet.

Poort van (een deel van) `wetsanalyse-ai/tools/graph-qa/tests/test_orchestrator.py`, getrimd tot
wat werkwijze-story 044 bouwt (geen supervisor/annotatieketen/decompositie).
"""

from __future__ import annotations

from agent.orchestrator import MAX_TURNS, build_graph
from tests.fakes import FakeGraph, FakeLLM, make_settings, response, text_block, tool_block


def test_gelukkig_pad_tool_call_dan_gegrond_antwoord() -> None:
    llm = FakeLLM(
        [
            response(
                [tool_block("t1", "search_wetgeving", {"query": "belastingschuldige"})],
                "tool_use",
            ),
            response(
                [
                    text_block(
                        "Zie <urn:bwb:BWBR0004770:artikel:2:lid:1>: "
                        '"belastingschuldige is degene die belasting verschuldigd is".'
                    )
                ],
                "end_turn",
            ),
        ]
    )
    graph = FakeGraph(
        result=(
            "<urn:bwb:BWBR0004770:artikel:2:lid:1> "
            '"belastingschuldige is degene die belasting verschuldigd is"'
        )
    )
    settings = make_settings()

    result = build_graph(settings, llm, graph).invoke(
        {"question": "Wat is een belastingschuldige?"}
    )

    assert result["grounding_niveau"] == "gegrond"
    assert result["grounded"] is True
    assert len(result["sources"]) == 1
    assert graph.queries  # de tool heeft de graaf daadwerkelijk geraakt


def test_ongegrond_pad_krijgt_precies_een_correctieronde() -> None:
    llm = FakeLLM(
        [
            response([text_block("Zie <urn:bwb:BWBR9999999:artikel:1>.")], "end_turn"),
            response([text_block("Ik kan dit niet met een vindplaats onderbouwen.")], "end_turn"),
        ]
    )
    graph = FakeGraph(result="")
    settings = make_settings()

    result = build_graph(settings, llm, graph).invoke({"question": "Iets buiten de graaf"})

    # Eerste antwoord was ongegrond → correct_node draaide → tweede (herstelde) antwoord bevat geen
    # vindplaats meer, dus onbepaald — en er is geen derde create()-call nodig geweest (de FakeLLM
    # heeft er maar twee; een derde aanroep zou een IndexError geven en de test laten falen).
    assert result["corrected"] is True
    assert result["grounding_niveau"] == "onbepaald"
    assert llm.index == 2


def test_onbepaald_pad_zonder_vindplaats_of_citaat_geen_correctie() -> None:
    llm = FakeLLM(
        [response([text_block("Dit volgt uit de algemene systematiek van de wet.")], "end_turn")]
    )
    graph = FakeGraph(result="")
    settings = make_settings()

    result = build_graph(settings, llm, graph).invoke({"question": "Een algemene vraag"})

    assert result["grounding_niveau"] == "onbepaald"
    assert result.get("corrected") is not True
    assert llm.index == 1  # geen correctieronde nodig


def test_max_turns_vangnet_stopt_de_tool_lus() -> None:
    llm = FakeLLM(
        [
            response([tool_block(f"t{i}", "search_wetgeving", {"query": "x"})], "tool_use")
            for i in range(MAX_TURNS)
        ]
    )
    graph = FakeGraph(result="niets relevants")
    settings = make_settings()

    result = build_graph(settings, llm, graph).invoke({"question": "Blijf maar zoeken"})

    assert result["turns"] == MAX_TURNS
    assert result["pending_tools"] == []
    assert llm.index == MAX_TURNS  # geen negende create()-call
