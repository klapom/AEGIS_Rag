# TESTING STRATEGY - AEGIS RAG

**Purpose:** Compact guide for test architecture, patterns, and Sprint 13 focus areas
**Last Updated:** 2025-10-22 (Post-Sprint 12)
**Status:** Production Testing Framework Established

---

## TEST PYRAMID

### Distribution (Target Ratios)

```
        /\
       /  \  10% E2E Tests
      /────\  (Critical paths, NO MOCKS, ~52 tests)
     /      \
    /────────\ 30% Integration Tests
   /          \ (Real services, ~156 tests)
  /────────────\
 /              \ 60% Unit Tests
/────────────────\ (Fast, isolated, ~312 tests)
```

**Total Test Suite:** ~520 tests
**Current Pass Rate:** 90% overall, 88.5% E2E (Sprint 12 target: 80%)
**Execution Time:** <8 minutes (CI with Docker cache)

---

## KEY FIXTURES (tests/conftest.py)

### Real Service Fixtures (NO MOCKS - ADR-014)

#### 1. Redis Client (Layer 1 Memory)
```python
@pytest.fixture(scope="session")
async def redis_client():
    """Real Redis client for short-term memory testing.

    Location: localhost:6379/0
    Cleanup: Flushes test database after session
    Use: Session state, recent context, cache
    """
    from redis.asyncio import Redis

    client = await Redis.from_url(
        "redis://localhost:6379/0",
        encoding="utf-8",
        decode_responses=True,
    )

    await client.ping()  # Health check
    yield client

    await client.flushdb()  # Cleanup
    await client.close()
```

**Health Check Pattern:**
- Always verify connection with `ping()` before yield
- Skip test if service unavailable: `pytest.skip(f"Redis not available: {e}")`

#### 2. Qdrant Client (Layer 2 Memory)
```python
@pytest.fixture(scope="session")
def qdrant_client_real():
    """Real Qdrant client for vector search testing.

    Location: localhost:6333
    Cleanup: Deletes test_* collections after session
    Use: Semantic similarity, long-term memory
    """
    from qdrant_client import QdrantClient

    client = QdrantClient(host="localhost", port=6333)
    client.get_collections()  # Health check

    yield client

    # Cleanup: delete test collections
    collections = client.get_collections()
    for collection in collections.collections:
        if collection.name.startswith("test_"):
            client.delete_collection(collection_name=collection.name)
```

**Collection Naming:** Prefix all test collections with `test_` for cleanup

#### 3. Neo4j Driver (Layer 3 Memory + Graph RAG)
```python
@pytest.fixture(scope="session")
def neo4j_driver():
    """Real Neo4j driver for graph testing.

    Location: localhost:7687
    Cleanup: Deletes test nodes/relationships after session
    Use: LightRAG, Graphiti episodic memory
    """
    from neo4j import GraphDatabase
    from src.core.config import settings

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
    )

    driver.verify_connectivity()  # Health check
    yield driver

    # Cleanup: delete test nodes
    with driver.session() as session:
        session.run("""
            MATCH (n)
            WHERE n.name STARTS WITH 'test_' OR n.source = 'test'
            DETACH DELETE n
        """)

    driver.close()
```

**Data Isolation:** Mark test nodes with `source='test'` or `name STARTS WITH 'test_'`

#### 4. Ollama Client (LLM for E2E)
```python
@pytest.fixture(scope="session")
async def ollama_client_real():
    """Real Ollama client for LLM testing.

    Location: localhost:11434
    Models Required: llama3.2:3b, nomic-embed-text
    Use: Entity extraction, query understanding, answer generation
    """
    from ollama import AsyncClient

    client = AsyncClient(host="http://localhost:11434")

    # Verify models exist
    models_response = await client.list()
    available_models = [m.model for m in models_response.models]

    required_models = ["llama3.2:3b", "nomic-embed-text"]
    missing_models = []
    for required in required_models:
        if not any(required in model or model.startswith(required + ":") for model in available_models):
            missing_models.append(required)

    if missing_models:
        pytest.skip(f"Required Ollama models not available: {missing_models}")

    yield client
```

**Pre-requisites:** Pull models before running tests:
```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

#### 5. LightRAG Instance (Sprint 11 Workaround)
```python
@pytest.fixture
async def lightrag_instance():
    """LightRAG instance with Neo4j cleanup and singleton reset.

    Sprint 11 Workaround: Avoids pickle serialization errors
    Sprint 12 Issue: Connection issues (TD-28)

    Cleanup Strategy:
    1. Clean Neo4j database BEFORE test
    2. Clean LightRAG local cache files
    3. Reset singleton instance
    """
    from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
    from neo4j import AsyncGraphDatabase
    from src.core.config import settings
    import shutil
    from pathlib import Path

    # 1. Clean Neo4j database
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")
    await driver.close()

    # 2. Clean LightRAG cache (Windows-safe)
    lightrag_dir = Path(settings.lightrag_working_dir)
    if lightrag_dir.exists():
        for item in lightrag_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            except PermissionError:
                pass  # Best-effort cleanup
    else:
        lightrag_dir.mkdir(parents=True, exist_ok=True)

    # 3. Reset singleton
    import src.components.graph_rag.lightrag_wrapper as lightrag_module
    lightrag_module._lightrag_wrapper = None

    # Get fresh singleton instance
    wrapper = await get_lightrag_wrapper_async()
    yield wrapper
```

**Known Issue (TD-28):** Connection errors in 5 tests despite fixture fix

#### 6. Redis Checkpointer (Sprint 12 Fix)
```python
@pytest.fixture(scope="function")
async def redis_checkpointer():
    """Redis checkpointer with proper async cleanup.

    Sprint 12: Ensures Redis connections closed before event loop shutdown
    Eliminates: 9+ pytest event loop warnings
    """
    import structlog
    from src.agents.checkpointer import create_redis_checkpointer

    logger = structlog.get_logger(__name__)
    checkpointer = create_redis_checkpointer()

    yield checkpointer

    # Proper async cleanup BEFORE event loop closes
    if hasattr(checkpointer, 'aclose'):
        await checkpointer.aclose()
        logger.debug("redis_checkpointer_cleaned_up")
```

**Critical:** Always call `aclose()` in fixture teardown to prevent event loop warnings

---

## ASYNC EVENT LOOP PATTERNS

### pytest-asyncio Best Practices

#### 1. Event Loop Scope
```python
# tests/conftest.py

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
```

**pyproject.toml:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

#### 2. Async Test Patterns
```python
# ✅ CORRECT: Use @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_operation(redis_client):
    result = await redis_client.get("test_key")
    assert result is not None

# ❌ WRONG: Missing decorator
async def test_without_decorator(redis_client):  # Will not run
    result = await redis_client.get("test_key")
```

#### 3. Cleanup Best Practices
```python
# ✅ CORRECT: Async cleanup in fixture
@pytest.fixture
async def async_resource():
    resource = await create_resource()
    yield resource
    await resource.close()  # Always use await

# ❌ WRONG: Sync cleanup (causes warnings)
@pytest.fixture
async def async_resource_bad():
    resource = await create_resource()
    yield resource
    resource.close()  # Missing await
```

#### 4. Common Event Loop Errors (Sprint 13 Focus)

**TD-26: Memory Agent Event Loop Errors (4 tests)**
```python
# Error: RuntimeError: Event loop is closed
# Cause: Async cleanup after event loop shutdown
# Fix: Ensure aclose() called in fixture teardown

# tests/integration/agents/test_memory_agent_e2e.py
@pytest.mark.asyncio
async def test_memory_agent_retrieval_e2e(memory_router):
    # Issue: memory_router fixture doesn't close properly
    result = await memory_router.search_memory("test query")
    # Solution: Add aclose() to fixture
```

**Mitigation Pattern:**
```python
@pytest.fixture
async def memory_router(redis_memory_manager, qdrant_client_real, graphiti_wrapper):
    router = MemoryRouter(session_id="test_session_e2e")
    yield router
    # CRITICAL: Close all async resources
    if hasattr(router, 'aclose'):
        await router.aclose()
```

---

## NO MOCKS PRINCIPLE (ADR-014)

### Why NO MOCKS for E2E/Integration Tests?

**Key Decision (Sprint 7):**
> "We prioritize real integration confidence over test speed, leveraging stable Docker infrastructure and cost-free Ollama LLM to enable comprehensive E2E testing without mocking."

**Benefits:**
- ✅ Catch real bugs (mock behavior ≠ real behavior)
- ✅ Validate service configurations (timeouts, connection pools)
- ✅ Test actual performance (latency, throughput)
- ✅ Easier debugging (reproduce CI failures locally)
- ✅ No mock maintenance burden

**Trade-offs:**
- ⚠️ Slower execution (2-5 minutes vs <10s)
- ⚠️ Requires Docker Compose setup
- ⚠️ Possible flakiness (network, timing)

**When to Mock (Exceptions):**
1. **External APIs:** Azure OpenAI (if used), third-party services
2. **Pure Unit Tests:** Logic without I/O (20% of tests)
3. **Expensive LLM Calls:** Only in unit tests (use mock_ollama_client)

### Mock vs Real Decision Tree
```
Is this a unit test (pure logic, no I/O)?
├─ YES → Mock dependencies (fast execution)
└─ NO → Is this testing integration/E2E?
   ├─ YES → Use real services (Docker Compose)
   └─ NO → Is this an external API (Azure OpenAI)?
      ├─ YES → Mock (cost/rate limit concerns)
      └─ NO → Use real service (default)
```

---

## COMMON TEST PATTERNS

### 1. Mocking Ollama (Unit Tests Only)
```python
@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for unit tests (NO E2E usage)."""
    from unittest.mock import AsyncMock

    client = AsyncMock()
    client.chat.return_value = {
        "message": {
            "content": "Mocked LLM response"
        }
    }
    client.embeddings.return_value = {
        "embedding": [0.1] * 768
    }
    return client
```

**Usage:**
```python
@pytest.mark.unit  # NOT integration or e2e
async def test_query_understanding(mock_ollama_client):
    agent = QueryAgent(llm_client=mock_ollama_client)
    result = await agent.classify_query("What is RAG?")
    assert result["type"] == "factual"
```

### 2. Mocking Neo4j (Unit Tests Only)
```python
@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver for unit tests."""
    from unittest.mock import MagicMock

    driver = MagicMock()
    session = MagicMock()
    result = MagicMock()

    # Configure mock chain
    driver.session.return_value.__enter__.return_value = session
    session.run.return_value = result
    result.single.return_value = {"count": 42}

    return driver
```

### 3. Mocking Qdrant (Unit Tests Only)
```python
@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for unit tests."""
    from unittest.mock import MagicMock, AsyncMock
    from qdrant_client.models import ScoredPoint

    client = MagicMock()
    client.search = AsyncMock(return_value=[
        ScoredPoint(
            id="point1",
            score=0.95,
            payload={"text": "Test document", "source": "test.md"},
            version=1,
        )
    ])
    return client
```

### 4. E2E Test Pattern (Real Services)
```python
@pytest.mark.e2e  # Critical path
@pytest.mark.asyncio
async def test_hybrid_search_e2e(
    qdrant_client_real,  # Real Qdrant
    ollama_client_real,  # Real Ollama
    neo4j_driver,        # Real Neo4j
):
    """E2E test: Hybrid vector+graph search with real services."""

    # 1. Setup: Ingest test document
    doc_text = "AEGIS RAG uses hybrid retrieval."
    embedding = await ollama_client_real.embeddings(
        model="nomic-embed-text",
        prompt=doc_text,
    )

    qdrant_client_real.upsert(
        collection_name="test_collection",
        points=[{
            "id": "test_doc_1",
            "vector": embedding["embedding"],
            "payload": {"text": doc_text},
        }]
    )

    # 2. Execute: Hybrid search
    from src.components.vector_search.hybrid_search import HybridSearch

    hybrid = HybridSearch(
        qdrant_client=qdrant_client_real,
        embedding_service=None,  # Uses real Ollama
    )

    results = await hybrid.search(
        query="What retrieval does AEGIS RAG use?",
        top_k=5,
    )

    # 3. Assert: Quality checks
    assert len(results) > 0
    assert results[0]["score"] > 0.8
    assert "hybrid" in results[0]["text"].lower()

    # 4. Performance check
    assert results[0]["metadata"]["latency_ms"] < 300
```

### 5. Integration Test Pattern (Real Services, No Full Pipeline)
```python
@pytest.mark.integration  # Component integration
@pytest.mark.asyncio
async def test_memory_consolidation_integration(
    redis_client,
    qdrant_client_real,
):
    """Integration test: Redis → Qdrant consolidation."""

    # Setup: Store in Redis
    await redis_client.set("test:fact", "Important fact about RAG")
    await redis_client.set("test:fact:access_count", "5")

    # Execute: Consolidate
    from src.components.memory.consolidation import MemoryConsolidationPipeline

    pipeline = MemoryConsolidationPipeline()
    stats = await pipeline.consolidate_redis_to_qdrant(min_access_count=3)

    # Assert: Migration successful
    assert stats["consolidated_count"] >= 1

    # Verify: Retrievable from Qdrant
    results = qdrant_client_real.scroll(
        collection_name="memory",
        limit=10,
    )
    texts = [r.payload.get("text", "") for r in results[0]]
    assert any("Important fact about RAG" in text for text in texts)
```

---

## SPRINT 13 FOCUS (TD-26, TD-27, TD-28 Fixes)

### TD-26: Memory Agent Event Loop Errors (4 tests, MEDIUM)

**Location:** `tests/integration/agents/test_memory_agent_e2e.py`

**Error:**
```
RuntimeError: Event loop is closed
tests/integration/agents/test_memory_agent_e2e.py::test_memory_agent_retrieval_e2e
```

**Root Cause:** Async cleanup after event loop shutdown

**Fix Strategy:**
```python
# Step 1: Add aclose() to MemoryRouter
# src/components/memory/memory_router.py
class MemoryRouter:
    async def aclose(self):
        """Close all async resources."""
        if self.redis_manager:
            await self.redis_manager.close()
        if self.graphiti_wrapper:
            await self.graphiti_wrapper.close()

# Step 2: Update fixture cleanup
# tests/conftest.py
@pytest.fixture
async def memory_router(redis_memory_manager, qdrant_client_real, graphiti_wrapper):
    router = MemoryRouter(session_id="test_session_e2e")
    yield router
    await router.aclose()  # Proper cleanup
```

**Tests to Fix:**
1. `test_memory_agent_retrieval_e2e`
2. `test_memory_agent_multi_layer_search_e2e`
3. `test_memory_agent_temporal_query_e2e`
4. `test_memory_agent_consolidation_e2e`

### TD-27: Graphiti API Compatibility (18 tests, CRITICAL)

**Location:** `tests/integration/memory/test_graphiti_e2e.py`, `test_temporal_queries_e2e.py`

**Error:**
```
graphiti_core.Graphiti() takes 1 positional argument but 5 were given
```

**Root Cause:** graphiti-core 0.3.0 changed constructor signature

**Old API (Sprint 9):**
```python
graphiti_client = Graphiti(
    uri=neo4j_uri,
    user=neo4j_user,
    password=neo4j_password,
    llm_client=OllamaLLMClient(),
)
```

**New API (graphiti-core 0.3.0):**
```python
# Constructor simplified - no direct params
graphiti_client = Graphiti()

# Configuration via environment or class attributes
```

**Fix Strategy (Sprint 13.2):**
1. Update `GraphitiWrapper` initialization
2. Use environment variables for Neo4j connection
3. Update all 18 Graphiti tests
4. Verify with `graphiti-core==0.3.0`

### TD-28: LightRAG Fixture Connection (5 tests, CRITICAL)

**Location:** `tests/integration/test_sprint5_critical_e2e.py`

**Error:**
```
E   fixture 'lightrag_instance' not found
```

**Root Cause:** Fixture exists but connection/import issues

**Fix Strategy (Sprint 13.3):**
```python
# Step 1: Verify fixture is accessible
# tests/conftest.py
@pytest.fixture
async def lightrag_instance():  # Must be defined
    # Current implementation (lines 820-876)
    ...

# Step 2: Check test imports
# tests/integration/test_sprint5_critical_e2e.py
import pytest

@pytest.mark.asyncio
async def test_entity_extraction_ollama_neo4j_e2e(lightrag_instance):
    # Verify fixture parameter name matches
    wrapper = lightrag_instance
```

**Tests to Fix:**
1. `test_entity_extraction_ollama_neo4j_e2e`
2. `test_community_detection_leiden_e2e`
3. `test_dual_level_search_e2e`
4. `test_graph_query_generation_e2e`
5. `test_lightrag_insert_update_flow_e2e`

---

## TEST MARKERS

```python
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "sprint8: Sprint 8 critical path E2E tests",
    "slow: Slow tests (>5s execution time)",
]
```

**Usage:**
```bash
# Run unit tests only (fast)
pytest -m unit

# Run integration tests (real services)
pytest -m integration

# Run critical path E2E tests
pytest -m "sprint8 or e2e"

# Run all except slow tests
pytest -m "not slow"

# Run specific marker combination
pytest -m "integration and not slow"
```

---

## CI/CD TESTING

### GitHub Actions Configuration

```yaml
# .github/workflows/ci.yml (Sprint 12 Enhanced)

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 20  # Increased from 10min

    services:
      redis:
        image: redis:7-alpine
        ports: [6379:6379]
        options: --health-cmd "redis-cli ping"

      qdrant:
        image: qdrant/qdrant:v1.11.0
        ports: [6333:6333]
        options: --health-cmd "curl -f http://localhost:6333/health"

      neo4j:
        image: neo4j:5.24-community
        ports: [7474:7474, 7687:7687]
        env:
          NEO4J_AUTH: neo4j/testpassword
        options: --health-cmd "wget --spider http://localhost:7474"

      ollama:  # Sprint 12: Added Ollama service
        image: ollama/ollama:latest
        ports: [11434:11434]
        options: --health-cmd "curl -f http://localhost:11434/api/version"

    steps:
      - name: Pull Ollama Models
        run: |
          docker exec ollama ollama pull nomic-embed-text
          docker exec ollama ollama pull llama3.2:3b

      - name: Run Tests
        run: |
          pytest tests/ \
            --cov=src \
            --cov-report=term-missing \
            -v \
            --tb=short
```

---

## PERFORMANCE TARGETS

| Test Type | Count | Execution Time | Pass Rate Target |
|-----------|-------|----------------|------------------|
| Unit | ~312 | <2 minutes | 95%+ |
| Integration | ~156 | <4 minutes | 90%+ |
| E2E | ~52 | <3 minutes | 80%+ |
| **Total** | **~520** | **<8 minutes** | **90%+** |

**Current (Sprint 12):**
- Total Tests: ~520
- Pass Rate: 90% overall, 88.5% E2E
- CI Build Time: 8 minutes (with Docker cache)

**Sprint 13 Target:**
- Fix TD-26, TD-27, TD-28 → 95% pass rate
- Maintain <10 minutes CI execution

---

## REFERENCES

- **ADR-014:** E2E Integration Testing Strategy (NO MOCKS principle)
- **ADR-015:** Critical Path Testing Strategy (4 critical paths)
- **Sprint 8:** E2E testing framework established (80% baseline)
- **Sprint 12:** Test infrastructure fixes (TD-23, TD-24, TD-25 resolved)
- **Sprint 13 Plan:** Test infrastructure focus (TD-26, TD-27, TD-28)

---

**Last Updated:** 2025-10-22 (Post-Sprint 12)
**Status:** 520 tests, 90% pass rate, 88.5% E2E
**Next Sprint:** Sprint 13 (Fix event loop, Graphiti, LightRAG issues)
