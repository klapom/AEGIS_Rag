"""AegisRAG Domain Layer.

Sprint 56: Domain-Driven Design boundaries for business logic.

Domains:
- knowledge_graph: Graph-based knowledge management (entities, relations, communities)
- document_processing: Document ingestion and chunking (parsing, enrichment, pipeline)
- vector_search: Vector-based retrieval (Qdrant, hybrid search, embeddings)
- memory: 3-layer memory system (Redis, Graphiti, conversation)
- llm_integration: LLM provisioning (AegisLLMProxy, routing, cost tracking)

Usage:
    from src.domains.knowledge_graph import query_graph, extract_entities
    from src.domains.document_processing import process_document
    from src.domains.vector_search import hybrid_search
    from src.domains.memory import get_conversation_history
    from src.domains.llm_integration import generate_response
"""

__all__ = [
    "knowledge_graph",
    "document_processing",
    "vector_search",
    "memory",
    "llm_integration",
]
