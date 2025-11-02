"""User Profiling Components for AEGIS RAG Sprint 17.

This module provides implicit user profiling capabilities:
- Profile signal extraction from conversations
- Neo4j knowledge graph for behavioral patterns
- Profile-aware retrieval for personalization
- Privacy-first design (no PII storage)
- Conversation archiving pipeline (Phase 1)

Key Components:
- ProfileExtractor: Extract behavioral signals from conversations
- Neo4jProfileManager: Manage user profile graph in Neo4j
- ProfileAwareRetrieval: Personalize retrieval based on user profile
- ConversationArchiver: Archive conversations to Qdrant for semantic search

Sprint 17 Feature 17.4: Implicit User Profiling with Neo4j + Conversation Archiving
"""

from src.components.profiling.conversation_archiver import (
    ConversationArchiver,
    get_conversation_archiver,
)

# TODO: Sprint 17 - Implement remaining profiling modules
# from src.components.profiling.neo4j_profile_manager import (
#     Neo4jProfileManager,
#     get_profile_manager,
# )
# from src.components.profiling.profile_aware_retrieval import (
#     ProfileAwareRetrieval,
#     get_profile_aware_retrieval,
# )
# from src.components.profiling.profile_extractor import (
#     ExpertiseLevel,
#     ProfileExtractor,
#     ProfileSignals,
#     get_profile_extractor,
# )

__all__ = [
    # Conversation Archiving (Phase 1 - Implemented)
    "ConversationArchiver",
    "get_conversation_archiver",
    # TODO: Sprint 17 - Uncomment when implemented
    # # Profile Extraction
    # "ProfileExtractor",
    # "ProfileSignals",
    # "ExpertiseLevel",
    # "get_profile_extractor",
    # # Neo4j Profile Manager
    # "Neo4jProfileManager",
    # "get_profile_manager",
    # # Profile-Aware Retrieval
    # "ProfileAwareRetrieval",
    # "get_profile_aware_retrieval",
]
