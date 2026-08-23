"""Schema-introspectie van de kennisgraaf, met in-proces cache (werkwijze-story 041).

Het model vraagt de live tellingen op via de `graph_schema`-tool i.p.v. te vertrouwen op
bevroren cijfers die verouderen zodra de graaf groeit.

Poort van `wetsanalyse-ai/tools/graph-qa/agent/graph/schema.py`, 1:1.
"""

from __future__ import annotations

from ..ports import GraphPort
from . import queries

_cache: str | None = None


def reset_cache() -> None:
    """Leeg de cache (voor tests)."""
    global _cache
    _cache = None


def graph_schema(graph: GraphPort) -> str:
    """Geef een (gecachete) samenvatting van omvang en regelingen van de graaf."""
    global _cache
    if _cache is not None:
        return _cache

    counts = graph.sparql(queries.count_by_type())
    regelingen = graph.sparql(queries.list_regelingen())

    _cache = (
        "AANTALLEN PER TYPE (eigen IRI-ruimte, sameAs-tweelingen niet meegeteld):\n"
        f"{counts}\n\n"
        "REGELINGEN IN DE GRAAF:\n"
        f"{regelingen}"
    )
    return _cache
