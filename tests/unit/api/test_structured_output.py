"""Unit tests for structured output formatting.

Sprint 63 Feature 63.4: Structured Output Formatting (5 SP)

Tests cover:
- Response format parameter validation
- Natural format (default)
- Structured format transformation
- Source metadata extraction
- Performance (<1ms overhead)
"""

import time
from datetime import UTC, datetime

import pytest

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


class TestStructuredOutputModels:
    """Test structured output Pydantic models."""

    def test_section_metadata_creation(self):
        """Test SectionMetadata model."""
        section = SectionMetadata(
            section_headings=["Chapter 1", "Section 1.1"],
            section_pages=[1, 2],
            primary_section="Chapter 1",
        )

        assert section.section_headings == ["Chapter 1", "Section 1.1"]
        assert section.section_pages == [1, 2]
        assert section.primary_section == "Chapter 1"

    def test_structured_source_creation(self):
        """Test StructuredSource model."""
        source = StructuredSource(
            text="Sample text content",
            score=0.92,
            document_id="doc_123",
            chunk_id="chunk_456",
            source="docs/test.md",
            title="Test Document",
            section=SectionMetadata(
                section_headings=["Introduction"],
                section_pages=[1],
                primary_section="Introduction",
            ),
            entities=["Entity1", "Entity2"],
            relationships=["related_to"],
            metadata={"key": "value"},
        )

        assert source.text == "Sample text content"
        assert source.score == 0.92
        assert source.document_id == "doc_123"
        assert source.chunk_id == "chunk_456"
        assert source.section is not None
        assert source.section.primary_section == "Introduction"
        assert len(source.entities) == 2
        assert len(source.relationships) == 1

    def test_response_metadata_creation(self):
        """Test ResponseMetadata model."""
        metadata = ResponseMetadata(
            latency_ms=245.3,
            search_type="hybrid",
            reranking_used=True,
            graph_used=True,
            total_sources=10,
            session_id="session-123",
            agent_path=["router", "vector_agent"],
        )

        assert metadata.latency_ms == 245.3
        assert metadata.search_type == "hybrid"
        assert metadata.reranking_used is True
        assert metadata.graph_used is True
        assert metadata.total_sources == 10
        assert metadata.session_id == "session-123"
        assert len(metadata.agent_path) == 2

        # Timestamp should be valid ISO 8601
        assert "T" in metadata.timestamp
        assert "Z" in metadata.timestamp or "+" in metadata.timestamp

    def test_structured_chat_response_creation(self):
        """Test StructuredChatResponse model."""
        response = StructuredChatResponse(
            query="What is AegisRAG?",
            answer="AegisRAG is...",
            sources=[
                StructuredSource(
                    text="Source text",
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
            followup_questions=["Question 1", "Question 2"],
        )

        assert response.query == "What is AegisRAG?"
        assert response.answer == "AegisRAG is..."
        assert len(response.sources) == 1
        assert len(response.followup_questions) == 2
        assert response.metadata.search_type == "vector"

    def test_structured_research_response_creation(self):
        """Test StructuredResearchResponse model."""
        response = StructuredResearchResponse(
            query="How does hybrid search work?",
            synthesis="Hybrid search combines...",
            sources=[
                StructuredSource(
                    text="Source text",
                    score=0.85,
                    document_id="doc2",
                    chunk_id="chunk2",
                )
            ],
            metadata=ResponseMetadata(
                latency_ms=1500.0,
                search_type="research",
                reranking_used=True,
                graph_used=True,
                total_sources=5,
            ),
            research_plan=["query1", "query2"],
            iterations=2,
            quality_metrics={"coverage": 0.85},
        )

        assert response.query == "How does hybrid search work?"
        assert response.synthesis == "Hybrid search combines..."
        assert len(response.sources) == 1
        assert len(response.research_plan) == 2
        assert response.iterations == 2
        assert response.quality_metrics["coverage"] == 0.85


class TestResponseFormatter:
    """Test response formatter service."""

    def test_format_chat_response_basic(self):
        """Test basic chat response formatting."""
        sources = [
            {
                "text": "Sample text",
                "score": 0.9,
                "source": "docs/test.md",
                "title": "Test Doc",
                "metadata": {
                    "document_id": "doc1",
                    "chunk_id": "chunk1",
                },
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
        assert response.answer == "Test answer"
        assert len(response.sources) == 1
        assert response.sources[0].score == 0.9
        assert response.metadata.search_type == "vector"
        assert response.metadata.session_id == "session-123"
        assert response.metadata.latency_ms == pytest.approx(200.0, rel=0.1)

    def test_format_chat_response_with_sections(self):
        """Test chat response formatting with section metadata."""
        sources = [
            {
                "text": "Content with sections",
                "score": 0.92,
                "source": "docs/guide.md",
                "title": "Guide - Section: 'Installation'",
                "metadata": {
                    "section_headings": ["Installation", "Prerequisites"],
                    "section_pages": [1],
                    "primary_section": "Installation",
                    "entities": ["Docker", "Python"],
                    "relationships": ["requires"],
                },
            }
        ]

        response = format_chat_response_structured(
            query="How to install?",
            answer="Installation steps...",
            sources=sources,
            metadata={"intent": "hybrid", "latency_seconds": 0.3},
        )

        assert len(response.sources) == 1
        source = response.sources[0]
        assert source.section is not None
        assert source.section.primary_section == "Installation"
        assert len(source.section.section_headings) == 2
        assert len(source.entities) == 2
        assert "Docker" in source.entities

    def test_format_chat_response_with_followup_questions(self):
        """Test chat response with follow-up questions."""
        response = format_chat_response_structured(
            query="What is RAG?",
            answer="RAG stands for...",
            sources=[],
            metadata={"intent": "vector"},
            followup_questions=[
                "How does RAG work?",
                "What are RAG use cases?",
            ],
        )

        assert len(response.followup_questions) == 2
        assert "How does RAG work?" in response.followup_questions

    def test_format_chat_response_latency_calculation(self):
        """Test latency calculation from start_time."""
        start_time = time.time()
        time.sleep(0.01)  # Simulate 10ms processing

        response = format_chat_response_structured(
            query="Test",
            answer="Answer",
            sources=[],
            metadata={},
            start_time=start_time,
        )

        # Should be at least 10ms
        assert response.metadata.latency_ms >= 10.0
        # Should be less than 100ms (generous upper bound)
        assert response.metadata.latency_ms < 100.0

    def test_format_chat_response_graph_detection(self):
        """Test graph usage detection from intent."""
        # Hybrid intent should set graph_used=True
        response = format_chat_response_structured(
            query="Test",
            answer="Answer",
            sources=[],
            metadata={"intent": "hybrid"},
        )
        assert response.metadata.graph_used is True

        # Graph intent should set graph_used=True
        response = format_chat_response_structured(
            query="Test",
            answer="Answer",
            sources=[],
            metadata={"intent": "graph"},
        )
        assert response.metadata.graph_used is True

        # Vector intent should set graph_used=False
        response = format_chat_response_structured(
            query="Test",
            answer="Answer",
            sources=[],
            metadata={"intent": "vector"},
        )
        assert response.metadata.graph_used is False

    def test_format_research_response_basic(self):
        """Test basic research response formatting."""
        sources = [
            {
                "text": "Research source",
                "score": 0.85,
                "source": "docs/research.md",
                "metadata": {},
            }
        ]

        response = format_research_response_structured(
            query="Research question",
            synthesis="Research synthesis...",
            sources=sources,
            research_plan=["query1", "query2"],
            iterations=2,
            quality_metrics={"coverage": 0.85, "coherence": 0.92},
        )

        assert isinstance(response, StructuredResearchResponse)
        assert response.query == "Research question"
        assert response.synthesis == "Research synthesis..."
        assert len(response.sources) == 1
        assert len(response.research_plan) == 2
        assert response.iterations == 2
        assert response.quality_metrics["coverage"] == 0.85
        assert response.metadata.search_type == "research"
        assert response.metadata.graph_used is True
        assert response.metadata.reranking_used is True

    def test_format_research_response_with_latency(self):
        """Test research response latency calculation."""
        start_time = time.time()
        time.sleep(0.02)  # Simulate 20ms processing

        response = format_research_response_structured(
            query="Test",
            synthesis="Synthesis",
            sources=[],
            research_plan=[],
            iterations=1,
            quality_metrics={},
            start_time=start_time,
        )

        assert response.metadata.latency_ms >= 20.0
        assert response.metadata.latency_ms < 100.0

    def test_structured_source_from_pydantic_model(self):
        """Test source conversion from Pydantic model."""
        from src.api.v1.chat import SourceDocument

        # Create Pydantic model source
        pydantic_source = SourceDocument(
            text="Test text",
            score=0.88,
            source="docs/test.md",
            title="Test",
            metadata={
                "document_id": "doc123",
                "entities": ["Entity1"],
            },
        )

        response = format_chat_response_structured(
            query="Test",
            answer="Answer",
            sources=[pydantic_source],
            metadata={},
        )

        assert len(response.sources) == 1
        assert response.sources[0].text == "Test text"
        assert response.sources[0].score == 0.88
        assert response.sources[0].document_id == "doc123"

    def test_performance_overhead(self):
        """Test that structured formatting adds <1ms overhead."""
        # Create typical response with 5 sources
        sources = [
            {
                "text": f"Source {i} text content",
                "score": 0.9 - i * 0.1,
                "source": f"docs/file{i}.md",
                "metadata": {
                    "document_id": f"doc{i}",
                    "chunk_id": f"chunk{i}",
                    "entities": [f"Entity{i}"],
                },
            }
            for i in range(5)
        ]

        # Measure formatting time
        start = time.time()
        response = format_chat_response_structured(
            query="Test query with multiple sources",
            answer="Detailed answer with multiple citations",
            sources=sources,
            metadata={"intent": "hybrid", "latency_seconds": 0.25},
            session_id="session-123",
            followup_questions=["Q1", "Q2", "Q3"],
        )
        elapsed_ms = (time.time() - start) * 1000

        # Formatting should take less than 1ms
        assert elapsed_ms < 1.0, f"Formatting took {elapsed_ms:.2f}ms (> 1ms threshold)"

        # Verify response is complete
        assert len(response.sources) == 5
        assert len(response.followup_questions) == 3

    def test_empty_sources_handling(self):
        """Test handling of empty sources list."""
        response = format_chat_response_structured(
            query="Test",
            answer="Answer without sources",
            sources=[],
            metadata={"intent": "vector"},
        )

        assert len(response.sources) == 0
        assert response.metadata.total_sources == 0

    def test_missing_metadata_fields(self):
        """Test handling of missing metadata fields."""
        response = format_chat_response_structured(
            query="Test",
            answer="Answer",
            sources=[],
            metadata={},  # Empty metadata
        )

        assert response.metadata.search_type == "unknown"
        assert response.metadata.graph_used is False
        assert response.metadata.reranking_used is False
        assert len(response.metadata.agent_path) == 0

    def test_agent_path_extraction(self):
        """Test agent path extraction from metadata."""
        response = format_chat_response_structured(
            query="Test",
            answer="Answer",
            sources=[],
            metadata={
                "agent_path": ["router", "vector_agent", "generator"],
            },
        )

        assert len(response.metadata.agent_path) == 3
        assert response.metadata.agent_path[0] == "router"
        assert response.metadata.agent_path[-1] == "generator"


class TestResponseFormatValidation:
    """Test response format parameter validation."""

    def test_valid_natural_format(self):
        """Test valid 'natural' format."""
        from src.api.v1.chat import ChatRequest

        request = ChatRequest(
            query="Test query",
            response_format="natural",
        )
        assert request.response_format == "natural"

    def test_valid_structured_format(self):
        """Test valid 'structured' format."""
        from src.api.v1.chat import ChatRequest

        request = ChatRequest(
            query="Test query",
            response_format="structured",
        )
        assert request.response_format == "structured"

    def test_invalid_format_rejected(self):
        """Test invalid format is rejected."""
        from pydantic import ValidationError

        from src.api.v1.chat import ChatRequest

        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(
                query="Test query",
                response_format="invalid_format",
            )

        assert "response_format" in str(exc_info.value)

    def test_default_format_is_natural(self):
        """Test default response format is 'natural'."""
        from src.api.v1.chat import ChatRequest

        request = ChatRequest(query="Test query")
        assert request.response_format == "natural"


class TestModelSerialization:
    """Test model serialization to JSON."""

    def test_structured_chat_response_serialization(self):
        """Test StructuredChatResponse serializes to valid JSON."""
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
            followup_questions=["Q1"],
        )

        # Serialize to dict
        data = response.model_dump()
        assert isinstance(data, dict)
        assert data["query"] == "Test"
        assert data["answer"] == "Answer"
        assert len(data["sources"]) == 1
        assert data["metadata"]["latency_ms"] == 200.0

        # Serialize to JSON string
        json_str = response.model_dump_json()
        assert isinstance(json_str, str)
        assert "Test" in json_str
        assert "Answer" in json_str

    def test_structured_research_response_serialization(self):
        """Test StructuredResearchResponse serializes to valid JSON."""
        response = StructuredResearchResponse(
            query="Research query",
            synthesis="Synthesis",
            sources=[],
            metadata=ResponseMetadata(
                latency_ms=1500.0,
                search_type="research",
                reranking_used=True,
                graph_used=True,
                total_sources=0,
            ),
            research_plan=["query1"],
            iterations=1,
            quality_metrics={"coverage": 0.85},
        )

        data = response.model_dump()
        assert isinstance(data, dict)
        assert data["query"] == "Research query"
        assert data["synthesis"] == "Synthesis"
        assert data["iterations"] == 1
        assert data["quality_metrics"]["coverage"] == 0.85
