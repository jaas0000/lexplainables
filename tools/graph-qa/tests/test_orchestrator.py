"""De antwoord-agent-loop: supervisor-routing, gelukkig pad, ongegrond-correctie, onbepaald,
max-turns-vangnet, afwijzen, decompositie (multi-hop), volledige annotatieketen, gespreksgeheugen.

Eigen tests (niet geport van de referentie se `tests/test_orchestrator.py`/`test_agent_loop.py` —
niet gelezen, alleen hun bestandsgrootte gezien via een Explore-agent), tegen `agent/
orchestrator.py`, dat zelf wél 1:1 op het legacy-QA-pad geport is (stories 044-050).
"""

from __future__ import annotations

import asyncio
import json

from langgraph.checkpoint.memory import MemorySaver

from agent.orchestrator import (
    MAX_TURNS,
    _heeft_doel,
    annoteer_node,
    build_graph,
    critic_node,
    emit_node,
    herzie_node,
    nieuwe_beurt_invoer,
    parse_subquestions,
    patch_node,
    route_na_critic,
    route_na_patch,
)
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


# ---- Critic (story 048, enkele ronde) — losstaande functie, geen build_graph ----------------


def test_critic_node_gelukkig_pad_zet_aandacht_en_motivatie() -> None:
    voorstellen = [
        {"id": "elementid01", "klasse": "Rechtssubject", "tekst": "Degene die aangifte doet"},
        {"id": "elementid02", "klasse": "Rechtsfeit", "tekst": "aangifte doet"},
    ]
    llm = FakeLLM(
        [
            response(
                [
                    text_block(
                        json.dumps(
                            {
                                "oordelen": [
                                    {
                                        "id": "elementid01",
                                        "aandacht": "groen",
                                        "motivatie": "helder",
                                        "actie": "behoud",
                                    },
                                    {
                                        "id": "elementid02",
                                        "aandacht": "geel",
                                        "motivatie": "grensgeval",
                                        "actie": "behoud",
                                    },
                                ],
                                "ontbrekend": [],
                            }
                        )
                    )
                ],
                "end_turn",
            )
        ]
    )
    settings = make_settings()

    result = critic_node(
        {"voorstellen": voorstellen, "corpus": "corpus-tekst"}, settings=settings, llm=llm
    )

    assert result["critic_gefaald"] is False
    assert result["critic_ronde"] == 1
    voorstel1, voorstel2 = result["voorstellen"]
    assert voorstel1["aandacht"] == "groen"
    assert voorstel1["critic"] == "helder"
    assert voorstel2["aandacht"] == "geel"
    assert len(voorstel1["critic_rondes"]) == 1
    assert voorstel1["critic_rondes"][0]["ronde"] == 1


def test_critic_node_meldt_nieuw_ontbrekend_en_dedupliceert_bij_herhaling() -> None:
    voorstellen = [{"id": "elementid01", "klasse": "Rechtssubject", "tekst": "iets"}]
    respons = response(
        [
            text_block(
                json.dumps(
                    {
                        "oordelen": [{"id": "elementid01", "aandacht": "groen", "actie": "behoud"}],
                        "ontbrekend": [
                            {"klasse": "Rechtsfeit", "reden": "mist", "tekst": "een handeling"}
                        ],
                    }
                )
            )
        ],
        "end_turn",
    )
    settings = make_settings()

    eerste = critic_node(
        {"voorstellen": voorstellen, "corpus": "corpus-tekst"},
        settings=settings,
        llm=FakeLLM([respons]),
    )
    assert len(eerste["nieuw_ontbrekend"]) == 1
    assert len(eerste["gemeld_ontbrekend"]) == 1

    # Tweede ronde: hetzelfde ontbrekend-item, nu al gemeld — geen nieuw item meer.
    tweede = critic_node(
        {
            "voorstellen": voorstellen,
            "corpus": "corpus-tekst",
            "gemeld_ontbrekend": eerste["gemeld_ontbrekend"],
        },
        settings=settings,
        llm=FakeLLM([respons]),
    )
    assert tweede["nieuw_ontbrekend"] == []


def test_critic_node_ronde_twee_dempt_zelfweerspreking() -> None:
    voorstel = {
        "id": "elementid01",
        "klasse": "Rechtsbetrekking",  # resultaat van een al toegepaste ronde-1-correctie
        "alternatieven": [],
        "critic_rondes": [
            {
                "ronde": 1,
                "aandacht": "rood",
                "actie": "vervang",
                "voorstel_klasse": "Rechtsbetrekking",
                "toegepast": True,
            }
        ],
    }
    llm = FakeLLM(
        [
            response(
                [
                    text_block(
                        json.dumps(
                            {
                                "oordelen": [
                                    {
                                        "id": "elementid01",
                                        "aandacht": "rood",
                                        "actie": "vervang",
                                        "motivatie": "toch geen Rechtsbetrekking",
                                        "voorstel_klasse": "Rechtsobject",
                                    }
                                ],
                                "ontbrekend": [],
                            }
                        )
                    )
                ],
                "end_turn",
            )
        ]
    )
    settings = make_settings()

    result = critic_node(
        {"voorstellen": [voorstel], "corpus": "corpus-tekst", "critic_ronde": 1},
        settings=settings,
        llm=llm,
    )

    assert result["critic_ronde"] == 2
    uitkomst = result["voorstellen"][0]
    assert uitkomst["aandacht"] == "geel"  # gedempt, niet rood
    assert any(a["klasse"] == "Rechtsobject" for a in uitkomst["alternatieven"])


def test_critic_node_faalpad_laat_voorstellen_ongemoeid() -> None:
    voorstellen = [{"id": "elementid01", "klasse": "Rechtssubject", "tekst": "iets"}]
    # `content=None` breekt de content-iteratie in critic_node — simuleert een kapotte respons
    # zonder de FakeLLM zelf te hoeven aanpassen.
    llm = FakeLLM([response(None, "end_turn")])
    settings = make_settings()

    result = critic_node(
        {"voorstellen": voorstellen, "corpus": "corpus-tekst"}, settings=settings, llm=llm
    )

    assert result["critic_gefaald"] is True
    assert result["voorstellen"] == voorstellen
    assert result["critic_feedback"] == []


def test_critic_node_zonder_voorstellen_doet_geen_llm_call() -> None:
    llm = FakeLLM([])  # een aanroep zou IndexError geven
    settings = make_settings()

    result = critic_node({"voorstellen": []}, settings=settings, llm=llm)

    assert result == {}


# ---- Annotatieketen afronden: patch/routing/herzie/emit/graaf-wiring (story 049) -------------

_CORPUS = "1. Degene die aangifte doet, is verplicht de gegevens waarheidsgetrouw te verstrekken."


def test_heeft_doel() -> None:
    assert _heeft_doel({"doel": {"bwbId": "x", "artikel": "1"}}) == "annoteer"
    assert _heeft_doel({"question": "iets"}) == "supervisor"


def test_patch_node_voert_rood_vervang_door() -> None:
    voorstel = {
        "id": "eid1",
        "klasse": "Rechtssubject",
        "tekst": "Degene die aangifte doet",
        "alternatieven": [],
        "critic_rondes": [{"ronde": 1}],
    }
    feedback = [
        {
            "id": "eid1",
            "aandacht": "rood",
            "actie": "vervang",
            "voorstel_klasse": "Rechtsfeit",
        }
    ]
    result = patch_node({"voorstellen": [voorstel], "critic_feedback": feedback, "corpus": _CORPUS})

    assert result["patch_toegepast"] == 1
    assert result["voorstellen"][0]["klasse"] == "Rechtsfeit"
    assert result["critic_feedback"] == []  # instructie volledig afgehandeld


def test_route_na_critic() -> None:
    aan = make_settings(critic_max_rondes=1)
    uit = make_settings(critic_max_rondes=0)
    assert route_na_critic({}, settings=uit) == "emit"
    assert route_na_critic({"critic_gefaald": True}, settings=aan) == "emit"
    assert route_na_critic({"critic_ronde": 2}, settings=aan) == "emit"
    assert route_na_critic({"critic_ronde": 1}, settings=aan) == "patch"


def test_route_na_patch() -> None:
    assert route_na_patch({"nieuw_ontbrekend": [{"klasse": "x"}]}) == "herzie"
    assert route_na_patch({"verworpen_fragmenten": [{"klasse": "x"}]}) == "herzie"
    assert route_na_patch({"patch_toegepast": 1}) == "critic"
    assert route_na_patch({"patch_toegepast": 0}) == "emit"


def test_herzie_node_voegt_gemist_element_toe_en_behoudt_bestaand() -> None:
    voorstel = {
        "id": "eid1",
        "klasse": "Rechtssubject",
        "tekst": "Degene die aangifte doet",
        "lid": "",
        "alternatieven": [],
        "critic_rondes": [],
        "aandacht": "",
        "critic": "",
    }
    llm = FakeLLM(
        [
            response(
                [
                    text_block(
                        json.dumps(
                            {
                                "elementen": [
                                    {
                                        "id": "eid1",
                                        "klasse": "Rechtssubject",
                                        "tekst": "Degene die aangifte doet",
                                        "lid": "",
                                    },
                                    {
                                        "id": "",
                                        "klasse": "Rechtsfeit",
                                        "tekst": "aangifte doet",
                                        "lid": "",
                                    },
                                ]
                            }
                        )
                    )
                ],
                "end_turn",
            )
        ]
    )
    settings = make_settings()

    result = herzie_node(
        {
            "voorstellen": [voorstel],
            "corpus": _CORPUS,
            "doel": {"bwbId": "BWBR0004770", "artikel": "10"},
            "critic_feedback": [],
            "critic_ontbrekend": [
                {"klasse": "Rechtsfeit", "reden": "mist", "tekst": "aangifte doet"}
            ],
            "verworpen_fragmenten": [],
        },
        settings=settings,
        llm=llm,
    )

    assert len(result["voorstellen"]) == 2
    klassen = {v["klasse"] for v in result["voorstellen"]}
    assert klassen == {"Rechtssubject", "Rechtsfeit"}
    assert result["critic_feedback"] == []
    assert result["nieuw_ontbrekend"] == []


def test_herzie_node_alleen_jurist_markeringen_niets_te_herzien() -> None:
    result = herzie_node(
        {"voorstellen": [{"id": "eid1", "van_jurist": True}]},
        settings=make_settings(),
        llm=FakeLLM([]),
    )
    assert result == {}


def test_herzie_node_faalpad_behoudt_vorige_voorstellen() -> None:
    voorstel = {"id": "eid1", "klasse": "Rechtssubject", "tekst": "x"}
    result = herzie_node(
        {
            "voorstellen": [voorstel],
            "corpus": _CORPUS,
            "doel": {"bwbId": "BWBR0004770", "artikel": "10"},
        },
        settings=make_settings(),
        llm=FakeLLM([response(None, "end_turn")]),
    )
    assert result == {"critic_feedback": []}


def test_emit_node_levert_openstaande_suggestie() -> None:
    voorstel = {
        "id": "eid1",
        "klasse": "Rechtssubject",
        "tekst": "Degene die aangifte doet",
        "aandacht": "rood",
        "critic_rondes": [
            {
                "actie": "vervang",
                "toegepast": False,
                "voorstel_klasse": "Rechtsfeit",
                "voorstel_tekst": "aangifte doet",
                "motivatie": "beter zo",
            }
        ],
    }
    result = emit_node({"voorstellen": [voorstel], "corpus": _CORPUS, "critic_ontbrekend": []})

    assert len(result["suggesties"]) == 1
    assert result["suggesties"][0]["voorstel_klasse"] == "Rechtsfeit"
    assert "1 JAS-elementen" in result["answer"]


def test_emit_node_zonder_voorstellen() -> None:
    assert emit_node({"voorstellen": []}) == {}


def test_build_graph_volledige_annotatieketen_met_doel() -> None:
    """`doel` in de state routeert om de supervisor heen; een rood+vervang-correctie in de eerste
    Critic-ronde wordt gepatcht, waarna een tweede (eind-)beoordeling naar `emit` gaat."""
    llm = FakeLLM(
        [
            response(  # annoteer
                [
                    text_block(
                        json.dumps(
                            {
                                "elementen": [
                                    {
                                        "klasse": "Rechtssubject",
                                        "tekst": "Degene die aangifte doet",
                                    }
                                ]
                            }
                        )
                    )
                ],
                "end_turn",
            ),
            response(  # critic ronde 1: rood+vervang
                [
                    text_block(
                        json.dumps(
                            {
                                "oordelen": [
                                    {
                                        "index": 0,
                                        "aandacht": "rood",
                                        "actie": "vervang",
                                        "voorstel_klasse": "Rechtsfeit",
                                        "motivatie": "beter zo",
                                    }
                                ],
                                "ontbrekend": [],
                            }
                        )
                    )
                ],
                "end_turn",
            ),
            response(  # critic ronde 2 (eindbeoordeling): groen
                [
                    text_block(
                        json.dumps(
                            {"oordelen": [{"index": 0, "aandacht": "groen"}], "ontbrekend": []}
                        )
                    )
                ],
                "end_turn",
            ),
        ]
    )
    # `artikel.artikel_corpus` parseert dit als SPARQL-TSV (net als
    # `test_annoteer_node_haalt_corpus_op_en_verwerkt_de_classificatie` hierboven) — geen platte
    # tekst, anders "vindt" `_verwerk` het fragment niet terug in de (verkeerd geparste) corpus.
    corpus_tsv = (
        "?tekst\t?jci\t?lid\t?lidnummer\t?lidtekst\t?onderdeel\t?onderdeeltekst\n"
        '\t\t\t"1"\t"Degene die aangifte doet, is verplicht de gegevens waarheidsgetrouw te '
        'verstrekken."@nl\t\t'
    )
    graph = FakeGraph(result=corpus_tsv)
    settings = make_settings()

    result = build_graph(settings, llm, graph).invoke(
        {"doel": {"bwbId": "BWBR0004770", "artikel": "1"}}
    )

    assert llm.index == 3  # annoteer + 2 critic-passen, geen supervisor-call
    assert result["voorstellen"][0]["klasse"] == "Rechtsfeit"  # gepatcht
    assert result["voorstellen"][0]["aandacht"] == "groen"  # eindoordeel
    assert result["answer"]


# ---- Gespreksgeheugen: checkpointer + nieuwe_beurt_invoer (story 050) -------------------------


def test_nieuwe_beurt_invoer_met_vraag_zaait_bericht_en_reset() -> None:
    invoer = nieuwe_beurt_invoer(question="Wat is een belastingschuldige?")

    assert invoer["question"] == "Wat is een belastingschuldige?"
    assert invoer["messages"] == [{"role": "user", "content": "Wat is een belastingschuldige?"}]
    assert invoer["turns"] == 0
    assert invoer["critic_ronde"] == 0
    assert invoer["voorstellen"] == []
    assert invoer["doel"] == {}


def test_nieuwe_beurt_invoer_met_doel_zaait_geen_bericht() -> None:
    invoer = nieuwe_beurt_invoer(doel={"bwbId": "BWBR0004770", "artikel": "1"})

    assert invoer["doel"] == {"bwbId": "BWBR0004770", "artikel": "1"}
    assert "messages" not in invoer
    assert invoer["question"] == ""


def test_checkpointer_onthoudt_het_gesprek_over_twee_beurten() -> None:
    async def _run() -> None:
        saver = MemorySaver()
        graph = FakeGraph(result="")
        thread = {"configurable": {"thread_id": "gesprek-1"}}

        app1 = build_graph(
            make_settings(),
            FakeLLM([_supervisor_ok(), response([text_block("Eerste antwoord.")], "end_turn")]),
            graph,
            checkpointer=saver,
        )
        await app1.ainvoke(nieuwe_beurt_invoer(question="Wat is een belastingschuldige?"), thread)

        app2 = build_graph(
            make_settings(),
            FakeLLM([_supervisor_ok(), response([text_block("Tweede antwoord.")], "end_turn")]),
            graph,
            checkpointer=saver,
        )
        result2 = await app2.ainvoke(nieuwe_beurt_invoer(question="En de aanslag dan?"), thread)

        gespreks_tekst = json.dumps(result2["messages"])
        assert "Wat is een belastingschuldige?" in gespreks_tekst
        assert "Eerste antwoord." in gespreks_tekst
        assert "En de aanslag dan?" in gespreks_tekst

        # Een ANDER gesprek deelt geen geheugen.
        ander_thread = {"configurable": {"thread_id": "gesprek-2"}}
        app3 = build_graph(
            make_settings(),
            FakeLLM([_supervisor_ok(), response([text_block("Los antwoord.")], "end_turn")]),
            graph,
            checkpointer=saver,
        )
        result3 = await app3.ainvoke(
            nieuwe_beurt_invoer(question="Geheel andere vraag"), ander_thread
        )
        gespreks_tekst_3 = json.dumps(result3["messages"])
        assert "belastingschuldige" not in gespreks_tekst_3

    asyncio.run(_run())


def test_checkpointer_reset_ephemere_annotatievelden_bij_een_nieuwe_beurt() -> None:
    """Een annotatiebeurt laat `critic_ronde`/`corpus`/`voorstellen` gevuld achter; een
    daaropvolgende QA-beurt in hetzelfde gesprek raakt die velden niet, maar hoort ze via de
    reset in `nieuwe_beurt_invoer` toch weer op de default te zien."""

    async def _run() -> None:
        saver = MemorySaver()
        thread = {"configurable": {"thread_id": "gesprek-annotatie"}}
        corpus_tsv = (
            "?tekst\t?jci\t?lid\t?lidnummer\t?lidtekst\t?onderdeel\t?onderdeeltekst\n"
            '\t\t\t"1"\t"Degene die aangifte doet."@nl\t\t'
        )

        app1 = build_graph(
            make_settings(),
            FakeLLM(
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
                                            }
                                        ]
                                    }
                                )
                            )
                        ],
                        "end_turn",
                    ),
                    response(
                        [text_block(json.dumps({"oordelen": [{"index": 0, "aandacht": "groen"}]}))],
                        "end_turn",
                    ),
                ]
            ),
            FakeGraph(result=corpus_tsv),
            checkpointer=saver,
        )
        eerste = await app1.ainvoke(
            nieuwe_beurt_invoer(doel={"bwbId": "BWBR0004770", "artikel": "1"}), thread
        )
        assert eerste["critic_ronde"] == 1  # critic_max_rondes-default stopt na 1 (geel/groen)

        app2 = build_graph(
            make_settings(),
            FakeLLM([_supervisor_ok(), response([text_block("Gewoon antwoord.")], "end_turn")]),
            FakeGraph(result=""),
            checkpointer=saver,
        )
        tweede = await app2.ainvoke(
            nieuwe_beurt_invoer(question="Een gewone vraag, geen annotatie"), thread
        )

        assert tweede["critic_ronde"] == 0
        assert tweede["corpus"] == ""
        assert tweede["voorstellen"] == []
        assert tweede["doel"] == {}

    asyncio.run(_run())


def test_supervisor_krijgt_eerdere_berichten_als_gesprekscontext() -> None:
    """Zonder dit ziet de supervisor een vervolgvraag als 'en welk artikel regelt dat begrip
    precies?' los van het gesprek — live gevonden tijdens de verificatie van story 050."""
    voorgeschiedenis = [
        {"role": "user", "content": "Wat is een belastingschuldige?"},
        {"role": "assistant", "content": [{"type": "text", "text": "Dat is degene die betaalt."}]},
    ]
    # AFWIJZEN als canned respons: de graaf stopt na de supervisor, dus we hoeven de rest van de
    # keten niet mee te geven — deze test toetst alleen wát de supervisor kreeg te lezen.
    llm = FakeLLM([_supervisor_ok("algemeen", "AFWIJZEN")])
    settings = make_settings()

    build_graph(settings, llm, FakeGraph(result="")).invoke(
        {"question": "En welk artikel regelt dat begrip?", "messages": voorgeschiedenis}
    )

    system = llm.calls[0]["system"]
    assert "GESPREKSCONTEXT" in system
    assert "belastingschuldige" in system


def test_supervisor_geen_gesprekscontext_bij_de_eerste_vraag() -> None:
    llm = FakeLLM([_supervisor_ok("algemeen", "AFWIJZEN")])
    settings = make_settings()

    build_graph(settings, llm, FakeGraph(result="")).invoke({"question": "Een eerste vraag"})

    assert "GESPREKSCONTEXT" not in llm.calls[0]["system"]
