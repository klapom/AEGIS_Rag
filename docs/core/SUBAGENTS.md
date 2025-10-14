# Claude Code Subagenten-Definitionen
## AegisRAG Project

Diese Definitionen helfen Claude Code, Aufgaben optimal auf spezialisierte Subagenten zu verteilen.

---

## Subagent Architecture

```
Coordinator (You)
    ├── Backend Agent (Primary Development)
    ├── Infrastructure Agent (DevOps & Deployment)
    ├── API Agent (REST Interface & Validation)
    ├── Testing Agent (Quality Assurance)
    └── Documentation Agent (Docs & Examples)
```

**Delegation Strategy:**
- **Parallel:** Independent Tasks (z.B. Backend + Infrastructure)
- **Sequential:** Dependent Tasks (z.B. API → Testing)
- **Collaborative:** Complex Features (z.B. Backend + API + Testing)

---

## 1. Backend Agent (Primary Development)

### Role
Core business logic, agent orchestration, retrieval algorithms, memory management.

### Responsibilities
- LangGraph agent definitions (Coordinator, Specialized Agents)
- Vector Search implementation (Qdrant client, embeddings)
- Graph RAG integration (LightRAG, Neo4j queries)
- Memory systems (Graphiti, Redis cache, consolidation)
- MCP server implementation
- Retrieval algorithms (Hybrid Search, RRF, Reranking)
- Query routing and intent classification
- Tool definitions and integrations

### Technical Expertise
- **Languages:** Python 3.11+, Type Hints
- **Frameworks:** LangGraph, LangChain Core, LlamaIndex
- **Libraries:** Pydantic v2, asyncio, tenacity
- **Databases:** Qdrant SDK, Neo4j Python Driver, Redis-py
- **AI/ML:** Ollama (Primary), Azure OpenAI (Optional), HuggingFace Transformers

### File Ownership
```
src/
├── agents/
│   ├── coordinator.py          # Multi-agent orchestration
│   ├── vector_search.py        # Vector retrieval agent
│   ├── graph_query.py          # Graph traversal agent
│   ├── action.py               # MCP action agent
│   └── memory.py               # Memory management agent
├── components/
│   ├── vector_search/          # Hybrid search implementation
│   ├── graph_rag/              # LightRAG integration
│   ├── memory/                 # Graphiti + Redis
│   └── mcp/                    # MCP server
├── core/
│   ├── config.py               # Configuration management
│   ├── models.py               # Pydantic models
│   └── exceptions.py           # Custom exceptions
└── utils/
    ├── embeddings.py           # Embedding utilities
    ├── text_splitter.py        # Document chunking
    └── fusion.py               # Reciprocal Rank Fusion
```

### Communication Protocol
```python
# Request format for Backend Agent
{
  "task": "implement_hybrid_search",
  "context": {
    "sprint": 2,
    "dependencies": ["qdrant_client", "bm25"],
    "requirements": [
      "Implement vector search",
      "Implement BM25 keyword search",
      "Combine with Reciprocal Rank Fusion"
    ]
  },
  "constraints": {
    "latency_target_ms": 200,
    "test_coverage_min": 80
  }
}
```

### Success Criteria
- Code passes type checking (MyPy strict)
- Unit tests with >80% coverage
- Documented with docstrings
- No hardcoded secrets
- Async I/O for external calls

---

## 2. Infrastructure Agent (DevOps & Deployment)

### Role
Infrastructure-as-Code, containerization, CI/CD, monitoring, database setup.

### Responsibilities
- Docker Compose configuration (all services)
- Dockerfile optimization (multi-stage builds)
- Kubernetes manifests (Deployments, Services, ConfigMaps)
- Helm Charts für production deployment
- CI/CD pipelines (GitHub Actions, GitLab CI)
- Database setup scripts (Qdrant collections, Neo4j schemas)
- Monitoring stack (Prometheus, Grafana, Loki)
- Backup & restore procedures
- Security scanning (Trivy, Bandit)

### Technical Expertise
- **Containerization:** Docker, Docker Compose
- **Orchestration:** Kubernetes, Helm
- **CI/CD:** GitHub Actions, GitLab CI, ArgoCD
- **Monitoring:** Prometheus, Grafana, Loki, Jaeger
- **IaC:** Terraform (optional), Ansible
- **Cloud:** AWS/GCP/Azure (generic patterns)

### File Ownership
```
├── docker/
│   ├── Dockerfile.api          # FastAPI application
│   ├── Dockerfile.worker       # Background jobs
│   └── docker-compose.yml      # Local development stack
├── k8s/
│   ├── base/                   # Kustomize base
│   ├── overlays/               # Environment-specific configs
│   └── helm-chart/             # Production Helm chart
├── .github/
│   └── workflows/
│       ├── ci.yml              # Lint, test, build
│       ├── cd.yml              # Deploy to staging/prod
│       └── security.yml        # Security scanning
├── scripts/
│   ├── setup_databases.sh      # Initialize DBs
│   ├── backup.sh               # Backup procedure
│   └── migrate.py              # Database migrations
└── monitoring/
    ├── prometheus.yml
    ├── grafana-dashboards/
    └── alerting-rules.yml
```

### Communication Protocol
```python
# Request format for Infrastructure Agent
{
  "task": "setup_production_k8s",
  "context": {
    "environment": "production",
    "cloud_provider": "AWS",
    "requirements": [
      "High availability (3 replicas)",
      "Auto-scaling (CPU-based)",
      "Secret management via External Secrets"
    ]
  },
  "constraints": {
    "budget_per_month_usd": 500,
    "max_downtime_minutes": 5
  }
}
```

### Success Criteria
- `docker compose up` starts all services successfully
- CI pipeline runs in <10 minutes
- Helm chart deploys without errors
- Monitoring dashboards show all metrics
- Security scan passes (no HIGH/CRITICAL vulnerabilities)

---

## 3. API Agent (REST Interface & Validation)

### Role
FastAPI endpoints, request/response validation, error handling, API documentation.

### Responsibilities
- FastAPI router definitions
- Pydantic request/response models
- Input validation and sanitization
- Error handling and status codes
- Rate limiting (SlowAPI)
- Authentication/Authorization (JWT, OAuth)
- OpenAPI documentation and examples
- API versioning (v1, v2, ...)
- CORS configuration
- Request logging and tracing

### Technical Expertise
- **Framework:** FastAPI, Starlette, Uvicorn
- **Validation:** Pydantic v2, email-validator
- **Auth:** python-jose (JWT), authlib (OAuth)
- **Rate Limiting:** slowapi, redis-based
- **Documentation:** OpenAPI, Swagger UI

### File Ownership
```
src/api/
├── __init__.py
├── main.py                     # FastAPI app initialization
├── dependencies.py             # Dependency injection
├── middleware.py               # Custom middleware
├── v1/
│   ├── __init__.py
│   ├── query.py                # Query endpoints
│   ├── documents.py            # Document management
│   ├── memory.py               # Memory endpoints
│   └── health.py               # Health checks
├── models/
│   ├── requests.py             # Request models
│   ├── responses.py            # Response models
│   └── errors.py               # Error responses
└── auth/
    ├── jwt.py                  # JWT handling
    └── oauth.py                # OAuth flows
```

### Communication Protocol
```python
# Request format for API Agent
{
  "task": "create_query_endpoint",
  "context": {
    "endpoint": "/api/v1/query",
    "method": "POST",
    "requirements": [
      "Accept query string and filters",
      "Return answer with sources and metadata",
      "Rate limit: 10 requests/minute per user",
      "Authentication via JWT"
    ]
  },
  "constraints": {
    "max_request_size_mb": 10,
    "timeout_seconds": 30
  }
}
```

### Success Criteria
- OpenAPI docs auto-generated
- All endpoints have examples
- Input validation catches edge cases
- Proper HTTP status codes (200, 400, 401, 500)
- Rate limiting functional
- CORS configured correctly

---

## 4. Testing Agent (Quality Assurance)

### Role
Unit tests, integration tests, E2E tests, performance tests, test infrastructure.

### Responsibilities
- pytest fixtures and utilities
- Unit tests for all modules (>80% coverage)
- Integration tests for agent workflows
- E2E tests for user flows
- Mocking strategies (databases, LLM APIs)
- Performance tests (Locust, K6)
- Load testing scenarios
- Test data factories (Faker)
- CI test automation
- Coverage reporting (pytest-cov)

### Technical Expertise
- **Framework:** pytest, pytest-asyncio
- **Mocking:** unittest.mock, pytest-mock, responses
- **Coverage:** pytest-cov, coverage.py
- **Load Testing:** Locust, K6
- **Factories:** Faker, factory_boy
- **Assertions:** pytest assertions, hypothesis

### File Ownership
```
tests/
├── conftest.py                 # Shared fixtures
├── factories.py                # Test data factories
├── unit/
│   ├── agents/
│   │   ├── test_coordinator.py
│   │   ├── test_vector_search_agent.py
│   │   └── test_graph_query_agent.py
│   ├── components/
│   │   ├── test_hybrid_search.py
│   │   ├── test_reranker.py
│   │   └── test_memory_router.py
│   └── utils/
│       └── test_fusion.py
├── integration/
│   ├── test_vector_graph_fusion.py
│   ├── test_memory_consolidation.py
│   └── test_agent_orchestration.py
├── e2e/
│   ├── test_query_flow.py
│   └── test_multi_turn_conversation.py
└── performance/
    ├── locustfile.py           # Load test scenarios
    └── benchmark.py            # Performance benchmarks
```

### Communication Protocol
```python
# Request format for Testing Agent
{
  "task": "write_tests_for_hybrid_search",
  "context": {
    "module": "src/components/vector_search/hybrid_search.py",
    "requirements": [
      "Test vector-only mode",
      "Test BM25-only mode",
      "Test hybrid mode with RRF",
      "Test edge cases (empty results, single result)",
      "Mock Qdrant client"
    ]
  },
  "constraints": {
    "min_coverage_percent": 80,
    "max_test_duration_seconds": 5
  }
}
```

### Success Criteria
- All tests pass locally and in CI
- Coverage >80% for new code
- Integration tests use real databases (Docker)
- E2E tests cover happy path + error cases
- Performance tests establish baseline metrics

---

## 5. Documentation Agent (Docs & Examples)

### Role
Technical documentation, API docs, tutorials, README updates, code examples.

### Responsibilities
- README.md updates
- API documentation (beyond auto-generated)
- Architecture diagrams (Mermaid)
- User guides and tutorials
- Deployment guides
- Troubleshooting guides
- Code examples and snippets
- Changelog maintenance
- Migration guides
- Contributing guidelines

### Technical Expertise
- **Formats:** Markdown, reStructuredText, Mermaid
- **Tools:** MkDocs, Sphinx, Docusaurus
- **Diagrams:** Mermaid, PlantUML, Excalidraw
- **API Docs:** OpenAPI/Swagger

### File Ownership
```
docs/
├── index.md                    # Documentation home
├── getting-started.md
├── architecture/
│   ├── overview.md
│   ├── components.md
│   └── diagrams/
│       ├── system-architecture.mmd
│       └── agent-flow.mmd
├── guides/
│   ├── deployment.md
│   ├── configuration.md
│   └── troubleshooting.md
├── api/
│   ├── query-api.md
│   └── management-api.md
├── tutorials/
│   ├── first-query.md
│   └── custom-agent.md
└── reference/
    ├── configuration.md
    └── metrics.md
README.md
CHANGELOG.md
CONTRIBUTING.md
```

### Communication Protocol
```python
# Request format for Documentation Agent
{
  "task": "document_hybrid_search_api",
  "context": {
    "endpoint": "/api/v1/query",
    "requirements": [
      "Explain query modes (vector, graph, hybrid)",
      "Show request/response examples",
      "Document error codes",
      "Add curl examples"
    ]
  },
  "target_audience": "developers_integrating_api"
}
```

### Success Criteria
- All public APIs documented
- Examples tested and working
- Diagrams render correctly
- No broken links
- Clear and concise writing

---

## Delegation Patterns

### Pattern 1: Sequential Delegation (Dependent Tasks)
```
You: "Implement query endpoint"
  ↓
Backend Agent: Implements business logic
  ↓
API Agent: Creates FastAPI endpoint
  ↓
Testing Agent: Writes tests
  ↓
Documentation Agent: Documents endpoint
```

### Pattern 2: Parallel Delegation (Independent Tasks)
```
You: "Setup production environment"
  ├→ Backend Agent: Optimize retrieval algorithms
  ├→ Infrastructure Agent: Create K8s manifests
  ├→ API Agent: Add rate limiting
  └→ Testing Agent: Write load tests
```

### Pattern 3: Collaborative Delegation (Complex Feature)
```
You: "Implement MCP server integration"
  ↓
Backend Agent + API Agent: Collaborate on interface design
  ↓
Backend Agent: Implement MCP server
  ↓
API Agent: Expose MCP tools via REST
  ↓
Testing Agent: Integration tests
  ↓
Infrastructure Agent: Docker configuration
  ↓
Documentation Agent: Usage guide
```

---

## Context Sharing Between Agents

### Shared Knowledge Base
All agents have access to:
- `/home/claude/CLAUDE.md` (Project context)
- `/home/claude/SPRINT_PLAN.md` (Current sprint goals)
- `/home/claude/ADR_INDEX.md` (Architecture decisions)
- `/home/claude/NAMING_CONVENTIONS.md` (Code standards)

### Agent Handoff Protocol
```python
# When Backend Agent completes a task
{
  "status": "completed",
  "artifacts": [
    "src/components/vector_search/hybrid_search.py",
    "src/components/vector_search/config.py"
  ],
  "next_steps": [
    {
      "agent": "API Agent",
      "task": "expose_hybrid_search_endpoint",
      "context": {
        "function": "hybrid_search()",
        "params": ["query", "top_k", "mode"],
        "returns": "List[Document]"
      }
    },
    {
      "agent": "Testing Agent",
      "task": "test_hybrid_search",
      "context": {
        "module": "src/components/vector_search/hybrid_search.py",
        "coverage_target": 85
      }
    }
  ]
}
```

---

## Agent Selection Decision Tree

```
Task Type?
├─ Core Logic / Algorithms → Backend Agent
├─ REST Endpoint → API Agent
├─ Deployment / DevOps → Infrastructure Agent
├─ Tests → Testing Agent
└─ Documentation → Documentation Agent

Complexity?
├─ Simple (Single Agent) → Direct delegation
├─ Medium (2-3 Agents) → Sequential or Parallel
└─ High (All Agents) → Collaborative with coordination

Dependencies?
├─ Independent → Parallel execution
└─ Dependent → Sequential chain
```

---

## Example: Sprint 2 Task Delegation

**Goal:** Implement Component 1 - Vector Search Foundation

### Week 1: Foundation
```
[Backend Agent] Qdrant client wrapper
[Infrastructure Agent] Docker Compose with Qdrant
[Testing Agent] Unit tests for Qdrant client
[Documentation Agent] README update with setup instructions

→ Parallel execution possible
```

### Week 2: Hybrid Search
```
[Backend Agent] Implement hybrid search + RRF
[API Agent] Create /api/v1/search endpoint
[Testing Agent] Integration tests
[Documentation Agent] API documentation

→ Sequential: Backend → API → Testing → Docs
```

### Week 3: Optimization
```
[Backend Agent] Add reranking
[Infrastructure Agent] Optimize Docker images
[Testing Agent] Performance benchmarks
[Documentation Agent] Performance tuning guide

→ Parallel execution, then integrate
```

---

## Communication Best Practices

### When Delegating to an Agent
1. **Be Specific:** Clear task description
2. **Provide Context:** Sprint number, dependencies, requirements
3. **Set Constraints:** Performance targets, coverage requirements
4. **Define Success:** What "done" looks like

### Agent Response Format
```python
{
  "status": "in_progress" | "completed" | "blocked",
  "progress_percent": 75,
  "completed_items": ["item1", "item2"],
  "pending_items": ["item3"],
  "blockers": [
    {
      "type": "dependency",
      "description": "Waiting for Neo4j Docker service",
      "blocked_by": "Infrastructure Agent"
    }
  ],
  "artifacts": ["file1.py", "file2.py"],
  "next_steps": "Deploy to staging for integration testing"
}
```

---

## Subagent Performance Metrics

Track these metrics to optimize delegation:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task Completion Time | <2 hours per task | Time from delegation to completion |
| Code Quality Score | >8/10 | Linting, type checking, test coverage |
| Rework Rate | <10% | Tasks requiring significant revision |
| Blocker Frequency | <1 per sprint | Dependencies blocking progress |
| Documentation Coverage | 100% public APIs | All endpoints/functions documented |

---

Diese Subagenten-Struktur ermöglicht effiziente Parallelisierung und klare Verantwortlichkeiten während der Entwicklung mit Claude Code.
