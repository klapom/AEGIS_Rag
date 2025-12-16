# End-to-End Tests for AEGIS RAG

Comprehensive E2E tests that validate complete workflows from document upload to query responses, ensuring all system components work together correctly.

## Test Suites

### 1. Document Ingestion Workflow (`test_e2e_document_ingestion_workflow.py`)

**Purpose:** Validates the complete document lifecycle from upload to query.

**Workflow:**
1. User uploads a document
2. Document is processed through ingestion pipeline (Docling)
3. Chunks are indexed in Qdrant + BM25
4. Entities and relations are extracted to Neo4j
5. User queries the document
6. System retrieves relevant information with citations

**Validates:**
- ✅ Document upload via UI
- ✅ Chunking and indexing (Qdrant)
- ✅ Entity extraction (Neo4j)
- ✅ Relation extraction with source_chunk_id (Sprint 49.5)
- ✅ BM25 corpus updates
- ✅ Query retrieval accuracy
- ✅ Citation references

**Runtime:** ~2-3 minutes

---

### 2. Sprint 49 Features (`test_e2e_sprint49_features.py`)

**Purpose:** Validates all Sprint 49 features in production-like scenarios.

**Features Tested:**
- **Feature 49.5:** Provenance Tracking (source_chunk_id on relationships)
- **Feature 49.6:** Index Consistency Validation (Qdrant ↔ Neo4j ↔ BM25)
- **Feature 49.7:** Semantic Relation Deduplication (BGE-M3 clustering)
- **Feature 49.8:** Manual Relation Synonym Overrides (Redis-backed)
- **Feature 49.9:** BGE-M3 Entity Deduplication

**Validates:**
- ✅ Index consistency across all storage layers
- ✅ Relation deduplication reduces duplicate types
- ✅ Manual overrides take precedence over semantic clustering
- ✅ All relationships have proper provenance data

**Runtime:** ~3-4 minutes

---

### 3. Hybrid Search Quality (`test_e2e_hybrid_search_quality.py`)

**Purpose:** Validates retrieval quality and performance across search types.

**Search Types Tested:**
- **BM25:** Exact keyword matching (technical terms, identifiers)
- **Vector:** Semantic/conceptual queries (paraphrases, synonyms)
- **Hybrid (RRF):** Balanced fusion of both approaches

**Validates:**
- ✅ BM25 excels at exact matches
- ✅ Vector search handles semantic similarity
- ✅ Hybrid provides balanced results
- ✅ Ranking quality (relevance ordering)
- ✅ Result diversity
- ✅ Performance benchmarks (< 500ms for hybrid)

**Runtime:** ~2-3 minutes

---

## Prerequisites

### 1. Running Services

All services must be running locally:

```bash
# Start all services with Docker Compose
docker compose -f docker-compose.dgx-spark.yml up -d

# Verify all services are healthy
docker ps
```

**Required services:**
- ✅ Backend API (port 8000)
- ✅ Frontend (port 5179)
- ✅ Qdrant (port 6333/6334)
- ✅ Neo4j (port 7687/7474)
- ✅ Redis (port 6379)
- ✅ Ollama (port 11434)

### 2. Dependencies

Install Playwright browsers:

```bash
# Install Playwright browsers (one-time setup)
poetry run playwright install chromium

# Or with pip
python -m playwright install chromium
```

### 3. Test User Account

The tests use default admin credentials:
- Username: `admin`
- Password: `admin123`

Ensure this account exists and has admin privileges.

---

## Running Tests

### Run All E2E Tests

```bash
# From project root
poetry run pytest tests/e2e/ -v -s

# Or with pytest directly
pytest tests/e2e/ -v -s
```

### Run Specific Test Suite

```bash
# Document ingestion workflow
pytest tests/e2e/test_e2e_document_ingestion_workflow.py -v -s

# Sprint 49 features
pytest tests/e2e/test_e2e_sprint49_features.py -v -s

# Hybrid search quality
pytest tests/e2e/test_e2e_hybrid_search_quality.py -v -s
```

### Run Specific Test

```bash
# Run a single test by name
pytest tests/e2e/test_e2e_document_ingestion_workflow.py::TestDocumentIngestionWorkflow::test_complete_document_ingestion_workflow -v -s
```

### Debug Mode (Headed Browser)

To see the browser UI during test execution:

```bash
# Run in headed mode
HEADED=1 pytest tests/e2e/ -v -s

# With slow motion (500ms delay between actions)
HEADED=1 SLOWMO=500 pytest tests/e2e/ -v -s
```

### Filter by Marker

```bash
# Run only Sprint 49 tests
pytest tests/e2e/ -m sprint49 -v -s

# Run only fast tests (exclude slow)
pytest tests/e2e/ -m "not slow" -v

# Run only E2E tests
pytest tests/e2e/ -m e2e -v -s
```

---

## Test Output

### Successful Test Output Example

```
===============================================================================
Starting Test: test_complete_document_ingestion_workflow
===============================================================================

✓ Login successful
✓ Baseline: 1234 chunks, 567 entities, 890 relations
✓ Navigated to upload page
✓ Uploaded document: test_ml_research.txt
✓ Ingestion success message received
✓ Qdrant: 15 new chunks added (total: 1249)
✓ Chunk structure validated: chunk_id=chunk_abc123def456...
✓ Neo4j: 8 new entities extracted (total: 575)
✓ Key entities found: ['Andrew Ng', 'Stanford University', 'Google Brain']
✓ Neo4j: 12 new relations extracted (total: 902)
✓ Sprint 49.5: 12 MENTIONED_IN relations have source_chunk_id
✓ BM25 corpus functional: 5 results returned
✓ Query submitted: 'Who is Andrew Ng and what did he found?'
✓ Answer contains expected content: ['Andrew Ng', 'Google Brain', 'Coursera']
✓ Found 3 citations in response
✓ Citation references uploaded document

======================================================================
✅ COMPLETE DOCUMENT INGESTION WORKFLOW TEST PASSED
======================================================================
Summary:
  - Chunks added: 15
  - Entities extracted: 8
  - Relations extracted: 12
  - Relations with source_chunk_id: 12
  - Query answered correctly: Yes
  - Citations valid: True
```

---

## Troubleshooting

### Test Failures

**Problem:** `Connection refused` errors

**Solution:** Ensure all services are running:
```bash
docker compose -f docker-compose.dgx-spark.yml ps
curl http://localhost:8000/health
curl http://localhost:5179
```

---

**Problem:** Playwright browser not installed

**Solution:** Install Chromium browser:
```bash
poetry run playwright install chromium
```

---

**Problem:** Tests timeout waiting for ingestion

**Solution:** Check backend logs for errors:
```bash
docker logs aegis-api --tail 50 --follow
```

Common issues:
- Docling service not available
- LLM (Ollama) not responding
- Neo4j connection timeout

---

**Problem:** Login fails

**Solution:** Verify admin account exists and credentials are correct:
```bash
# Check API health
curl http://localhost:8000/api/v1/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

---

**Problem:** Tests fail due to insufficient data

**Solution:** Run tests with a clean database state:
```bash
# Reset Neo4j (WARNING: deletes all data)
docker exec -it aegis-neo4j cypher-shell -u neo4j -p <password> "MATCH (n) DETACH DELETE n"

# Reset Qdrant
curl -X DELETE http://localhost:6333/collections/aegis_documents
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest

    services:
      qdrant:
        image: qdrant/qdrant:v1.11.0
        ports:
          - 6333:6333
          - 6334:6334

      neo4j:
        image: neo4j:5.24-community
        ports:
          - 7687:7687
          - 7474:7474
        env:
          NEO4J_AUTH: neo4j/testpassword

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
          poetry run playwright install chromium

      - name: Run E2E tests
        run: |
          poetry run pytest tests/e2e/ -v -s --maxfail=1
        env:
          BASE_URL: http://localhost:5179
          API_BASE_URL: http://localhost:8000
```

---

## Best Practices

### 1. Test Isolation

Each test should:
- ✅ Be independent (no shared state)
- ✅ Clean up after itself
- ✅ Not rely on execution order

### 2. Assertions

- ✅ Use descriptive assertion messages
- ✅ Validate both positive and negative cases
- ✅ Check data consistency across systems

### 3. Timeouts

- ✅ Use appropriate timeouts for async operations
- ✅ Distinguish between fast (< 5s) and slow (< 60s) operations
- ✅ Handle race conditions gracefully

### 4. Screenshots

Capture screenshots on failure:
```python
@pytest.fixture(autouse=True)
async def screenshot_on_failure(page, request):
    yield
    if request.node.rep_call.failed:
        await page.screenshot(path=f"screenshots/{request.node.name}.png")
```

---

## Performance Targets

| Operation | Target (p95) | Notes |
|-----------|--------------|-------|
| Document upload | < 30s | Includes chunking + indexing |
| Graph extraction | < 45s | Entity/relation extraction |
| BM25 search | < 100ms | Keyword matching |
| Vector search | < 150ms | Semantic search |
| Hybrid search | < 200ms | RRF fusion |
| Query response | < 1000ms | End-to-end with reasoning |

---

## Contributing

When adding new E2E tests:

1. **Follow naming convention:** `test_e2e_<feature>_<aspect>.py`
2. **Add docstrings:** Explain what the test validates
3. **Use markers:** Add appropriate pytest markers
4. **Update README:** Document new test suites
5. **Validate locally:** Run tests before committing

---

**Last Updated:** 2025-12-16
**Test Coverage:** Sprint 49 + Core Features
**Total Test Runtime:** ~8-10 minutes for all E2E tests
