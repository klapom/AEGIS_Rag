# Sprint 21: Container-Based Ingestion Pipeline - TEST PLAN

**Sprint:** 21 - Container-Based Ingestion with LangGraph Orchestration
**Test Strategy:** NO MOCKS for Integration/E2E (ADR-014), Real Services Only
**Target Coverage:** 80% overall, 90% critical path
**Estimated Test Effort:** 15 days (parallel to implementation)
**Last Updated:** 2025-11-07

---

## 🎯 Testing Objectives

### **Primary Goals:**
1. ✅ Verify Docling container lifecycle (start/stop/parse)
2. ✅ Validate LangGraph state transitions (5 nodes, error handling)
3. ✅ Test batch processing with 100+ documents (no OOM)
4. ✅ Verify memory isolation (<4.4GB RAM peak)
5. ✅ Test SSE streaming to React UI (real-time progress)
6. ✅ Validate chunking strategy (1200-1800 tokens)
7. ✅ End-to-end pipeline (Docling → Qdrant + Neo4j)

### **Success Criteria:**
- ✅ 80% overall test coverage (unit + integration + E2E)
- ✅ 90% coverage for critical path (pipeline nodes)
- ✅ All integration tests pass with real Docker services
- ✅ E2E test: Single document through full pipeline (<5 min)
- ✅ E2E test: Batch of 100 documents without OOM
- ✅ Performance: Docling parsing <30s for 10-page PDF
- ✅ Memory: Peak <4.4GB RAM (verified with docker stats)

---

## 📊 Test Pyramid for Sprint 21

```
        /\
       /  \  15% E2E Tests (~18 tests)
      /────\  Full pipeline, real services, NO MOCKS
     /      \
    /────────\ 35% Integration Tests (~42 tests)
   /          \ Real Docker containers, component interaction
  /────────────\
 /              \ 50% Unit Tests (~60 tests)
/────────────────\ Fast, isolated, mocked dependencies
```

**Total Test Suite:** ~120 tests (Sprint 21 specific)
**Execution Time:** <15 minutes (with Docker cache)
**Coverage Target:** 80% overall, 90% critical path

---

## 🧪 Unit Tests (50% - ~60 tests)

### **Feature 21.1: Docling Container Client (12 tests)**

**File:** `tests/ingestion/test_docling_client_unit.py`

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.components.ingestion.docling_client import DoclingContainerClient

class TestDoclingContainerClient:
    """Unit tests for Docling container lifecycle and API calls."""

    @pytest.fixture
    def client(self):
        return DoclingContainerClient(base_url="http://localhost:8080")

    @patch("subprocess.run")
    async def test_start_container_success(self, mock_run, client):
        """Test successful container startup."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        with patch.object(client, "_wait_for_ready", new=AsyncMock()):
            await client.start_container()

        mock_run.assert_called_once_with(
            ["docker-compose", "up", "-d", "docling"],
            capture_output=True,
            text=True
        )

    @patch("subprocess.run")
    async def test_start_container_failure(self, mock_run, client):
        """Test container startup failure handling."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: Image not found"
        )

        with pytest.raises(RuntimeError, match="Failed to start Docling"):
            await client.start_container()

    @patch("subprocess.run")
    async def test_stop_container(self, mock_run, client):
        """Test container stop."""
        mock_run.return_value = MagicMock(returncode=0)

        await client.stop_container()

        mock_run.assert_called_once_with(
            ["docker-compose", "stop", "docling"],
            capture_output=True
        )

    @pytest.mark.asyncio
    async def test_wait_for_ready_success(self, client):
        """Test waiting for container ready state."""
        with patch.object(client.client, "get", new=AsyncMock(
            return_value=MagicMock(status_code=200)
        )):
            await client._wait_for_ready(max_retries=3)

    @pytest.mark.asyncio
    async def test_wait_for_ready_timeout(self, client):
        """Test timeout when container doesn't become ready."""
        with patch.object(client.client, "get", new=AsyncMock(
            side_effect=Exception("Connection refused")
        )):
            with pytest.raises(TimeoutError, match="did not become ready"):
                await client._wait_for_ready(max_retries=3)

    @pytest.mark.asyncio
    async def test_parse_document_success(self, client, tmp_path):
        """Test successful document parsing."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"fake pdf content")

        mock_response = MagicMock(
            status_code=200,
            json=lambda: {
                "content": "# Document Title\n\nParsed content",
                "metadata": {"pages": 5, "tables": 2, "images": 1}
            }
        )

        with patch.object(client.client, "post", new=AsyncMock(
            return_value=mock_response
        )):
            result = await client.parse_document(test_file)

        assert result["content"] == "# Document Title\n\nParsed content"
        assert result["metadata"]["pages"] == 5

    @pytest.mark.asyncio
    async def test_parse_document_failure(self, client, tmp_path):
        """Test document parsing failure handling."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"corrupted pdf")

        mock_response = MagicMock(
            status_code=400,
            text="Invalid PDF format"
        )

        with patch.object(client.client, "post", new=AsyncMock(
            return_value=mock_response
        )):
            with pytest.raises(ValueError, match="Docling parsing failed"):
                await client.parse_document(test_file)

    # Additional unit tests:
    # - test_parse_document_large_file (10MB PDF)
    # - test_parse_document_empty_file
    # - test_parse_document_unsupported_format
    # - test_concurrent_parse_requests (max 3 concurrent)
    # - test_client_timeout_handling
```

**Coverage Target:** 90% for `docling_client.py`

---

### **Feature 21.2: LangGraph State Machine Nodes (30 tests)**

**File:** `tests/ingestion/nodes/test_memory_check_unit.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from src.components.ingestion.nodes.memory_check import memory_check_node, should_proceed
from src.components.ingestion.state import IngestionState

class TestMemoryCheckNode:
    """Unit tests for memory check node."""

    @pytest.fixture
    def initial_state(self):
        return {
            "document_path": "/tmp/test.pdf",
            "document_id": "doc_123",
            "errors": [],
            "current_memory_mb": 0.0,
        }

    @patch("psutil.virtual_memory")
    async def test_memory_check_sufficient(self, mock_memory, initial_state):
        """Test memory check with sufficient RAM."""
        mock_memory.return_value = MagicMock(available=2000 * 1024 ** 2)  # 2GB

        result = await memory_check_node(initial_state)

        assert result["current_memory_mb"] == 2000.0
        assert len(result["errors"]) == 0

    @patch("psutil.virtual_memory")
    async def test_memory_check_insufficient(self, mock_memory, initial_state):
        """Test memory check with insufficient RAM."""
        mock_memory.return_value = MagicMock(available=500 * 1024 ** 2)  # 500MB

        result = await memory_check_node(initial_state)

        assert result["current_memory_mb"] == 500.0
        assert len(result["errors"]) == 1
        assert "Insufficient memory" in result["errors"][0]["error"]

    def test_should_proceed_with_errors(self, initial_state):
        """Test conditional routing with errors."""
        initial_state["errors"] = [{"stage": "memory_check", "error": "OOM"}]

        decision = should_proceed(initial_state)

        assert decision == "insufficient_memory"

    def test_should_proceed_no_errors(self, initial_state):
        """Test conditional routing without errors."""
        decision = should_proceed(initial_state)

        assert decision == "proceed"
```

**File:** `tests/ingestion/nodes/test_docling_node_unit.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.components.ingestion.nodes.docling import docling_processing_node

class TestDoclingProcessingNode:
    """Unit tests for Docling processing node."""

    @pytest.fixture
    def initial_state(self):
        return {
            "document_path": "/tmp/test.pdf",
            "document_id": "doc_123",
            "docling_status": "pending",
            "parsed_content": "",
            "parsed_metadata": {},
            "overall_progress": 0.0,
            "errors": [],
        }

    @patch("src.components.ingestion.nodes.docling.DoclingContainerClient")
    async def test_docling_node_success(self, mock_client_class, initial_state):
        """Test successful Docling processing."""
        mock_client = AsyncMock()
        mock_client.parse_document.return_value = {
            "content": "# Test Document\n\nContent here",
            "metadata": {"pages": 3, "tables": 1, "images": 0}
        }
        mock_client_class.return_value = mock_client

        result = await docling_processing_node(initial_state)

        assert result["docling_status"] == "completed"
        assert result["parsed_content"] == "# Test Document\n\nContent here"
        assert result["parsed_metadata"]["pages"] == 3
        assert result["overall_progress"] == 0.25
        assert len(result["errors"]) == 0

        # Verify container lifecycle
        mock_client.start_container.assert_called_once()
        mock_client.parse_document.assert_called_once()
        mock_client.stop_container.assert_called_once()

    @patch("src.components.ingestion.nodes.docling.DoclingContainerClient")
    async def test_docling_node_failure(self, mock_client_class, initial_state):
        """Test Docling processing failure."""
        mock_client = AsyncMock()
        mock_client.parse_document.side_effect = Exception("Parse error")
        mock_client_class.return_value = mock_client

        result = await docling_processing_node(initial_state)

        assert result["docling_status"] == "failed"
        assert len(result["errors"]) == 1
        assert "Parse error" in result["errors"][0]["error"]

    # Additional unit tests:
    # - test_docling_node_container_start_failure
    # - test_docling_node_timeout
    # - test_docling_node_large_document (>100MB)
```

**Files for other nodes:**
- `test_chunking_node_unit.py` (8 tests)
- `test_embedding_node_unit.py` (8 tests)
- `test_graph_extraction_node_unit.py` (10 tests)

**Coverage Target:** 85% for all node implementations

---

### **Feature 21.3: Batch Orchestrator (10 tests)**

**File:** `tests/ingestion/test_batch_orchestrator_unit.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.components.ingestion.batch_orchestrator import BatchOrchestrator

class TestBatchOrchestrator:
    """Unit tests for batch orchestrator."""

    @pytest.fixture
    def mock_graph(self):
        graph = MagicMock()
        graph.astream = AsyncMock()
        return graph

    @pytest.fixture
    def orchestrator(self, mock_graph):
        return BatchOrchestrator(graph=mock_graph)

    @pytest.mark.asyncio
    async def test_batch_start_event(self, orchestrator, tmp_path):
        """Test batch start event emission."""
        files = [tmp_path / "doc1.pdf", tmp_path / "doc2.pdf"]
        for f in files:
            f.write_bytes(b"fake content")

        events = []
        async for event in orchestrator.process_batch(files, "batch_123"):
            events.append(event)
            if event["type"] == "batch_start":
                break

        start_event = events[0]
        assert start_event["type"] == "batch_start"
        assert start_event["batch_id"] == "batch_123"
        assert start_event["total_documents"] == 2

    @pytest.mark.asyncio
    async def test_batch_progress_events(self, orchestrator, tmp_path, mock_graph):
        """Test document progress events."""
        files = [tmp_path / "doc1.pdf"]
        files[0].write_bytes(b"content")

        # Mock graph stream
        mock_graph.astream.return_value = [
            {"docling": {"docling_status": "running", "overall_progress": 0.1}},
            {"chunking": {"chunking_status": "completed", "overall_progress": 0.5}},
        ]

        events = []
        async for event in orchestrator.process_batch(files, "batch_123"):
            events.append(event)

        progress_events = [e for e in events if e["type"] == "document_progress"]
        assert len(progress_events) >= 2

    # Additional unit tests:
    # - test_batch_complete_event
    # - test_batch_with_failures
    # - test_batch_empty_file_list
    # - test_batch_concurrent_processing
    # - test_batch_cancellation
    # - test_batch_memory_tracking
```

**Coverage Target:** 80% for `batch_orchestrator.py`

---

### **Feature 21.4: Chunking Service (8 tests)**

**File:** `tests/ingestion/test_chunking_service_unit.py`

```python
import pytest
from src.components.ingestion.chunking_service import ChunkingService

class TestChunkingService:
    """Unit tests for chunking service."""

    @pytest.fixture
    def chunker(self):
        return ChunkingService(
            chunk_size=1800,
            overlap=300,
            strategy="adaptive",
            min_chunk_size=600
        )

    def test_chunk_small_text(self, chunker):
        """Test chunking of small text (<600 tokens)."""
        text = "This is a small paragraph with less than 600 tokens."

        chunks = chunker.chunk_text(text, "doc_123")

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert 0 < chunks[0].token_count < 100

    def test_chunk_large_text(self, chunker):
        """Test chunking of large text (>1800 tokens)."""
        # Generate text with ~3000 tokens
        text = "This is a paragraph. " * 300

        chunks = chunker.chunk_text(text, "doc_123")

        assert len(chunks) >= 2
        for chunk in chunks:
            assert chunk.token_count >= 600  # Min size
            assert chunk.token_count <= 2200  # Max with overlap

    def test_chunk_overlap(self, chunker):
        """Test chunk overlap preservation."""
        text = "Paragraph 1.\n\n" + ("Sentence. " * 200) + "\n\nParagraph 2.\n\n" + ("Sentence. " * 200)

        chunks = chunker.chunk_text(text, "doc_123")

        if len(chunks) > 1:
            # Check overlap exists
            overlap_text = chunker._get_overlap_text(chunks[0].content)
            assert overlap_text in chunks[1].content

    def test_chunk_min_size_enforcement(self, chunker):
        """Test minimum chunk size enforcement (merge small chunks)."""
        text = "Short para 1.\n\n" + ("Word " * 100) + "\n\nShort para 2."

        chunks = chunker.chunk_text(text, "doc_123")

        for chunk in chunks:
            assert chunk.token_count >= 600 or chunk == chunks[-1]  # Last chunk exception

    # Additional unit tests:
    # - test_chunk_paragraph_boundary_preservation
    # - test_chunk_metadata_generation
    # - test_chunk_token_counting_accuracy
    # - test_chunk_strategy_fixed_vs_adaptive
```

**Coverage Target:** 85% for `chunking_service.py`

---

## 🔗 Integration Tests (35% - ~42 tests)

### **Real Docker Services Required:**
- ✅ Docling container (CUDA)
- ✅ Ollama (BGE-M3 embeddings, Gemma-3-4b LLM)
- ✅ Qdrant (vector storage)
- ✅ Neo4j (graph storage)
- ✅ Redis (state persistence)

### **Feature 21.1: Docling Container Integration (6 tests)**

**File:** `tests/ingestion/test_docling_container_integration.py`

```python
import pytest
from pathlib import Path
from src.components.ingestion.docling_client import DoclingContainerClient

@pytest.mark.integration
class TestDoclingContainerIntegration:
    """Integration tests with real Docling container."""

    @pytest.fixture(scope="class")
    async def docling_client(self):
        """Real Docling container client."""
        client = DoclingContainerClient()

        # Start container for all tests
        await client.start_container()

        yield client

        # Stop container after all tests
        await client.stop_container()

    @pytest.mark.asyncio
    async def test_parse_pdf_real(self, docling_client, sample_pdf_file):
        """Test parsing real PDF with GPU acceleration."""
        result = await docling_client.parse_document(sample_pdf_file)

        assert "content" in result
        assert len(result["content"]) > 0
        assert result["metadata"]["pages"] > 0

    @pytest.mark.asyncio
    async def test_parse_pptx_real(self, docling_client, sample_pptx_file):
        """Test parsing real PowerPoint file."""
        result = await docling_client.parse_document(sample_pptx_file)

        assert "content" in result
        assert result["metadata"]["pages"] > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_parse_large_pdf_performance(self, docling_client, large_pdf_file):
        """Test parsing 10-page PDF performance (<30s target)."""
        import time

        start = time.time()
        result = await docling_client.parse_document(large_pdf_file)
        elapsed = time.time() - start

        assert elapsed < 30.0  # Performance target
        assert result["metadata"]["pages"] == 10

    @pytest.mark.asyncio
    async def test_container_restart(self, docling_client):
        """Test container stop/start cycle."""
        await docling_client.stop_container()
        await docling_client.start_container()

        # Verify still functional
        result = await docling_client.parse_document(sample_pdf_file)
        assert len(result["content"]) > 0

    # Additional integration tests:
    # - test_parse_table_extraction_accuracy
    # - test_gpu_memory_utilization (nvidia-smi check)
```

**Coverage Target:** 75% for container lifecycle + parsing

---

### **Feature 21.2: LangGraph Pipeline Integration (12 tests)**

**File:** `tests/ingestion/test_pipeline_integration.py`

```python
import pytest
from pathlib import Path
from src.components.ingestion.graph import create_ingestion_graph

@pytest.mark.integration
class TestIngestionPipelineIntegration:
    """Integration tests for LangGraph pipeline with real services."""

    @pytest.fixture(scope="class")
    def pipeline(self):
        """Compiled LangGraph pipeline."""
        return create_ingestion_graph()

    @pytest.mark.asyncio
    async def test_single_document_pipeline(self, pipeline, sample_pdf_file):
        """Test full pipeline with single document."""
        initial_state = {
            "document_path": str(sample_pdf_file),
            "document_id": "test_doc_001",
            "batch_id": "batch_001",
            "batch_index": 1,
            "total_documents": 1,
            "parsed_content": "",
            "parsed_metadata": {},
            "chunks": [],
            "embedded_chunks": [],
            "entities": [],
            "relations": [],
            "docling_status": "pending",
            "chunking_status": "pending",
            "embedding_status": "pending",
            "graph_status": "pending",
            "overall_progress": 0.0,
            "current_memory_mb": 0.0,
            "requires_container_restart": False,
            "errors": [],
            "retry_count": 0,
            "max_retries": 3,
        }

        final_state = None
        async for event in pipeline.astream(initial_state):
            node_name = list(event.keys())[0]
            final_state = event[node_name]

        # Verify all stages completed
        assert final_state["docling_status"] == "completed"
        assert final_state["chunking_status"] == "completed"
        assert final_state["embedding_status"] == "completed"
        assert final_state["graph_status"] == "completed"
        assert final_state["overall_progress"] == 1.0
        assert len(final_state["errors"]) == 0

        # Verify outputs
        assert len(final_state["parsed_content"]) > 0
        assert len(final_state["chunks"]) > 0
        assert len(final_state["embedded_chunks"]) > 0

    @pytest.mark.asyncio
    async def test_pipeline_memory_check_failure(self, pipeline, monkeypatch):
        """Test pipeline abort on insufficient memory."""
        # Mock low memory
        def mock_memory():
            from unittest.mock import MagicMock
            return MagicMock(available=500 * 1024 ** 2)  # 500MB

        monkeypatch.setattr("psutil.virtual_memory", mock_memory)

        initial_state = {...}  # Same as above

        final_state = None
        async for event in pipeline.astream(initial_state):
            node_name = list(event.keys())[0]
            final_state = event[node_name]

        # Verify pipeline stopped at memory check
        assert len(final_state["errors"]) > 0
        assert "Insufficient memory" in final_state["errors"][0]["error"]

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_pipeline_with_large_document(self, pipeline, large_pdf_file):
        """Test pipeline with large document (10+ pages)."""
        initial_state = {...}  # Setup state

        final_state = None
        async for event in pipeline.astream(initial_state):
            node_name = list(event.keys())[0]
            final_state = event[node_name]

        # Verify successful processing
        assert final_state["overall_progress"] == 1.0
        assert len(final_state["chunks"]) > 10  # Large doc → many chunks

    # Additional integration tests:
    # - test_pipeline_error_recovery (retry logic)
    # - test_pipeline_concurrent_documents (parallel processing)
    # - test_pipeline_state_persistence (Redis checkpoint)
    # - test_pipeline_progress_tracking
    # - test_pipeline_memory_monitoring
    # - test_pipeline_container_lifecycle
    # - test_pipeline_qdrant_integration
    # - test_pipeline_neo4j_integration
    # - test_pipeline_timeout_handling
```

**Coverage Target:** 85% for pipeline orchestration

---

### **Feature 21.3: Batch Processing Integration (8 tests)**

**File:** `tests/ingestion/test_batch_processing_integration.py`

```python
import pytest
from pathlib import Path
from src.components.ingestion.batch_orchestrator import BatchOrchestrator
from src.components.ingestion.graph import create_ingestion_graph

@pytest.mark.integration
class TestBatchProcessingIntegration:
    """Integration tests for batch processing with real services."""

    @pytest.fixture
    def orchestrator(self):
        graph = create_ingestion_graph()
        return BatchOrchestrator(graph=graph)

    @pytest.mark.asyncio
    async def test_batch_10_documents(self, orchestrator, sample_documents_10):
        """Test batch processing of 10 documents."""
        batch_id = "batch_test_10"

        events = []
        async for event in orchestrator.process_batch(sample_documents_10, batch_id):
            events.append(event)

        # Verify batch complete
        batch_complete = [e for e in events if e["type"] == "batch_complete"][0]
        assert batch_complete["successful"] == 10
        assert batch_complete["failed"] == 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_batch_100_documents_no_oom(self, orchestrator, sample_documents_100):
        """Test batch processing of 100 documents without OOM."""
        batch_id = "batch_test_100"

        import psutil

        max_memory_mb = 0.0

        async for event in orchestrator.process_batch(sample_documents_100, batch_id):
            # Track peak memory
            current_memory = psutil.virtual_memory().used / (1024 ** 2)
            max_memory_mb = max(max_memory_mb, current_memory)

        # Verify no OOM
        assert max_memory_mb < 4400  # <4.4GB target

        # Verify completion
        batch_complete = [e for e in events if e["type"] == "batch_complete"][-1]
        assert batch_complete["successful"] + batch_complete["failed"] == 100

    @pytest.mark.asyncio
    async def test_batch_with_failures(self, orchestrator, tmp_path):
        """Test batch processing with some document failures."""
        # Create mix of valid and corrupted files
        files = []
        for i in range(5):
            f = tmp_path / f"doc_{i}.pdf"
            if i == 2:
                f.write_bytes(b"corrupted")  # Invalid PDF
            else:
                f.write_bytes(b"%PDF-1.4\nValid content")
            files.append(f)

        events = []
        async for event in orchestrator.process_batch(files, "batch_mixed"):
            events.append(event)

        batch_complete = [e for e in events if e["type"] == "batch_complete"][0]
        assert batch_complete["successful"] >= 3  # At least 3 valid docs
        assert batch_complete["failed"] >= 1     # At least 1 failed

    # Additional integration tests:
    # - test_batch_progress_percentage_accuracy
    # - test_batch_event_order
    # - test_batch_concurrent_batches
    # - test_batch_cancellation
    # - test_batch_resume_after_interruption (TD-41)
```

**Coverage Target:** 80% for batch processing

---

### **Feature 21.4: Chunking Integration (4 tests)**

**File:** `tests/ingestion/test_chunking_integration.py`

```python
import pytest
from src.components.ingestion.chunking_service import ChunkingService

@pytest.mark.integration
class TestChunkingIntegration:
    """Integration tests for chunking with real documents."""

    @pytest.fixture
    def chunker(self):
        return ChunkingService(
            chunk_size=1800,
            overlap=300,
            strategy="adaptive",
            min_chunk_size=600
        )

    def test_chunk_real_pdf_content(self, chunker, parsed_pdf_content):
        """Test chunking of real PDF parsed content."""
        chunks = chunker.chunk_text(parsed_pdf_content, "doc_real_001")

        # Verify chunk size distribution
        chunk_sizes = [c.token_count for c in chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)

        assert 1200 <= avg_size <= 1800  # Target range
        assert all(c.token_count >= 600 for c in chunks)  # Min size

    def test_chunk_real_pptx_content(self, chunker, parsed_pptx_content):
        """Test chunking of real PowerPoint parsed content."""
        chunks = chunker.chunk_text(parsed_pptx_content, "doc_pptx_001")

        # Verify fewer chunks than Sprint 20 baseline (103 → ~35)
        # Assuming ~10K tokens total from 103 pages
        expected_max_chunks = (10000 // 1200) + 1
        assert len(chunks) <= expected_max_chunks

    # Additional integration tests:
    # - test_chunk_overlap_semantic_consistency
    # - test_chunk_markdown_structure_preservation
```

**Coverage Target:** 75% for chunking with real data

---

## 🌐 End-to-End (E2E) Tests (15% - ~18 tests)

### **Critical Path: Full Pipeline (8 tests)**

**File:** `tests/e2e/test_ingestion_pipeline_e2e.py`

```python
import pytest
from pathlib import Path
from qdrant_client import QdrantClient
from neo4j import GraphDatabase

@pytest.mark.e2e
@pytest.mark.no_mocks
class TestIngestionPipelineE2E:
    """E2E tests for full ingestion pipeline with all real services.

    ADR-014: NO MOCKS - Real Docker services only.
    """

    @pytest.fixture(scope="class")
    def qdrant_client(self):
        """Real Qdrant client for verification."""
        client = QdrantClient(host="localhost", port=6333)
        yield client
        # Cleanup test collections
        collections = client.get_collections()
        for c in collections.collections:
            if c.name.startswith("test_e2e_"):
                client.delete_collection(c.name)

    @pytest.fixture(scope="class")
    def neo4j_driver(self):
        """Real Neo4j driver for verification."""
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )
        yield driver
        # Cleanup test nodes
        with driver.session() as session:
            session.run("MATCH (n:TestE2E) DETACH DELETE n")
        driver.close()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_e2e_single_pdf_to_qdrant_neo4j(
        self,
        sample_pdf_file,
        qdrant_client,
        neo4j_driver
    ):
        """E2E: Single PDF → Docling → Chunking → Qdrant + Neo4j.

        Target: <5 minutes total processing time.
        """
        from src.components.ingestion.graph import create_ingestion_graph
        import time

        pipeline = create_ingestion_graph()

        initial_state = {
            "document_path": str(sample_pdf_file),
            "document_id": "e2e_test_001",
            # ... all required fields
        }

        start_time = time.time()

        final_state = None
        async for event in pipeline.astream(initial_state):
            node_name = list(event.keys())[0]
            final_state = event[node_name]

        elapsed = time.time() - start_time

        # Verify completion
        assert final_state["overall_progress"] == 1.0
        assert len(final_state["errors"]) == 0

        # Verify Qdrant storage
        collection_name = "test_e2e_documents"
        points = qdrant_client.scroll(collection_name, limit=100)[0]
        assert len(points) == len(final_state["embedded_chunks"])

        # Verify Neo4j storage
        with neo4j_driver.session() as session:
            result = session.run(
                "MATCH (n) WHERE n.document_id = $doc_id RETURN count(n) as cnt",
                doc_id="e2e_test_001"
            )
            count = result.single()["cnt"]
            assert count > 0  # Entities created

        # Performance check
        assert elapsed < 300  # <5 minutes

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_e2e_batch_100_documents(self, sample_documents_100):
        """E2E: Batch 100 documents → Full pipeline → Verify storage.

        Target: All documents processed without OOM.
        """
        from src.components.ingestion.batch_orchestrator import BatchOrchestrator
        from src.components.ingestion.graph import create_ingestion_graph

        graph = create_ingestion_graph()
        orchestrator = BatchOrchestrator(graph=graph)

        import psutil
        max_memory_mb = 0.0

        successful = 0
        failed = 0

        async for event in orchestrator.process_batch(sample_documents_100, "e2e_batch_100"):
            # Track memory
            current = psutil.virtual_memory().used / (1024 ** 2)
            max_memory_mb = max(max_memory_mb, current)

            if event["type"] == "batch_complete":
                successful = event["successful"]
                failed = event["failed"]

        # Verify completion
        assert successful + failed == 100
        assert successful >= 95  # At least 95% success rate

        # Verify memory constraint
        assert max_memory_mb < 4400  # <4.4GB RAM

    @pytest.mark.asyncio
    async def test_e2e_container_lifecycle_isolation(self, sample_pdf_file):
        """E2E: Verify container start/stop isolation (memory freed)."""
        import psutil

        memory_before = psutil.virtual_memory().used / (1024 ** 2)

        # Run pipeline
        from src.components.ingestion.graph import create_ingestion_graph
        pipeline = create_ingestion_graph()

        initial_state = {...}  # Setup

        async for event in pipeline.astream(initial_state):
            pass  # Process

        memory_after = psutil.virtual_memory().used / (1024 ** 2)

        # Memory should be freed (Docling container stopped)
        memory_leaked = memory_after - memory_before
        assert memory_leaked < 500  # <500MB acceptable leak

    # Additional E2E tests:
    # - test_e2e_mixed_document_types (PDF + PPTX + DOCX)
    # - test_e2e_error_recovery_retry
    # - test_e2e_chunking_quality (verify 1200-1800 tokens)
    # - test_e2e_embedding_accuracy (BGE-M3 verification)
    # - test_e2e_graph_extraction_quality (entity/relation counts)
```

**Coverage Target:** 90% for critical path (full pipeline)

---

### **API E2E Tests (6 tests)**

**File:** `tests/e2e/test_ingestion_api_e2e.py`

```python
import pytest
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.mark.e2e
class TestIngestionAPIE2E:
    """E2E tests for ingestion API with SSE streaming."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_batch_upload_sse_stream(self, client, sample_pdf_bytes):
        """E2E: Upload batch via API → SSE stream → Verify events."""
        files = [
            ("files", ("test1.pdf", sample_pdf_bytes, "application/pdf")),
            ("files", ("test2.pdf", sample_pdf_bytes, "application/pdf")),
        ]

        response = client.post("/api/v1/ingestion/batch", files=files, stream=True)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        # Parse SSE events
        events = []
        for line in response.iter_lines():
            if line.startswith("data: "):
                import json
                event = json.loads(line[6:])
                events.append(event)

        # Verify event sequence
        event_types = [e["type"] for e in events]
        assert "batch_start" in event_types
        assert "document_progress" in event_types
        assert "batch_complete" in event_types

        # Verify final event
        batch_complete = [e for e in events if e["type"] == "batch_complete"][0]
        assert batch_complete["successful"] == 2

    # Additional API E2E tests:
    # - test_batch_upload_large_files (10MB+ PDFs)
    # - test_batch_upload_invalid_files
    # - test_sse_stream_cancellation
    # - test_concurrent_batch_uploads
    # - test_api_error_handling
```

**Coverage Target:** 80% for API endpoints

---

### **React UI E2E Tests (4 tests)**

**File:** `frontend/tests/e2e/ingestion-monitor.spec.ts` (Playwright)

```typescript
import { test, expect } from '@playwright/test';

test.describe('Ingestion Monitor E2E', () => {
  test('should display real-time progress during batch ingestion', async ({ page }) => {
    // Navigate to ingestion page
    await page.goto('/ingestion');

    // Upload test files
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles([
      'tests/fixtures/test1.pdf',
      'tests/fixtures/test2.pdf',
    ]);

    // Start batch
    await page.click('button:has-text("Start Ingestion")');

    // Wait for batch start event
    await expect(page.locator('.batch-status')).toContainText('Processing');

    // Verify progress bar updates
    const progressBar = page.locator('.progress-fill');
    await expect(progressBar).toHaveCSS('width', /[1-9][0-9]?%/);

    // Verify event log
    await expect(page.locator('.event-log .event')).toHaveCount(2, { timeout: 60000 });

    // Verify completion
    await expect(page.locator('.batch-status')).toContainText('Complete');
  });

  // Additional React UI E2E tests:
  // - test_progress_bar_accuracy
  // - test_error_display
  // - test_batch_cancellation
});
```

**Coverage Target:** 75% for UI components

---

## 🚀 Performance & Load Tests (Bonus)

**File:** `tests/performance/test_ingestion_performance.py`

```python
import pytest
from locust import HttpUser, task, between

class IngestionLoadTest(HttpUser):
    """Load test for ingestion API."""
    wait_time = between(1, 3)

    @task
    def upload_batch(self):
        files = [("files", ("test.pdf", b"fake content", "application/pdf"))]
        self.client.post("/api/v1/ingestion/batch", files=files)

# Run: locust -f tests/performance/test_ingestion_performance.py --host http://localhost:8000
```

---

## 📋 Test Execution Plan

### **Daily Development (During Sprint 21)**

```bash
# Unit tests only (fast feedback)
pytest tests/ingestion/ -m "not integration and not e2e" -v

# Integration tests (with Docker services)
docker-compose up -d
pytest tests/ingestion/ -m integration -v

# E2E tests (full pipeline)
pytest tests/e2e/ -m e2e --slow -v
```

### **Pre-Commit (CI Pipeline)**

```bash
# All tests except slow E2E
pytest tests/ -m "not slow" --cov=src --cov-report=term

# Coverage check
pytest --cov=src --cov-fail-under=80
```

### **Nightly (Full Test Suite)**

```bash
# All tests including slow E2E
pytest tests/ --cov=src --cov-report=html --slow

# Performance tests
locust -f tests/performance/test_ingestion_performance.py --headless --users 10 --spawn-rate 1 --run-time 5m
```

---

## 📊 Sprint 21 Test Metrics Dashboard

| Metric | Target | Status |
|--------|--------|--------|
| **Overall Coverage** | 80% | TBD |
| **Critical Path Coverage** | 90% | TBD |
| **Unit Tests** | 60 tests | TBD |
| **Integration Tests** | 42 tests | TBD |
| **E2E Tests** | 18 tests | TBD |
| **Total Tests** | 120 tests | TBD |
| **Test Execution Time** | <15 min | TBD |
| **E2E Success Rate** | >95% | TBD |
| **Memory Peak (E2E Batch 100)** | <4.4GB | TBD |
| **Docling Parse Speed (10-page PDF)** | <30s | TBD |

---

## ✅ Sprint 21 Test Completion Criteria

- ✅ All 120 tests implemented and passing
- ✅ 80% overall coverage achieved
- ✅ 90% critical path coverage (pipeline nodes)
- ✅ E2E test: Single document through full pipeline (<5 min)
- ✅ E2E test: Batch 100 documents without OOM (<4.4GB RAM)
- ✅ Integration tests pass with all real Docker services
- ✅ Performance test: Docling <30s for 10-page PDF
- ✅ CI pipeline configured with test automation
- ✅ Test fixtures documented in `tests/README.md`

---

**Sprint 21 Testing:** Comprehensive coverage with NO MOCKS for integration/E2E ✅
**Next Sprint:** Sprint 22 - Pipeline Recovery Testing (Redis checkpointing)

**Last Updated:** 2025-11-07
**Author:** Claude Code
**Test Strategy:** ADR-014 (Real Services Only, NO MOCKS)
