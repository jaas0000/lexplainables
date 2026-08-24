"""Centrale configuratie: één gevalideerd Settings-model dat de omgeving één keer inleest.

Bewust een gewone pydantic `BaseModel` + `from_env()` i.p.v. `pydantic-settings`: zelfde effect
(validatie, één inleespunt), geen extra runtime-dependency (matcht de referentie-app).

Scoped tot wat de poorten (deze story) nodig hebben — GraphDB-MCP-verbinding + LLM-verbinding.
Meer velden (orkestrator-knoppen, annotatieketen-tuning, rate-limiting, OTel, …) komen erbij
zodra de story die ze nodig heeft er is, zelfde patroon als `tools/bwb-import`'s `Settings`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel


def _read_secret(env: Mapping[str, str], name: str) -> str | None:
    """Lees een secret: eerst `<NAME>_FILE` (host-bestand, werkwijze-ADR-0006), anders `<NAME>`
    (bewust een minder strikte fallback dan bwb-import's `_read_secret`: deze accepteert ook een
    platte waarde, zodat lokale dev zonder secret-bestanden kan — de referentie-app doet
    hetzelfde)."""
    path = env.get(name + "_FILE")
    if path:
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            return None
    return env.get(name)


class Settings(BaseModel):
    # GraphDB MCP
    graphdb_mcp_url: str = ""  # verplicht; zie require_graph()
    graphdb_token: str | None = None
    repository_id: str = "inning"
    graphdb_sparql_tool: str = "sparql_query"  # naam van de SPARQL-tool op de MCP-server
    similarity_index: str = ""  # GraphDB-similarity-index voor semantic_search; leeg = nog uit

    # LLM (Azure AI Foundry / Anthropic)
    azure_foundry_api_key: str | None = None
    # Korte resource-naam (bv. "jjpl-m8ei8xzz-eastus2"), niet een volledige URL — dat is wat
    # `anthropic.AnthropicFoundry(resource=...)` verwacht (de dedicated Foundry-client-class,
    # zie story 039).
    azure_foundry_resource: str | None = None
    llm_model: str = "claude-sonnet-4-6"
    # Prompt-caching is op Azure AI Foundry een beta-functie; de adapter zet 'm zelf uit als de
    # provider een cache-punt weigert (zie adapters/anthropic_llm.py). Deze knop is voor bewust
    # vooraf uitzetten (bv. lokale dev tegen een resource zonder de beta).
    prompt_caching: bool = True

    # Decompositie (story 046): multi-hop-graaf-variant, standaard uit — zie orchestrator.py
    # build_graph() voor de vertakking.
    enable_decomposition: bool = False
    max_subquestions: int = 5  # cap op het aantal deelvragen (kosten/latency begrenzen)
    sub_max_turns: int = 8  # agent⇄tools-beurten per deelvraag, los van MAX_TURNS

    # Annotatie-critic (story 049): 0 = uit (annoteer → critic → emit, geen patch/herziening),
    # >0 = aan.
    critic_max_rondes: int = 1

    # Gespreksgeheugen (story 050): LangGraph-checkpointer, voorrang Postgres → SQLite-bestand →
    # in-memory. Zie agent/checkpointer.py.
    checkpoint_db_url: str | None = None
    checkpoint_db_path: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        e = env if env is not None else os.environ
        raw: dict[str, object] = {
            "graphdb_mcp_url": e.get("GRAPHDB_MCP_URL"),
            "graphdb_token": _read_secret(e, "GRAPHDB_TOKEN"),
            "repository_id": e.get("GRAPHDB_REPOSITORY_ID"),
            "graphdb_sparql_tool": e.get("GRAPHDB_SPARQL_TOOL"),
            "similarity_index": e.get("SIMILARITY_INDEX"),
            "azure_foundry_api_key": _read_secret(e, "AZURE_FOUNDRY_API_KEY"),
            "azure_foundry_resource": e.get("AZURE_FOUNDRY_RESOURCE"),
            "llm_model": e.get("LLM_MODEL"),
            "prompt_caching": e.get("PROMPT_CACHING"),
            "enable_decomposition": e.get("ENABLE_DECOMPOSITION"),
            "max_subquestions": e.get("MAX_SUBQUESTIONS"),
            "sub_max_turns": e.get("SUB_MAX_TURNS"),
            "critic_max_rondes": e.get("CRITIC_MAX_RONDES"),
            "checkpoint_db_url": e.get("CHECKPOINT_DB_URL"),
            "checkpoint_db_path": e.get("CHECKPOINT_DB_PATH"),
        }
        # None én lege string weglaten zodat de veld-defaults van kracht blijven.
        return cls(**{k: v for k, v in raw.items() if v is not None and v != ""})

    def require_graph(self) -> None:
        if not self.graphdb_mcp_url:
            raise ValueError("Graaf niet geconfigureerd: zet GRAPHDB_MCP_URL.")
        if not self.graphdb_token:
            raise ValueError("Graaf niet geconfigureerd: zet GRAPHDB_TOKEN.")

    def require_llm(self) -> None:
        if not self.azure_foundry_api_key or not self.azure_foundry_resource:
            raise ValueError(
                "LLM niet geconfigureerd: zet AZURE_FOUNDRY_API_KEY en AZURE_FOUNDRY_RESOURCE."
            )
