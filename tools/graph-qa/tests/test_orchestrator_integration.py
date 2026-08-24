"""Live integratietests: de volledige antwoord-agent-loop tegen de echte GraphDB + Foundry
(werkwijze-stories 044-050).

Standaard geskipt (`-m "not integration"`) — vereist een draaiende `deploy/graphdb`-stack (gevuld
met de Invorderingswet-fixture, zie stories 040/041) en een geldige Foundry-key/-resource in de
omgeving.
"""

from __future__ import annotations

import json
import os

import pytest
from langgraph.checkpoint.memory import MemorySaver

from agent.adapters.anthropic_llm import AnthropicLLM
from agent.adapters.graphdb_graph import make_graph
from agent.config import Settings
from agent.jas_klassen import GELDIGE_JAS_KLASSEN
from agent.orchestrator import annoteer_node, build_graph, critic_node, nieuwe_beurt_invoer


@pytest.mark.integration
def test_live_antwoord_op_vraag_over_invorderingswet() -> None:
    settings = Settings.from_env(os.environ)
    if not settings.azure_foundry_api_key or not settings.azure_foundry_resource:
        pytest.skip("AZURE_FOUNDRY_API_KEY(_FILE)/AZURE_FOUNDRY_RESOURCE niet in de omgeving")
    if not settings.graphdb_mcp_url or not settings.graphdb_token:
        pytest.skip("GRAPHDB_MCP_URL/GRAPHDB_TOKEN niet in de omgeving")

    llm = AnthropicLLM(settings)
    graph = make_graph(settings)
    try:
        vraag = "Wat staat er in artikel 2 van de Invorderingswet 1990 over belastingschuldigen?"
        result = build_graph(settings, llm, graph).invoke({"question": vraag})
    finally:
        graph.close()

    # Geen inhoudscontrole (dat is eval-werk) — alleen dat de keten daadwerkelijk de graaf raakte
    # en een oordeel velde, niet dat de agent het "goede" antwoord gaf.
    assert result["source_trace"], "de agent heeft geen enkele tool aangeroepen"
    assert result["grounding_niveau"] in {"gegrond", "onbepaald"}, (
        f"onverwacht ongegrond: {result.get('unsupported')} / {result.get('niet_letterlijk')}"
    )
    assert (result["answer"] or "").strip() != ""


@pytest.mark.integration
def test_live_supervisor_routeert_begripsvraag_naar_definitie() -> None:
    settings = Settings.from_env(os.environ)
    if not settings.azure_foundry_api_key or not settings.azure_foundry_resource:
        pytest.skip("AZURE_FOUNDRY_API_KEY(_FILE)/AZURE_FOUNDRY_RESOURCE niet in de omgeving")
    if not settings.graphdb_mcp_url or not settings.graphdb_token:
        pytest.skip("GRAPHDB_MCP_URL/GRAPHDB_TOKEN niet in de omgeving")

    llm = AnthropicLLM(settings)
    graph = make_graph(settings)
    try:
        vraag = "Wat betekent het begrip belastingschuldige volgens de Invorderingswet 1990?"
        result = build_graph(settings, llm, graph).invoke({"question": vraag})
    finally:
        graph.close()

    assert result["specialist"] == "definitie", f"onverwachte routing: {result.get('plan')}"
    assert result["source_trace"], "de definitie-specialist heeft geen enkele tool aangeroepen"


@pytest.mark.integration
def test_live_afwijst_vraag_buiten_de_wetgeving_zonder_de_graaf_te_raken() -> None:
    settings = Settings.from_env(os.environ)
    if not settings.azure_foundry_api_key or not settings.azure_foundry_resource:
        pytest.skip("AZURE_FOUNDRY_API_KEY(_FILE)/AZURE_FOUNDRY_RESOURCE niet in de omgeving")
    if not settings.graphdb_mcp_url or not settings.graphdb_token:
        pytest.skip("GRAPHDB_MCP_URL/GRAPHDB_TOKEN niet in de omgeving")

    llm = AnthropicLLM(settings)
    graph = make_graph(settings)
    try:
        vraag = "Wat is het weer vandaag in Amsterdam?"
        result = build_graph(settings, llm, graph).invoke({"question": vraag})
    finally:
        graph.close()

    assert result["afwijzen"] is True
    assert result["source_trace"] == [], "een afgewezen vraag hoort de graaf niet te raken"
    assert (result["answer"] or "").strip() != ""


@pytest.mark.integration
def test_live_decompositie_splitst_een_samengestelde_vraag() -> None:
    settings = Settings.from_env(os.environ)
    if not settings.azure_foundry_api_key or not settings.azure_foundry_resource:
        pytest.skip("AZURE_FOUNDRY_API_KEY(_FILE)/AZURE_FOUNDRY_RESOURCE niet in de omgeving")
    if not settings.graphdb_mcp_url or not settings.graphdb_token:
        pytest.skip("GRAPHDB_MCP_URL/GRAPHDB_TOKEN niet in de omgeving")
    settings = settings.model_copy(update={"enable_decomposition": True})

    llm = AnthropicLLM(settings)
    graph = make_graph(settings)
    try:
        vraag = (
            "Wat is een belastingschuldige, en wat is een belastingaanslag, volgens de "
            "Invorderingswet 1990?"
        )
        result = build_graph(settings, llm, graph).invoke({"question": vraag})
    finally:
        graph.close()

    assert len(result["sub_questions"]) >= 2, f"geen splitsing: {result.get('sub_questions')}"
    assert result["source_trace"], "de decompositie-lus heeft geen enkele tool aangeroepen"
    assert result["grounding_niveau"] in {"gegrond", "onbepaald"}, (
        f"onverwacht ongegrond: {result.get('unsupported')} / {result.get('niet_letterlijk')}"
    )
    assert (result["answer"] or "").strip() != ""


@pytest.mark.integration
def test_live_annoteer_node_classificeert_een_echte_bepaling() -> None:
    settings = Settings.from_env(os.environ)
    if not settings.azure_foundry_api_key or not settings.azure_foundry_resource:
        pytest.skip("AZURE_FOUNDRY_API_KEY(_FILE)/AZURE_FOUNDRY_RESOURCE niet in de omgeving")
    if not settings.graphdb_mcp_url or not settings.graphdb_token:
        pytest.skip("GRAPHDB_MCP_URL/GRAPHDB_TOKEN niet in de omgeving")

    llm = AnthropicLLM(settings)
    graph = make_graph(settings)
    try:
        # Artikel 1 heeft echte normatieve inhoud (toepassingsbereik + een uitzonderingsbepaling
        # op de Awb) — anders dan artikel 2's pure definitie-opsomming een betere proef voor JAS-
        # classificatie (Rechtsbetrekking/Voorwaarde/Delegatiebevoegdheid-achtige elementen).
        doel = {"bwbId": "BWBR0004770", "artikel": "1"}
        result = annoteer_node({"doel": doel}, settings=settings, llm=llm, graph=graph)
    finally:
        graph.close()

    assert result["corpus"].strip(), "geen corpus opgehaald"
    assert result["voorstellen"], "geen enkel voorstel geleverd"
    for v in result["voorstellen"]:
        assert v["klasse"] in GELDIGE_JAS_KLASSEN, f"onbekende klasse: {v['klasse']}"
        assert v["grounded"] is True
        assert v["tekst"].strip()


@pytest.mark.integration
def test_live_critic_node_beoordeelt_echte_voorstellen() -> None:
    settings = Settings.from_env(os.environ)
    if not settings.azure_foundry_api_key or not settings.azure_foundry_resource:
        pytest.skip("AZURE_FOUNDRY_API_KEY(_FILE)/AZURE_FOUNDRY_RESOURCE niet in de omgeving")
    if not settings.graphdb_mcp_url or not settings.graphdb_token:
        pytest.skip("GRAPHDB_MCP_URL/GRAPHDB_TOKEN niet in de omgeving")

    llm = AnthropicLLM(settings)
    graph = make_graph(settings)
    try:
        doel = {"bwbId": "BWBR0004770", "artikel": "1"}
        annotatie = annoteer_node({"doel": doel}, settings=settings, llm=llm, graph=graph)
        assert annotatie["voorstellen"], "annoteer_node leverde geen voorstellen om te beoordelen"
        result = critic_node(
            {"voorstellen": annotatie["voorstellen"], "corpus": annotatie["corpus"]},
            settings=settings,
            llm=llm,
        )
    finally:
        graph.close()

    assert result["critic_gefaald"] is False
    assert result["critic_ronde"] == 1
    for v in result["voorstellen"]:
        assert v["aandacht"] in {"", "groen", "geel", "rood"}
        # Geen enkele Critic-motivatie hoort een rauwe interne id te bevatten — die is via
        # vervang_ids_door_citaat vertaald naar een citaat (of "een ander element").
        assert not any(
            other["id"] and other["id"] != v["id"] and other["id"] in v["critic"]
            for other in result["voorstellen"]
        )


@pytest.mark.integration
def test_live_build_graph_met_doel_doorloopt_de_volledige_annotatieketen() -> None:
    """`build_graph(...).invoke({"doel": {...}})` — de graaf-wiring uit story 049: annoteren,
    beoordelen, eventueel patchen/herzien, en een finale structuur zonder crash."""
    settings = Settings.from_env(os.environ)
    if not settings.azure_foundry_api_key or not settings.azure_foundry_resource:
        pytest.skip("AZURE_FOUNDRY_API_KEY(_FILE)/AZURE_FOUNDRY_RESOURCE niet in de omgeving")
    if not settings.graphdb_mcp_url or not settings.graphdb_token:
        pytest.skip("GRAPHDB_MCP_URL/GRAPHDB_TOKEN niet in de omgeving")

    llm = AnthropicLLM(settings)
    graph = make_graph(settings)
    try:
        result = build_graph(settings, llm, graph).invoke(
            {"doel": {"bwbId": "BWBR0004770", "artikel": "1"}}
        )
    finally:
        graph.close()

    assert result["voorstellen"], "geen enkel voorstel geleverd"
    assert (result.get("answer") or "").strip() != ""
    for v in result["voorstellen"]:
        assert v["klasse"] in GELDIGE_JAS_KLASSEN


@pytest.mark.integration
def test_live_gespreksgeheugen_over_twee_beurten() -> None:
    """Een echte tweede vraag in hetzelfde gesprek (checkpointer, story 050) — de agent moet de
    eerste vraag/het eerste antwoord terugzien in zijn messages-historie."""
    import asyncio

    settings = Settings.from_env(os.environ)
    if not settings.azure_foundry_api_key or not settings.azure_foundry_resource:
        pytest.skip("AZURE_FOUNDRY_API_KEY(_FILE)/AZURE_FOUNDRY_RESOURCE niet in de omgeving")
    if not settings.graphdb_mcp_url or not settings.graphdb_token:
        pytest.skip("GRAPHDB_MCP_URL/GRAPHDB_TOKEN niet in de omgeving")

    async def _run() -> None:
        llm = AnthropicLLM(settings)
        graph = make_graph(settings)
        saver = MemorySaver()
        thread = {"configurable": {"thread_id": "live-gesprek-1"}}
        try:
            app = build_graph(settings, llm, graph, checkpointer=saver)
            await app.ainvoke(
                nieuwe_beurt_invoer(
                    question="Wat is een belastingschuldige volgens de Invorderingswet 1990?"
                ),
                thread,
            )
            tweede = await app.ainvoke(
                nieuwe_beurt_invoer(question="En wat is een belastingaanslag?"), thread
            )
        finally:
            graph.close()

        gespreks_tekst = json.dumps(tweede["messages"])
        assert "belastingschuldige" in gespreks_tekst.lower()
        assert (tweede.get("answer") or "").strip() != ""

    asyncio.run(_run())
