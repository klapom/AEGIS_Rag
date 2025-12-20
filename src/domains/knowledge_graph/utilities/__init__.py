"""Knowledge Graph Utilities.

Sprint 56.2: Protocols, query templates, and utilities.

Usage:
    from src.domains.knowledge_graph.utilities import (
        GraphStorage,
        CommunityDetectorProtocol,
        LLMConfigProvider,
    )
"""

# Re-export from components/graph_rag
from src.components.graph_rag.llm_config_provider import (
    REDIS_KEY_SUMMARY_MODEL_CONFIG,
    get_configured_summary_model,
)
from src.components.graph_rag.protocols import (
    CommunityDetector as CommunityDetectorProtocol,
)
from src.components.graph_rag.protocols import (
    GraphStorage,
    LLMConfigProvider,
)
from src.components.graph_rag.visualization_export import (
    GraphVisualizationExporter,
    get_visualization_exporter,
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
