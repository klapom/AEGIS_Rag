"""Pytest configuration and fixtures for Sprint 2 Tests."""

import asyncio
import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# Setup logger for fixture debugging
logger = logging.getLogger(__name__)
from fastapi.testclient import TestClient
from qdrant_client.models import (
    CollectionDescription,
    CollectionsResponse,
    ScoredPoint,
)

# WORKAROUND (Sprint 8): Optional import of app to avoid graphiti dependency conflict
# See docs/SPRINT_8_BLOCKER.md for details
try:
    from src.api.main import app
except ModuleNotFoundError as e:
    if "graphiti" in str(e):
        app = None  # Sprint 8 tests can run without FastAPI app
    else:
        raise

from src.core.config import get_settings

# ============================================================================
# Basic Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def disable_auth_for_tests(monkeypatch):
    """Disable API authentication and relax path validation for all tests.

    This fixture automatically disables JWT authentication and sets documents_base_path
    to root to allow test paths.
    """
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    # Force reload settings
    from src.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "api_auth_enabled", False)
    # Allow all paths for testing (security validation still runs, just with permissive base)
    monkeypatch.setattr(settings, "documents_base_path", "/")


@pytest.fixture
def mock_rate_limiter(monkeypatch):
    """Mock the rate limiter to disable rate limiting for API tests.

    This fixture should be explicitly used in API test modules that make many requests.
    """
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    from src.api import middleware

    # Create a limiter with very high limits for testing
    test_limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["10000/hour"],  # Very high limit for tests
        storage_uri="memory://",
    )
    monkeypatch.setattr(middleware, "limiter", test_limiter)


@pytest.fixture
def test_client() -> TestClient:
    """Create a FastAPI test client.

    Returns:
        Test client for API testing
    """
    if app is None:
        pytest.skip("FastAPI app not available (graphiti dependency conflict)")

    # Disable rate limiting by removing the limiter state from the app
    if hasattr(app.state, "limiter"):
        delattr(app.state, "limiter")

    return TestClient(app)


@pytest.fixture
def settings():
    """Get application settings.

    Returns:
        Settings instance
    """
    return get_settings()


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_query() -> str:
    """Sample query for testing.

    Returns:
        Sample query string
    """
    return "What are the main components of AEGIS RAG?"


@pytest.fixture
def sample_documents() -> list[dict[str, Any]]:
    """Sample documents for testing.

    Returns:
        List of sample document dicts
    """
    return [
        {
            "id": "doc1",
            "text": "AEGIS RAG consists of four main components: Vector Search, Graph Reasoning, Temporal Memory, and Tool Integration.",
            "source": "architecture.md",
            "document_id": "doc1",
        },
        {
            "id": "doc2",
            "text": "The Vector Search component uses Qdrant for hybrid search with BM25 and vector similarity.",
            "source": "tech-stack.md",
            "document_id": "doc2",
        },
        {
            "id": "doc3",
            "text": "Graph Reasoning is powered by LightRAG and Neo4j for multi-hop reasoning.",
            "source": "components.md",
            "document_id": "doc3",
        },
        {
            "id": "doc4",
            "text": "Temporal Memory maintains conversation context and tracks user preferences over time.",
            "source": "features.md",
            "document_id": "doc4",
        },
        {
            "id": "doc5",
            "text": "Tool Integration enables the RAG system to call external APIs and tools dynamically.",
            "source": "integration.md",
            "document_id": "doc5",
        },
    ]


@pytest.fixture
def sample_texts() -> list[str]:
    """Sample texts for embedding testing.

    Returns:
        List of sample text strings
    """
    return [
        "This is the first test document about machine learning.",
        "The second document discusses natural language processing.",
        "Document three covers vector databases and embeddings.",
        "The fourth text is about retrieval augmented generation.",
        "Finally, the fifth document talks about hybrid search.",
    ]


@pytest.fixture
def sample_embedding() -> list[float]:
    """Sample embedding vector (1024-dim for bge-m3).

    Returns:
        Mock embedding vector
    """
    return [0.1] * 1024


@pytest.fixture
def sample_embeddings(sample_texts: list[str]) -> list[list[float]]:
    """Sample embeddings for multiple texts.

    Returns:
        List of mock embedding vectors
    """
    return [[0.1 + i * 0.01] * 1024 for i in range(len(sample_texts))]


@pytest.fixture
def test_collection_name() -> str:
    """Unique test collection name.

    Returns:
        Collection name with random suffix
    """
    return f"test_collection_{uuid4().hex[:8]}"


# ============================================================================
# Mock Qdrant Client Fixtures
# ============================================================================


@pytest.fixture
def mock_qdrant_collections():
    """Mock Qdrant collections response."""
    return CollectionsResponse(
        collections=[
            CollectionDescription(name="test_collection"),
            CollectionDescription(name="aegis_documents"),
        ]
    )


@pytest.fixture
def mock_scored_points() -> list[ScoredPoint]:
    """Mock Qdrant search results."""
    return [
        ScoredPoint(
            id="point1",
            score=0.95,
            payload={
                "text": "AEGIS RAG is a multi-agent system.",
                "source": "docs.md",
                "document_id": "doc1",
            },
            version=1,
        ),
        ScoredPoint(
            id="point2",
            score=0.87,
            payload={
                "text": "Vector search uses Qdrant and nomic-embed-text.",
                "source": "tech.md",
                "document_id": "doc2",
            },
            version=1,
        ),
        ScoredPoint(
            id="point3",
            score=0.75,
            payload={
                "text": "Hybrid search combines vector and BM25 ranking.",
                "source": "search.md",
                "document_id": "doc3",
            },
            version=1,
        ),
    ]


@pytest.fixture
def mock_qdrant_client(mock_qdrant_collections, mock_scored_points):
    """Mock QdrantClientWrapper for unit tests.

    Returns:
        Mock Qdrant client with configured behavior
    """
    client = MagicMock()
    async_client = AsyncMock()

    # Configure async client methods
    async_client.get_collections.return_value = mock_qdrant_collections
    async_client.create_collection.return_value = True
    async_client.upsert.return_value = MagicMock(status="completed")
    async_client.search.return_value = mock_scored_points
    async_client.scroll.return_value = ([], None)
    async_client.delete_collection.return_value = True
    async_client.get_collection.return_value = MagicMock(
        vectors_count=100,
        points_count=100,
        indexed_vectors_count=100,
        status="green",
    )
    async_client.close.return_value = None

    # Attach async_client to wrapper mock
    wrapper = MagicMock()
    wrapper.async_client = async_client
    wrapper.client = client
    wrapper.host = "localhost"
    wrapper.port = 6333
    wrapper.collection_name = "test_collection"

    # Configure wrapper methods
    wrapper.health_check = AsyncMock(return_value=True)
    wrapper.create_collection = AsyncMock(return_value=True)
    wrapper.upsert_points = AsyncMock(return_value=True)
    wrapper.search = AsyncMock(
        return_value=[
            {
                "id": "point1",
                "score": 0.95,
                "payload": {
                    "text": "AEGIS RAG is a multi-agent system.",
                    "source": "docs.md",
                    "document_id": "doc1",
                },
            }
        ]
    )
    wrapper.get_collection_info = AsyncMock(
        return_value=MagicMock(
            vectors_count=100,
            points_count=100,
        )
    )
    wrapper.delete_collection = AsyncMock(return_value=True)
    wrapper.close = AsyncMock(return_value=None)

    return wrapper


# ============================================================================
# Mock Embedding Service Fixtures
# ============================================================================


@pytest.fixture
def mock_ollama_embedding_model():
    """Mock OllamaEmbedding model."""
    model = AsyncMock()
    model.aget_text_embedding = AsyncMock(return_value=[0.1] * 1024)
    model.aget_text_embedding_batch = AsyncMock(
        return_value=[[0.1 + i * 0.01] * 1024 for i in range(5)]
    )
    return model


@pytest.fixture
def mock_embedding_service(mock_ollama_embedding_model, sample_embedding):
    """Mock EmbeddingService for unit tests.

    Returns:
        Mock embedding service with configured behavior
    """
    from src.components.shared.embedding_service import LRUCache

    service = MagicMock()
    service.model_name = "nomic-embed-text"
    service.base_url = "http://localhost:11434"
    service.batch_size = 32
    service.enable_cache = True
    service._cache = LRUCache(max_size=10000)  # Use actual LRUCache instead of dict
    service._embedding_model = mock_ollama_embedding_model

    # Configure methods
    service.embed_text = AsyncMock(return_value=sample_embedding)
    service.embed_batch = AsyncMock(return_value=[[0.1 + i * 0.01] * 1024 for i in range(5)])
    service.get_embedding_dimension = MagicMock(return_value=1024)
    service.clear_cache = MagicMock()
    service.get_cache_size = MagicMock(return_value=0)
    service._get_cache_key = MagicMock(return_value="test_hash")

    return service


# ============================================================================
# Mock BM25 Search Fixtures
# ============================================================================


@pytest.fixture
def mock_bm25_search(sample_documents):
    """Mock BM25Search for unit tests.

    Returns:
        Mock BM25 search with configured behavior
    """
    search = MagicMock()
    search._corpus = [doc["text"] for doc in sample_documents]
    search._metadata = [{"id": doc["id"], "source": doc["source"]} for doc in sample_documents]
    search._is_fitted = True
    search._bm25 = MagicMock()

    # Configure methods
    search.fit = MagicMock()
    search.search = MagicMock(
        return_value=[
            {
                "text": doc["text"],
                "score": 10.0 - i,
                "metadata": {"id": doc["id"], "source": doc["source"]},
                "rank": i + 1,
            }
            for i, doc in enumerate(sample_documents[:3])
        ]
    )
    search.get_corpus_size = MagicMock(return_value=len(sample_documents))
    search.is_fitted = MagicMock(return_value=True)
    search.clear = MagicMock()
    search._tokenize = MagicMock(side_effect=lambda text: text.lower().split())

    return search


# ============================================================================
# Mock LlamaIndex Fixtures
# ============================================================================


@pytest.fixture
def mock_llama_documents():
    """Mock LlamaIndex Document objects."""
    from llama_index.core import Document

    return [
        Document(
            text="This is test document 1 about AEGIS RAG.",
            metadata={"file_name": "doc1.txt", "file_path": "/tmp/doc1.txt"},
            doc_id="doc1",
        ),
        Document(
            text="This is test document 2 about vector search.",
            metadata={"file_name": "doc2.txt", "file_path": "/tmp/doc2.txt"},
            doc_id="doc2",
        ),
        Document(
            text="This is test document 3 about hybrid retrieval.",
            metadata={"file_name": "doc3.txt", "file_path": "/tmp/doc3.txt"},
            doc_id="doc3",
        ),
    ]


@pytest.fixture
def mock_llama_nodes(mock_llama_documents):
    """Mock LlamaIndex TextNode objects."""
    from llama_index.core.schema import TextNode

    nodes = []
    for idx, doc in enumerate(mock_llama_documents):
        node = TextNode(
            text=doc.text,
            metadata=doc.metadata,
            id_=f"node_{idx}",
            ref_doc_id=doc.doc_id,
        )
        nodes.append(node)
    return nodes


@pytest.fixture
def mock_directory_reader(mock_llama_documents):
    """Mock LlamaIndex SimpleDirectoryReader."""
    reader = MagicMock()
    reader.load_data.return_value = mock_llama_documents
    return reader


# ============================================================================
# Temporary Test Directory Fixtures
# ============================================================================


@pytest.fixture
def temp_test_dir(tmp_path: Path) -> Path:
    """Create temporary test directory with sample files.

    Args:
        tmp_path: Pytest temporary path fixture

    Returns:
        Path to test directory with sample files
    """
    test_dir = tmp_path / "test_documents"
    test_dir.mkdir()

    # Create sample text files
    (test_dir / "doc1.txt").write_text("This is test document 1 about AEGIS RAG.")
    (test_dir / "doc2.txt").write_text("This is test document 2 about vector search.")
    (test_dir / "doc3.md").write_text("# Test Document 3\n\nHybrid retrieval system.")

    return test_dir


# ============================================================================
# Async Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for Windows compatibility."""
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="function")
def event_loop():
    """Create event loop for each test function."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# E2E Integration Test Fixtures (Sprint 7: NO MOCKS - Real Services Only)
# ============================================================================


@pytest.fixture(scope="session")
async def redis_client():
    """Real Redis client for Layer 1 short-term memory (E2E testing).

    Connects to real Redis instance at localhost:6379/0.
    Automatically cleans up test data after session.

    Returns:
        Async Redis client
    """
    from redis.asyncio import Redis

    client = await Redis.from_url(
        "redis://localhost:6379/0",
        encoding="utf-8",
        decode_responses=True,
    )

    # Verify connection
    try:
        await client.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    yield client

    # Cleanup: flush test database
    await client.flushdb()
    await client.close()


@pytest.fixture(scope="function")
async def redis_checkpointer():
    """Redis checkpointer with proper async cleanup.

    Sprint 12: Ensures Redis connections closed before event loop shutdown.
    """
    import structlog

    from src.agents.checkpointer import create_redis_checkpointer

    logger = structlog.get_logger(__name__)

    # Create checkpointer
    checkpointer = create_redis_checkpointer()

    yield checkpointer

    # Proper async cleanup BEFORE event loop closes
    if hasattr(checkpointer, "aclose"):
        await checkpointer.aclose()
        logger.debug("redis_checkpointer_cleaned_up")


@pytest.fixture(scope="session")
def qdrant_client_real():
    """Real Qdrant client for Layer 2 long-term memory (E2E testing).

    Connects to real Qdrant instance at localhost:6333.
    Automatically cleans up test collections after session.

    Returns:
        Qdrant client
    """
    from qdrant_client import QdrantClient

    client = QdrantClient(host="localhost", port=6333)

    # Verify connection
    try:
        client.get_collections()
    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")

    yield client

    # Cleanup: delete test collections
    try:
        collections = client.get_collections()
        for collection in collections.collections:
            if collection.name.startswith("test_"):
                client.delete_collection(collection_name=collection.name)
    except Exception:
        pass


@pytest.fixture(scope="session")
def neo4j_driver():
    """Real Neo4j driver for Layer 3 episodic memory (E2E testing).

    Connects to real Neo4j instance at localhost:7687.
    Automatically cleans up test nodes/relationships after session.

    Returns:
        Neo4j driver
    """
    from neo4j import GraphDatabase

    from src.core.config import settings

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
    )

    # Verify connection
    try:
        driver.verify_connectivity()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")

    yield driver

    # Cleanup: delete test nodes and relationships
    with driver.session() as session:
        session.run(
            """
            MATCH (n)
            WHERE n.name STARTS WITH 'test_' OR n.source = 'test'
            DETACH DELETE n
            """
        )

    driver.close()


@pytest.fixture(scope="session")
async def ollama_client_real():
    """Real Ollama client for LLM calls (E2E testing).

    Connects to real Ollama instance at localhost:11434.
    Verifies required models are available.

    Returns:
        Async Ollama client
    """
    from ollama import AsyncClient

    client = AsyncClient(host="http://localhost:11434")

    # Verify models exist
    try:
        models_response = await client.list()
        available_models = [m.model for m in models_response.models]

        required_models = ["hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0", "nomic-embed-text"]
        # Check if models exist (with or without tag like :latest)
        missing_models = []
        for required in required_models:
            if not any(
                required in model or model.startswith(required + ":") for model in available_models
            ):
                missing_models.append(required)

        if missing_models:
            pytest.skip(f"Required Ollama models not available: {missing_models}")

    except Exception as e:
        pytest.skip(f"Ollama not available: {e}")

    yield client


@pytest.fixture
async def redis_memory_manager(redis_client):
    """Real RedisMemoryManager instance for E2E testing.

    Uses real Redis connection for testing Layer 1 short-term memory.

    Sprint 13: Fixed async cleanup to prevent event loop errors.

    Returns:
        RedisMemoryManager instance
    """
    import structlog

    from src.components.memory import RedisMemoryManager

    logger = structlog.get_logger(__name__)

    manager = RedisMemoryManager()
    yield manager

    # Proper async cleanup BEFORE event loop closes
    try:
        # Cleanup: flush test keys
        await redis_client.flushdb()

        # Close manager connection
        if hasattr(manager, "aclose"):
            await manager.aclose()
            logger.debug("redis_memory_manager_cleaned_up")
    except Exception as e:
        logger.warning("redis_memory_manager_cleanup_error", error=str(e))


@pytest.fixture
async def graphiti_wrapper(neo4j_driver, ollama_client_real):
    """Real GraphitiWrapper instance for E2E testing.

    Uses real Neo4j + Ollama for testing Layer 3 episodic memory.

    Sprint 13: Fixed async cleanup to prevent event loop errors.

    Returns:
        GraphitiWrapper instance
    """
    import structlog

    from src.components.memory import GraphitiWrapper

    logger = structlog.get_logger(__name__)

    try:
        wrapper = GraphitiWrapper()
        yield wrapper

        # Cleanup: delete test episodes (sync Neo4j session - driver is sync)
        logger.info("graphiti_wrapper_cleanup_start")
        with neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (e)
                WHERE e.source = 'test' OR e.name STARTS WITH 'test_'
                DETACH DELETE e
                """
            )
            logger.info(
                "graphiti_wrapper_cleanup_neo4j_done",
                deleted=result.consume().counters.nodes_deleted,
            )

        # Proper async cleanup BEFORE event loop closes
        if hasattr(wrapper, "aclose"):
            await wrapper.aclose()
            logger.debug("graphiti_wrapper_cleaned_up")
    except Exception as e:
        pytest.skip(f"Graphiti not available: {e}")


@pytest.fixture
async def memory_router(redis_memory_manager, qdrant_client_real, graphiti_wrapper):
    """Real MemoryRouter instance for E2E testing.

    Uses real services for testing 3-layer memory routing.

    Returns:
        MemoryRouter instance
    """
    from src.components.memory import MemoryRouter

    router = MemoryRouter(session_id="test_session_e2e")
    yield router

    # Cleanup handled by individual service fixtures


@pytest.fixture
async def temporal_query(neo4j_driver):
    """Real TemporalMemoryQuery instance for E2E testing.

    Uses real Neo4j for testing bi-temporal queries.

    Returns:
        TemporalMemoryQuery instance
    """
    from src.components.memory import TemporalMemoryQuery

    query = TemporalMemoryQuery()
    yield query

    # Cleanup handled by neo4j_driver fixture


@pytest.fixture
async def consolidation_pipeline(redis_memory_manager, qdrant_client_real, graphiti_wrapper):
    """Real MemoryConsolidationPipeline instance for E2E testing.

    Uses real services for testing memory consolidation.

    Returns:
        MemoryConsolidationPipeline instance
    """
    from src.components.memory import MemoryConsolidationPipeline

    pipeline = MemoryConsolidationPipeline()
    yield pipeline

    # Cleanup handled by individual service fixtures


@pytest.fixture(scope="session")
def ollama_embedding_service():
    """Real Ollama embedding service for E2E testing (Sprint 8).

    Uses real Ollama nomic-embed-text model for embeddings.
    Session-scoped to reuse across all tests (model loading is expensive).

    Returns:
        EmbeddingService instance
    """
    from src.components.vector_search.embeddings import EmbeddingService

    service = EmbeddingService(
        model_name="nomic-embed-text",
        base_url="http://localhost:11434",
        batch_size=32,
        enable_cache=True,
    )

    # Verify Ollama is available
    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        test_embedding = loop.run_until_complete(service.embed_text("test"))
        loop.close()

        if len(test_embedding) != 1024:
            pytest.skip("Ollama embedding dimension incorrect")
    except Exception as e:
        pytest.skip(f"Ollama embedding service not available: {e}")

    yield service

    # Cleanup: clear cache
    service.clear_cache()


@pytest.fixture
async def test_client_async():
    """Async FastAPI TestClient for E2E API testing.

    Uses httpx AsyncClient for testing real API endpoints.

    Returns:
        Async HTTP client
    """
    if app is None:
        pytest.skip("FastAPI app not available (graphiti dependency conflict)")

    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def lightrag_instance():
    """LightRAG instance with Neo4j cleanup.

    Sprint 11: Uses singleton LightRAG instance (avoids re-initialization)
    but cleans Neo4j database before each test for isolation.

    Sprint 13: Enhanced logging for debugging fixture connection issues.

    Returns:
        LightRAGWrapper: Singleton instance with llama3.2:3b model
    """
    logger.info("=== LIGHTRAG FIXTURE START ===")

    from neo4j import AsyncGraphDatabase

    from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
    from src.core.config import settings

    # Clean Neo4j, LightRAG caches, AND reset singleton BEFORE test
    try:
        logger.info("Step 1/3: Cleaning Neo4j database...")
        # 1. Clean Neo4j database
        # Note: Pydantic SecretStr needs .get_secret_value() to extract actual string
        neo4j_user = settings.neo4j_user
        neo4j_password = (
            settings.neo4j_password.get_secret_value()
            if hasattr(settings.neo4j_password, "get_secret_value")
            else settings.neo4j_password
        )

        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(neo4j_user, neo4j_password),
        )
        async with driver.session() as session:
            result = await session.run("MATCH (n) DETACH DELETE n")
            await result.consume()
            logger.info("Neo4j cleanup complete: deleted nodes/relationships")
        await driver.close()
        logger.info("Neo4j driver closed")

        logger.info("Step 2/3: Cleaning LightRAG local cache files...")
        # 2. Clean LightRAG local cache files (Windows-compatible approach)
        import shutil
        from pathlib import Path

        lightrag_dir = Path(settings.lightrag_working_dir)

        if lightrag_dir.exists():
            file_count = 0
            dir_count = 0
            # Delete all FILES in directory (safer than rmtree on Windows)
            # This avoids PermissionError when process has directory handle open
            for item in lightrag_dir.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                        file_count += 1
                    elif item.is_dir():
                        shutil.rmtree(item)
                        dir_count += 1
                except PermissionError as e:
                    # Skip files/dirs that are locked (best-effort cleanup)
                    logger.warning(f"PermissionError cleaning {item.name}: {e}")
                    pass
            logger.info(
                f"Cache cleanup complete: removed {file_count} files, {dir_count} directories"
            )
        else:
            # Create directory if it doesn't exist
            lightrag_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created LightRAG working directory: {lightrag_dir}")

        logger.info("Step 3/3: Resetting singleton instance...")
        # 3. Reset singleton instance so it re-initializes with clean state
        import src.components.graph_rag.lightrag_wrapper as lightrag_module

        lightrag_module._lightrag_wrapper = None
        logger.info("Singleton reset complete")
    except Exception as e:
        logger.error(f"Cleanup error (best-effort): {type(e).__name__}: {e}")
        pass  # Best-effort cleanup

    # Get fresh singleton instance (will re-initialize with clean caches)
    logger.info("Initializing LightRAG wrapper...")
    wrapper = await get_lightrag_wrapper_async()
    logger.info(f"LightRAG wrapper initialized: {type(wrapper).__name__} at {id(wrapper)}")
    logger.info("=== LIGHTRAG FIXTURE READY ===")

    yield wrapper

    logger.info("=== LIGHTRAG FIXTURE TEARDOWN ===")
    # Sprint 13 TD-26/27: Properly shutdown LightRAG workers to prevent event loop errors
    try:
        if hasattr(wrapper, "rag") and wrapper.rag is not None:
            import asyncio

            # LightRAG uses async worker pools that need cleanup
            logger.info("Shutting down LightRAG async workers...")

            # Cancel all pending tasks in the current event loop
            # This prevents workers from calling asyncio.get_event_loop().time() after teardown
            try:
                # Get all pending tasks except current task
                current_task = asyncio.current_task()
                pending_tasks = [
                    task
                    for task in asyncio.all_tasks()
                    if task is not current_task and not task.done()
                ]

                if pending_tasks:
                    logger.info(f"Cancelling {len(pending_tasks)} pending async tasks...")
                    for task in pending_tasks:
                        task.cancel()

                    # Wait for tasks to finish cancellation (with timeout)
                    await asyncio.wait(pending_tasks, timeout=2.0)
                    logger.info("All pending tasks cancelled")
                else:
                    logger.info("No pending tasks to cancel")
            except Exception as e:
                logger.warning(f"Task cancellation warning: {e}")

            # Give workers final grace period to shutdown
            logger.info("Waiting for workers to finish...")
            await asyncio.sleep(0.5)

        logger.info("LightRAG teardown complete")
    except Exception as e:
        logger.warning(f"Teardown warning (non-critical): {e}")

    # Note: No data cleanup after test - cleanup happens before next test
