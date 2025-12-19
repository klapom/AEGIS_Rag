"""Knowledge Graph Utilities.

Sprint 56.2: Protocols, query templates, and utilities.

Usage:
    from src.domains.knowledge_graph.utilities import (
        GraphStorage,
        CommunityDetectorProtocol,
        LLMConfigProvider,
    )
"""

# OPL-009: Re-export from components/graph_rag until Sprint 58
from src.components.graph_rag.protocols import (
    GraphStorage,
    CommunityDetector as CommunityDetectorProtocol,
    LLMConfigProvider,
)
from src.components.graph_rag.visualization_export import (
    GraphVisualizationExporter,
    get_visualization_exporter,
)
from src.components.graph_rag.llm_config_provider import (
    get_configured_summary_model,
    REDIS_KEY_SUMMARY_MODEL_CONFIG,
)

__all__ = [
    # Protocols
    "GraphStorage",
    "CommunityDetectorProtocol",
    "LLMConfigProvider",
    # Visualization
    "GraphVisualizationExporter",
    "get_visualization_exporter",
    # LLM Config Provider
    "get_configured_summary_model",
    "REDIS_KEY_SUMMARY_MODEL_CONFIG",
]
