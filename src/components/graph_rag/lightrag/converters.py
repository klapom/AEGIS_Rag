"""LightRAG format converters.

Sprint 55 Feature 55.5: Conversion utilities for LightRAG data.

This module provides functions to convert between different data formats:
- Chunk text to LightRAG chunk format
- Extracted entities to LightRAG entity format
- Extracted relations to LightRAG relation format
"""

import hashlib
from typing import Any

import structlog
import tiktoken

logger = structlog.get_logger(__name__)


def chunk_text_with_metadata(
    text: str,
    document_id: str,
    chunk_token_size: int = 600,
    chunk_overlap_token_size: int = 100,
) -> list[dict[str, Any]]:
    """Chunk text using tiktoken-based chunking.

    Sprint 16 Feature 16.1: Uses tiktoken-based chunking for LightRAG compatibility.
    Note: Production ingestion uses adaptive_chunking.py (Sprint 121 TD-054).

    Args:
        text: Document text to chunk
        document_id: Source document ID for provenance tracking
        chunk_token_size: Target chunk size in tokens (default: 600)
        chunk_overlap_token_size: Overlap between chunks (default: 100)

    Returns:
        List of chunk dictionaries compatible with LightRAG format
    """
    logger.info(
        "chunking_text_with_tiktoken",
        document_id=document_id,
        text_length=len(text),
        chunk_token_size=chunk_token_size,
        chunk_overlap=chunk_overlap_token_size,
    )

    # Get tiktoken encoding
    try:
        encoding = tiktoken.encoding_for_model("gpt-4")
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens = encoding.encode(text)
    chunks = []

    # Simple token-based chunking with overlap
    start = 0
    chunk_idx = 0
    while start < len(tokens):
        end = min(start + chunk_token_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)

        # Generate chunk_id compatible with Qdrant
        chunk_hash = hashlib.md5(
            f"{document_id}:{chunk_idx}:{chunk_text[:100]}".encode()
        ).hexdigest()[:8]
        chunk_id = f"{document_id[:8]}-chunk-{chunk_idx}-{chunk_hash}"

        chunks.append(
            {
                "chunk_id": chunk_id,
                "text": chunk_text,
                "content": chunk_text,  # Alias for compatibility
                "tokens": len(chunk_tokens),
                "token_count": len(chunk_tokens),  # Alias for compatibility
                "document_id": document_id,
                "chunk_index": chunk_idx,
                "start_token": start,
                "end_token": end,
            }
        )

        chunk_idx += 1
        start = end - chunk_overlap_token_size if end < len(tokens) else end

    logger.info(
        "chunking_complete",
        document_id=document_id,
        total_chunks=len(chunks),
    )

    return chunks


def convert_chunks_to_lightrag_format(
    chunks: list[dict[str, Any]],
    document_id: str,
) -> list[dict[str, Any]]:
    """Convert chunks to LightRAG ainsert_custom_kg format.

    Sprint 30 FIX: Converts chunks to format expected by LightRAG's ainsert_custom_kg()
    to populate chunk_to_source_map and prevent UNKNOWN source_id warnings.

    LightRAG expects:
    {
        "content": str,      # Chunk text
        "source_id": str,    # Unique identifier (KEY in chunk_to_source_map)
        "file_path": str,    # Document provenance
    }

    Args:
        chunks: List of chunk dictionaries
        document_id: Document ID for file_path

    Returns:
        List of chunks in LightRAG ainsert_custom_kg format
    """
    logger.info("converting_chunks_to_lightrag", count=len(chunks), document_id=document_id)

    lightrag_chunks = []
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id", f"chunk_{chunk.get('chunk_index', 0)}")
        lightrag_chunk = {
            "content": chunk.get("text", ""),
            "source_id": chunk_id,
            "file_path": document_id,
        }
        lightrag_chunks.append(lightrag_chunk)

    logger.info(
        "chunks_converted",
        original_count=len(chunks),
        converted_count=len(lightrag_chunks),
    )

    return lightrag_chunks


def convert_entities_to_lightrag_format(
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert extracted entities to LightRAG format.

    Sprint 14 Feature 14.1 - Phase 3: Entity Format Conversion
    Sprint 32 FIX: Handle both "name" and "entity_name" keys

    Input formats (both supported):
    - Three-Phase: {"name": "...", "type": "..."}
    - LLMExtractionPipeline: {"entity_name": "...", "entity_type": "..."}

    LightRAG Format:
    {
        "entity_name": "Entity Name",
        "entity_id": "Entity Name",
        "entity_type": "PERSON",
        "description": "...",
        "source_id": "abc123...",
        "file_path": "docs/file.md"
    }

    Args:
        entities: List of entities from extraction pipeline

    Returns:
        List of entities in LightRAG format
    """
    logger.info("converting_entities_to_lightrag", count=len(entities))

    lightrag_entities = []
    for entity in entities:
        # Handle both "name" and "entity_name" keys
        entity_name = entity.get("name", entity.get("entity_name", "UNKNOWN"))

        # Sprint 30: Ensure source_id is never empty
        chunk_id = entity.get("chunk_id", "")
        document_id = entity.get("document_id", "")
        source_id = chunk_id if chunk_id else document_id

        if not source_id or source_id == "UNKNOWN":
            logger.warning(
                "entity_missing_source_id",
                entity_name=entity_name,
                chunk_id=chunk_id,
                document_id=document_id,
            )

        # Handle both "type" and "entity_type" keys
        entity_type = entity.get("type", entity.get("entity_type", "UNKNOWN"))

        lightrag_entity = {
            "entity_name": entity_name,
            "entity_id": entity_name,
            "entity_type": entity_type,
            "description": entity.get("description", ""),
            "source_id": source_id,
            "file_path": document_id,
            "chunk_index": entity.get("chunk_index"),
            "start_token": entity.get("start_token"),
            "end_token": entity.get("end_token"),
        }
        lightrag_entities.append(lightrag_entity)

    logger.info(
        "entities_converted",
        original_count=len(entities),
        converted_count=len(lightrag_entities),
    )

    return lightrag_entities


def convert_relations_to_lightrag_format(
    relations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert extracted relations to LightRAG format.

    Sprint 14 Feature 14.1 - Phase 4: Relation Format Conversion

    Input Format:
    {
        "source": "Entity A",
        "target": "Entity B",
        "type": "WORKS_WITH",
        "description": "...",
        "confidence": 0.95,
        "chunk_id": "abc123...",
        "document_id": "docs/file.md"
    }

    LightRAG Format:
    {
        "src_id": "Entity A",
        "tgt_id": "Entity B",
        "description": "...",
        "keywords": "WORKS_WITH",
        "weight": 0.95,
        "source_id": "abc123...",
        "file_path": "docs/file.md"
    }

    Args:
        relations: List of relations from extraction pipeline

    Returns:
        List of relations in LightRAG format
    """
    logger.info("converting_relations_to_lightrag", count=len(relations))

    lightrag_relations = []
    for relation in relations:
        # Sprint 125: Handle both old {source,target,type} and new S-P-O {subject,relation,object} formats
        rel_type = relation.get("type") or relation.get("relation_type") or relation.get("relation", "RELATED_TO")

        # Sprint 30: Ensure source_id is never empty
        chunk_id = relation.get("chunk_id", "")
        document_id = relation.get("document_id", "")
        source_id = chunk_id if chunk_id else document_id

        lightrag_relation = {
            "src_id": relation.get("source") or relation.get("subject", "UNKNOWN"),
            "tgt_id": relation.get("target") or relation.get("object", "UNKNOWN"),
            "description": relation.get("description", ""),
            "keywords": rel_type,
            "weight": relation.get("confidence", 1.0),
            "source_id": source_id,
            "file_path": document_id,
            "chunk_index": relation.get("chunk_index"),
            "start_token": relation.get("start_token"),
            "end_token": relation.get("end_token"),
        }
        lightrag_relations.append(lightrag_relation)

    logger.info(
        "relations_converted",
        original_count=len(relations),
        converted_count=len(lightrag_relations),
    )

    return lightrag_relations


__all__ = [
    "chunk_text_with_metadata",
    "convert_chunks_to_lightrag_format",
    "convert_entities_to_lightrag_format",
    "convert_relations_to_lightrag_format",
]
