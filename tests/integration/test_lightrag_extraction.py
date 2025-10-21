"""
Integration test for LightRAG entity extraction with llama3.2:3b.

Sprint 11 Feature 11.4: Verify that llama3.2:3b correctly extracts entities
and relationships, fixing the issue with qwen3:0.6b producing malformed JSON.
"""

import pytest

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async


@pytest.mark.asyncio
async def test_lightrag_entity_extraction_with_llama32():
    """Test that llama3.2:3b correctly extracts entities."""
    lightrag = await get_lightrag_wrapper_async()

    # Insert test document
    result = await lightrag.insert_documents([
        {
            "text": "AEGIS RAG is a multi-agent system. "
                    "It uses LangGraph for orchestration and Neo4j for knowledge graphs."
        }
    ])

    assert result["success"] > 0

    # Check graph statistics
    stats = await lightrag.get_stats()

    # Should extract at least 3 entities
    assert stats["entity_count"] >= 3
    # Should extract at least 2 relationships
    assert stats["relationship_count"] >= 2
