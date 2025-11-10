"""Integration tests for Docling CUDA Container - Sprint 21 Feature 21.1.

These tests require a REAL Docker environment with:
- Docker + Docker Compose installed
- NVIDIA GPU + Container Toolkit (for CUDA support)
- Internet connection (first run downloads models)

ADR-014: NO MOCKS - Integration tests use real services.

Prerequisites:
    # Start Docker daemon
    # Ensure GPU accessible: nvidia-smi
    # Ensure NVIDIA Container Toolkit installed

Run tests:
    pytest tests/integration/components/ingestion/test_docling_container_integration.py -v

Note: First run downloads ~2GB models (OCR, layout, table detection)
      Subsequent runs are fast (models cached in Docker volumes)

Test Coverage:
- Real container start/stop with GPU
- Health check with actual HTTP endpoint
- Document parsing with real Docling API
- Batch processing with memory monitoring
- Error handling with real timeouts
- Performance benchmarks
"""

import asyncio
import time
from pathlib import Path

import pytest

from src.components.ingestion.docling_client import (
    DoclingContainerClient,
    DoclingParsedDocument,
    parse_document_with_docling,
)
from src.core.exceptions import IngestionError


# =============================================================================
# Pytest Configuration
# =============================================================================


@pytest.fixture(scope="module")
def sample_documents(tmp_path_factory):
    """Create sample documents for testing.

    Creates:
    - test_simple.txt: Plain text file
    - test_pdf.pdf: Mock PDF (for API testing, real PDF parsing requires actual file)
    - test_batch_*.txt: 3 text files for batch testing
    """
    temp_dir = tmp_path_factory.mktemp("docling_test_docs")

    # Simple text file
    simple_txt = temp_dir / "test_simple.txt"
    simple_txt.write_text("This is a simple test document.\nWith multiple lines.\n")

    # Mock PDF file (note: Docling might reject this as invalid PDF)
    # For real PDF testing, use actual PDF files from data/sample_documents/
    mock_pdf = temp_dir / "test_mock.pdf"
    mock_pdf.write_bytes(b"%PDF-1.4\nMock PDF content for testing\n")

    # Batch files
    batch_files = []
    for i in range(3):
        batch_file = temp_dir / f"test_batch_{i}.txt"
        batch_file.write_text(f"Batch test document {i}\nContent line 1\nContent line 2\n")
        batch_files.append(batch_file)

    return {
        "simple_txt": simple_txt,
        "mock_pdf": mock_pdf,
        "batch_files": batch_files,
        "temp_dir": temp_dir,
    }


# =============================================================================
# Integration Tests: Container Lifecycle
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_container_start_and_stop_real():
    """Test real Docker container start and stop with health check.

    WARNING: This starts the actual Docling CUDA container!
    Requires: Docker + GPU + NVIDIA Container Toolkit
    """
    client = DoclingContainerClient(base_url="http://localhost:8080")

    # Start container
    print("\n[TEST] Starting Docling container (may take 30-60s on first run)...")
    start_time = time.time()
    await client.start_container()
    start_duration = time.time() - start_time

    # Verify container running
    assert client._container_running is True
    print(f"[TEST] Container started in {start_duration:.1f}s")

    # Give container time to fully initialize
    await asyncio.sleep(5)

    # Stop container
    print("[TEST] Stopping Docling container...")
    stop_time = time.time()
    await client.stop_container()
    stop_duration = time.time() - stop_time

    # Verify container stopped
    assert client._container_running is False
    print(f"[TEST] Container stopped in {stop_duration:.1f}s")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_check_real_endpoint():
    """Test health check against real Docling container HTTP endpoint.

    Note: Assumes container is already running or will start it.
    """
    client = DoclingContainerClient()

    # Start container
    await client.start_container()

    try:
        # Test health check explicitly
        await client._wait_for_ready(max_wait_seconds=120)

        # If we reach here, health check succeeded
        assert client._container_running is True
        print("[TEST] Health check succeeded")

    finally:
        # Clean up: stop container
        await client.stop_container()


# =============================================================================
# Integration Tests: Document Parsing
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    not Path("data/sample_documents").exists(),
    reason="Requires real PDF files in data/sample_documents/"
)
async def test_parse_real_pdf_document():
    """Test parsing a REAL PDF document from data/sample_documents/.

    This test requires actual PDF files. Adjust the file path as needed.
    """
    # Find first PDF in sample_documents
    pdf_dir = Path("data/sample_documents")
    pdf_files = list(pdf_dir.rglob("*.pdf"))

    if not pdf_files:
        pytest.skip("No PDF files found in data/sample_documents/")

    test_pdf = pdf_files[0]
    print(f"\n[TEST] Parsing real PDF: {test_pdf.name}")

    client = DoclingContainerClient()

    async with client:  # Auto start/stop
        # Parse document
        parse_start = time.time()
        parsed = await client.parse_document(test_pdf)
        parse_duration = time.time() - parse_start

        # Verify result structure
        assert isinstance(parsed, DoclingParsedDocument)
        assert len(parsed.text) > 0, "Parsed text should not be empty"
        assert isinstance(parsed.metadata, dict)
        assert parsed.parse_time_ms > 0

        print(f"[TEST] Parse duration: {parse_duration:.2f}s")
        print(f"[TEST] Text length: {len(parsed.text)} chars")
        print(f"[TEST] Tables found: {len(parsed.tables)}")
        print(f"[TEST] Images found: {len(parsed.images)}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_text_file(sample_documents):
    """Test parsing a simple text file (should work without GPU)."""
    client = DoclingContainerClient()

    async with client:
        # Parse simple text file
        parsed = await client.parse_document(sample_documents["simple_txt"])

        # Verify result
        assert isinstance(parsed, DoclingParsedDocument)
        assert "simple test document" in parsed.text.lower()
        assert len(parsed.text) > 0


# =============================================================================
# Integration Tests: Batch Processing
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_processing_real(sample_documents):
    """Test batch processing with multiple files using real container."""
    client = DoclingContainerClient()

    async with client:
        batch_files = sample_documents["batch_files"]
        print(f"\n[TEST] Batch processing {len(batch_files)} files...")

        batch_start = time.time()
        results = await client.parse_batch(batch_files)
        batch_duration = time.time() - batch_start

        # Verify results
        assert len(results) == len(batch_files)
        assert all(isinstance(r, DoclingParsedDocument) for r in results)

        print(f"[TEST] Batch processed in {batch_duration:.2f}s")
        print(f"[TEST] Avg time per doc: {batch_duration/len(batch_files):.2f}s")


# =============================================================================
# Integration Tests: Error Handling
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_nonexistent_file_real():
    """Test error handling when file does not exist."""
    client = DoclingContainerClient()

    with pytest.raises(FileNotFoundError):
        await client.parse_document(Path("/nonexistent/file.pdf"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_container_timeout_handling():
    """Test timeout handling with very short timeout."""
    client = DoclingContainerClient(timeout_seconds=1)  # Very short timeout

    # This should timeout on health check (container takes >1s to start)
    with pytest.raises(IngestionError, match="health check timeout"):
        await client._wait_for_ready(max_wait_seconds=2)


# =============================================================================
# Integration Tests: Performance Benchmarks
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.skipif(
    not Path("data/sample_documents").exists(),
    reason="Requires PDF files for benchmarking"
)
async def test_performance_benchmark_pdf_parsing():
    """Benchmark: Measure parsing speed for different document types.

    Target: <5s for typical 10-page PDF
    """
    pdf_dir = Path("data/sample_documents")
    pdf_files = list(pdf_dir.rglob("*.pdf"))[:5]  # Test first 5 PDFs

    if not pdf_files:
        pytest.skip("No PDF files for benchmarking")

    client = DoclingContainerClient()

    async with client:
        timings = []

        for pdf_file in pdf_files:
            start = time.time()
            parsed = await client.parse_document(pdf_file)
            duration = time.time() - start

            timings.append({
                "file": pdf_file.name,
                "size_kb": pdf_file.stat().st_size / 1024,
                "duration_s": duration,
                "text_length": len(parsed.text),
                "tables": len(parsed.tables),
            })

            print(f"[BENCHMARK] {pdf_file.name}: {duration:.2f}s ({len(parsed.text)} chars)")

        # Calculate statistics
        avg_duration = sum(t["duration_s"] for t in timings) / len(timings)
        print(f"\n[BENCHMARK] Average parse time: {avg_duration:.2f}s")

        # Assert reasonable performance (adjust based on actual hardware)
        # Note: First parse is slower due to model loading
        assert avg_duration < 30, f"Avg parse time {avg_duration:.1f}s exceeds 30s target"


# =============================================================================
# Integration Tests: Convenience Function
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_convenience_function_auto_manage(sample_documents):
    """Test convenience function with automatic container management."""
    # This should start and stop container automatically
    parsed = await parse_document_with_docling(
        sample_documents["simple_txt"],
        auto_manage_container=True
    )

    # Verify result
    assert isinstance(parsed, DoclingParsedDocument)
    assert len(parsed.text) > 0


# =============================================================================
# Integration Tests: GPU Memory Monitoring
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.gpu
async def test_gpu_memory_usage_monitoring(sample_documents):
    """Monitor GPU memory usage during parsing (requires nvidia-smi).

    This test checks for memory leaks by parsing multiple documents
    and monitoring VRAM usage.
    """
    import subprocess

    def get_gpu_memory_mb():
        """Get current GPU memory usage in MB."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                check=True,
            )
            return int(result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("nvidia-smi not available")

    client = DoclingContainerClient()

    async with client:
        # Measure initial GPU memory
        initial_memory = get_gpu_memory_mb()
        print(f"\n[GPU] Initial VRAM: {initial_memory}MB")

        # Parse multiple documents
        memory_readings = []
        for i in range(5):
            await client.parse_document(sample_documents["batch_files"][0])
            current_memory = get_gpu_memory_mb()
            memory_readings.append(current_memory)
            print(f"[GPU] After parse {i+1}: {current_memory}MB")
            await asyncio.sleep(1)  # Brief pause

        # Check for memory leak (memory should not grow unbounded)
        memory_growth = max(memory_readings) - initial_memory
        print(f"[GPU] Max memory growth: {memory_growth}MB")

        # Warning if memory grows >500MB (indicates leak)
        if memory_growth > 500:
            pytest.fail(f"Possible GPU memory leak detected: {memory_growth}MB growth")


# =============================================================================
# Integration Tests: Container Restart
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_container_restart_between_batches():
    """Test container can be restarted between batches (memory leak mitigation)."""
    client = DoclingContainerClient()

    # First batch
    await client.start_container()
    assert client._container_running is True
    await client.stop_container()
    assert client._container_running is False

    # Second batch (restart)
    await client.start_container()
    assert client._container_running is True
    await client.stop_container()
    assert client._container_running is False

    print("[TEST] Container successfully restarted between batches")

# =============================================================================
# Integration Tests: Feature 21.5 - Table/Image/Layout Extraction
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.gpu
async def test_extract_tables_images_layout_from_pdf():
    """Test Feature 21.5: Extract tables, images, and layout from PDFs.

    Tests extraction of rich metadata from Docling JSON content:
    - Tables with captions, page numbers, bounding boxes
    - Images/pictures with captions and provenance
    - Layout information (schema, pages, texts count)

    Uses specific test documents to ensure consistent results.
    """
    from pathlib import Path

    # Use OTByteArray.pdf: small (446KB), quick to parse for initial testing
    test_pdf = Path("C:/Users/Klaus Pommer/OneDrive - Pommer IT-Consulting GmbH/99_Studium_Klaus/AEGIS_Rag/data/sample_documents/OTByteArray.pdf")

    assert test_pdf.exists(), f"Test PDF not found: {test_pdf}"

    test_pdfs = [test_pdf]  # Use small PDF for quick smoke test

    print(f"\n[TEST] Feature 21.5: Testing {len(test_pdfs)} PDFs for metadata extraction")

    client = DoclingContainerClient(base_url="http://localhost:8080")

    async with client:
        for pdf_file in test_pdfs:
            print(f"\n[TEST] Parsing: {pdf_file.name}")
            parsed = await client.parse_document(pdf_file)

            # Verify basic parsing
            assert isinstance(parsed, DoclingParsedDocument)
            assert len(parsed.text) > 0, f"{pdf_file.name}: Should have extracted text"

            # Feature 21.5: Verify tables extraction
            print(f"  Tables found: {len(parsed.tables)}")
            if parsed.tables:
                table = parsed.tables[0]
                assert "ref" in table, "Table should have 'ref' field"
                assert "label" in table, "Table should have 'label' field"
                assert "captions" in table, "Table should have 'captions' field"
                assert "page_no" in table, "Table should have 'page_no' field"
                assert "bbox" in table, "Table should have 'bbox' field"
                print(f"    First table: ref={table['ref']}, page={table['page_no']}")

            # Feature 21.5: Verify images extraction
            print(f"  Images found: {len(parsed.images)}")
            if parsed.images:
                image = parsed.images[0]
                assert "ref" in image, "Image should have 'ref' field"
                assert "label" in image, "Image should have 'label' field"
                assert "captions" in image, "Image should have 'captions' field"
                assert "page_no" in image, "Image should have 'page_no' field"
                assert "bbox" in image, "Image should have 'bbox' field"
                print(f"    First image: ref={image['ref']}, page={image['page_no']}")

            # Feature 21.5: Verify layout extraction
            print(f"  Layout info:")
            assert isinstance(parsed.layout, dict), "Layout should be a dict"
            assert "schema_name" in parsed.layout, "Layout should have 'schema_name'"
            assert "version" in parsed.layout, "Layout should have 'version'"
            assert "pages" in parsed.layout, "Layout should have 'pages'"
            assert "texts_count" in parsed.layout, "Layout should have 'texts_count'"
            assert "groups_count" in parsed.layout, "Layout should have 'groups_count'"
            print(f"    Schema: {parsed.layout.get('schema_name')}")
            print(f"    Pages: {len(parsed.layout.get('pages', {}))}")
            print(f"    Texts: {parsed.layout.get('texts_count')}")

            # Verify metadata
            assert "schema_name" in parsed.metadata, "Metadata should include schema_name"
            assert "version" in parsed.metadata, "Metadata should include version"
            print(f"  Metadata: {list(parsed.metadata.keys())}")

            # Verify parse time
            assert parsed.parse_time_ms > 0, "Parse time should be recorded"
            print(f"  Parse time: {parsed.parse_time_ms:.0f}ms")

    print("\n[TEST] Feature 21.5: All metadata extraction tests passed!")
