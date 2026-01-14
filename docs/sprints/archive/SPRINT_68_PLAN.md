# Sprint 68: Production Hardening & Performan Optimization

**Status:** PLANNED
**Branch:** `sprint-68-production-hardening`
**Start Date:** TBD (nach Sprint 67)
**Estimated Duration:** 8-10 Tage
**Total Story Points:** 62 SP

---

## Sprint Overview

Sprint 68 ist ein **Production Hardening Sprint** - Konsolidierung und Optimierung der Sprint 67 Agentic Capabilities mit Fokus auf:

1. **E2E Test Completion** - 100% Critical Path Coverage (594 tests stabilized)
2. **Performance Optimization** - Memory Management, Query Latency, Throughput
3. **Section Community Detection** - Graph-based Section Analysis
4. **Advanced Adaptation Features** - Memory-Write Policy, Tool-Execution Rewards
5. **Bug Fixes & Stabilization** - Learnings aus Sprint 67 Deployment

**Architektur-Leitplanken:**
- Keine neuen Major Features (nur Completion & Optimization)
- Performance Regression Testing als Gate
- Code Coverage ≥85%
- Zero Known Critical Bugs

**Voraussetzung:**
Sprint 67 abgeschlossen (Sandbox, Adaptation, C-LARA deployed)

---

## Feature Overview

| # | Feature | SP | Priority | Dependencies |
|---|---------|-----|----------|--------------|
| 68.1 | E2E Test Completion (594 Tests) | 13 | P0 | - |
| 68.2 | Performance Profiling & Bottleneck Analysis | 5 | P0 | - |
| 68.3 | Memory Management & Budget Optimization | 8 | P0 | 68.2 |
| 68.4 | Query Latency Optimization | 8 | P0 | 68.2 |
| 68.5 | Section Community Detection | 10 | P1 | - |
| 68.6 | Memory-Write Policy + Forgetting (FEAT-006) | 10 | P1 | 68.3 |
| 68.7 | Tool-Execution Reward Loop (FEAT-007) | 8 | P2 | - |
| 68.8 | Sprint 67 Bug Fixes & Stabilization | 5 | P0 | Sprint 67 |
| 68.9 | Documentation Consolidation | 3 | P1 | - |
| 68.10 | Production Deployment Validation | 2 | P0 | All |

**Total: 72 SP** (reduced to 62 SP with parallel execution)

---

## Epic 1: E2E Test Completion & Stabilization - 13 SP

### Feature 68.1: E2E Test Completion (13 SP)

**Priority:** P0
**Ziel:** 100% Playwright E2E Test Coverage für kritische User Journeys

**Scope:**
- Complete all 594 Playwright tests (currently ~337 passing, 57%)
- Fix failing tests from Sprint 65/66
- Add missing test coverage for Sprint 67 features:
  - Sandbox execution tests
  - Adaptive tool tests (Reranker, Query Rewriter)
  - Intent classifier A/B tests
- Stabilize flaky tests
- CI/CD integration with parallelization

**Test Categories:**
| Category | Tests | Status | Target |
|----------|-------|--------|--------|
| **Document Ingestion** | 80 | 45 passing (56%) | 100% |
| **Search & Retrieval** | 120 | 75 passing (63%) | 100% |
| **Conversation** | 100 | 50 passing (50%) | 100% |
| **Admin UI** | 80 | 60 passing (75%) | 100% |
| **Graph Exploration** | 60 | 35 passing (58%) | 100% |
| **Domain Training** | 50 | 25 passing (50%) | 100% |
| **Sandbox & Agents** | 50 | 0 passing (NEW) | 100% |
| **Adaptation Tools** | 54 | 0 passing (NEW) | 100% |
| **Total** | **594** | **337 (57%)** | **594 (100%)** |

**New Test Suites:**
```typescript
// frontend/e2e/sandbox-execution.spec.ts
test('execute bash command in sandbox', async ({ page }) => {
  await page.goto('/agents');
  await page.fill('[data-testid="command-input"]', 'ls -la');
  await page.click('[data-testid="execute-btn"]');
  await expect(page.locator('[data-testid="output"]')).toContainText('total');
});

// frontend/e2e/adaptive-reranker.spec.ts
test('reranker improves retrieval quality', async ({ page }) => {
  // Query with baseline reranker
  const baseline_results = await queryWithReranker(page, 'baseline');
  // Query with adaptive reranker v1
  const v1_results = await queryWithReranker(page, 'v1');
  // Assert: v1 has better relevance score
  expect(v1_results.relevance_score).toBeGreaterThan(baseline_results.relevance_score);
});
```

**Acceptance Criteria:**
- [ ] 594/594 tests passing (100%)
- [ ] Test suite runs <20 minutes (parallelized)
- [ ] Zero flaky tests (3x consecutive pass)
- [ ] CI/CD integration functional
- [ ] Code coverage ≥85%

---

## Epic 2: Performance Optimization - 21 SP

### Feature 68.2: Performance Profiling & Bottleneck Analysis (5 SP)

**Priority:** P0
**Ziel:** Identify and document performance bottlenecks

**Scope:**
- **Profiling Tools:**
  - Python: `cProfile`, `py-spy`, `memory_profiler`
  - Database: Neo4j Query Profiler, Qdrant Metrics
  - HTTP: Prometheus + Grafana Dashboard
- **Target Metrics:**
  - Query Latency (P50, P95, P99)
  - Memory Usage (VRAM, RAM, Heap)
  - Throughput (QPS)
  - Database Response Times

**Implementation:**
```bash
# Profile end-to-end query
python scripts/profile_query.py \
  --query "Was sind die neuen Features?" \
  --iterations 100 \
  --output reports/profile_query_20251231.json

# Memory profiling
mprof run scripts/profile_memory.py
mprof plot --output reports/memory_profile.png

# Neo4j Query Profiling
# PROFILE MATCH (e:base)-[:RELATES_TO]->(e2) RETURN count(*) AS relationships
```

**Deliverables:**
- **Performance Report:**
  ```markdown
  ## Performance Bottlenecks (Sprint 67 Baseline)

  ### Query Latency Breakdown (P95)
  - Intent Classification: 80ms (16%)
  - Vector Retrieval: 150ms (30%)
  - Graph Retrieval: 100ms (20%)
  - RRF Fusion: 30ms (6%)
  - Reranking: 50ms (10%)
  - Answer Generation: 90ms (18%)
  **Total: 500ms**

  ### Memory Usage
  - BGE-M3 Embeddings: 2.1GB VRAM
  - Neo4j Graph: 3.5GB RAM
  - Qdrant Vectors: 1.8GB RAM
  - Application: 1.2GB RAM
  **Total: 8.6GB**

  ### Bottlenecks
  1. **Vector Retrieval** - 150ms (30% of total) - Qdrant query optimization needed
  2. **Intent Classification** - 80ms (16%) - C-LARA should reduce to 50-100ms
  3. **Graph Retrieval** - 100ms (20%) - Community Detection precomputation needed
  ```

**Acceptance Criteria:**
- [ ] Performance report generated
- [ ] Bottlenecks identified & ranked
- [ ] Optimization targets defined
- [ ] Baseline metrics documented

---

### Feature 68.3: Memory Management & Budget Optimization (8 SP)

**Priority:** P0
**Ziel:** Reduce memory footprint by 20-30%

**Scope:**
- **Optimization Targets:**
  - BGE-M3 Embeddings: Reduce from 2.1GB to 1.5GB VRAM (quantization)
  - Neo4j Graph: Connection pooling optimization
  - Qdrant: Vector compression (scalar quantization)
  - Application: Memory leak detection & fix
- **Memory Budgeting:**
  - Define limits per component
  - Implement OOM protection
  - Auto-scaling policies

**Implementation:**
```python
# BGE-M3 Quantization (FP16 → INT8)
from optimum.onnxruntime import ORTModelForFeatureExtraction

model = ORTModelForFeatureExtraction.from_pretrained(
    "BAAI/bge-m3",
    export=True,
    provider="CUDAExecutionProvider",
    use_io_binding=True,
    quantization_config="int8"  # Reduce VRAM by ~50%
)

# Qdrant Scalar Quantization
from qdrant_client.models import ScalarQuantization

client.update_collection(
    collection_name="documents_v1",
    quantization_config=ScalarQuantization(
        scalar={"type": "int8", "quantile": 0.99}
    )
)
# Expected: -30% memory, -5% accuracy
```

**Acceptance Criteria:**
- [ ] Memory usage reduced by 20-30%
- [ ] No accuracy degradation >5%
- [ ] OOM protection implemented
- [ ] Memory budgets documented

---

### Feature 68.4: Query Latency Optimization (8 SP)

**Priority:** P0
**Ziel:** Reduce P95 query latency from 500ms to 350ms

**Scope:**
- **Optimization Strategies:**
  1. **Intent Classification:** C-LARA (80ms → 50ms)
  2. **Vector Retrieval:** Qdrant indexing + caching (150ms → 100ms)
  3. **Graph Retrieval:** Community Detection precomputation (100ms → 70ms)
  4. **RRF Fusion:** Parallel execution (30ms → 20ms)
  5. **Reranking:** Batch processing (50ms → 30ms)
  6. **Answer Generation:** Streaming + caching (90ms → 80ms)

**Implementation:**
```python
# 1. Parallel RRF Fusion
async def weighted_reciprocal_rank_fusion_parallel(
    vector_results: list,
    bm25_results: list,
    graph_local_results: list,
    graph_global_results: list,
    weights: dict
) -> list:
    """Parallel RRF with asyncio."""
    # Process all 4 result sets in parallel
    tasks = [
        asyncio.create_task(process_results(vector_results, weights["vector"])),
        asyncio.create_task(process_results(bm25_results, weights["bm25"])),
        asyncio.create_task(process_results(graph_local_results, weights["local"])),
        asyncio.create_task(process_results(graph_global_results, weights["global"]))
    ]
    processed = await asyncio.gather(*tasks)
    # Fuse results
    return fuse(processed)

# 2. Community Detection Precomputation
# Instead of runtime computation, precompute during ingestion
await detector.detect_communities_in_section(
    section_heading="Introduction",
    store_in_neo4j=True  # Store for fast retrieval
)
```

**Acceptance Criteria:**
- [ ] P95 latency reduced from 500ms to 350ms (-30%)
- [ ] P99 latency <600ms
- [ ] Throughput +20% (40 QPS → 50 QPS)
- [ ] No accuracy degradation

---

## Epic 3: Section Community Detection - 10 SP

### Feature 68.5: Section Community Detection (10 SP)

**Priority:** P1
**Ziel:** Graph-based Section Analysis mit Louvain/Leiden

**Scope:**
- Community Detection pro Section
- Cross-Section overlap analysis
- Community-based retrieval
- Graph visualization updates
- Integration mit section_community_detection_queries.md

**Architecture:**
```
Document
   |
   +--[:HAS_SECTION]-->Section
                         |
                         +--[:DEFINES]-->Entity (base)
                                           |
                                           +--[:BELONGS_TO_COMMUNITY]-->Community
                                           |
                                           +--[:RELATES_TO]-->Entity
```

**Implementation:**
```python
# src/domains/knowledge_graph/communities/section_community_detector.py
from networkx.algorithms import community as nx_community

class SectionCommunityDetector:
    async def detect_communities_in_section(
        self,
        section_heading: str,
        document_id: str,
        algorithm: str = "louvain",
        resolution: float = 1.0
    ) -> dict:
        """Detect communities within a section."""
        # 1. Get section entities (Query #1 from section_community_detection_queries.md)
        entities = await self._get_section_entities(section_heading)

        # 2. Get section subgraph (Query #2)
        subgraph = await self._get_section_subgraph(section_heading)

        # 3. Build NetworkX graph
        G = nx.Graph()
        G.add_edges_from([(r["source"], r["target"]) for r in subgraph])

        # 4. Detect communities
        if algorithm == "louvain":
            communities = nx_community.louvain_communities(G, resolution=resolution)
        elif algorithm == "leiden":
            communities = nx_community.leiden(G, resolution=resolution)

        # 5. Store communities (Query #3)
        for idx, community in enumerate(communities):
            await self._store_community(
                community_id=f"section_community_{idx}",
                section_heading=section_heading,
                entity_ids=list(community),
                size=len(community),
                density=self._calculate_density(G, community),
                algorithm=algorithm,
                resolution=resolution
            )

        # 6. Update section metadata (Query #9)
        await self._update_section_metadata(
            section_heading=section_heading,
            community_count=len(communities)
        )

        return {
            "section": section_heading,
            "communities": len(communities),
            "algorithm": algorithm,
            "resolution": resolution
        }
```

**Cypher Queries** (from section_community_detection_queries.md):
```cypher
// Get Section Entities (Query #1)
MATCH (s:Section)-[:DEFINES]->(e:base)
WHERE s.heading = $section_heading
RETURN e.entity_id, e.name, e.type

// Get Section Subgraph (Query #2)
MATCH (s:Section {heading: $section_heading})
MATCH (s)-[:DEFINES]->(e1:base)
MATCH (s)-[:DEFINES]->(e2:base)
MATCH (e1)-[r:RELATES_TO]-(e2)
WHERE e1.entity_id < e2.entity_id
RETURN e1.entity_id AS source, e2.entity_id AS target

// Store Communities (Query #3)
UNWIND $entity_ids AS entity_id
MATCH (e:base {entity_id: entity_id})
MERGE (e)-[r:BELONGS_TO_COMMUNITY]->(c:Community {
    community_id: $community_id,
    section_heading: $section_heading
})
ON CREATE SET c.created_at = datetime(), c.size = $size, c.density = $density
```

**Acceptance Criteria:**
- [ ] Community Detection pro Section funktional
- [ ] Louvain + Leiden algorithms supported
- [ ] Communities stored in Neo4j (BELONGS_TO_COMMUNITY)
- [ ] Cross-Section overlap analysis
- [ ] Performance: <200ms per section
- [ ] Graph UI zeigt Communities an

---

## Epic 4: Advanced Adaptation Features - 18 SP

### Feature 68.6: Memory-Write Policy + Forgetting (FEAT-006) - 10 SP

**Priority:** P1
**Ziel:** Steuerung was in Long-term Memory persistiert wird

**Scope:**
- **Memory-Write Policy:**
  - Decide: keep/summarize/drop per chunk/fact
  - Utility signal aus Eval-Metrics (grounding_score, citation_coverage)
  - Budget constraints (tokens, chunks, time)
- **Forgetting Strategy:**
  - Temporal decay (old memories fade)
  - Utility-based (low-utility memories dropped)
  - Summarization (compress instead of drop)
- **Versionierung:**
  - Memory snapshots (point-in-time restore)

**Implementation:**
```python
class MemoryWritePolicy:
    def __init__(
        self,
        token_budget: int = 100000,
        chunk_budget: int = 1000,
        min_utility_score: float = 0.5
    ):
        self.token_budget = token_budget
        self.chunk_budget = chunk_budget
        self.min_utility_score = min_utility_score

    async def decide(
        self,
        chunk: dict,
        utility_score: float,
        age_days: int
    ) -> str:
        """Decide: keep/summarize/drop."""
        # 1. Utility check
        if utility_score < self.min_utility_score:
            return "drop"

        # 2. Age check (temporal decay)
        if age_days > 90 and utility_score < 0.7:
            return "summarize"

        # 3. Budget check
        current_usage = await self._get_current_memory_usage()
        if current_usage["tokens"] > self.token_budget * 0.9:
            # Drop lowest-utility chunks
            return "drop"

        return "keep"

# Utility Score calculation
utility_score = (
    0.4 * grounding_score +      # How well grounded in evidence?
    0.3 * citation_coverage +     # How often cited in answers?
    0.2 * retrieval_frequency +   # How often retrieved?
    0.1 * freshness_score         # How recent?
)
```

**Acceptance Criteria:**
- [ ] Memory-Write Policy implementiert
- [ ] Utility signal aus Eval-Metrics
- [ ] Forgetting Strategy funktional
- [ ] Memory-Bloat reduziert (-20%)
- [ ] Answer-Qualität erhalten (keine Regression)

---

### Feature 68.7: Tool-Execution Reward Loop (FEAT-007) - 8 SP

**Priority:** P2 (Optional)
**Ziel:** Reward aus Tool-Ausführung für Plan/Query Optimization

**Scope:**
- **Execution-Check:**
  - SQL/Code-Execution mit pass/fail + diagnostics
  - Reward-Signal (binary + shaped)
  - Logging in Traces
- **Reward-Definition:**
  - Binary: 1.0 if pass, 0.0 if fail
  - Shaped: Partial credit (0.0-1.0) basierend auf diagnostics
- **Integration:**
  - Dataset Builder übernimmt Rewards
  - Canary-Subset für Execution Tasks

**Implementation:**
```python
class ExecutionRewardCalculator:
    async def calculate_reward(
        self,
        query: str,
        generated_code: str,
        execution_result: dict
    ) -> float:
        """Calculate reward from tool execution."""
        # 1. Binary reward
        if execution_result["success"]:
            return 1.0

        # 2. Shaped reward (partial credit)
        diagnostics = execution_result["diagnostics"]

        # Syntax error → low reward
        if "SyntaxError" in diagnostics["error_type"]:
            return 0.2

        # Runtime error → medium reward (syntax correct)
        if "RuntimeError" in diagnostics["error_type"]:
            return 0.5

        # Timeout → high reward (execution started)
        if "TimeoutError" in diagnostics["error_type"]:
            return 0.7

        return 0.0

# Example: SQL Query Execution
query = "Get all users with >10 orders"
generated_sql = "SELECT u.* FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id HAVING COUNT(o.id) > 10"

result = await execute_sql(generated_sql)
reward = await reward_calculator.calculate_reward(query, generated_sql, result)
# reward = 1.0 if success, 0.0-1.0 if partial success
```

**Acceptance Criteria:**
- [ ] Execution-Tooling implementiert (SQL/Python Runner)
- [ ] Reward-Definition (binary + shaped)
- [ ] Rewards in Traces gespeichert
- [ ] Dataset Builder übernimmt Rewards
- [ ] Canary-Subset für Execution Tasks (20 queries)

---

## Epic 5: Stabilization & Documentation - 10 SP

### Feature 68.8: Sprint 67 Bug Fixes & Stabilization (5 SP)

**Priority:** P0
**Ziel:** Fix alle kritischen Bugs aus Sprint 67 Deployment

**Scope:**
- Bug Tracking aus Sprint 67 Beta Deployment
- Hotfixes für Production Blockers
- Regression Testing
- Performance Regression Checks

**Potential Bug Categories:**
- Sandbox Escape Vulnerabilities
- Intent Classifier Edge Cases
- Adaptive Tool Failures
- Memory Leaks
- Race Conditions

**Acceptance Criteria:**
- [ ] Zero kritische Bugs (P0)
- [ ] ≤5 High-Priority Bugs (P1)
- [ ] Regression Tests für alle Fixed Bugs

---

### Feature 68.9: Documentation Consolidation (3 SP)

**Priority:** P1
**Ziel:** Dokumentation auf aktuellem Stand

**Scope:**
- **ADRs:**
  - ADR-067: Secure Shell Sandbox (deepagents)
  - ADR-068: Agents Adaptation Framework
  - ADR-069: C-LARA Intent Classifier
  - ADR-070: Section Community Detection
- **User Guides:**
  - Agent Sandbox Quickstart
  - Tool Adaptation Tutorial
  - Performance Tuning Guide
- **API Documentation:**
  - Trace Format Reference
  - Eval Metrics Reference
  - Dataset Builder API

**Acceptance Criteria:**
- [ ] 4 neue ADRs erstellt
- [ ] User Guides aktualisiert
- [ ] API Docs vollständig

---

### Feature 68.10: Production Deployment Validation (2 SP)

**Priority:** P0
**Ziel:** Validate Production Deployment auf 192.168.178.10

**Scope:**
- Smoke Tests auf Production
- Performance Validation (P95 ≤350ms)
- E2E Tests auf Production Environment
- Rollback Plan dokumentiert

**Validation Checklist:**
```bash
# 1. Health Checks
curl http://192.168.178.10/health
# Expected: 200 OK, all services UP

# 2. Query Latency
curl -X POST http://192.168.178.10/api/v1/chat/stream \
  -d '{"query": "Was sind die neuen Features?"}' \
  -H "Content-Type: application/json"
# Expected: P95 ≤350ms

# 3. E2E Tests
cd frontend && npm run test:e2e:prod
# Expected: 594/594 passing

# 4. Performance Profiling
python scripts/production_performance_test.py \
  --target http://192.168.178.10 \
  --queries 1000 \
  --concurrency 10
# Expected: QPS ≥50, P95 ≤350ms
```

**Acceptance Criteria:**
- [ ] Smoke Tests passing
- [ ] Performance targets met (P95 ≤350ms, QPS ≥50)
- [ ] E2E Tests passing on production
- [ ] Rollback Plan dokumentiert

---

## Parallel Execution Strategy

### Wave 1 (Tag 1-3): Profiling & Test Foundation
- **Team A (Testing):** 68.1 E2E Test Completion (13 SP) - start
- **Team B (Backend):** 68.2 Performance Profiling (5 SP)
- **Team C (Backend):** 68.5 Section Community Detection (10 SP) - start

### Wave 2 (Tag 4-6): Memory & Latency Optimization
- **Team A (Testing):** 68.1 E2E Test Completion (continued)
- **Team B (Backend):** 68.3 Memory Management (8 SP)
- **Team C (Backend):** 68.4 Query Latency Optimization (8 SP)
- **Team D (Backend):** 68.5 Section Community Detection (continued)

### Wave 3 (Tag 7-9): Advanced Features
- **Team A (Testing):** 68.1 E2E Test Completion (final)
- **Team B (Backend):** 68.6 Memory-Write Policy (10 SP)
- **Team C (Backend):** 68.7 Tool-Execution Reward Loop (8 SP) - optional
- **Team D (Documentation):** 68.9 Documentation (3 SP)

### Wave 4 (Tag 10): Stabilization & Validation
- **All Teams:** 68.8 Bug Fixes (5 SP)
- **All Teams:** 68.10 Production Validation (2 SP)

**Parallelization:**
- Wave 1: 3 teams = 28 SP in 3 days
- Wave 2: 4 teams = 21 SP in 3 days
- Wave 3: 4 teams = 21 SP in 3 days
- Wave 4: All teams = 7 SP in 1 day
- **Total Duration: 10 days**

---

## Definition of Done

**E2E Tests (Epic 1):**
- [ ] 594/594 Playwright tests passing
- [ ] Test suite <20 minutes (parallelized)
- [ ] Zero flaky tests
- [ ] Code coverage ≥85%

**Performance (Epic 2):**
- [ ] P95 query latency ≤350ms (-30%)
- [ ] Memory usage -20-30%
- [ ] Throughput ≥50 QPS (+25%)
- [ ] No accuracy degradation >5%

**Section Communities (Epic 3):**
- [ ] Community Detection pro Section funktional
- [ ] Louvain + Leiden algorithms supported
- [ ] Performance: <200ms per section

**Adaptation (Epic 4):**
- [ ] Memory-Write Policy implementiert
- [ ] Optional: Tool-Execution Reward Loop

**Stabilization (Epic 5):**
- [ ] Zero kritische Bugs
- [ ] Dokumentation vollständig
- [ ] Production Deployment validated

---

## Success Criteria

**Quantitative:**
- [ ] E2E Test Pass Rate: 57% → 100%
- [ ] Query Latency P95: 500ms → 350ms (-30%)
- [ ] Memory Usage: 8.6GB → 6.0GB (-30%)
- [ ] Throughput: 40 QPS → 50 QPS (+25%)
- [ ] Code Coverage: 80% → 85%

**Qualitative:**
- [ ] Zero known critical bugs
- [ ] Production deployment stable
- [ ] Documentation vollständig
- [ ] Performance targets met
- [ ] User feedback positive

---

## Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Performance Optimizations break functionality | Medium | High | Regression tests after each optimization |
| E2E Tests flaky on CI/CD | Medium | Medium | Parallelization, retry logic, stable test data |
| Memory Optimization reduces accuracy | Low | High | A/B testing with accuracy gates |
| Production Deployment issues | Low | Critical | Canary deployment, rollback plan |

---

## Abhängigkeiten

### Python Packages (New)
```toml
# pyproject.toml - Sprint 68 Dependencies
[tool.poetry.dependencies]
py-spy = ">=0.3.14"           # CPU profiling
memory-profiler = ">=0.61.0"  # Memory profiling
optimum = ">=1.14.0"          # ONNX quantization
```

---

## Referenzen

### Related Sprints
- [SPRINT_67_PLAN.md](SPRINT_67_PLAN.md) - Agentic Capabilities & Tool Adaptation
- [SPRINT_66_PLAN.md](SPRINT_66_PLAN.md) - E2E Test Stabilization

### Technical Documents
- [section_community_detection_queries.md](../technical/section_community_detection_queries.md) - Cypher Queries Reference
- [SPRINT_AGENTS_ADAPTATION.md](SPRINT_AGENTS_ADAPTATION.md) - Adaptation Framework (FEAT-006, FEAT-007)

### ADRs
- [ADR-024: BGE-M3 Embeddings](../adr/ADR_INDEX.md)
- ADR-067: Secure Shell Sandbox (TBD in Sprint 67)
- ADR-068: Agents Adaptation Framework (TBD in Sprint 67)
- ADR-069: C-LARA Intent Classifier (TBD in Sprint 67)
- ADR-070: Section Community Detection (TBD in Sprint 68)

---

**END OF SPRINT 68 PLAN**
