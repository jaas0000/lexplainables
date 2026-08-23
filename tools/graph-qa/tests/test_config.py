from __future__ import annotations

from pathlib import Path

import pytest

from agent.config import Settings


def test_from_env_defaults_zonder_env_vars() -> None:
    settings = Settings.from_env({})

    assert settings.graphdb_mcp_url == ""
    assert settings.repository_id == "inning"
    assert settings.llm_model == "claude-sonnet-4-6"
    assert settings.graphdb_token is None


def test_from_env_leest_platte_waarden() -> None:
    env = {
        "GRAPHDB_MCP_URL": "http://localhost:8004/mcp",
        "GRAPHDB_TOKEN": "geheim-token",
        "GRAPHDB_REPOSITORY_ID": "inning",
        "AZURE_FOUNDRY_API_KEY": "sleutel",
        "AZURE_FOUNDRY_RESOURCE": "jjpl-m8ei8xzz-eastus2",
        "LLM_MODEL": "claude-opus-5",
    }
    settings = Settings.from_env(env)

    assert settings.graphdb_mcp_url == "http://localhost:8004/mcp"
    assert settings.graphdb_token == "geheim-token"
    assert settings.azure_foundry_resource == "jjpl-m8ei8xzz-eastus2"
    assert settings.llm_model == "claude-opus-5"


def test_secret_file_heeft_voorrang_boven_platte_waarde(tmp_path: Path) -> None:
    secret_file = tmp_path / "graphdb_token"
    secret_file.write_text("uit-bestand\n")
    env = {
        "GRAPHDB_TOKEN_FILE": str(secret_file),
        "GRAPHDB_TOKEN": "platte-waarde-genegeerd",
    }
    settings = Settings.from_env(env)

    assert settings.graphdb_token == "uit-bestand"


def test_lege_env_waarde_valt_terug_op_default() -> None:
    """Een gezette maar lege env-var (LLM_MODEL="") mag de default niet overschrijven met ''."""
    settings = Settings.from_env({"LLM_MODEL": ""})

    assert settings.llm_model == "claude-sonnet-4-6"


def test_require_graph_zonder_config_gooit() -> None:
    settings = Settings.from_env({})
    with pytest.raises(ValueError, match="GRAPHDB_MCP_URL"):
        settings.require_graph()


def test_require_graph_zonder_token_gooit() -> None:
    settings = Settings.from_env({"GRAPHDB_MCP_URL": "http://x"})
    with pytest.raises(ValueError, match="GRAPHDB_TOKEN"):
        settings.require_graph()


def test_require_graph_met_volledige_config_gooit_niet() -> None:
    settings = Settings.from_env({"GRAPHDB_MCP_URL": "http://x", "GRAPHDB_TOKEN": "t"})
    settings.require_graph()  # geen exception


def test_require_llm_zonder_config_gooit() -> None:
    settings = Settings.from_env({})
    with pytest.raises(ValueError, match="AZURE_FOUNDRY"):
        settings.require_llm()


def test_require_llm_met_volledige_config_gooit_niet() -> None:
    settings = Settings.from_env({"AZURE_FOUNDRY_API_KEY": "k", "AZURE_FOUNDRY_RESOURCE": "r"})
    settings.require_llm()  # geen exception


def test_prompt_caching_default_aan() -> None:
    settings = Settings.from_env({})
    assert settings.prompt_caching is True


def test_prompt_caching_uit_via_env() -> None:
    settings = Settings.from_env({"PROMPT_CACHING": "false"})
    assert settings.prompt_caching is False


def test_prompt_caching_lege_env_waarde_valt_terug_op_default() -> None:
    settings = Settings.from_env({"PROMPT_CACHING": ""})
    assert settings.prompt_caching is True
