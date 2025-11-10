# CLAUDE.md - AegisRAG Project Context

## 🔄 Session Continuity Check

**Falls diese Session kompaktiert wurde:**
1. Lies dieses gesamte CLAUDE.md Dokument
2. Checke SPRINT_PLAN.md für aktuellen Sprint-Status
3. Reaktiviere Subagenten-Context aus SUBAGENTS.md
4. Verifiziere ADR-Awareness aus ADR_INDEX.md
5. Bestätige Naming Conventions aus NAMING_CONVENTIONS.md

**Zeichen für Context Loss:**
- Du kennst Projekt-Struktur nicht mehr
- Du fragst nach bereits beantworteten Architektur-Fragen
- Du nutzt Subagenten nicht mehr systematisch
- Du hältst dich nicht an Naming Conventions

→ Dann: Context Refresh durchführen!

---

## 📍 Current Project State (Sprint 21)

**Sprint 20 Status**: ✅ COMPLETE (2025-10-31 - 2025-11-06)
- ✅ Performance Optimization & Extraction Quality
- ✅ Chunk overhead analysis (65% overhead identified with 600-token chunks)
- ✅ LLM extraction quality improvements
- ✅ Pure LLM pipeline introduced (ADR-026)
- ✅ Preparation for 1800-token chunking strategy

**Sprint 21 Status**: ✅ COMPLETE (2025-11-07 - 2025-11-10, branch: `sprint-21-container-ingestion`)
- **Objective**: Container-based document ingestion with GPU-accelerated OCR
- **Key Achievements**:
  - ✅ **Docling CUDA Container Integration** (ADR-027)
    - GPU-accelerated OCR (EasyOCR): 95% accuracy (vs 70% LlamaIndex)
    - Table structure preservation: 92% detection rate
    - Performance: 420s → 120s per document (3.5x faster)
    - Container isolation: Manage 6GB VRAM allocation
  - ✅ **LlamaIndex Deprecation** (ADR-028)
    - Deprecated as primary ingestion framework
    - Retained as fallback + connector library (300+ connectors)
  - ✅ **LangGraph Pipeline Redesign**
    - 6-node state machine: Docling → VLM → Chunking → Embedding → Graph → Validation
    - 31 integration tests for DoclingContainerClient
  - ✅ **Documentation Cleanup**
    - 4 critical ADRs created (ADR-027 to ADR-030, 1,900+ lines)
    - Sprint 1-9, 13, 18 documentation backfilled (17,132 words)
    - Drift analysis completed (18 drifts identified)

- **Architecture Decisions**:
  - ADR-027: Docling Container vs. LlamaIndex
  - ADR-028: LlamaIndex Deprecation Strategy
  - ADR-029: React Migration Deferral
  - ADR-030: Sprint Extension from 12 to 21+ Sprints

**Sprint 22 Status**: 📋 PLANNED (2025-11-11+)
- **Objective**: Production deployment readiness
- **Planned Features**:
  - React frontend migration (deferred from Sprint 15, ADR-029)
  - Kubernetes deployment manifests
  - External user onboarding
  - Performance validation (100+ docs batch ingestion)

**Next Steps**: Sprint 21 documentation complete. Ready for Sprint 22 React migration or production deployment.

For full details, see:
- [SPRINT_21_PLAN_v2.md](sprints/SPRINT_21_PLAN_v2.md)
- [DRIFT_ANALYSIS.md](DRIFT_ANALYSIS.md)
- [DOCUMENTATION_PLAN.md](DOCUMENTATION_PLAN.md)

---

## Project Overview
**AegisRAG** (Agentic Enterprise Graph Intelligence System) ist ein produktionsreifes agentisches RAG-System mit vier Core-Komponenten:

1. **Vector Search** (Qdrant + Hybrid Search)
2. **Graph Reasoning** (LightRAG + Neo4j)
3. **Temporal Memory** (Graphiti + Bi-Temporal Structure)
4. **Tool Integration** (Model Context Protocol Server)

**Orchestration:** LangGraph Multi-Agent System
**Data Ingestion:** Docling CUDA Container + LlamaIndex fallback (ADR-027, ADR-028)
**Monitoring:** LangSmith + Prometheus + RAGAS

---

## Architecture Principles

### Core Design Patterns
- **Hybrid Retrieval:** Vector Similarity + Graph Traversal + BM25 Keyword
- **Parallel Execution:** Async Retrieval via LangGraph Send API
- **3-Layer Memory:** Redis (Short-Term) → Qdrant (Semantic) → Graphiti (Episodic)
- **Intent-Based Routing:** Query Classifier → Specialized Agents
- **Fail-Safe Design:** Graceful Degradation, Retry with Exponential Backoff

### Technology Stack
```yaml
Backend: Python 3.12.7, FastAPI, Pydantic v2
Orchestration: LangGraph 0.6.10, LangChain Core
Data Ingestion:
  - Primary: Docling CUDA Container (GPU-accelerated OCR, ADR-027)
  - Fallback: LlamaIndex 0.14.3 (connectors only, ADR-028)
Vector DB: Qdrant 1.11.0
Graph DB: Neo4j 5.24 Community Edition
Memory Cache: Redis 7.x with Persistence
LLM Models:
  - Generation: llama3.2:3b (query) / llama3.2:8b (generation)
  - Extraction: gemma-3-4b-it-Q8_0 (ADR-018)
  - Vision: llava:7b-v1.6-mistral-q2_K (Feature 21.6)
Embeddings: BGE-M3 (1024-dim, multilingual, ADR-024) - Local & Cost-Free
Optional Production: Azure OpenAI GPT-4o (if needed)
MCP: Official Python SDK (anthropic/mcp)
Container Runtime: Docker Compose + NVIDIA Container Toolkit (CUDA 12.4)
```

### Repository Structure
```
aegis-rag/
├── src/
│   ├── agents/              # LangGraph Agents
│   │   ├── coordinator.py
│   │   ├── vector_search.py
│   │   ├── graph_query.py
│   │   ├── action.py
│   │   └── memory.py
│   ├── components/          # Core Components
│   │   ├── ingestion/       # Docling Container + LangGraph Pipeline (Sprint 21)
│   │   ├── vector_search/   # Qdrant + Hybrid Search + BGE-M3
│   │   ├── graph_rag/       # LightRAG + Neo4j + Three-Phase Extraction
│   │   ├── memory/          # Graphiti + Redis
│   │   └── mcp/             # MCP Client (tool integration)
│   ├── core/                # Shared Core
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── models.py        # Pydantic Models
│   │   └── exceptions.py
│   ├── api/                 # FastAPI Endpoints
│   │   ├── v1/
│   │   └── health.py
│   └── utils/               # Helper Functions
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/                 # Deployment & Maintenance
├── config/                  # Configuration Files
├── docker/                  # Dockerfiles
├── k8s/                     # Kubernetes Manifests
├── docs/                    # Documentation
├── .github/                 # CI/CD Workflows
├── pyproject.toml
├── docker-compose.yml
├── CLAUDE.md               # This file
├── SPRINT_PLAN.md
├── ADR/                    # Architecture Decision Records
└── README.md
```

---

## Development Workflow

### 🎯 Feature-basierte Sprint-Entwicklung (WICHTIG!)

**Neue Regel ab Sprint 2:**
Jeder Sprint wird in **einzelne Features** heruntergebrochen, um granulare Git-Commits zu ermöglichen.

**Vorteile:**
✅ 1 Feature = 1 Git Commit (Atomic Rollbacks)
✅ Bessere Nachvollziehbarkeit und Code-Review
✅ Parallele Entwicklung mehrerer Features
✅ Klare Ownership und Zuständigkeiten

**Feature-Definition:**
Jedes Feature hat:
1. **Feature-ID:** {Sprint}.{Nr} (z.B. 2.1, 2.2, 2.3)
2. **Feature-Name:** Kurz und prägnant
3. **Deliverables:** Konkrete Outputs
4. **Technical Tasks:** Implementation Steps
5. **Git Commit:** feat(scope): description
6. **Tests:** Unit + Integration (>80% coverage)
7. **Dependencies:** Benötigt andere Features?

**Beispiel Sprint 2:**
- Feature 2.1: Qdrant Client Foundation
- Feature 2.2: Document Ingestion Pipeline
- Feature 2.3: Embedding Service
- Feature 2.4: Text Chunking Strategy
- Feature 2.5: BM25 Search Engine
- Feature 2.6: Hybrid Search (Vector + BM25)
- Feature 2.7: Retrieval API Endpoints
- Feature 2.8: Security Hardening

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: Feature development (1 Feature = 1 Branch)
- `fix/*`: Bug fixes
- `sprint-N`: Sprint-specific branches

### Commit Convention
```
<type>(<scope>): <subject>

[optional body]
[optional footer]
```

**Types:** feat, fix, docs, style, refactor, test, chore
**Scopes:** vector, graph, memory, mcp, agent, api, infra, security

**Examples:**
```
feat(vector): implement hybrid search with BM25
feat(qdrant): implement client wrapper with connection pooling
feat(security): add P0 input validation and injection prevention
fix(graph): resolve neo4j connection pooling issue
docs(api): add OpenAPI schema for retrieval endpoints
```

**REGEL:** 1 Feature = 1 Commit (außer bei sehr großen Features: dann Feature-Teilschritte)

### Code Quality Gates
- **Linting:** Ruff (replaces Flake8, isort, pyupgrade)
- **Formatting:** Black (line-length=100)
- **Type Checking:** MyPy (strict mode)
- **Security:** Bandit, Safety
- **Testing:** pytest with coverage >80%
- **Pre-commit Hooks:** Auto-run on `git commit`

---

## Subagent Responsibilities

### Backend Subagent (primary)
**Focus:** Core business logic, agent implementation, orchestration
- LangGraph agent definitions
- Retrieval algorithms (Hybrid Search, RRF)
- Memory management logic
- MCP server implementation
- Unit & integration tests

### Infrastructure Subagent
**Focus:** DevOps, deployment, observability
- Docker Compose & Dockerfiles
- Kubernetes manifests (Helm charts)
- CI/CD pipelines (GitHub Actions)
- Monitoring setup (Prometheus, Grafana)
- Database migrations & backups

### API Subagent
**Focus:** REST API, input validation, error handling
- FastAPI routers & endpoints
- Pydantic request/response models
- OpenAPI documentation
- Rate limiting & authentication
- API integration tests

### Testing Subagent
**Focus:** Test coverage, quality assurance
- pytest fixtures & utilities
- Unit tests for all modules
- Integration tests for agents
- E2E tests for user flows
- Performance & load tests

---

## Critical Implementation Details

### LangGraph Agent Pattern
```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

# State Management
class AgentState(MessagesState):
    query: str
    intent: str
    retrieved_contexts: List[Document]
    final_answer: str

# Graph Construction
graph = StateGraph(AgentState)
graph.add_node("router", route_query)
graph.add_node("vector_search", vector_search_agent)
graph.add_node("graph_query", graph_query_agent)
graph.add_node("fusion", context_fusion)
graph.add_node("generate", generation_agent)

# Conditional Routing
graph.add_conditional_edges(
    "router",
    determine_path,
    {
        "vector": "vector_search",
        "graph": "graph_query",
        "hybrid": "vector_search",  # Then parallel to graph
    }
)
```

### Hybrid Search Implementation
```python
# Reciprocal Rank Fusion
def reciprocal_rank_fusion(
    vector_results: List[Document],
    bm25_results: List[Document],
    k: int = 60
) -> List[Document]:
    """Combine vector and keyword search with RRF."""
    scores = defaultdict(float)
    for rank, doc in enumerate(vector_results):
        scores[doc.id] += 1 / (k + rank + 1)
    for rank, doc in enumerate(bm25_results):
        scores[doc.id] += 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### Error Handling Pattern
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def retrieval_with_retry(query: str) -> List[Document]:
    """Retrieve with automatic retry on transient failures."""
    try:
        return await qdrant_client.search(query)
    except QdrantException as e:
        logger.error(f"Retrieval failed: {e}")
        raise
```

---

## Environment Variables

### Required Configuration
```bash
# Ollama (Primary - No API Keys needed!)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=llama3.2:8b
OLLAMA_MODEL_QUERY=llama3.2:3b
OLLAMA_MODEL_EMBEDDING=nomic-embed-text

# Optional: Azure OpenAI (Production only)
# USE_AZURE_LLM=false
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_API_KEY=your-api-key
# ANTHROPIC_API_KEY=sk-ant-...  # Optional fallback

# Databases
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=<optional>

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure-password>

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<optional>

# Observability
LANGSMITH_API_KEY=<optional>
LANGSMITH_PROJECT=aegis-rag

# MCP
MCP_SERVER_PORT=3000
MCP_AUTH_ENABLED=true
```

---

## Performance Requirements

### Latency Targets
- **Simple Query (Vector Only):** <200ms p95
- **Hybrid Query (Vector + Graph):** <500ms p95
- **Complex Multi-Hop:** <1000ms p95
- **Memory Retrieval:** <100ms p95

### Throughput
- **Sustained Load:** 50 QPS
- **Peak Load:** 100 QPS (with auto-scaling)

### Resource Limits
- **Memory per Request:** <512MB
- **Total System Memory:** <16GB (excluding DBs)
- **CPU:** <4 cores sustained

---

## Testing Strategy

### Unit Tests (>80% coverage)
- Test each agent in isolation with mocked dependencies
- Test retrieval algorithms with synthetic data
- Test memory consolidation logic

### Integration Tests
- Test agent → component interactions
- Test database operations (Qdrant, Neo4j, Redis)
- Test MCP server communication

### E2E Tests
- Test full query flows (User Query → Final Answer)
- Test multi-turn conversations with memory
- Test error handling and recovery

### Performance Tests
- Load testing with Locust (100 concurrent users)
- Stress testing to find breaking point
- Soak testing (24h sustained load)

---

## Monitoring & Observability

### Metrics to Track
```yaml
Retrieval Metrics:
  - query_latency_ms (p50, p95, p99)
  - retrieval_precision_at_k
  - context_relevance_score
  - document_coverage

Agent Metrics:
  - agent_execution_time_ms
  - tool_call_count
  - tool_call_success_rate
  - routing_accuracy

Memory Metrics:
  - memory_hit_rate (per layer)
  - memory_eviction_rate
  - memory_consolidation_latency

System Metrics:
  - requests_per_second
  - error_rate (4xx, 5xx)
  - active_connections
  - database_connection_pool_usage
```

### Alerting Rules
- **Critical:** p95 latency >1000ms for 5min
- **Warning:** Error rate >5% for 3min
- **Info:** Memory hit rate <60%

---

## Common Issues & Solutions

### Issue: Qdrant Connection Timeout
**Solution:** Increase connection pool size in `config.py`, check network latency

### Issue: Neo4j Out of Memory during Indexing
**Solution:** Batch processing, reduce concurrent writes, increase `dbms.memory.heap.max_size`

### Issue: LangGraph State Not Persisting
**Solution:** Verify Redis connection, check state serialization (Pydantic compatibility)

### Issue: MCP OAuth Flow Fails
**Solution:** Check redirect URI configuration, verify Auth0/Clerk credentials

---

## Security Considerations

### Input Validation
- Sanitize all user inputs (query, parameters)
- Validate file uploads (type, size, malware scan)
- Rate limiting per user/IP

### Secrets Management
- Never commit secrets to Git
- Use environment variables or secret managers (Vault, AWS Secrets Manager)
- Rotate API keys regularly

### Data Access
- Implement RBAC for multi-tenancy
- Audit logs for sensitive operations
- Encrypt data at rest (Neo4j, Redis)

### API Security
- HTTPS only in production
- JWT authentication with short expiry
- CORS configuration for allowed origins

---

## Deployment

### Local Development
```bash
# Start all services
docker compose up -d

# Run migrations
python scripts/migrate.py

# Start API server
uvicorn src.api.main:app --reload --port 8000
```

### Production (Kubernetes)
```bash
# Deploy with Helm
helm install aegis-rag ./k8s/helm-chart \
  --namespace production \
  --values k8s/values-prod.yaml

# Check deployment
kubectl get pods -n production
kubectl logs -f deployment/aegis-rag-api -n production
```

---

## Troubleshooting Commands

```bash
# Check service health
curl http://localhost:8000/health

# View logs
docker compose logs -f api
docker compose logs -f qdrant
docker compose logs -f neo4j

# Database access
# Qdrant UI: http://localhost:6333/dashboard
# Neo4j Browser: http://localhost:7474
# Redis CLI: redis-cli -h localhost -p 6379

# Run specific test suite
pytest tests/integration/test_agents.py -v

# Performance profiling
python -m cProfile -o profile.stats scripts/benchmark.py
```

---

## Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LlamaIndex Docs](https://docs.llamaindex.ai/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [RAGAS Evaluation](https://docs.ragas.io/)

---

## Contact & Support

- **Project Lead:** [Your Name]
- **Repository:** github.com/your-org/aegis-rag
- **Documentation:** docs.aegis-rag.com
- **Issue Tracker:** GitHub Issues
- **Community:** Discord/Slack Channel
