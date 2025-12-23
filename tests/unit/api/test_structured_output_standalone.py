"""Standalone tests for structured output formatting.

Sprint 63 Feature 63.4: Structured Output Formatting (5 SP)

These tests run without loading the full app to avoid import issues.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.api.models.structured_output import (
    ResponseMetadata,
    SectionMetadata,
    StructuredChatResponse,
    StructuredResearchResponse,
    StructuredSource,
)
from src.api.services.response_formatter import (
    format_chat_response_structured,
    format_research_response_structured,
)


def test_section_metadata():
    """Test SectionMetadata model."""
    section = SectionMetadata(
        section_headings=["Chapter 1", "Section 1.1"],
        section_pages=[1, 2],
        primary_section="Chapter 1",
    )
    assert section.section_headings == ["Chapter 1", "Section 1.1"]
    print("✓ SectionMetadata test passed")


def test_structured_source():
    """Test StructuredSource model."""
    source = StructuredSource(
        text="Sample text",
        score=0.92,
        document_id="doc_123",
        chunk_id="chunk_456",
        source="docs/test.md",
        title="Test",
        entities=["Entity1"],
        relationships=["related_to"],
        metadata={},
    )
    assert source.score == 0.92
    assert source.document_id == "doc_123"
    print("✓ StructuredSource test passed")


def test_response_metadata():
    """Test ResponseMetadata model."""
    metadata = ResponseMetadata(
        latency_ms=245.3,
        search_type="hybrid",
        reranking_used=True,
        graph_used=True,
        total_sources=10,
    )
    assert metadata.latency_ms == 245.3
    assert metadata.search_type == "hybrid"
    assert "T" in metadata.timestamp
    print("✓ ResponseMetadata test passed")


def test_structured_chat_response():
    """Test StructuredChatResponse model."""
    response = StructuredChatResponse(
        query="What is AegisRAG?",
        answer="AegisRAG is...",
        sources=[
            StructuredSource(
                text="Source",
                score=0.9,
                document_id="doc1",
                chunk_id="chunk1",
            )
        ],
        metadata=ResponseMetadata(
            latency_ms=200.0,
            search_type="vector",
            reranking_used=False,
            graph_used=False,
            total_sources=1,
        ),
        followup_questions=["Q1", "Q2"],
    )
    assert response.query == "What is AegisRAG?"
    assert len(response.sources) == 1
    assert len(response.followup_questions) == 2
    print("✓ StructuredChatResponse test passed")


def test_format_chat_response():
    """Test chat response formatting."""
    sources = [
        {
            "text": "Sample",
            "score": 0.9,
            "source": "test.md",
            "metadata": {"document_id": "doc1", "chunk_id": "chunk1"},
        }
    ]

    response = format_chat_response_structured(
        query="Test query",
        answer="Test answer",
        sources=sources,
        metadata={"intent": "vector", "latency_seconds": 0.2},
        session_id="session-123",
    )

    assert isinstance(response, StructuredChatResponse)
    assert response.query == "Test query"
    assert len(response.sources) == 1
    assert response.metadata.latency_ms == 200.0
    print("✓ format_chat_response_structured test passed")


def test_format_with_sections():
    """Test formatting with section metadata."""
    sources = [
        {
            "text": "Content",
            "score": 0.92,
            "source": "guide.md",
            "metadata": {
                "section_headings": ["Installation"],
                "section_pages": [1],
                "primary_section": "Installation",
                "entities": ["Docker"],
            },
        }
    ]

    response = format_chat_response_structured(
        query="How to install?",
        answer="Installation steps...",
        sources=sources,
        metadata={"intent": "hybrid"},
    )

    source = response.sources[0]
    assert source.section is not None
    assert source.section.primary_section == "Installation"
    assert "Docker" in source.entities
    print("✓ Section metadata formatting test passed")


def test_latency_calculation():
    """Test latency calculation."""
    start_time = time.time()
    time.sleep(0.01)  # 10ms

    response = format_chat_response_structured(
        query="Test",
        answer="Answer",
        sources=[],
        metadata={},
        start_time=start_time,
    )

    assert response.metadata.latency_ms >= 10.0
    assert response.metadata.latency_ms < 100.0
    print("✓ Latency calculation test passed")


def test_graph_detection():
    """Test graph usage detection."""
    # Hybrid should set graph_used=True
    response = format_chat_response_structured(
        query="Test",
        answer="Answer",
        sources=[],
        metadata={"intent": "hybrid"},
    )
    assert response.metadata.graph_used is True

    # Vector should set graph_used=False
    response = format_chat_response_structured(
        query="Test",
        answer="Answer",
        sources=[],
        metadata={"intent": "vector"},
    )
    assert response.metadata.graph_used is False
    print("✓ Graph detection test passed")


def test_format_research_response():
    """Test research response formatting."""
    sources = [
        {
            "text": "Research source",
            "score": 0.85,
            "source": "research.md",
            "metadata": {},
        }
    ]

    response = format_research_response_structured(
        query="Research question",
        synthesis="Synthesis...",
        sources=sources,
        research_plan=["query1", "query2"],
        iterations=2,
        quality_metrics={"coverage": 0.85},
    )

    assert isinstance(response, StructuredResearchResponse)
    assert len(response.research_plan) == 2
    assert response.iterations == 2
    assert response.quality_metrics["coverage"] == 0.85
    print("✓ format_research_response_structured test passed")


def test_performance():
    """Test formatting performance (<1ms overhead)."""
    sources = [
        {
            "text": f"Source {i}",
            "score": 0.9 - i * 0.1,
            "source": f"file{i}.md",
            "metadata": {"document_id": f"doc{i}"},
        }
        for i in range(5)
    ]

    start = time.time()
    response = format_chat_response_structured(
        query="Test query",
        answer="Answer",
        sources=sources,
        metadata={"intent": "hybrid"},
        followup_questions=["Q1", "Q2"],
    )
    elapsed_ms = (time.time() - start) * 1000

    assert elapsed_ms < 1.0, f"Formatting took {elapsed_ms:.2f}ms (> 1ms)"
    assert len(response.sources) == 5
    print(f"✓ Performance test passed ({elapsed_ms:.3f}ms < 1ms)")


def test_serialization():
    """Test model serialization to JSON."""
    response = StructuredChatResponse(
        query="Test",
        answer="Answer",
        sources=[
            StructuredSource(
                text="Source",
                score=0.9,
                document_id="doc1",
                chunk_id="chunk1",
            )
        ],
        metadata=ResponseMetadata(
            latency_ms=200.0,
            search_type="vector",
            reranking_used=False,
            graph_used=False,
            total_sources=1,
        ),
        followup_questions=[],
    )

    # Serialize to dict
    data = response.model_dump()
    assert isinstance(data, dict)
    assert data["query"] == "Test"

    # Serialize to JSON
    json_str = response.model_dump_json()
    assert isinstance(json_str, str)
    assert "Test" in json_str
    print("✓ Serialization test passed")


def test_empty_sources():
    """Test empty sources handling."""
    response = format_chat_response_structured(
        query="Test",
        answer="Answer",
        sources=[],
        metadata={"intent": "vector"},
    )
    assert len(response.sources) == 0
    assert response.metadata.total_sources == 0
    print("✓ Empty sources test passed")


def test_missing_metadata():
    """Test missing metadata fields."""
    response = format_chat_response_structured(
        query="Test",
        answer="Answer",
        sources=[],
        metadata={},  # Empty
    )
    assert response.metadata.search_type == "unknown"
    assert response.metadata.graph_used is False
    print("✓ Missing metadata test passed")


if __name__ == "__main__":
    print("Running standalone structured output tests...")
    print()

    test_section_metadata()
    test_structured_source()
    test_response_metadata()
    test_structured_chat_response()
    test_format_chat_response()
    test_format_with_sections()
    test_latency_calculation()
    test_graph_detection()
    test_format_research_response()
    test_performance()
    test_serialization()
    test_empty_sources()
    test_missing_metadata()

    print()
    print("=" * 60)
    print("ALL TESTS PASSED! ✓")
    print("=" * 60)
