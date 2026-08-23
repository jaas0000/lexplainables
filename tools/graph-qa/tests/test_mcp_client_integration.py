"""Live integratietest tegen een echte GraphDB-MCP-server (werkwijze-story 040).

Standaard geskipt (`-m "not integration"`, zie `graph-qa-ci.yml`) — vereist een draaiende
`deploy/graphdb`-stack en `GRAPHDB_MCP_URL`/`GRAPHDB_TOKEN` in de omgeving.
"""

from __future__ import annotations

import os

import pytest

from agent.mcp_client import MCPClient


@pytest.mark.integration
def test_live_sparql_tegen_graphdb() -> None:
    url = os.environ.get("GRAPHDB_MCP_URL")
    token = os.environ.get("GRAPHDB_TOKEN")
    if not url or not token:
        pytest.skip("GRAPHDB_MCP_URL/GRAPHDB_TOKEN niet in de omgeving")

    repository_id = os.environ.get("GRAPHDB_REPOSITORY_ID", "inning")
    client = MCPClient(url=url, token=token, repository_id=repository_id)
    try:
        resultaat = client.sparql("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
    finally:
        client.close()

    assert resultaat.strip() != ""
