# ADR-014: E2E Integration Testing Strategy with Real Services

**Status:** Accepted
**Date:** 2025-10-17
**Decision Makers:** Development Team
**Supersedes:** Previous mocking strategy in early sprints

---

## Context

In early sprints (Sprint 1-4), AEGIS RAG tests used extensive mocking for external services (Redis, Qdrant, Neo4j, Ollama) to enable fast unit testing without infrastructure dependencies. This approach had trade-offs:

**Benefits of Mocking:**
- ✅ Fast test execution (<10s for full suite)
- ✅ No infrastructure setup required
- ✅ Isolated unit test failures
- ✅ Deterministic test behavior

**Drawbacks of Mocking:**
- ❌ Mock behavior diverges from real service behavior
- ❌ Integration bugs not caught until production
- ❌ False confidence from passing mocked tests
- ❌ Maintenance burden of mock implementations
- ❌ No validation of service configurations
- ❌ Missing edge cases (timeouts, connection errors, data consistency)

**Key Incident (Sprint 6):**
- All unit tests passed with mocked Neo4j
- Integration tests failed in CI with real Neo4j (timeout issues)
- Required multiple iterations to fix health checks and wait logic
- **Root cause:** Mocked Neo4j didn't simulate real startup time or connection behavior

**System Maturity (Sprint 7):**
- Infrastructure is stable (Docker Compose, all services configured)
- Service reliability is high (Redis, Qdrant, Neo4j, Ollama all running)
- System complexity increased (3-layer memory, bi-temporal queries)
- Integration points are critical (memory router, consolidation pipeline)

**Strategic Question:**
> "Should we continue mocking or switch to E2E integration testing with real services?"

---

## Decision

**We adopt E2E Integration Testing as the primary testing strategy for Sprint 7 and beyond.**

Starting with Sprint 7 (Memory System), all tests will:
1. **Use real services** (Redis, Qdrant, Neo4j, Ollama) running in Docker Compose
2. **Test full integration paths** from API → Agent → Component → Database
3. **Validate actual behavior** including latency, error handling, data consistency
4. **Run in CI** with Docker Compose services in GitHub Actions
5. **Minimize mocking** to only external APIs (Azure OpenAI in prod fallback scenarios)

**Test Categories:**
- **E2E Integration Tests:** 80% of tests (real services, full stack)
- **Unit Tests:** 20% of tests (pure logic, no I/O, no mocking needed)

---

## Rationale

### Why E2E Integration Testing Now?

**1. Infrastructure Readiness**
```yaml
# docker-compose.yml provides all services
services:
  redis:       # Layer 1 - Short-term memory
  qdrant:      # Layer 2 - Semantic memory
  neo4j:       # Layer 3 - Episodic memory + Graph RAG
  ollama:      # LLM for all inference (local, cost-free)
```
- All services run reliably in Docker Compose
- Health checks ensure services are ready before tests
- Consistent environment for local dev and CI

**2. Cost-Free LLM (Ollama)**
```python
# ADR-002: Ollama-First Strategy
LLM: Ollama llama3.2:8b (local, no API costs)
Embeddings: nomic-embed-text (local, no API costs)
```
- No API rate limits or costs for testing
- Fast inference on local hardware (<2s per query)
- Deterministic behavior with temperature=0.1

**3. System Complexity**
```
┌────────────────────────────────────────────────┐
│   3-Layer Memory Architecture (Sprint 7)       │
├────────────────────────────────────────────────┤
│  Layer 1: Redis      → <10ms                   │
│  Layer 2: Qdrant     → <50ms                   │
│  Layer 3: Graphiti   → <100ms                  │
│     └─ Neo4j backend (bi-temporal)             │
│     └─ Ollama LLM (entity extraction)          │
│  Memory Router: Intelligent layer selection    │
│  Consolidation: Redis → Qdrant, Conv → Graphiti│
└────────────────────────────────────────────────┘
```
- Mocking this complexity would require 5+ mock implementations
- Real integration bugs (race conditions, timing, consistency) only caught with real services
- Memory consolidation logic depends on actual Redis TTL, Qdrant search, Neo4j transactions

**4. CI/CD Reliability**
- Sprint 6 showed CI integration test failures despite passing unit tests
- Real services in CI catch configuration issues (timeouts, memory limits, connection pools)
- GitHub Actions supports Docker Compose services natively

**5. Developer Confidence**
- "Tests pass" → System actually works (not just mocks work)
- Integration issues caught in development, not production
- Easier debugging: reproduce CI failures locally with same Docker setup

---

## Implementation Strategy

### Test Structure

```
tests/
├── integration/              # E2E tests with real services (80%)
│   ├── memory/
│   │   ├── test_graphiti_e2e.py
│   │   ├── test_memory_router_e2e.py
│   │   ├── test_consolidation_e2e.py
│   │   └── test_temporal_queries_e2e.py
│   ├── agents/
│   │   ├── test_memory_agent_e2e.py
│   │   └── test_coordinator_e2e.py
│   └── api/
│       └── test_memory_api_e2e.py
├── unit/                     # Pure logic tests (20%)
│   ├── utils/
│   │   ├── test_text_processing.py
│   │   └── test_validation.py
│   └── models/
│       └── test_pydantic_models.py
└── conftest.py               # Shared fixtures (real service clients)
```

### Pytest Fixtures (Real Services)

```python
# tests/conftest.py

import pytest
from redis.asyncio import Redis
from qdrant_client import QdrantClient
from neo4j import GraphDatabase
from ollama import AsyncClient

@pytest.fixture(scope="session")
async def redis_client():
    """Real Redis client for all tests."""
    client = Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    yield client
    await client.flushdb()  # Clean up after all tests
    await client.close()

@pytest.fixture(scope="session")
def qdrant_client():
    """Real Qdrant client for all tests."""
    client = QdrantClient(host="localhost", port=6333)
    yield client
    # Cleanup: delete test collections

@pytest.fixture(scope="session")
def neo4j_driver():
    """Real Neo4j driver for all tests."""
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "testpassword")
    )
    yield driver
    # Cleanup: delete test nodes
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    driver.close()

@pytest.fixture(scope="session")
async def ollama_client():
    """Real Ollama client for all tests."""
    client = AsyncClient(host="http://localhost:11434")
    # Verify models are available
    models = await client.list()
    assert "llama3.2:8b" in [m.model for m in models]
    assert "nomic-embed-text" in [m.model for m in models]
    yield client
```

### Example E2E Test

```python
# tests/integration/memory/test_memory_router_e2e.py

import pytest
from src.components.memory import get_memory_router

@pytest.mark.asyncio
@pytest.mark.integration  # Mark as integration test
async def test_memory_router_recent_context_query_e2e(
    redis_client,
    qdrant_client,
    neo4j_driver,
):
    """E2E test: Recent context query routes to Redis (Layer 1)."""
    # Setup: Store recent conversation in Redis
    router = get_memory_router()
    await router.store_conversation_turn(
        session_id="test_session",
        user_message="What is RAG?",
        assistant_message="RAG is Retrieval-Augmented Generation...",
    )

    # Execute: Query with recent context pattern
    results = await router.search_memory(
        query="What did you just say about RAG?",
        layers=None,  # Auto-route
    )

    # Verify: Redis layer was queried
    assert "redis" in results
    assert len(results["redis"]) > 0
    assert "RAG is Retrieval-Augmented Generation" in results["redis"][0]["text"]

    # Verify: Latency target met (<10ms for Redis)
    assert results["redis"][0]["metadata"]["latency_ms"] < 10

@pytest.mark.asyncio
@pytest.mark.integration
async def test_memory_consolidation_redis_to_qdrant_e2e(
    redis_client,
    qdrant_client,
):
    """E2E test: Consolidation moves frequent items from Redis to Qdrant."""
    # Setup: Store item in Redis and simulate accesses
    router = get_memory_router()
    key = "test:frequent_item"
    await redis_client.set(key, "Important fact about RAG")
    await redis_client.set(f"{key}:access_count", "5")  # Simulate 5 accesses

    # Execute: Run consolidation
    pipeline = MemoryConsolidationPipeline()
    stats = await pipeline.consolidate_redis_to_qdrant(
        min_access_count=3,
    )

    # Verify: Item moved to Qdrant
    assert stats["consolidated_count"] >= 1

    # Verify: Item retrievable from Qdrant
    qdrant_results = qdrant_client.search(
        collection_name="memory",
        query_vector=[...],  # Get from embedding
        limit=5,
    )
    assert any("Important fact about RAG" in r.payload.get("text", "") for r in qdrant_results)
```

### CI/CD Configuration

```yaml
# .github/workflows/ci.yml (updated)

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      qdrant:
        image: qdrant/qdrant:v1.11.0
        ports:
          - 6333:6333
        options: >-
          --health-cmd "curl -f http://localhost:6333/health"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      neo4j:
        image: neo4j:5.24-community
        ports:
          - 7474:7474
          - 7687:7687
        env:
          NEO4J_AUTH: neo4j/testpassword
          NEO4J_server_memory_heap_initial__size: 512m
          NEO4J_server_memory_heap_max__size: 1g
        options: >-
          --health-cmd "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"
          --health-interval 10s
          --health-timeout 10s
          --health-retries 20
          --health-start-period 60s

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Ollama
        run: |
          curl -fsSL https://ollama.com/install.sh | sh
          ollama serve &
          sleep 10
          ollama pull llama3.2:8b
          ollama pull nomic-embed-text

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Wait for Services
        run: |
          # Services already healthy from health checks
          echo "✅ All services ready"

      - name: Run Integration Tests
        run: |
          poetry run pytest tests/integration/ \
            --cov=src \
            --cov-report=term-missing \
            -v \
            -m integration
```

---

## Test Execution Guidelines

### Local Development

```bash
# 1. Start all services
docker compose up -d

# 2. Verify services are healthy
docker compose ps

# 3. Run E2E integration tests
pytest tests/integration/ -v -m integration

# 4. Run specific test file
pytest tests/integration/memory/test_memory_router_e2e.py -v

# 5. Run with coverage
pytest tests/integration/ --cov=src --cov-report=html -v
```

### Test Markers

```python
# Mark integration tests
@pytest.mark.integration

# Mark slow tests (optional skip in fast mode)
@pytest.mark.slow

# Mark tests requiring specific services
@pytest.mark.redis
@pytest.mark.neo4j
@pytest.mark.ollama
```

### Performance Expectations

| Test Suite | Test Count | Execution Time | Coverage |
|------------|------------|----------------|----------|
| Integration Tests | 60-80 | 2-5 minutes | 80%+ |
| Unit Tests | 20-30 | 5-10 seconds | 95%+ |
| **Total** | **80-110** | **<6 minutes** | **80%+** |

**Rationale for execution time:**
- Real Ollama inference: ~1-2s per LLM call
- Database operations: ~10-50ms each
- Test setup/teardown: ~100ms per test
- Total: Acceptable tradeoff for real integration validation

---

## Benefits

### For Development

✅ **Catch Real Bugs Early**
- Integration issues found in development, not production
- Service configuration problems detected immediately
- Race conditions and timing issues caught

✅ **Easier Debugging**
- Reproduce CI failures locally with same Docker setup
- Inspect real database state during test debugging
- No mock behavior mismatches

✅ **Faster Iteration**
- No time spent maintaining mock implementations
- Tests validate actual behavior, not mock behavior
- Refactoring is safer (real integration contract)

### For CI/CD

✅ **Higher Confidence**
- "Tests pass" → System actually works
- Deployments less risky
- Fewer production hotfixes

✅ **Service Validation**
- Health checks ensure services are ready
- Configuration issues caught before deployment
- Resource limits validated (memory, connections)

### For System Quality

✅ **Real Performance Data**
- Actual latency measurements (not mock timings)
- Identify bottlenecks with real workloads
- Validate performance targets (<10ms Redis, <50ms Qdrant, <100ms Graphiti)

✅ **Data Consistency**
- Validate bi-temporal queries with real Neo4j
- Test consolidation with real Redis TTL
- Ensure Qdrant vector search accuracy

---

## Tradeoffs

### Advantages

| Aspect | E2E Integration | Mocked Unit Tests |
|--------|-----------------|-------------------|
| **Bug Detection** | ✅ High (real behavior) | ⚠️ Medium (mock divergence) |
| **Confidence** | ✅ High (system works) | ⚠️ Medium (mocks work) |
| **Debugging** | ✅ Easy (real state) | ❌ Hard (mock artifacts) |
| **Maintenance** | ✅ Low (no mocks) | ❌ High (mock upkeep) |
| **CI Reliability** | ✅ High (catches config) | ⚠️ Medium (mock passes, CI fails) |

### Disadvantages

| Aspect | E2E Integration | Mocked Unit Tests |
|--------|-----------------|-------------------|
| **Speed** | ⚠️ Slower (2-5 min) | ✅ Fast (<10s) |
| **Setup** | ⚠️ Requires Docker | ✅ No setup |
| **Flakiness** | ⚠️ Possible (network, timing) | ✅ Deterministic |
| **Isolation** | ❌ Cross-test pollution risk | ✅ Isolated |

### Mitigation Strategies

**For Speed:**
- Pytest `scope="session"` fixtures (reuse connections)
- Parallel test execution with `pytest-xdist`
- Fast Docker image caching in CI

**For Setup:**
- Docker Compose one-command setup
- Documented prerequisites in README
- Pre-built Docker images in CI

**For Flakiness:**
- Robust health checks before tests
- Retry logic for transient failures
- Cleanup fixtures after each test

**For Isolation:**
- Separate test databases/collections
- Unique test data prefixes (`test_*`)
- Cleanup in teardown fixtures

---

## Migration Path (Sprint 7 Only)

**Sprint 7 Implementation:**
1. ✅ Create E2E integration tests for all Sprint 7 features (no mocks)
2. ✅ Document ADR-014 (this document)
3. ✅ Update CI configuration for service containers

**Future Sprints (8-10):**
- Continue E2E-first approach for new features
- No migration of old tests (Sprint 1-6 tests remain as-is)
- Ratio: 80% E2E integration, 20% unit tests (pure logic)

**Old Tests (Sprint 1-6):**
- Keep existing mocked tests as-is (don't break what works)
- Gradually replace with E2E tests if bugs found
- No large-scale test refactoring (not worth the effort)

---

## Alternatives Considered

### Alternative 1: Continue Mocking
**Rejected because:**
- Mock maintenance burden too high
- Sprint 6 CI issues showed mock inadequacy
- System complexity makes mocking error-prone

### Alternative 2: Hybrid Approach (50% Mocked, 50% E2E)
**Rejected because:**
- Confusing strategy (when to mock vs E2E?)
- Maintenance burden of both approaches
- Half-measures don't solve the confidence problem

### Alternative 3: Testcontainers
**Considered but deferred:**
- Testcontainers provides programmatic Docker management
- Adds complexity (Python SDK, Docker-in-Docker in CI)
- Docker Compose is simpler and sufficient
- Could revisit in future if needed

---

## Success Metrics

**Sprint 7 Targets:**
- ✅ 80%+ code coverage with E2E integration tests
- ✅ <6 minutes total test execution time
- ✅ Zero mock implementations for Sprint 7 code
- ✅ All integration tests pass in CI with real services

**Long-term Metrics:**
- Reduce production bugs by 50% (fewer integration surprises)
- Reduce CI troubleshooting time by 30% (easier to debug)
- Increase developer confidence in deployments

---

## Conclusion

**E2E Integration Testing with real services is the right strategy for AEGIS RAG starting Sprint 7.**

**Key Decision:**
> "We prioritize real integration confidence over test speed, leveraging stable Docker infrastructure and cost-free Ollama LLM to enable comprehensive E2E testing without mocking."

This approach aligns with AEGIS RAG's maturity, infrastructure readiness, and the critical importance of the 3-layer memory system working correctly in production.

---

**References:**
- ADR-002: Ollama-First LLM Strategy (enables cost-free testing)
- ADR-006: 3-Layer Memory Architecture (complexity requires E2E validation)
- Sprint 6 CI Issues: Neo4j timeout failures with mocked tests passing

**Status:** ✅ Accepted and implemented in Sprint 7

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
