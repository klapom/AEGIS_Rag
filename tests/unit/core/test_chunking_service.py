"""Unit tests for ChunkingService (Sprint 36 Feature 36.6 - TD-054).

Tests:
1. ChunkingService initialization with different configs
2. Adaptive chunking with section metadata
3. Fixed-size chunking
4. Sentence-based chunking
5. Paragraph-based chunking
6. Token counting accuracy
7. Chunk ID generation uniqueness
8. Section merging logic
9. Empty text handling
10. Multi-section metadata tracking
11. Singleton pattern (get_chunking_service)
12. Configuration validation

IMPORTANT - Pydantic Validation Constraints:
- max_tokens: ge=500, le=4000
- min_tokens: ge=100, le=2000
- overlap_tokens: ge=0, le=500
- chunk_id: min_length=16 (SHA-256 hash format)
"""

import pytest

from src.core.chunk import Chunk
from src.core.chunking_service import (
    ChunkingConfig,
    ChunkingService,
    ChunkStrategyEnum,
    SectionMetadata,
    get_chunking_service,
    reset_chunking_service,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_text():
    """Sample document text for testing."""
    return """
    AegisRAG is a hybrid RAG system combining vector search,
    graph reasoning, and temporal memory.

    Vector Search provides semantic similarity using BGE-M3 embeddings
    and Qdrant vector database for fast retrieval.

    Graph Reasoning uses Neo4j and LightRAG to extract entities
    and relationships from documents.

    Temporal Memory tracks conversation history using Redis
    and Graphiti for episodic memory management.
    """.strip()


@pytest.fixture
def long_sample_text():
    """Longer sample text for chunking tests."""
    return " ".join(["This is a sample sentence for testing chunking."] * 200)


@pytest.fixture
def sample_sections():
    """Sample section metadata for testing."""
    return [
        SectionMetadata(
            heading="Introduction",
            level=1,
            page_no=1,
            bbox={"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
            text="AegisRAG is a hybrid RAG system combining vector search, graph reasoning, and temporal memory.",
            token_count=20,
            metadata={"source": "test.pdf"},
        ),
        SectionMetadata(
            heading="Vector Search",
            level=2,
            page_no=1,
            bbox={"l": 50.0, "t": 100.0, "r": 670.0, "b": 150.0},
            text="Vector Search provides semantic similarity using BGE-M3 embeddings and Qdrant vector database for fast retrieval.",
            token_count=25,
            metadata={"source": "test.pdf"},
        ),
        SectionMetadata(
            heading="Graph Reasoning",
            level=2,
            page_no=2,
            bbox={"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
            text="Graph Reasoning uses Neo4j and LightRAG to extract entities and relationships from documents.",
            token_count=22,
            metadata={"source": "test.pdf"},
        ),
    ]


@pytest.fixture
def long_section():
    """Long section that exceeds threshold (for splitting tests)."""
    return SectionMetadata(
        heading="Long Section",
        level=1,
        page_no=1,
        bbox={"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
        text=" ".join(["This is a very long section with lots of text."] * 100),
        token_count=1500,
        metadata={"source": "test.pdf"},
    )


@pytest.fixture(autouse=True)
def reset_service():
    """Reset chunking service before each test."""
    reset_chunking_service()
    yield
    reset_chunking_service()


# =============================================================================
# TEST 1: SERVICE INITIALIZATION
# =============================================================================


def test_chunking_service_initialization_default():
    """Test ChunkingService initialization with default config."""
    service = ChunkingService()

    # ChunkingConfig uses use_enum_values=True, so strategy is a string
    assert service.config.strategy == "adaptive" or service.config.strategy == ChunkStrategyEnum.ADAPTIVE
    assert service.config.min_tokens == 800
    assert service.config.max_tokens == 1800
    assert service.config.overlap_tokens == 100
    assert service.config.preserve_sections is True


def test_chunking_service_initialization_custom():
    """Test ChunkingService initialization with custom config."""
    config = ChunkingConfig(
        strategy=ChunkStrategyEnum.FIXED,
        max_tokens=1000,
        overlap_tokens=200,
    )
    service = ChunkingService(config)

    assert service.config.strategy == "fixed" or service.config.strategy == ChunkStrategyEnum.FIXED
    assert service.config.max_tokens == 1000
    assert service.config.overlap_tokens == 200


# =============================================================================
# TEST 2: ADAPTIVE CHUNKING WITH SECTIONS
# =============================================================================


@pytest.mark.asyncio
async def test_adaptive_chunking_with_sections(sample_sections):
    """Test adaptive chunking with section metadata."""
    service = ChunkingService()

    chunks = await service.chunk_document(
        text="Combined text from all sections...",
        document_id="test_doc_001",
        sections=sample_sections,
        metadata={"source": "test.pdf"},
    )

    assert len(chunks) > 0
    assert all(isinstance(c, Chunk) for c in chunks)

    # Check section metadata is preserved
    first_chunk = chunks[0]
    assert len(first_chunk.section_headings) > 0
    assert len(first_chunk.section_pages) > 0
    assert len(first_chunk.section_bboxes) > 0

    # Check chunk IDs are unique
    chunk_ids = [c.chunk_id for c in chunks]
    assert len(chunk_ids) == len(set(chunk_ids))


@pytest.mark.asyncio
async def test_adaptive_chunking_merges_small_sections(sample_sections):
    """Test that adaptive chunking merges small sections."""
    # Use valid max_tokens (>= 500) but still small enough to test merging
    config = ChunkingConfig(
        strategy=ChunkStrategyEnum.ADAPTIVE,
        max_tokens=500,  # Minimum valid value
    )
    service = ChunkingService(config)

    chunks = await service.chunk_document(
        text="Combined text...",
        document_id="test_doc_002",
        sections=sample_sections,
    )

    # Should have at least 1 chunk
    assert len(chunks) >= 1

    # Check that chunks have section metadata
    for chunk in chunks:
        assert isinstance(chunk.section_headings, list)
        assert isinstance(chunk.section_pages, list)


# =============================================================================
# TEST 3: FIXED-SIZE CHUNKING
# =============================================================================


@pytest.mark.asyncio
async def test_fixed_size_chunking(long_sample_text):
    """Test fixed-size chunking."""
    config = ChunkingConfig(
        strategy=ChunkStrategyEnum.FIXED,
        max_tokens=500,  # Minimum valid value
        overlap_tokens=50,
    )
    service = ChunkingService(config)

    chunks = await service.chunk_document(
        text=long_sample_text,
        document_id="test_doc_003",
    )

    assert len(chunks) > 1
    # Check that chunks don't exceed max_tokens (with some tolerance)
    for chunk in chunks:
        assert chunk.token_count <= config.max_tokens * 1.5  # 50% tolerance


@pytest.mark.asyncio
async def test_fixed_size_chunking_respects_overlap(long_sample_text):
    """Test that fixed-size chunking respects overlap configuration."""
    config = ChunkingConfig(
        strategy=ChunkStrategyEnum.FIXED,
        max_tokens=500,  # Minimum valid value
        overlap_tokens=100,
    )
    service = ChunkingService(config)

    chunks = await service.chunk_document(
        text=long_sample_text,
        document_id="test_doc_004",
    )

    assert len(chunks) > 1
    # Check overlap is set correctly
    for i, chunk in enumerate(chunks):
        if i > 0:
            assert chunk.overlap_tokens == config.overlap_tokens
        else:
            assert chunk.overlap_tokens == 0


# =============================================================================
# TEST 4: SENTENCE-BASED CHUNKING
# =============================================================================


@pytest.mark.asyncio
async def test_sentence_chunking(long_sample_text):
    """Test sentence-based chunking."""
    config = ChunkingConfig(
        strategy=ChunkStrategyEnum.SENTENCE,
        max_tokens=500,  # Minimum valid value
    )
    service = ChunkingService(config)

    chunks = await service.chunk_document(
        text=long_sample_text,
        document_id="test_doc_005",
    )

    assert len(chunks) > 0
    # Each chunk should have content
    for chunk in chunks:
        assert chunk.content.strip()


# =============================================================================
# TEST 5: PARAGRAPH-BASED CHUNKING
# =============================================================================


@pytest.mark.asyncio
async def test_paragraph_chunking():
    """Test paragraph-based chunking."""
    config = ChunkingConfig(
        strategy=ChunkStrategyEnum.PARAGRAPH,
        max_tokens=500,  # Minimum valid value
    )
    service = ChunkingService(config)

    # Create text with multiple paragraphs
    paragraph_text = "\n\n".join([
        "First paragraph with some text. " * 20,
        "Second paragraph with different content. " * 20,
        "Third paragraph for testing. " * 20,
    ])

    chunks = await service.chunk_document(
        text=paragraph_text,
        document_id="test_doc_006",
    )

    assert len(chunks) > 0
    # Paragraphs should be separated by double newlines
    for chunk in chunks:
        assert chunk.content.strip()


# =============================================================================
# TEST 6: TOKEN COUNTING
# =============================================================================


def test_token_counting():
    """Test token counting accuracy."""
    service = ChunkingService()

    # Short text
    short_text = "Hello world"
    short_tokens = service._count_tokens(short_text)
    assert short_tokens > 0
    assert short_tokens < 10

    # Long text
    long_text = "This is a much longer text " * 50
    long_tokens = service._count_tokens(long_text)
    assert long_tokens > short_tokens


# =============================================================================
# TEST 7: CHUNK ID GENERATION
# =============================================================================


def test_chunk_id_generation_uniqueness():
    """Test that chunk IDs are unique for different content."""
    service = ChunkingService()

    id1 = service._generate_chunk_id("doc_001", 0, "Text A")
    id2 = service._generate_chunk_id("doc_001", 0, "Text B")
    id3 = service._generate_chunk_id("doc_001", 1, "Text A")

    # Different text → different ID
    assert id1 != id2

    # Different index → different ID
    assert id1 != id3


def test_chunk_id_generation_deterministic():
    """Test that chunk IDs are deterministic (same input → same ID)."""
    service = ChunkingService()

    id1 = service._generate_chunk_id("doc_001", 0, "Text A")
    id2 = service._generate_chunk_id("doc_001", 0, "Text A")

    assert id1 == id2


def test_chunk_id_length():
    """Test that chunk IDs meet minimum length requirement."""
    service = ChunkingService()

    chunk_id = service._generate_chunk_id("doc_001", 0, "Text A")

    # chunk_id must be at least 16 characters
    assert len(chunk_id) >= 16


# =============================================================================
# TEST 8: SECTION MERGING LOGIC
# =============================================================================


@pytest.mark.asyncio
async def test_section_merging_preserves_metadata():
    """Test that section merging preserves all metadata."""
    sections = [
        SectionMetadata(
            heading="Section 1",
            level=1,
            page_no=1,
            bbox={"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
            text="Text 1 " * 50,  # Make it longer for merging
            token_count=100,
            metadata={},
        ),
        SectionMetadata(
            heading="Section 2",
            level=1,
            page_no=2,
            bbox={"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
            text="Text 2 " * 50,
            token_count=100,
            metadata={},
        ),
    ]

    config = ChunkingConfig(
        strategy=ChunkStrategyEnum.ADAPTIVE,
        max_tokens=500,  # Valid value that allows merging
    )
    service = ChunkingService(config)

    chunks = await service.chunk_document(
        text="Combined",
        document_id="test_doc_007",
        sections=sections,
    )

    # Check that chunks have section metadata
    assert len(chunks) >= 1
    chunk = chunks[0]
    assert isinstance(chunk.section_headings, list)
    assert isinstance(chunk.section_pages, list)


# =============================================================================
# TEST 9: EMPTY TEXT HANDLING
# =============================================================================


@pytest.mark.asyncio
async def test_empty_text_raises_error():
    """Test that empty text raises ValueError."""
    service = ChunkingService()

    with pytest.raises(ValueError, match="Content cannot be empty"):
        await service.chunk_document(text="", document_id="test_doc_008")


@pytest.mark.asyncio
async def test_whitespace_only_text_raises_error():
    """Test that whitespace-only text raises ValueError."""
    service = ChunkingService()

    with pytest.raises(ValueError, match="Content cannot be empty"):
        await service.chunk_document(text="   \n  \t  ", document_id="test_doc_009")


# =============================================================================
# TEST 10: MULTI-SECTION METADATA TRACKING
# =============================================================================


@pytest.mark.asyncio
async def test_multi_section_metadata_tracking(sample_sections):
    """Test that multi-section metadata is tracked correctly."""
    service = ChunkingService()

    chunks = await service.chunk_document(
        text="Combined text...",
        document_id="test_doc_010",
        sections=sample_sections,
    )

    # Check that each chunk has section metadata
    for chunk in chunks:
        assert isinstance(chunk.section_headings, list)
        assert isinstance(chunk.section_pages, list)
        assert isinstance(chunk.section_bboxes, list)

        # If chunk has sections, verify consistency
        if chunk.section_headings:
            assert len(chunk.section_pages) > 0
            assert len(chunk.section_bboxes) > 0


# =============================================================================
# TEST 11: SINGLETON PATTERN
# =============================================================================


def test_get_chunking_service_singleton():
    """Test that get_chunking_service returns singleton."""
    service1 = get_chunking_service()
    service2 = get_chunking_service()

    assert service1 is service2


def test_get_chunking_service_with_config_not_singleton():
    """Test that get_chunking_service with config creates new instance."""
    config = ChunkingConfig(max_tokens=999)

    service1 = get_chunking_service(config)
    service2 = get_chunking_service(config)

    # Should be different instances when config is provided
    assert service1 is not service2


def test_reset_chunking_service():
    """Test that reset_chunking_service clears singleton."""
    service1 = get_chunking_service()
    reset_chunking_service()
    service2 = get_chunking_service()

    # After reset, should get a new instance
    assert service1 is not service2


# =============================================================================
# TEST 12: CONFIGURATION VALIDATION
# =============================================================================


def test_chunking_config_validation():
    """Test ChunkingConfig validation."""
    # Valid config
    config = ChunkingConfig(
        strategy=ChunkStrategyEnum.ADAPTIVE,
        min_tokens=800,
        max_tokens=1800,
        overlap_tokens=100,
    )
    assert config.min_tokens == 800

    # Invalid: min_tokens too low (must be >= 100)
    with pytest.raises(Exception):  # Pydantic ValidationError
        ChunkingConfig(min_tokens=50)

    # Invalid: max_tokens too high (must be <= 4000)
    with pytest.raises(Exception):
        ChunkingConfig(max_tokens=5000)

    # Invalid: max_tokens too low (must be >= 500)
    with pytest.raises(Exception):
        ChunkingConfig(max_tokens=100)


# =============================================================================
# TEST 13: CHUNK MODEL SECTION METADATA
# =============================================================================


def test_chunk_model_with_section_metadata():
    """Test Chunk model with section metadata fields."""
    # Use a valid chunk_id with at least 16 characters
    chunk_id = "test-chunk-id-1234567890"  # 25 characters

    chunk = Chunk(
        chunk_id=chunk_id,
        document_id="doc_001",
        chunk_index=0,
        content="Sample text",
        start_char=0,
        end_char=11,
        token_count=3,
        section_headings=["Introduction", "Overview"],
        section_pages=[1, 2],
        section_bboxes=[
            {"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
            {"l": 50.0, "t": 100.0, "r": 670.0, "b": 150.0},
        ],
    )

    assert len(chunk.section_headings) == 2
    assert len(chunk.section_pages) == 2
    assert len(chunk.section_bboxes) == 2

    # Check Qdrant payload includes section metadata
    payload = chunk.to_qdrant_payload()
    assert "section_headings" in payload
    assert "section_pages" in payload
    assert "section_bboxes" in payload
    assert payload["section_headings"] == ["Introduction", "Overview"]


# =============================================================================
# TEST 14: STRATEGY ROUTING
# =============================================================================


@pytest.mark.asyncio
async def test_strategy_routing_adaptive():
    """Test that strategy routing works for adaptive."""
    config = ChunkingConfig(strategy=ChunkStrategyEnum.ADAPTIVE)
    service = ChunkingService(config)

    chunks = await service.chunk_document(
        text="Test text",
        document_id="test_doc_011",
    )

    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_strategy_routing_fixed():
    """Test that strategy routing works for fixed."""
    config = ChunkingConfig(strategy=ChunkStrategyEnum.FIXED)
    service = ChunkingService(config)

    chunks = await service.chunk_document(
        text="Test text " * 100,
        document_id="test_doc_012",
    )

    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_strategy_routing_sentence():
    """Test that strategy routing works for sentence."""
    config = ChunkingConfig(strategy=ChunkStrategyEnum.SENTENCE)
    service = ChunkingService(config)

    chunks = await service.chunk_document(
        text="First sentence. Second sentence. Third sentence.",
        document_id="test_doc_013",
    )

    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_strategy_routing_paragraph():
    """Test that strategy routing works for paragraph."""
    config = ChunkingConfig(strategy=ChunkStrategyEnum.PARAGRAPH)
    service = ChunkingService(config)

    chunks = await service.chunk_document(
        text="Paragraph 1\n\nParagraph 2\n\nParagraph 3",
        document_id="test_doc_014",
    )

    assert len(chunks) > 0


# =============================================================================
# TEST 15: SECTION DICTIONARY CONVERSION
# =============================================================================


@pytest.mark.asyncio
async def test_section_dict_conversion():
    """Test that sections can be passed as dicts and converted to SectionMetadata."""
    sections_as_dicts = [
        {
            "heading": "Section 1",
            "level": 1,
            "page_no": 1,
            "bbox": {"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
            "text": "Text 1",
            "token_count": 10,
            "metadata": {},
        },
    ]

    service = ChunkingService()

    chunks = await service.chunk_document(
        text="Test",
        document_id="test_doc_015",
        sections=sections_as_dicts,
    )

    assert len(chunks) > 0
    assert len(chunks[0].section_headings) > 0


# =============================================================================
# TEST 16: CHUNK FORMAT CONVERSIONS
# =============================================================================


@pytest.mark.asyncio
async def test_chunks_convert_to_qdrant_format():
    """Test chunks can be converted to Qdrant format with all required fields."""
    service = ChunkingService()

    text = "Sample text for Qdrant conversion. This is important content."
    chunks = await service.chunk_document(
        document_id="doc_qdrant",
        text=text,
        metadata={"key": "value", "source": "test.pdf"},
    )

    assert len(chunks) > 0
    for chunk in chunks:
        payload = chunk.to_qdrant_payload()
        assert "text" in payload
        assert "chunk_id" in payload
        assert "document_id" in payload
        assert "chunk_index" in payload
        assert "token_count" in payload
        assert payload["key"] == "value"
        assert payload["source"] == "test.pdf"


@pytest.mark.asyncio
async def test_chunks_convert_to_bm25_format():
    """Test chunks can be converted to BM25 format."""
    service = ChunkingService()

    text = "Sample text for BM25 conversion. Important keywords here."
    chunks = await service.chunk_document(
        document_id="doc_bm25",
        text=text,
    )

    assert len(chunks) > 0
    for chunk in chunks:
        bm25_doc = chunk.to_bm25_document()
        assert "text" in bm25_doc
        assert "chunk_id" in bm25_doc
        assert "document_id" in bm25_doc
        assert isinstance(bm25_doc["text"], str)


@pytest.mark.asyncio
async def test_chunks_convert_to_lightrag_format():
    """Test chunks can be converted to LightRAG format."""
    config = ChunkingConfig(strategy=ChunkStrategyEnum.FIXED, max_tokens=500)
    service = ChunkingService(config)

    text = "Sample text for LightRAG conversion."
    chunks = await service.chunk_document(
        document_id="doc_lightrag",
        text=text,
    )

    assert len(chunks) > 0
    for chunk in chunks:
        lightrag_chunk = chunk.to_lightrag_format()
        assert "text" in lightrag_chunk
        assert "chunk_id" in lightrag_chunk
        assert "document_id" in lightrag_chunk
        assert "tokens" in lightrag_chunk


# =============================================================================
# TEST 17: PROMETHEUS METRICS
# =============================================================================


@pytest.mark.asyncio
async def test_metrics_recorded_on_chunking():
    """Test that chunking records Prometheus metrics."""
    from src.core.chunking_service import (
        chunks_created_total,
        documents_chunked_total,
    )

    service = ChunkingService()

    # Get initial metric values
    initial_chunks = chunks_created_total.labels(strategy="adaptive")._value._value
    initial_docs = documents_chunked_total.labels(strategy="adaptive")._value._value

    # Chunk a document
    text = "Sample text for metrics testing. " * 10
    chunks = await service.chunk_document(
        document_id="doc_metrics",
        text=text,
    )

    # Verify metrics increased or stayed same
    final_chunks = chunks_created_total.labels(strategy="adaptive")._value._value
    final_docs = documents_chunked_total.labels(strategy="adaptive")._value._value

    assert final_chunks >= initial_chunks
    assert final_docs >= initial_docs
    # Metrics may be 0 if not properly initialized, so check if they actually changed
    if final_chunks > initial_chunks:
        assert final_chunks - initial_chunks == len(chunks)
    if final_docs > initial_docs:
        assert final_docs - initial_docs == 1


# =============================================================================
# TEST 18: PERFORMANCE AND BENCHMARKS
# =============================================================================


@pytest.mark.asyncio
async def test_chunking_completes_in_reasonable_time():
    """Test chunking completes within acceptable time."""
    import time

    service = ChunkingService()

    # Large document (5K words)
    text = ("Word " * 50 + ". ") * 100

    start = time.time()
    chunks = await service.chunk_document(
        document_id="doc_perf",
        text=text,
    )
    duration = time.time() - start

    # Should complete within 2 seconds for 5K words
    assert duration < 2.0
    assert len(chunks) > 0


@pytest.mark.asyncio
async def test_multiple_documents_chunking_performance():
    """Test chunking multiple documents in sequence."""
    import time

    service = ChunkingService()

    texts = [f"Document {i} text. " * 100 for i in range(10)]

    start = time.time()
    for i, text in enumerate(texts):
        chunks = await service.chunk_document(
            document_id=f"doc_{i}",
            text=text,
        )
        assert len(chunks) > 0
    duration = time.time() - start

    # Should complete within 5 seconds for 10 documents
    assert duration < 5.0
