from __future__ import annotations

from agent.ports import GraphPort, LLMPort, LLMStream
from tests.fakes import FakeGraph, FakeLLM, response, text_block, tool_block


def test_fake_graph_voldoet_aan_graphport() -> None:
    assert isinstance(FakeGraph(), GraphPort)


def test_fake_llm_voldoet_aan_llmport() -> None:
    assert isinstance(FakeLLM([]), LLMPort)


def test_fake_graph_onthoudt_sparql_en_geeft_canned_resultaat() -> None:
    graph = FakeGraph(result="canned")

    resultaat = graph.sparql("SELECT * WHERE { ?s ?p ?o }")

    assert resultaat == "canned"
    assert graph.queries == ["SELECT * WHERE { ?s ?p ?o }"]


def test_fake_graph_results_callback_krijgt_de_query() -> None:
    graph = FakeGraph(results=lambda q: f"antwoord-op:{q}")

    assert graph.sparql("Q1") == "antwoord-op:Q1"


def test_fake_graph_semantic_search_apart_bijgehouden() -> None:
    graph = FakeGraph(result="x")
    graph.semantic_search("belastingrente")

    assert graph.semantic_queries == ["belastingrente"]
    assert graph.queries == []


def test_fake_graph_close_zet_vlag() -> None:
    graph = FakeGraph()
    assert graph.closed is False
    graph.close()
    assert graph.closed is True


def test_fake_llm_create_speelt_responses_in_volgorde_af() -> None:
    r1 = response([text_block("eerste")], "end_turn")
    r2 = response([text_block("tweede")], "end_turn")
    llm = FakeLLM([r1, r2])

    assert llm.create(model="m", max_tokens=10, system="s", tools=[], messages=[]) is r1
    assert llm.create(model="m", max_tokens=10, system="s", tools=[], messages=[]) is r2


def test_fake_llm_onthoudt_calls() -> None:
    llm = FakeLLM([response([text_block("x")], "end_turn")])
    llm.create(
        model="m", max_tokens=10, system="systeemtekst", tools=[], messages=[{"role": "user"}]
    )

    assert len(llm.calls) == 1
    assert llm.calls[0]["system"] == "systeemtekst"


def test_fake_llm_gesplitst_systeemblok_wordt_samengevoegd_voor_calls() -> None:
    llm = FakeLLM([response([text_block("x")], "end_turn")])
    llm.create(model="m", max_tokens=10, system=["stabiel", "variabel"], tools=[], messages=[])

    assert llm.calls[0]["system"] == "stabiel\n\nvariabel"
    assert llm.calls[0]["system_delen"] == ["stabiel", "variabel"]


def test_fake_llm_stream_levert_tekst_in_brokjes_en_final_message() -> None:
    r = response([text_block("een tamelijk lange tekst om te bekijken")], "end_turn")
    llm = FakeLLM([r])

    with llm.stream(model="m", max_tokens=10, system="s", tools=[], messages=[]) as stream:
        assert isinstance(stream, LLMStream)
        brokjes = list(stream.text_deltas)
        assert "".join(brokjes) == "een tamelijk lange tekst om te bekijken"
        assert stream.final_message() is r


def test_fake_llm_stream_en_create_delen_dezelfde_index() -> None:
    r1 = response([text_block("a")], "end_turn")
    r2 = response([text_block("b")], "end_turn")
    llm = FakeLLM([r1, r2])

    llm.create(model="m", max_tokens=10, system="s", tools=[], messages=[])
    with llm.stream(model="m", max_tokens=10, system="s", tools=[], messages=[]) as stream:
        assert stream.final_message() is r2


def test_tool_block_vorm() -> None:
    blok = tool_block("id1", "search_wetgeving", {"query": "belastingrente"})
    assert blok.type == "tool_use"
    assert blok.id == "id1"
    assert blok.name == "search_wetgeving"
    assert blok.input == {"query": "belastingrente"}
