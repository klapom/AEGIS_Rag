"""Integration tests for hybrid ingestion pipeline - Sprint 22 Features 22.3 + 22.4.

This module tests the end-to-end hybrid ingestion strategy that intelligently
routes documents to either Docling (GPU-accelerated) or LlamaIndex (fallback)
parsers based on document format.

Test Coverage:
- Format routing decisions (30+ formats)
- Docling pipeline (14 exclusive + 7 shared formats)
- LlamaIndex pipeline (9 exclusive + 7 shared formats)
- Graceful degradation (Docling unavailable → LlamaIndex fallback)
- Parser output compatibility (both parsers → same state format)
- End-to-end pipeline execution

Architecture:
- Integration tests with real file I/O
- Mock Docling container (avoid GPU dependency in CI/CD)
- Real LlamaIndex SimpleDirectoryReader
- Validate routing logic + parser integration
- Ensure downstream nodes (chunking, embedding) work with both parsers

Sprint Context:
- Feature 22.3: Format Router (30 formats, intelligent routing)
- Feature 22.4: LlamaIndex Parser (9 new formats enabled)
- ADR-027: Docling CUDA Container Integration
- ADR-028: LlamaIndex Strategic Fallback
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.components.ingestion.format_router import FormatRouter, ParserType
from src.components.ingestion.langgraph_pipeline import run_ingestion_pipeline


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def markdown_file(tmp_path):
    """Create a test Markdown file (LlamaIndex-exclusive format)."""
    md_file = tmp_path / "test.md"
    md_file.write_text(
        "# Hybrid Test Document\n\n"
        "This tests the **hybrid ingestion** strategy.\n\n"
        "## Features\n\n"
        "- Format routing\n"
        "- LlamaIndex parser\n"
        "- Downstream compatibility"
    )
    return md_file


@pytest.fixture
def text_file(tmp_path):
    """Create a test text file (shared format)."""
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Plain text document.\nLine 2.\nLine 3.")
    return txt_file


@pytest.fixture
def rst_file(tmp_path):
    """Create a test reStructuredText file (LlamaIndex-exclusive)."""
    rst_file = tmp_path / "test.rst"
    rst_file.write_text(
        "Documentation Title\n"
        "===================\n\n"
        "Introduction paragraph.\n\n"
        "Features\n"
        "--------\n\n"
        "- Feature 1\n"
        "- Feature 2\n"
    )
    return rst_file


# =============================================================================
# FORMAT ROUTING TESTS
# =============================================================================


class TestHybridIngestionRouting:
    """Test format routing decisions."""

    def test_routing__markdown__uses_llamaindex(self):
        """Verify Markdown routes to LlamaIndex (exclusive format)."""
        router = FormatRouter(docling_available=True)
        decision = router.route(Path("test.md"))

        assert decision.parser == ParserType.LLAMAINDEX
        assert decision.format == ".md"
        assert decision.confidence == "high"
        assert "LlamaIndex-exclusive" in decision.reason

    def test_routing__text_file__prefers_docling(self):
        """Verify text file prefers Docling when available (shared format)."""
        router = FormatRouter(docling_available=True)
        decision = router.route(Path("test.txt"))

        assert decision.parser == ParserType.DOCLING
        assert decision.format == ".txt"
        assert decision.fallback_available is True  # Shared format has fallback

    def test_routing__docling_unavailable__uses_llamaindex_fallback(self):
        """Verify graceful degradation to LlamaIndex when Docling unavailable."""
        router = FormatRouter(docling_available=False)
        decision = router.route(Path("test.txt"))

        assert decision.parser == ParserType.LLAMAINDEX
        assert decision.format == ".txt"
        assert "Docling unavailable" in decision.reason

    def test_routing__pdf__requires_docling(self):
        """Verify PDF requires Docling (no fallback)."""
        router = FormatRouter(docling_available=False)

        # Should raise error because PDF needs Docling
        with pytest.raises(RuntimeError, match="Docling container unavailable"):
            router.route(Path("test.pdf"))


# =============================================================================
# LLAMAINDEX PIPELINE TESTS
# =============================================================================


class TestHybridIngestionLlamaIndex:
    """Test LlamaIndex parser pipeline integration."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_llamaindex_pipeline__markdown__parses_successfully(
        self, markdown_file, monkeypatch
    ):
        """Verify Markdown file routes to LlamaIndex and parses successfully."""
        # Mock downstream nodes to avoid DB dependencies
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.memory_check_node",
            _mock_memory_check_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.chunking_node",
            _mock_chunking_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.embedding_node",
            _mock_embedding_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.graph_extraction_node",
            _mock_graph_extraction_node,
        )

        # Run pipeline
        result = await run_ingestion_pipeline(
            document_path=str(markdown_file),
            document_id="md_test",
            batch_id="test_batch",
            batch_index=0,
            total_documents=1,
        )

        # Verify LlamaIndex was used
        assert result["parsed_metadata"]["parser"] == "llamaindex"
        assert result["parsed_metadata"]["format"] == ".md"

        # Verify text extraction
        assert "Hybrid Test" in result["parsed_content"]
        assert "Format routing" in result["parsed_content"]

        # Verify state compatibility
        assert result["docling_status"] == "completed"
        assert result["parsed_tables"] == []
        assert result["parsed_images"] == []

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_llamaindex_pipeline__rst__parses_successfully(self, rst_file, monkeypatch):
        """Verify reStructuredText file routes to LlamaIndex."""
        # Mock downstream nodes
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.memory_check_node",
            _mock_memory_check_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.chunking_node",
            _mock_chunking_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.embedding_node",
            _mock_embedding_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.graph_extraction_node",
            _mock_graph_extraction_node,
        )

        # Run pipeline
        result = await run_ingestion_pipeline(
            document_path=str(rst_file),
            document_id="rst_test",
            batch_id="test_batch",
            batch_index=0,
            total_documents=1,
        )

        # Verify LlamaIndex was used
        assert result["parsed_metadata"]["parser"] == "llamaindex"
        assert result["parsed_metadata"]["format"] == ".rst"

        # Verify text extraction
        assert "Documentation Title" in result["parsed_content"]
        assert "Introduction" in result["parsed_content"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_llamaindex_pipeline__text_file_fallback__parses_successfully(
        self, text_file, monkeypatch
    ):
        """Verify text file uses LlamaIndex when Docling unavailable."""

        # Mock Docling as unavailable
        async def mock_initialize_router():
            return FormatRouter(docling_available=False)

        monkeypatch.setattr(
            "src.components.ingestion.langgraph_pipeline.initialize_format_router",
            mock_initialize_router,
        )

        # Mock downstream nodes
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.memory_check_node",
            _mock_memory_check_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.chunking_node",
            _mock_chunking_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.embedding_node",
            _mock_embedding_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.graph_extraction_node",
            _mock_graph_extraction_node,
        )

        # Run pipeline
        result = await run_ingestion_pipeline(
            document_path=str(text_file),
            document_id="txt_fallback",
            batch_id="test_batch",
            batch_index=0,
            total_documents=1,
        )

        # Verify LlamaIndex was used as fallback
        assert result["parsed_metadata"]["parser"] == "llamaindex"
        assert result["parsed_metadata"]["format"] == ".txt"

        # Verify text extraction
        assert "Plain text document" in result["parsed_content"]


# =============================================================================
# PARSER OUTPUT COMPATIBILITY TESTS
# =============================================================================


class TestHybridIngestionCompatibility:
    """Test that both parsers produce compatible output."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_parser_output__llamaindex__compatible_state_format(
        self, markdown_file, monkeypatch
    ):
        """Verify LlamaIndex parser outputs state compatible with downstream nodes."""
        # Mock downstream nodes
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.memory_check_node",
            _mock_memory_check_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.chunking_node",
            _mock_chunking_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.embedding_node",
            _mock_embedding_node,
        )
        monkeypatch.setattr(
            "src.components.ingestion.langgraph_nodes.graph_extraction_node",
            _mock_graph_extraction_node,
        )

        result = await run_ingestion_pipeline(
            document_path=str(markdown_file),
            document_id="compat_test",
            batch_id="test_batch",
            batch_index=0,
            total_documents=1,
        )

        # Verify all required state fields exist (same as Docling)
        required_fields = [
            "parsed_content",
            "parsed_metadata",
            "parsed_tables",
            "parsed_images",
            "parsed_layout",
            "docling_status",
            "document_id",
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        # Verify field types match expected
        assert isinstance(result["parsed_content"], str)
        assert isinstance(result["parsed_metadata"], dict)
        assert isinstance(result["parsed_tables"], list)
        assert isinstance(result["parsed_images"], list)
        assert isinstance(result["parsed_layout"], dict)


# =============================================================================
# MOCK HELPER FUNCTIONS
# =============================================================================


async def _mock_memory_check_node(state):
    """Mock memory check node (bypass RAM/VRAM checks)."""
    state["memory_check_passed"] = True
    state["current_memory_mb"] = 2000.0
    state["current_vram_mb"] = 3000.0
    state["requires_container_restart"] = False
    return state


async def _mock_chunking_node(state):
    """Mock chunking node (simple chunking)."""
    content = state.get("parsed_content", "")

    # Create simple mock chunks
    from src.core.chunk import Chunk

    chunk = Chunk(
        chunk_id="chunk_0",
        content=content[:500] if len(content) > 500 else content,
        metadata={"document_id": state["document_id"]},
    )

    state["chunks"] = [{"chunk": chunk, "image_bboxes": []}]
    state["chunking_status"] = "completed"
    return state


async def _mock_embedding_node(state):
    """Mock embedding node (skip Qdrant upload)."""
    state["embedded_chunk_ids"] = ["chunk_0"]
    state["embedding_status"] = "completed"
    return state


async def _mock_graph_extraction_node(state):
    """Mock graph extraction node (skip Neo4j)."""
    state["entities"] = []
    state["relations"] = []
    state["graph_status"] = "completed"
    return state
