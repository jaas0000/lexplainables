"""De antwoord-agent-loop: supervisor-routing, gelukkig pad, ongegrond-correctie, onbepaald,
max-turns-vangnet, afwijzen.

Eigen tests (niet geport van de referentie se `tests/test_orchestrator.py`/`test_agent_loop.py` —
niet gelezen, alleen hun bestandsgrootte gezien via een Explore-agent), tegen `agent/
orchestrator.py`, dat zelf wél 1:1 op het legacy-QA-pad geport is (stories 044-045).
"""

from __future__ import annotations

from agent.orchestrator import MAX_TURNS, build_graph
from tests.fakes import FakeGraph, FakeLLM, make_settings, response, text_block, tool_block


def _supervisor_ok(specialist: str = "algemeen", plan: str = "beantwoord de vraag"):
    """Een geldige supervisor-respons die naar `agent_node` doorroutert — voor tests die de
    supervisor-stap zelf niet toetsen, alleen laten passeren."""
    return response([text_block(f"SPECIALIST: {specialist}\nPLAN: {plan}")], "end_turn")


def test_gelukkig_pad_tool_call_dan_gegrond_antwoord() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok(),
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
            _supervisor_ok(),
            response([text_block("Zie <urn:bwb:BWBR9999999:artikel:1>.")], "end_turn"),
            response([text_block("Ik kan dit niet met een vindplaats onderbouwen.")], "end_turn"),
        ]
    )
    graph = FakeGraph(result="")
    settings = make_settings()

    result = build_graph(settings, llm, graph).invoke({"question": "Iets buiten de graaf"})

    # Eerste antwoord was ongegrond → correct_node draaide → tweede (herstelde) antwoord bevat geen
    # vindplaats meer, dus onbepaald — en er is geen vierde create()-call nodig geweest (de FakeLLM
    # heeft er maar drie; een vierde aanroep zou een IndexError geven en de test laten falen).
    assert result["corrected"] is True
    assert result["grounding_niveau"] == "onbepaald"
    assert llm.index == 3


def test_onbepaald_pad_zonder_vindplaats_of_citaat_geen_correctie() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok(),
            response([text_block("Dit volgt uit de algemene systematiek van de wet.")], "end_turn"),
        ]
    )
    graph = FakeGraph(result="")
    settings = make_settings()

    result = build_graph(settings, llm, graph).invoke({"question": "Een algemene vraag"})

    assert result["grounding_niveau"] == "onbepaald"
    assert result.get("corrected") is not True
    assert llm.index == 2  # geen correctieronde nodig


def test_max_turns_vangnet_stopt_de_tool_lus() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok(),
            *[
                response([tool_block(f"t{i}", "search_wetgeving", {"query": "x"})], "tool_use")
                for i in range(MAX_TURNS)
            ],
        ]
    )
    graph = FakeGraph(result="niets relevants")
    settings = make_settings()

    result = build_graph(settings, llm, graph).invoke({"question": "Blijf maar zoeken"})

    assert result["turns"] == MAX_TURNS
    assert result["pending_tools"] == []
    assert llm.index == MAX_TURNS + 1  # de supervisor-call + MAX_TURNS agent-calls


def test_supervisor_routeert_naar_specialist_en_beperkt_de_toolset() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok("definitie", "begripsvraag"),
            response(
                [tool_block("t1", "resolve_begrip", {"term": "belastingschuldige"})], "tool_use"
            ),
            response([text_block("Een definitie zonder vindplaats.")], "end_turn"),
        ]
    )
    graph = FakeGraph(result="")
    settings = make_settings()

    result = build_graph(settings, llm, graph).invoke(
        {"question": "Wat is een belastingschuldige?"}
    )

    assert result["specialist"] == "definitie"
    # De tweede call (index 1) is agent_node se eerste aanroep — met de beperkte definitie-toolset.
    agent_call = llm.calls[1]
    tool_names = {t["name"] for t in agent_call["tools"]}
    assert tool_names == {
        "resolve_begrip",
        "search_wetgeving",
        "semantic_search",
        "get_artikel",
        "get_lid",
        "graph_schema",
        "raw_sparql",
    }
    assert "DEFINITIE-specialist" in agent_call["system"]


def test_afwijzen_pad_raakt_de_graaf_niet() -> None:
    llm = FakeLLM([_supervisor_ok("algemeen", "AFWIJZEN")])
    graph = FakeGraph(result="")
    settings = make_settings()

    result = build_graph(settings, llm, graph).invoke({"question": "Wat is het weer vandaag?"})

    assert result["afwijzen"] is True
    assert result["sources"] == []
    assert graph.queries == []
    assert llm.index == 1  # geen tweede (agent_node-)call


def test_onbekende_specialist_valt_terug_op_algemeen_volledige_toolset() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok("bestaat-niet", "onduidelijke vraag"),
            response([text_block("Een antwoord zonder tools.")], "end_turn"),
        ]
    )
    graph = FakeGraph(result="")
    settings = make_settings()

    build_graph(settings, llm, graph).invoke({"question": "Iets vaags"})

    agent_call = llm.calls[1]
    assert len(agent_call["tools"]) == 13  # de volledige registry, net als vóór story 045
