"""make_graph(): bouwt een GraphPort-conforme MCPClient uit Settings (werkwijze-story 040)."""

from __future__ import annotations

import pytest

from agent.adapters.graphdb_graph import make_graph
from agent.config import Settings
from agent.mcp_client import MCPClient
from agent.ports import GraphPort


def test_make_graph_zonder_config_gooit() -> None:
    settings = Settings.from_env({})
    with pytest.raises(ValueError, match="GRAPHDB_MCP_URL"):
        make_graph(settings)


def test_make_graph_geeft_graphport_conforme_client() -> None:
    settings = Settings.from_env(
        {
            "GRAPHDB_MCP_URL": "http://localhost:8004/mcp",
            "GRAPHDB_TOKEN": "t",
            "GRAPHDB_REPOSITORY_ID": "inning",
            "SIMILARITY_INDEX": "bwb_similarity",
        }
    )

    graph = make_graph(settings)

    assert isinstance(graph, GraphPort)
    assert isinstance(graph, MCPClient)
    assert graph.url == "http://localhost:8004/mcp"
    assert graph._repository_id == "inning"
    assert graph._similarity_index == "bwb_similarity"
