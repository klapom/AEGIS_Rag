"""Community Detection and Summarization.

Sprint 56.2: Communities subdomain of knowledge_graph.
Sprint 62.8: Section-Based Community Detection.

Usage:
    from src.domains.knowledge_graph.communities import (
        CommunityDetector,
        CommunitySummarizer,
        CommunitySearch,
        SectionCommunityDetector,  # Sprint 62.8
    )
"""

# Re-export from components/graph_rag
from src.components.graph_rag.community_delta_tracker import (
    CommunityDelta,
    get_entity_communities_snapshot,
    track_community_changes,
)
from src.components.graph_rag.community_detector import (
    CommunityDetector,
    get_community_detector,
)
from src.components.graph_rag.community_search import (
    CommunitySearch,
    get_community_search,
)
from src.components.graph_rag.community_summarizer import (
    CommunitySummarizer,
    get_community_summarizer,
)

# Sprint 62.8: Section-Based Community Detection
from src.domains.knowledge_graph.communities.section_community_detector import (
    CrossSectionCommunityComparison,
    SectionCommunityDetector,
    SectionCommunityMetadata,
    SectionCommunityResult,
    get_section_community_detector,
    reset_section_community_detector,
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
    # Section-Based Detection (Sprint 62.8)
    "SectionCommunityDetector",
    "get_section_community_detector",
    "reset_section_community_detector",
    "SectionCommunityResult",
    "SectionCommunityMetadata",
    "CrossSectionCommunityComparison",
]
