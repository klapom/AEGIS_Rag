"""Neo4j Persistence.

Sprint 56.2: Persistence subdomain of knowledge_graph.

Usage:
    from src.domains.knowledge_graph.persistence import (
        Neo4jClient,
        get_neo4j_client,
        GraphQueryTemplates,
    )
"""

# OPL-009: Re-export from components/graph_rag until Sprint 58
from src.components.graph_rag.neo4j_client import (
    Neo4jClient,
    get_neo4j_client,
    get_neo4j_client_async,
)
from src.components.graph_rag.query_templates import GraphQueryTemplates
from src.components.graph_rag.query_builder import CypherQueryBuilder
from src.components.graph_rag.temporal_query_builder import (
    TemporalQueryBuilder,
    get_temporal_query_builder,
)

__all__ = [
    # Neo4j Client
    "Neo4jClient",
    "get_neo4j_client",
    "get_neo4j_client_async",
    # Query Templates & Builder
    "GraphQueryTemplates",
    "CypherQueryBuilder",
    # Temporal Queries
    "TemporalQueryBuilder",
    "get_temporal_query_builder",
]
