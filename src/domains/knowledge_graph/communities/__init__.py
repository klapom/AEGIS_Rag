"""Community Detection and Summarization.

Sprint 56.2: Communities subdomain of knowledge_graph.

Usage:
    from src.domains.knowledge_graph.communities import (
        CommunityDetector,
        CommunitySummarizer,
        CommunitySearch,
    )
"""

# Re-export from components/graph_rag
from src.components.graph_rag.community_detector import (
    CommunityDetector,
    get_community_detector,
)
from src.components.graph_rag.community_summarizer import (
    CommunitySummarizer,
    get_community_summarizer,
)
from src.components.graph_rag.community_delta_tracker import (
    CommunityDelta,
    track_community_changes,
    get_entity_communities_snapshot,
)
from src.components.graph_rag.community_search import (
    CommunitySearch,
    get_community_search,
)

__all__ = [
    # Detection
    "CommunityDetector",
    "get_community_detector",
    # Summarization
    "CommunitySummarizer",
    "get_community_summarizer",
    # Delta Tracking
    "CommunityDelta",
    "track_community_changes",
    "get_entity_communities_snapshot",
    # Search
    "CommunitySearch",
    "get_community_search",
]
