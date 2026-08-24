"""Live integratietest: de volledige antwoord-agent-loop tegen de echte GraphDB + Foundry
(werkwijze-story 044).

Standaard geskipt (`-m "not integration"`) — vereist een draaiende `deploy/graphdb`-stack (gevuld
met de Invorderingswet-fixture, zie stories 040/041) en een geldige Foundry-key/-resource in de
omgeving.
"""

from __future__ import annotations

import os

import pytest

from agent.adapters.anthropic_llm import AnthropicLLM
from agent.adapters.graphdb_graph import make_graph
from agent.config import Settings
from agent.orchestrator import build_graph


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
