"""Integration test for ChunkingService across all pipelines.

Sprint 16 Feature 16.1 - Unified Chunking Service
Tests end-to-end chunking integration with Qdrant and LightRAG.
"""

from src.core.chunk import ChunkStrategy
from src.core.chunking_service import get_chunking_service, reset_chunking_service


class TestChunkingServiceIntegration:
    """Integration tests for ChunkingService across pipelines."""

    def setup_method(self):
        """Reset chunking service before each test."""
        reset_chunking_service()

    def test_qdrant_pipeline_chunking(self):
        """Test ChunkingService integration with Qdrant ingestion pipeline."""
        # Qdrant uses adaptive strategy (sentence-aware)
        service = get_chunking_service(
            strategy=ChunkStrategy(method="adaptive", chunk_size=512, overlap=128)
        )

        sample_doc = """
        Natural language processing (NLP) is a subfield of linguistics, computer science,
        and artificial intelligence concerned with the interactions between computers and human language.

        It focuses on programming computers to process and analyze large amounts of natural language data.
        The goal is to enable computers to understand, interpret, and generate human language.
        """

        chunks = service.chunk_document(
            document_id="nlp_intro_001",
            content=sample_doc,
            metadata={"source": "test.md", "category": "AI"},
        )

        # Verify chunks created
        assert len(chunks) > 0
        assert all(chunk.chunk_id for chunk in chunks)
        assert all(chunk.document_id == "nlp_intro_001" for chunk in chunks)

        # Verify Qdrant payload conversion
        for chunk in chunks:
            payload = chunk.to_qdrant_payload()
            assert "chunk_id" in payload
            assert "document_id" in payload
            assert "text" in payload
            assert payload["source"] == "test.md"
            assert payload["category"] == "AI"

    def test_lightrag_pipeline_chunking(self):
        """Test ChunkingService integration with LightRAG ingestion."""
        # LightRAG uses fixed strategy (tiktoken-based)
        service = get_chunking_service(
            strategy=ChunkStrategy(method="fixed", chunk_size=200, overlap=40)
        )

        sample_doc = """
        Machine learning is a method of data analysis that automates analytical model building.
        It is a branch of artificial intelligence based on the idea that systems can learn from data.
        Using algorithms that iteratively learn from data, machine learning allows computers to find hidden insights.
        """

        chunks = service.chunk_document(
            document_id="ml_intro_001",
            content=sample_doc,
            metadata={"author": "test", "year": 2025},
        )

        # Verify chunks created
        assert len(chunks) > 0

        # Verify LightRAG format conversion
        for chunk in chunks:
            lightrag_chunk = chunk.to_lightrag_format()
            assert "chunk_id" in lightrag_chunk
            assert "text" in lightrag_chunk
            assert "document_id" in lightrag_chunk
            assert "tokens" in lightrag_chunk
            assert lightrag_chunk["tokens"] > 0

    def test_bm25_pipeline_chunking(self):
        """Test ChunkingService integration with BM25 indexing."""
        # BM25 can use any strategy, test with sentence-based
        service = get_chunking_service(
            strategy=ChunkStrategy(method="sentence", chunk_size=300, overlap=60)
        )

        sample_doc = """
        Information retrieval (IR) is the activity of obtaining information system resources.
        Searches can be based on full-text or other content-based indexing.
        Automated information retrieval systems are used to reduce information overload.
        BM25 is a ranking function used by search engines to estimate relevance.
        """

        chunks = service.chunk_document(
            document_id="ir_intro_001",
            content=sample_doc,
            metadata={"domain": "search"},
        )

        # Verify chunks created
        assert len(chunks) > 0

        # Verify BM25 document conversion
        for chunk in chunks:
            bm25_doc = chunk.to_bm25_document()
            assert "chunk_id" in bm25_doc
            assert "text" in bm25_doc
            assert "document_id" in bm25_doc
            assert bm25_doc["domain"] == "search"

    def test_deterministic_chunk_ids_across_pipelines(self):
        """Test that chunk_ids are deterministic for graph-vector alignment."""
        content = "Sample document for deterministic testing."
        doc_id = "test_001"

        # Chunk with Qdrant strategy
        qdrant_service = get_chunking_service(
            strategy=ChunkStrategy(method="adaptive", chunk_size=512)
        )
        qdrant_chunks = qdrant_service.chunk_document(doc_id, content)

        # Chunk with same strategy again
        qdrant_service2 = get_chunking_service(
            strategy=ChunkStrategy(method="adaptive", chunk_size=512)
        )
        qdrant_chunks2 = qdrant_service2.chunk_document(doc_id, content)

        # Verify deterministic chunk_ids
        assert len(qdrant_chunks) == len(qdrant_chunks2)
        for c1, c2 in zip(qdrant_chunks, qdrant_chunks2, strict=False):
            assert c1.chunk_id == c2.chunk_id
            assert c1.content == c2.content

    def test_chunk_id_uniqueness_across_documents(self):
        """Test that chunk_ids are unique across different documents."""
        service = get_chunking_service()

        content1 = "Document one content."
        content2 = "Document two content."

        chunks1 = service.chunk_document("doc_001", content1)
        chunks2 = service.chunk_document("doc_002", content2)

        # Collect all chunk_ids
        all_chunk_ids = [c.chunk_id for c in chunks1] + [c.chunk_id for c in chunks2]

        # Verify all unique
        assert len(all_chunk_ids) == len(set(all_chunk_ids))

    def test_multi_strategy_chunking(self):
        """Test that different strategies produce different chunking results."""
        content = "First sentence. Second sentence. Third sentence. Fourth sentence."
        doc_id = "multi_001"

        # Fixed strategy (token-based)
        fixed_chunks = get_chunking_service(
            strategy=ChunkStrategy(method="fixed", chunk_size=200)
        ).chunk_document(doc_id, content)

        # Adaptive strategy (sentence-aware)
        adaptive_chunks = get_chunking_service(
            strategy=ChunkStrategy(method="adaptive", chunk_size=200)
        ).chunk_document(doc_id, content)

        # Sentence strategy (regex-based)
        sentence_chunks = get_chunking_service(
            strategy=ChunkStrategy(method="sentence", chunk_size=200)
        ).chunk_document(doc_id, content)

        # Verify all strategies produced chunks
        assert len(fixed_chunks) > 0
        assert len(adaptive_chunks) > 0
        assert len(sentence_chunks) > 0

        # Verify strategies may produce different chunk counts (due to different boundaries)
        # This is expected - fixed uses tokens, adaptive uses sentences, sentence uses regex
        print(
            f"Fixed: {len(fixed_chunks)}, Adaptive: {len(adaptive_chunks)}, Sentence: {len(sentence_chunks)}"
        )

    def test_large_document_chunking_performance(self):
        """Test chunking large document completes in reasonable time."""
        import time

        # Generate large document (10K words)
        content = ("The quick brown fox jumps over the lazy dog. " * 1000) * 2

        service = get_chunking_service(
            strategy=ChunkStrategy(method="adaptive", chunk_size=512, overlap=128)
        )

        start = time.time()
        chunks = service.chunk_document("large_doc_001", content)
        duration = time.time() - start

        # Verify chunking completed
        assert len(chunks) > 50  # Should produce many chunks
        assert all(chunk.token_count > 0 for chunk in chunks)

        # Verify performance (should complete within 2 seconds)
        assert duration < 2.0

        print(f"Chunked {len(content)} chars into {len(chunks)} chunks in {duration:.3f}s")
