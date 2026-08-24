"""De antwoord-agent-loop: supervisor-routing, gelukkig pad, ongegrond-correctie, onbepaald,
max-turns-vangnet, afwijzen, decompositie (multi-hop), annotatie (enkele ronde).

Eigen tests (niet geport van de referentie se `tests/test_orchestrator.py`/`test_agent_loop.py` —
niet gelezen, alleen hun bestandsgrootte gezien via een Explore-agent), tegen `agent/
orchestrator.py`, dat zelf wél 1:1 op het legacy-QA-pad geport is (stories 044-047).
"""

from __future__ import annotations

import json

from agent.orchestrator import MAX_TURNS, annoteer_node, build_graph, parse_subquestions
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


# ---- Decompositie (story 046, enable_decomposition=True) -----------------------------------


def test_parse_subquestions_herkent_genummerde_regels() -> None:
    tekst = "1. Wat is een belastingschuldige?\n2. Wat is een belastingaanslag?"
    assert parse_subquestions(tekst, cap=5) == [
        "Wat is een belastingschuldige?",
        "Wat is een belastingaanslag?",
    ]


def test_parse_subquestions_geen_match_geeft_lege_lijst() -> None:
    # De aanroeper (decompose_node) vangt dit op met een terugval op de oorspronkelijke vraag —
    # deze functie blijft zuiver en geeft gewoon niets terug.
    assert parse_subquestions("gewoon een stukje proza zonder nummering", cap=5) == []


def test_parse_subquestions_respecteert_de_cap() -> None:
    tekst = "\n".join(f"{i}. deelvraag {i}" for i in range(1, 8))
    assert len(parse_subquestions(tekst, cap=3)) == 3


def test_decompositie_enkelvoudige_vraag_slaat_synthese_over() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok(),
            response([text_block("1. Wat is een belastingschuldige?")], "end_turn"),
            # Bewust geen vindplaats/citaat hier — anders keurt verify_node dit af als ongegrond
            # (geen tool_use in deze solve-beurt, dus een lege source_trace) en loopt de test via
            # resynth alsnog naar synthesize door. Dat pad heeft zijn eigen test hieronder.
            response(
                [text_block("Een belastingschuldige is degene die belasting betaalt.")], "end_turn"
            ),
        ]
    )
    graph = FakeGraph(result="")
    settings = make_settings(enable_decomposition=True)

    result = build_graph(settings, llm, graph).invoke(
        {"question": "Wat is een belastingschuldige?"}
    )

    assert result["sub_questions"] == ["Wat is een belastingschuldige?"]
    assert result["answer"] == "Een belastingschuldige is degene die belasting betaalt."
    assert llm.index == 3  # supervisor + decompose + 1 solve-call, geen synthesize


def test_decompositie_samengestelde_vraag_accumuleert_trace_en_synthetiseert() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok(),
            response(
                [text_block("1. Wat is een belastingschuldige?\n2. Wat is een belastingaanslag?")],
                "end_turn",
            ),
            response(
                [tool_block("t1", "search_wetgeving", {"query": "belastingschuldige"})],
                "tool_use",
            ),
            response([text_block("Een belastingschuldige is degene die betaalt.")], "end_turn"),
            response([text_block("Een belastingaanslag is de opgelegde aanslag.")], "end_turn"),
            response([text_block("Samengevat: beide begrippen uitgelegd.")], "end_turn"),
        ]
    )
    graph = FakeGraph(result="een graafresultaat")
    settings = make_settings(enable_decomposition=True)

    result = build_graph(settings, llm, graph).invoke(
        {"question": "Wat is een belastingschuldige, en wat is een belastingaanslag?"}
    )

    assert result["sub_questions"] == [
        "Wat is een belastingschuldige?",
        "Wat is een belastingaanslag?",
    ]
    assert len(result["sub_findings"]) == 2
    assert len(result["source_trace"]) == 1  # alleen sub 1 riep een tool aan
    assert graph.queries  # de tool heeft de graaf daadwerkelijk geraakt
    assert result["answer"] == "Samengevat: beide begrippen uitgelegd."
    assert llm.index == 6  # supervisor + decompose + 3 solve-calls + 1 synthesize

    # solve_node gebruikt de cachingsplit: een stabiele base_system + een groeiend variabel deel.
    eerste_solve_call = llm.calls[2]
    assert eerste_solve_call["system_delen"] is not None
    assert len(eerste_solve_call["system_delen"]) == 2
    tweede_deelvraag_call = llm.calls[4]
    assert "EERDERE DEELBEVINDINGEN" in tweede_deelvraag_call["system_delen"][1]


def test_decompositie_ongegronde_synthese_krijgt_precies_een_herkansing() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok(),
            response([text_block("1. eerste\n2. tweede")], "end_turn"),
            response([text_block("vinding 1")], "end_turn"),
            response([text_block("vinding 2")], "end_turn"),
            # Eerste synthese: verzonnen vindplaats + een citaat van >=5 woorden dat niet in de
            # (lege) trace staat — beide grounding-categorieën tegelijk.
            response(
                [
                    text_block(
                        'Zie <urn:bwb:BWBR9999999:artikel:1>: "een citaat dat niet in de bron '
                        'staat".'
                    )
                ],
                "end_turn",
            ),
            # Herstelde synthese na de correctie-instructie.
            response(
                [text_block("Vinding 1 en vinding 2 samengevat, zonder vindplaats.")], "end_turn"
            ),
        ]
    )
    graph = FakeGraph(result="")
    settings = make_settings(enable_decomposition=True)

    result = build_graph(settings, llm, graph).invoke({"question": "Twee losse onderdelen?"})

    assert result["corrected"] is True
    assert result["answer"] == "Vinding 1 en vinding 2 samengevat, zonder vindplaats."
    assert llm.index == 6  # geen derde synthese-poging

    # De herkansing benoemt beide categorieën, niet alleen de verzonnen vindplaats.
    herkansing_system = llm.calls[5]["system"]
    assert "niet-gegronde verwijzingen" in herkansing_system
    assert "niet letterlijk" in herkansing_system


def test_decompositie_sub_max_turns_vangnet_stopt_tools_op_de_laatste_beurt() -> None:
    llm = FakeLLM(
        [
            _supervisor_ok(),
            response([text_block("1. Blijf maar zoeken")], "end_turn"),
            response([tool_block("t1", "search_wetgeving", {"query": "x"})], "tool_use"),
            response([tool_block("t2", "search_wetgeving", {"query": "x"})], "tool_use"),
            # Laatste toegestane beurt: geen tools aangeboden, dus het model antwoordt in tekst.
            response([text_block("Antwoord op basis van wat is gevonden.")], "end_turn"),
        ]
    )
    graph = FakeGraph(result="niets relevants")
    settings = make_settings(enable_decomposition=True, sub_max_turns=3)

    result = build_graph(settings, llm, graph).invoke({"question": "Blijf maar zoeken"})

    assert result["answer"] == "Antwoord op basis van wat is gevonden."
    assert llm.calls[-1]["tools"] == []  # de laatste beurt bood geen tools aan
    assert len(graph.queries) == 2
    assert llm.index == 5  # supervisor + decompose + 3 solve-calls


def test_decompositie_afwijzen_kort_nog_steeds_voor_decompose() -> None:
    llm = FakeLLM([_supervisor_ok("algemeen", "AFWIJZEN")])
    graph = FakeGraph(result="")
    settings = make_settings(enable_decomposition=True)

    result = build_graph(settings, llm, graph).invoke({"question": "Wat is het weer vandaag?"})

    assert result["afwijzen"] is True
    assert graph.queries == []
    assert llm.index == 1  # geen decompose-call


# ---- Annotatie (story 047, enkele ronde) — losstaande functie, geen build_graph -------------


def test_annoteer_node_haalt_corpus_op_en_verwerkt_de_classificatie() -> None:
    corpus_tsv = (
        "?tekst\t?jci\t?lid\t?lidnummer\t?lidtekst\t?onderdeel\t?onderdeeltekst\n"
        '\t\t\t"1"\t"Degene die aangifte doet, is verplicht de gegevens waarheidsgetrouw te '
        'verstrekken."@nl\t\t'
    )
    llm = FakeLLM(
        [
            response(
                [
                    text_block(
                        json.dumps(
                            {
                                "elementen": [
                                    {
                                        "klasse": "Rechtssubject",
                                        "tekst": "Degene die aangifte doet",
                                        "lid": "1",
                                        "toelichting": "de drager van de aangifteplicht",
                                    }
                                ]
                            }
                        )
                    )
                ],
                "end_turn",
            )
        ]
    )
    graph = FakeGraph(result=corpus_tsv)
    settings = make_settings()

    result = annoteer_node(
        {"doel": {"bwbId": "BWBR0004770", "artikel": "10"}},
        settings=settings,
        llm=llm,
        graph=graph,
    )

    assert result["corpus"].startswith("1. Degene die aangifte doet")
    assert graph.queries  # de corpus is daadwerkelijk uit de graaf gehaald
    assert len(result["voorstellen"]) == 1
    assert result["voorstellen"][0]["klasse"] == "Rechtssubject"
    assert result["voorstellen"][0]["grounded"] is True
    assert result["verworpen_fragmenten"] == []
    # De prompt kreeg geen tools mee — dit is een pure classificatiestap, geen tool-lus.
    assert llm.calls[0]["tools"] == []
