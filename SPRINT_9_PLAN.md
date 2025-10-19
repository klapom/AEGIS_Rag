# Sprint 9 Plan - 3-Layer Memory Architecture + MCP Client Integration

**Sprint Goal:** Vollständige Memory-Architektur mit MCP Client für externe Tool-Nutzung
**Duration:** 1 Woche
**Story Points:** 35 SP
**Status:** IN PLANNING
**Priority:** HIGH

---

## Executive Summary

Sprint 9 kombiniert zwei strategische Komponenten:
1. **3-Layer Memory Architecture:** Redis (Short-Term), Qdrant (Long-Term), Graphiti (Episodic)
2. **MCP Client Integration:** Nutzung externer MCP-Tools (Filesystem, APIs, etc.)

Diese Kombination schafft die Grundlage für:
- Intelligentes Memory Management über verschiedene Zeitskalen
- Zugriff auf externe Tools via MCP-Standard
- Action Agent mit MCP-basierter Tool-Nutzung

**Wichtig:** Wir implementieren nur einen **MCP Client** (nutzt Tools), KEINEN Server (bietet Tools an)

---

## Part 1: 3-Layer Memory Architecture (20 SP)

### Deliverables

#### Feature 9.1: Redis Working Memory Manager (4 SP)
**Description:**
Short-Term Working Memory für aktive Conversations und Session State.

**Components:**
- Redis Connection Manager mit Cluster-Support
- Memory Entry Model (key-value, TTL, tags)
- Eviction Policies (LRU, TTL-based)
- Memory Capacity Monitoring

**Technical Tasks:**
- Redis Cluster Setup (Docker Compose)
- RedisMemoryManager Implementation
- TTL Configuration (default: 1 hour)
- Eviction Policy Implementation
- Unit Tests (20 tests)

**Success Criteria:**
- Memory Write/Read <10ms (p95)
- TTL-based auto-cleanup funktioniert
- Eviction bei 80% Capacity
- Cluster-fähig (3 nodes)

---

#### Feature 9.2: Memory Router (6 SP)
**Description:**
Intelligente Routing-Logik: Welche Memory-Layer für welche Query?

**Components:**
- MemoryRouter mit Routing-Strategy
- Recency-based Routing (new → Redis, old → Qdrant/Graphiti)
- Query-Type-based Routing (factual → Qdrant, episodic → Graphiti)
- Multi-Layer Retrieval (parallele Abfrage mehrerer Layers)

**Technical Tasks:**
- MemoryRouter Base Class
- Routing Strategy Interface
- Recency Calculator (timestamp-based)
- Query Classifier Integration (from Sprint 3)
- Parallel Retrieval mit asyncio.gather
- Unit Tests (25 tests)

**Success Criteria:**
- Routing Decision <5ms
- 90%+ korrekte Layer-Auswahl
- Multi-Layer Retrieval <100ms (parallel)
- Fallback zu allen Layers bei Unsicherheit

---

#### Feature 9.3: Memory Consolidation Pipeline (5 SP)
**Description:**
Automatische Migration: Redis → Qdrant (wichtige Memories) + Graphiti (episodic).

**Components:**
- ConsolidationScheduler (Cron-basiert)
- Relevance Scorer (für Importance-Berechnung)
- Migration Logic (Redis → Qdrant/Graphiti)
- Deduplication (avoid duplicate memories)

**Technical Tasks:**
- APScheduler Integration
- Relevance Scoring Algorithmus (Frequency, Recency, User Feedback)
- Migration Worker (async batch processing)
- Deduplication Logic (embedding similarity)
- Logging + Monitoring
- Unit Tests (15 tests)

**Success Criteria:**
- Consolidation läuft täglich (configurable)
- Top 20% memories migrated (importance-based)
- Deduplication rate >95%
- Zero data loss

---

#### Feature 9.4: Unified Memory API (3 SP)
**Description:**
Single API für alle Memory Layers (abstrahiert Komplexität).

**Components:**
- UnifiedMemoryAPI Facade
- Consistent Interface (store, retrieve, search, delete)
- Error Handling + Retry Logic
- Metrics Collection (per Layer)

**Technical Tasks:**
- UnifiedMemoryAPI Implementation
- Layer-agnostic Interface
- Error Handler mit Fallbacks
- Prometheus Metrics
- API Documentation
- Unit Tests (12 tests)

**Success Criteria:**
- Single API call für Memory Operations
- Automatische Layer-Auswahl (via Router)
- Graceful Degradation (Layer failures)
- API Response Time <50ms (median)

---

#### Feature 9.5: Memory Health Monitoring (2 SP)
**Description:**
Dashboard + Metrics für Memory System Health.

**Components:**
- Prometheus Metrics (memory size, latency, hit rate)
- Health Check Endpoints
- Capacity Planning Dashboard (Grafana)
- Alerting Rules (80% capacity, high latency)

**Technical Tasks:**
- Prometheus Exporter
- Health Check Endpoints (/health/memory)
- Grafana Dashboard JSON
- Alert Rules (Prometheus AlertManager)
- Documentation

**Success Criteria:**
- Real-time Metrics verfügbar
- Health Checks zeigen Layer Status
- Grafana Dashboard deployed
- Alerts bei kritischen Schwellwerten

---

## Part 2: MCP Client Integration (15 SP)

### Deliverables

#### Feature 9.6: MCP Client Implementation (6 SP)
**Description:**
MCP Client zum Verbinden mit externen MCP-Servern (Filesystem, GitHub, Slack, etc.).

**Components:**
- MCP Client Base (Python SDK)
- Connection Manager (multiple servers)
- Tool Discovery (list available tools)
- Transport Layer (stdio + HTTP)

**Technical Tasks:**
- MCP Python Client SDK Setup
- Multi-Server Connection Manager
- Tool Discovery Implementation
- stdio + HTTP Transport Clients
- Connection Pooling
- Unit Tests (25 tests)

**Success Criteria:**
- Client verbindet zu externen MCP-Servern
- Tool Discovery funktioniert (listet verfügbare Tools)
- stdio + HTTP Transports ready
- Multi-Server Support (parallel connections)
- Compatible mit MCP Spec 2025-06-18

**Example External MCP Servers:**
- Filesystem Server (read/write files)
- GitHub Server (repositories, issues, PRs)
- Slack Server (messages, channels)
- Database Server (SQL queries)

---

#### Feature 9.7: Tool Execution Handler (6 SP)
**Description:**
Robuste Tool-Ausführung mit Error Handling und Retry Logic.

**Components:**
- ToolExecutor (execute MCP tool calls)
- Error Handler (timeout, network, tool errors)
- Retry Logic (exponential backoff)
- Result Parser (handle different tool outputs)

**Technical Tasks:**
- ToolExecutor Implementation
- Error Classification (transient vs. permanent)
- Retry Logic mit tenacity (3 attempts, exponential backoff)
- Result Parsing (JSON, text, binary)
- Timeout Handling (configurable per tool)
- Unit Tests (22 tests)

**Success Criteria:**
- Tool Calls executed successfully
- Retry bei transient failures (3 attempts)
- Timeout nach 30s (configurable)
- Error messages user-friendly
- Result Parsing für gängige Formate

---

#### Feature 9.8: Action Agent (LangGraph Integration) (3 SP)
**Description:**
LangGraph Agent mit MCP Tool Calls.

**Components:**
- ActionAgent Node (LangGraph)
- MCP Tool Call Integration
- Tool Selection Logic (welches Tool für welche Action?)
- Execution Logging

**Technical Tasks:**
- ActionAgent Implementation
- LangGraph Node Definition
- Tool Selection Heuristics
- MCP ToolExecutor Integration
- LangSmith Tracing
- Unit Tests (15 tests)

**Success Criteria:**
- ActionAgent ruft MCP Tools auf
- LangGraph Integration funktioniert
- Tool Selection basierend auf Action-Type
- LangSmith zeigt Tool Calls
- Error Handling propagiert zu Agent

---

## Implementation Strategy

### Week Plan

**Day 1-2: Memory Architecture Foundation**
- Feature 9.1: Redis Working Memory Manager
- Feature 9.2: Memory Router (partial)

**Day 3: Memory Consolidation**
- Feature 9.2: Memory Router (complete)
- Feature 9.3: Memory Consolidation Pipeline

**Day 4: Memory API + MCP Client**
- Feature 9.4: Unified Memory API
- Feature 9.5: Memory Health Monitoring
- Feature 9.6: MCP Client Implementation (partial)

**Day 5: MCP Client + Integration**
- Feature 9.7: Tool Execution Handler
- Feature 9.8: Action Agent (LangGraph)

---

## Success Criteria

### Functional Requirements

- [ ] Redis Memory Manager speichert/liest <10ms
- [ ] Memory Router entscheidet korrekt (90%+)
- [ ] Consolidation läuft automatisch täglich
- [ ] Unified API abstrahiert alle Layers
- [ ] MCP Client verbindet zu externen Servern
- [ ] Tool Discovery funktioniert
- [ ] Tool Execution mit Retry Logic
- [ ] Action Agent nutzt externe MCP Tools
- [ ] Integration mit mindestens 1 externem MCP Server (z.B. Filesystem)

### Quality Metrics

| Metric | Target | Acceptance |
|--------|--------|------------|
| **Memory Latency** | <10ms (Redis), <50ms (Qdrant), <100ms (Graphiti) | <20ms, <100ms, <200ms |
| **Router Accuracy** | 90%+ | 85%+ |
| **Consolidation** | Zero data loss | <0.1% loss |
| **MCP Compliance** | 100% Spec 2025-06-18 | 95%+ |
| **Test Coverage** | >90% | >80% |

### Performance Benchmarks

| Component | Target | Acceptance |
|-----------|--------|------------|
| Redis Read/Write | <10ms p95 | <20ms p95 |
| Memory Router | <5ms decision | <10ms |
| Consolidation | <5min for 10K entries | <10min |
| MCP Tool Call | <100ms overhead | <200ms |

---

## Risk Assessment

### High Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Redis Cluster Complexity | Medium | Medium | Start with single-node, scale later |
| Memory Consolidation Data Loss | Low | High | Extensive testing, dry-run mode |
| MCP Spec Changes | Low | Medium | Pin to Spec 2025-06-18 |
| OAuth Integration Complexity | Medium | Low | Use proven libraries (authlib) |

### Medium Priority Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Memory Router Accuracy | Medium | Medium | A/B testing, user feedback |
| stdio Security Issues | Low | High | Strict path validation, sandboxing |
| HTTP Rate Limiting Bypass | Low | Medium | Token-based limiting |

---

## Deliverables

### Code Files Created

1. `src/components/memory/redis_manager.py` - Redis Memory Manager
2. `src/components/memory/memory_router.py` - Memory Router
3. `src/components/memory/consolidation.py` - Consolidation Pipeline
4. `src/components/memory/unified_api.py` - Unified Memory API
5. `src/components/memory/monitoring.py` - Health Monitoring
6. `src/components/mcp/client.py` - MCP Client Implementation
7. `src/components/mcp/tool_executor.py` - Tool Execution Handler
8. `src/agents/action_agent.py` - Action Agent

### Test Files Created

9. `tests/unit/components/memory/test_redis_manager.py` (20 tests)
10. `tests/unit/components/memory/test_memory_router.py` (25 tests)
11. `tests/unit/components/memory/test_consolidation.py` (15 tests)
12. `tests/unit/components/memory/test_unified_api.py` (12 tests)
13. `tests/unit/components/mcp/test_client.py` (25 tests)
14. `tests/unit/components/mcp/test_tool_executor.py` (22 tests)
15. `tests/unit/agents/test_action_agent.py` (15 tests)
16. `tests/integration/test_memory_e2e.py` (10 tests)
17. `tests/integration/test_mcp_e2e.py` (12 tests)

### Documentation Created

18. `docs/architecture/MEMORY_ARCHITECTURE.md`
19. `docs/architecture/MCP_CLIENT_INTEGRATION.md`
20. `docs/api/MEMORY_API.md`
21. `docs/examples/mcp_client_usage.md`
22. `SPRINT_9_COMPLETION_REPORT.md`

---

## Definition of Done

For Sprint 9 completion:

- [ ] All 8 Features implemented and tested
- [ ] 156+ Tests passing (134 unit + 22 integration)
- [ ] Memory System funktional (Redis + Router + Consolidation)
- [ ] MCP Client verbindet zu mindestens 1 externen Server
- [ ] Action Agent nutzt externe MCP Tools
- [ ] Documentation vollständig
- [ ] Performance Targets erreicht
- [ ] Code Review abgeschlossen
- [ ] Sprint 9 Completion Report published

---

## Dependencies

### External Services

- **Redis 7.x** - Memory Backend
- **Qdrant 1.7+** - Long-Term Memory (from Sprint 2)
- **Neo4j 5.x** - Graphiti Backend (from Sprint 7)

### External Libraries

```toml
[tool.poetry.dependencies]
redis = "^5.0.0"                    # Redis Client
apscheduler = "^3.10.0"             # Consolidation Scheduler
prometheus-client = "^0.19.0"       # Metrics
mcp-sdk = "^0.1.0"                 # Model Context Protocol SDK
authlib = "^1.3.0"                  # OAuth 2.1 Client
```

---

## Notes

- Sprint 9 baut auf Sprints 2 (Qdrant), 7 (Graphiti), 4 (LangGraph) auf
- MCP Integration bereitet Sprint 10 (UI) und Sprint 11 (Admin UI) vor
- Memory Architecture ist Grundlage für advanced Conversation Management
- Focus: Production-ready Memory System + standardisierte Tool-Integration

---

**Sprint 9 Status:** IN PLANNING
**Estimated Start:** Nach Sprint 8 completion
**Estimated Duration:** 1 Woche
**Story Points:** 35 SP (20 SP Memory + 15 SP MCP Client)
**Priority:** HIGH

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
