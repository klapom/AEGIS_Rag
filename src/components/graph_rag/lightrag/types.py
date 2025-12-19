"""LightRAG type definitions.

Sprint 55 Feature 55.2: Shared types for LightRAG integration.

This module contains dataclasses and type aliases used across the lightrag package.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class QueryMode(Enum):
    """LightRAG query modes for dual-level retrieval."""

    LOCAL = "local"  # Entity-level retrieval (specific entities and relationships)
    GLOBAL = "global"  # Topic-level retrieval (high-level summaries, communities)
    HYBRID = "hybrid"  # Combined local + global
    NAIVE = "naive"  # Simple retrieval without graph traversal


@dataclass
class LightRAGConfig:
    """Configuration for LightRAG client initialization.

    Attributes:
        working_dir: Working directory for LightRAG data files
        llm_model: LLM model name for extraction (e.g., llama3.2:8b)
        embedding_model: Embedding model name (e.g., bge-m3)
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
    """

    working_dir: str
    llm_model: str
    embedding_model: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str


@dataclass
class IngestionResult:
    """Result of document ingestion into the knowledge graph.

    Attributes:
        document_id: Unique identifier for the ingested document
        status: Ingestion status (success, error, skipped)
        chunks_processed: Number of chunks processed
        entities_created: Number of entities extracted and stored
        relations_created: Number of relations extracted and stored
        duration_ms: Total ingestion duration in milliseconds
        error: Error message if status is 'error'
    """

    document_id: str
    status: str
    chunks_processed: int = 0
    entities_created: int = 0
    relations_created: int = 0
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class ExtractionStats:
    """Statistics from entity/relation extraction.

    Attributes:
        total_chunks: Total number of chunks processed
        total_entities: Total entities extracted (before dedup)
        total_relations: Total relations extracted (before dedup)
        avg_entities_per_chunk: Average entities per chunk
        avg_relations_per_chunk: Average relations per chunk
        extraction_time_seconds: Total extraction time
        entity_types: Distribution of entity types
        relation_types: Distribution of relation types
    """

    total_chunks: int = 0
    total_entities: int = 0
    total_relations: int = 0
    avg_entities_per_chunk: float = 0.0
    avg_relations_per_chunk: float = 0.0
    extraction_time_seconds: float = 0.0
    entity_types: dict[str, int] = field(default_factory=dict)
    relation_types: dict[str, int] = field(default_factory=dict)


@dataclass
class ChunkMetadata:
    """Metadata for a document chunk.

    Attributes:
        chunk_id: Unique identifier (compatible with Qdrant UUID format)
        text: Chunk text content
        document_id: Source document ID
        chunk_index: Position within the document
        tokens: Token count
        start_token: Start position in original document
        end_token: End position in original document
    """

    chunk_id: str
    text: str
    document_id: str
    chunk_index: int
    tokens: int
    start_token: int = 0
    end_token: int = 0


@dataclass
class EntityData:
    """Entity data in LightRAG format.

    Attributes:
        entity_name: Entity display name
        entity_id: Unique identifier (usually same as entity_name)
        entity_type: Type classification (PERSON, ORGANIZATION, etc.)
        description: Entity description
        source_id: Source chunk ID for provenance
        file_path: Source document path
        chunk_index: Source chunk index
    """

    entity_name: str
    entity_id: str
    entity_type: str
    description: str = ""
    source_id: str = ""
    file_path: str = ""
    chunk_index: int | None = None


@dataclass
class RelationData:
    """Relation data in LightRAG format.

    Attributes:
        src_id: Source entity ID
        tgt_id: Target entity ID
        description: Relationship description
        keywords: Relationship type/keywords
        weight: Relationship strength (0.0-1.0)
        source_id: Source chunk ID for provenance
        file_path: Source document path
    """

    src_id: str
    tgt_id: str
    description: str = ""
    keywords: str = "RELATED_TO"
    weight: float = 1.0
    source_id: str = ""
    file_path: str = ""


__all__ = [
    "QueryMode",
    "LightRAGConfig",
    "IngestionResult",
    "ExtractionStats",
    "ChunkMetadata",
    "EntityData",
    "RelationData",
]
