"""Integration tests for Image-Enhanced Ingestion Pipeline - Sprint 21 Feature 21.6.

These tests verify the full E2E pipeline with Docker containers:
1. Docling Container (CUDA) - Document parsing + image extraction
2. Qwen3-VL (Ollama) - VLM image description
3. HybridChunker - BGE-M3 chunking with BBox mapping
4. Qdrant - Full provenance storage
5. Neo4j - Minimal provenance storage

Requirements:
- Docker + NVIDIA Container Toolkit installed
- docker-compose.yml configured
- Ollama with qwen3-vl:4b-instruct model pulled

Run with: pytest tests/integration/components/ingestion/test_image_pipeline_integration.py -v
"""

import asyncio
import time
from pathlib import Path

import pytest

# Mark all tests as integration and requiring Docker
pytestmark = [pytest.mark.integration, pytest.mark.docker]


# =============================================================================
# FIXTURES & SETUP
# =============================================================================


@pytest.fixture(scope="module")
def test_pdf_with_images(tmp_path_factory):
    """Create or use a test PDF with images for integration testing.

    For real integration testing, you should provide a sample PDF.
    This fixture returns a path to test documents.
    """
    test_docs_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "test_documents"
    test_docs_dir.mkdir(parents=True, exist_ok=True)

    # Check if test PDF exists
    test_pdf = test_docs_dir / "sample_with_images.pdf"

    if not test_pdf.exists():
        pytest.skip(
            f"Test PDF not found: {test_pdf}. "
            "Please add a sample PDF with images to data/test_documents/"
        )

    return test_pdf


@pytest.fixture(scope="module")
async def docker_services():
    """Ensure Docker services are running before tests.

    This fixture checks and starts necessary Docker containers:
    - Docling (ingestion profile)
    - Ollama (for Qwen3-VL)
    - Qdrant
    - Neo4j
    """
    import subprocess

    required_services = ["ollama", "qdrant", "neo4j"]

    # Check if services are running
    result = subprocess.run(
        ["docker", "compose", "ps", "--services", "--filter", "status=running"],
        capture_output=True,
        text=True,
        check=False,
    )

    running_services = set(result.stdout.strip().split("\n"))

    # Start missing services
    for service in required_services:
        if service not in running_services:
            print(f"Starting {service}...")
            subprocess.run(
                ["docker", "compose", "up", "-d", service],
                check=True,
            )

    # Start Docling with ingestion profile
    if "docling" not in running_services:
        print("Starting Docling container (ingestion profile)...")
        result = subprocess.run(
            ["docker", "compose", "--profile", "ingestion", "up", "-d", "docling"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            print(f"Warning: Could not start Docling: {result.stderr}")
            print("Checking if Docling is already running...")
            # Re-check running services
            check_result = subprocess.run(
                ["docker", "ps", "--filter", "name=aegis-docling", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if "aegis-docling" not in check_result.stdout:
                raise RuntimeError(f"Failed to start Docling: {result.stderr}")

    # Wait for services to be healthy
    print("Waiting for services to be healthy...")
    await asyncio.sleep(10)  # Give services time to start

    # Verify Ollama has Qwen3-VL model
    try:
        result = subprocess.run(
            ["docker", "exec", "aegis-ollama", "ollama", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        if "qwen3-vl" not in result.stdout:
            pytest.skip("Qwen3-VL model not found in Ollama. Run: ollama pull qwen3-vl:4b-instruct")
    except subprocess.CalledProcessError:
        pytest.skip("Could not verify Ollama models")

    yield

    # Cleanup: Stop Docling container after tests
    print("Stopping Docling container...")
    subprocess.run(["docker", "compose", "stop", "docling"], check=False)


# =============================================================================
# FULL PIPELINE INTEGRATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_full_image_pipeline__pdf_with_images__success(
    test_pdf_with_images, docker_services
):
    """Test complete E2E pipeline: Docling → VLM → Chunking → Qdrant → Neo4j.

    This is the main integration test for Feature 21.6.
    """
    from src.components.ingestion.docling_client import DoclingContainerClient
    from src.components.ingestion.image_processor import ImageProcessor
    from src.components.ingestion.ingestion_state import IngestionState
    from src.components.ingestion.langgraph_nodes import (
        chunking_node,
        docling_extraction_node,
        embedding_node,
        graph_extraction_node,
        image_enrichment_node,
        memory_check_node,
    )

    # Initialize state
    state: IngestionState = {
        "document_id": "test-integration-001",
        "document_path": str(test_pdf_with_images),
        "batch_index": 0,
        "errors": [],
        "overall_progress": 0.0,
    }

    # NODE 1: Memory Check
    print("\n=== NODE 1: Memory Check ===")
    state = await memory_check_node(state)
    assert state["memory_check_passed"] is True
    print(f"✓ Memory check passed (RAM: {state['current_memory_mb']:.0f}MB)")

    # NODE 2: Docling Extraction (with BBox + page dimensions)
    print("\n=== NODE 2: Docling Extraction ===")
    state = await docling_extraction_node(state)
    assert state["docling_status"] == "completed"
    assert "document" in state
    assert "page_dimensions" in state
    print(f"✓ Docling extraction completed")
    print(f"  Pages: {len(state['page_dimensions'])}")
    print(f"  Images: {len(state['document'].pictures) if hasattr(state['document'], 'pictures') else 0}")

    # NODE 2.5: VLM Image Enrichment
    print("\n=== NODE 2.5: VLM Image Enrichment ===")
    images_before = len(state["document"].pictures) if hasattr(state["document"], "pictures") else 0

    state = await image_enrichment_node(state)

    if images_before > 0:
        assert state["enrichment_status"] in ["completed", "failed"]
        if state["enrichment_status"] == "completed":
            assert len(state["vlm_metadata"]) > 0
            print(f"✓ VLM enrichment completed")
            print(f"  Images processed: {len(state['vlm_metadata'])}/{images_before}")

            # Verify VLM text was inserted into document
            for pic in state["document"].pictures:
                if hasattr(pic, "text") and pic.text:
                    print(f"  Sample VLM text: {pic.text[:100]}...")
                    break
        else:
            print(f"⚠ VLM enrichment failed (non-critical): {state.get('errors', [])}")
    else:
        assert state["enrichment_status"] == "skipped"
        print("✓ VLM enrichment skipped (no images)")

    # NODE 3: Chunking with HybridChunker + BBox mapping
    print("\n=== NODE 3: Chunking (HybridChunker) ===")
    state = await chunking_node(state)
    assert state["chunking_status"] == "completed"
    assert len(state["chunks"]) > 0
    print(f"✓ Chunking completed")
    print(f"  Chunks created: {len(state['chunks'])}")

    # Check for image annotations in chunks
    chunks_with_images = sum(1 for c in state["chunks"] if c.get("image_bboxes"))
    print(f"  Chunks with images: {chunks_with_images}")

    # NODE 4: Embedding with full provenance
    print("\n=== NODE 4: Embedding (Qdrant) ===")
    state = await embedding_node(state)
    assert state["embedding_status"] == "completed"
    assert len(state["embedded_chunk_ids"]) > 0
    print(f"✓ Embedding completed")
    print(f"  Points uploaded to Qdrant: {len(state['embedded_chunk_ids'])}")

    # NODE 5: Graph extraction with minimal provenance
    print("\n=== NODE 5: Graph Extraction (Neo4j) ===")
    state = await graph_extraction_node(state)
    assert state["graph_status"] == "completed"
    print(f"✓ Graph extraction completed")

    # VERIFICATION: Check Qdrant
    print("\n=== VERIFICATION: Qdrant ===")
    from src.components.vector_search.qdrant_client import QdrantClientWrapper
    from src.core.config import get_settings

    qdrant = QdrantClientWrapper()
    settings = get_settings()

    # Retrieve one chunk with annotations
    if chunks_with_images > 0:
        chunk_id = state["embedded_chunk_ids"][0]
        points = await qdrant.retrieve(
            collection_name=settings.qdrant_collection,
            ids=[chunk_id],
            with_payload=True,
        )

        if points and len(points) > 0:
            payload = points[0].payload
            print(f"✓ Sample chunk retrieved from Qdrant")
            print(f"  Contains images: {payload.get('contains_images', False)}")
            print(f"  Image annotations: {len(payload.get('image_annotations', []))}")

            if payload.get("image_annotations"):
                annot = payload["image_annotations"][0]
                print(f"  Sample annotation VLM: {annot.get('vlm_model', 'N/A')}")
                print(f"  Has BBox: {annot.get('bbox_absolute') is not None}")

    print("\n=== INTEGRATION TEST PASSED ===")


@pytest.mark.asyncio
async def test_docling_container__health_check__success(docker_services):
    """Test that Docling container is running and healthy."""
    import httpx

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8080/health", timeout=5.0)
            assert response.status_code == 200
            print("✓ Docling container is healthy")
        except httpx.RequestError as e:
            pytest.fail(f"Docling container not reachable: {e}")


@pytest.mark.asyncio
async def test_ollama_qwen3vl__model_available__success(docker_services):
    """Test that Qwen3-VL model is available in Ollama."""
    import subprocess

    result = subprocess.run(
        ["docker", "exec", "aegis-ollama", "ollama", "list"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "qwen3-vl" in result.stdout
    print("✓ Qwen3-VL model available in Ollama")


@pytest.mark.asyncio
async def test_qdrant__connection__success(docker_services):
    """Test Qdrant connection and collection creation."""
    from src.components.vector_search.qdrant_client import QdrantClientWrapper

    qdrant = QdrantClientWrapper()

    # Try to create collection (idempotent)
    await qdrant.create_collection(
        collection_name="test_integration_collection",
        vector_size=1024,  # BGE-M3
    )

    print("✓ Qdrant connection successful")


@pytest.mark.asyncio
async def test_neo4j__connection__success(docker_services):
    """Test Neo4j connection."""
    from neo4j import AsyncGraphDatabase
    from src.core.config import get_settings

    settings = get_settings()

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
    )

    try:
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS test")
            record = await result.single()
            assert record["test"] == 1
        print("✓ Neo4j connection successful")
    finally:
        await driver.close()


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.slow
async def test_vlm_processing__performance__acceptable_latency(docker_services):
    """Test VLM processing latency is acceptable (<30s per image)."""
    from PIL import Image
    from src.components.ingestion.image_processor import ImageProcessor

    processor = ImageProcessor()

    # Create test image (400x400 passes size filter)
    test_image = Image.new("RGB", (400, 400), color=(100, 150, 200))

    start_time = time.time()
    # skip_filtering=True to ensure VLM is called even if image fails filters
    description = processor.process_image(test_image, picture_index=0, skip_filtering=True)
    elapsed = time.time() - start_time

    assert description is not None, "VLM should return description for test image"
    assert len(description) > 10  # Should have meaningful description
    assert elapsed < 30.0  # Should be faster than 30 seconds

    print(f"[OK] VLM processing time: {elapsed:.2f}s")
    print(f"  Description: {description[:100]}...")

    processor.cleanup()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_pipeline__memory_usage__within_limits(
    test_pdf_with_images, docker_services
):
    """Test that full pipeline stays within memory limits."""
    import psutil

    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    # Run full pipeline (copy from main test, but focus on memory)
    from src.components.ingestion.ingestion_state import IngestionState
    from src.components.ingestion.langgraph_nodes import (
        chunking_node,
        docling_extraction_node,
        embedding_node,
        image_enrichment_node,
        memory_check_node,
    )

    state: IngestionState = {
        "document_id": "test-memory-001",
        "document_path": str(test_pdf_with_images),
        "batch_index": 0,
        "errors": [],
        "overall_progress": 0.0,
    }

    state = await memory_check_node(state)
    state = await docling_extraction_node(state)
    state = await image_enrichment_node(state)
    state = await chunking_node(state)
    state = await embedding_node(state)

    mem_after = process.memory_info().rss / 1024 / 1024  # MB
    mem_increase = mem_after - mem_before

    print(f"✓ Memory usage:")
    print(f"  Before: {mem_before:.0f}MB")
    print(f"  After: {mem_after:.0f}MB")
    print(f"  Increase: {mem_increase:.0f}MB")

    # Should not exceed 2GB increase
    assert mem_increase < 2000, f"Memory increase too high: {mem_increase:.0f}MB"


# =============================================================================
# ERROR HANDLING & EDGE CASES
# =============================================================================


@pytest.mark.asyncio
async def test_pipeline__invalid_pdf__handles_gracefully(docker_services, tmp_path):
    """Test pipeline handles invalid PDF gracefully."""
    from src.components.ingestion.ingestion_state import IngestionState
    from src.components.ingestion.langgraph_nodes import docling_extraction_node

    # Create invalid PDF
    invalid_pdf = tmp_path / "invalid.pdf"
    invalid_pdf.write_text("This is not a valid PDF")

    state: IngestionState = {
        "document_id": "test-invalid-001",
        "document_path": str(invalid_pdf),
        "batch_index": 0,
        "errors": [],
        "overall_progress": 0.0,
    }

    # Should raise IngestionError
    with pytest.raises(Exception):  # Could be IngestionError or other
        await docling_extraction_node(state)


@pytest.mark.asyncio
async def test_vlm_enrichment__no_ollama__fails_gracefully(docker_services):
    """Test VLM enrichment handles Ollama unavailability."""
    from src.components.ingestion.image_processor import ImageProcessor
    from PIL import Image
    from unittest.mock import patch

    processor = ImageProcessor()

    # Mock ollama.chat to fail (ImageProcessor uses ollama module-level function)
    with patch("src.components.ingestion.image_processor.ollama.chat", side_effect=Exception("Ollama down")):
        test_image = Image.new("RGB", (200, 200))

        # Process should return None on error (not raise)
        description = processor.process_image(test_image, picture_index=0, skip_filtering=True)
        assert description is None, "ImageProcessor should return None on Ollama error"

    processor.cleanup()


# =============================================================================
# CLEANUP
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def cleanup_test_data():
    """Cleanup test data after all tests."""
    yield

    # Clean up test collections/databases
    print("\n=== Cleanup ===")

    # Note: In real scenario, you might want to clean up test data from Qdrant/Neo4j
    # For now, we keep it for manual inspection

    print("[OK] Integration tests complete")
