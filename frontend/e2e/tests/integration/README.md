# Integration Tests

**Purpose:** Integration tests that require live backend services (API, Qdrant, Neo4j, Redis).

**Difference from E2E Tests:**
- **E2E Tests** (`e2e/tests/`): Frontend-only tests with mocked APIs (Playwright route mocking). No backend services required.
- **Integration Tests** (`e2e/tests/integration/`): Full-stack tests with real backend services. Require Docker Compose running.

---

## Running Integration Tests

### Prerequisites

Start all backend services:
```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag
docker compose -f docker-compose.dgx-spark.yml up -d
```

### Run Tests

```bash
cd /home/admin/projects/aegisrag/AEGIS_Rag/frontend

# Run all integration tests
npm run test:integration

# Run specific integration test
npm run test:e2e tests/integration/performance-regression.spec.ts
```

---

## Test Suites

### 1. Performance Regression Tests

**File:** `performance-regression.spec.ts`

**Purpose:** Automated performance regression testing to ensure latency SLAs are met.

**Tests (10):**
1. Simple vector query (<500ms p95)
2. Complex multi-hop query (<1000ms p95)
3. Document upload (<3 minutes)
4. Section extraction (<50s for 146 texts)
5. BM25 cache hit rate (>80%)
6. Redis memory usage (<2GB)
7. Qdrant search latency (<100ms p95)
8. Neo4j graph query (<500ms p95)
9. Embedding generation (<200ms batch of 10)
10. Reranking (<50ms top 10 results)

**Backend Requirements:**
- FastAPI backend running on `http://localhost:8000`
- Qdrant running on `localhost:6333`
- Neo4j running on `bolt://localhost:7687`
- Redis running on `localhost:6379`
- Ollama running on `http://localhost:11434`

**Usage:**
```bash
# Start backend
docker compose -f docker-compose.dgx-spark.yml up -d

# Run performance tests
npm run test:e2e tests/integration/performance-regression.spec.ts

# Stop backend
docker compose -f docker-compose.dgx-spark.yml down
```

---

## CI/CD Integration

Integration tests should run in CI/CD pipelines with Docker Compose:

```yaml
# .github/workflows/integration-tests.yml
- name: Start services
  run: docker compose up -d

- name: Wait for services
  run: ./scripts/wait-for-services.sh

- name: Run integration tests
  run: npm run test:integration

- name: Stop services
  run: docker compose down
```

---

## Adding New Integration Tests

1. Create test file in `e2e/tests/integration/`
2. Use real API endpoints (no mocking)
3. Require backend services in test description
4. Add to `package.json` scripts if needed
5. Update this README

---

**Last Updated:** 2026-01-03 (Sprint 72)
**Owner:** Klaus Pommer + Claude Code
