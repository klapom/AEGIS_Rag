# Sprint 70: Deep Research & Tool Use Integration

**Status:** ✅ COMPLETED
**Branch:** `main` (direct commits - Bug Fixes)
**Start Date:** 2026-01-01
**End Date:** 2026-01-02
**Duration:** 2 Tage
**Total Story Points:** 37 SP

---

## Sprint Overview

Sprint 70 repariert und integriert zwei kritische Features, die bisher **isoliert oder kaputt** waren:

1. **Deep Research Reparatur**: Broken Multi-Turn Iterative Search wird repariert durch **Wiederverwendung** von CoordinatorAgent & AnswerGenerator (kein Code-Duplikat!)
2. **Tool Use Integration**: MCP Tools (ActionAgent) werden in **beide Graphen** (Normal Chat + Deep Research) via **ReAct Pattern** integriert

**Problem-Analyse (Sprint 69 Post-Mortem):**
- Deep Research API ist broken:
  - `TypeError: AegisLLMProxy.generate() got an unexpected keyword argument 'prompt'`
  - `ModuleNotFoundError: No module named 'src.components.vector_search.hybrid'`
  - Returns "No information found" statt echte Ergebnisse
- Action Agent existiert, aber **nicht integriert** in Main Graph
- Code-Duplikation: Deep Research re-implementiert Search statt CoordinatorAgent zu nutzen

**Lösung (Design-Driven Architecture):**
- Supervisor-Pattern mit **Component Reuse**
- ReAct Pattern für Tool Use
- Zwei separate Graphen (Normal Chat + Deep Research)
- Zero Code Duplication

---

## Feature Overview

| # | Feature | SP | Priority | Status |
|---|--------|----|----------|--------|
| **Phase 1: Deep Research Repair** | | | | |
| 70.1 | Deep Research - Planner Fix (LLMTask API) | 3 | P0 | ✅ Done |
| 70.2 | Deep Research - Searcher Reuse (CoordinatorAgent) | 5 | P0 | ✅ Done |
| 70.3 | Deep Research - Synthesizer Reuse (AnswerGenerator) | 3 | P0 | ✅ Done |
| 70.4 | Deep Research - Supervisor Graph Creation | 5 | P0 | ✅ Done |
| **Phase 2: Tool Use Integration** | | | | |
| 70.5 | Tool Use - ReAct Integration (Normal Chat) | 3 | P1 | ✅ Done |
| 70.6 | Tool Use - ReAct Integration (Deep Research) | 2 | P1 | ✅ Done |
| **Phase 3: Tool Configuration & Monitoring** | | | | |
| 70.7 | Admin UI Toggle for Tool Use | 3 | P1 | ✅ Done |
| 70.8 | E2E Tests for Tool Use User Journeys | 2 | P2 | ✅ Done |
| 70.9 | Tool Result Streaming (Phase Events) | 3 | P2 | ✅ Done |
| 70.10 | Tool Analytics & Monitoring (Prometheus) | 3 | P2 | ✅ Done |
| 70.11 | LLM-based Tool Detection (Adaptive Strategies) | 5 | P2 | ✅ Done |

**Total: 37 SP**

---

## Feature Details

### Feature 70.1: Deep Research Planner Fix (3 SP)

**Priority:** P0
**Status:** ✅ Completed
**Ziel:** Planner verwendet korrekte LLMTask API statt broken `llm.generate(prompt=...)`

**Problem:**
```python
# BROKEN (TypeError):
response = await llm.generate(
    prompt=planning_prompt,
    temperature=0.7,
    max_tokens=500,
)
```

**Lösung:**
```python
# FIXED (LLMTask):
from src.domains.llm_integration.models import LLMTask, TaskType, Complexity

task = LLMTask(
    task_type=TaskType.GENERATION,
    prompt=planning_prompt,
    complexity=Complexity.SIMPLE,
    max_tokens=500,
    temperature=0.7,
)
response = await llm.generate(task)
queries = parse_plan(response.content)  # Extract from LLMResponse
```

**Geänderte Dateien:**
- `src/agents/research/planner.py` (Lines 40-85)

**Acceptance Criteria:**
- [x] Verwendet LLMTask statt kwargs
- [x] Keine TypeError mehr
- [x] Parsed LLMResponse.content korrekt
- [x] Fallback auf original query bei Fehlern

---

### Feature 70.2: Deep Research Searcher Reuse (5 SP)

**Priority:** P0
**Status:** ✅ Completed
**Ziel:** Searcher verwendet CoordinatorAgent statt broken duplicate imports

**Problem:**
```python
# BROKEN (Module nicht vorhanden):
from src.components.vector_search.hybrid import search_hybrid  # Doesn't exist!
from src.components.graph_rag.query import query_graph  # Doesn't exist!
```

**Lösung:**
```python
# FIXED (Component Reuse):
from src.agents.coordinator import CoordinatorAgent

coordinator = CoordinatorAgent()
result = await coordinator.process_query(
    query=query,
    intent="hybrid",  # Always hybrid for research
    namespace=namespace,
    include_sources=True,
)
contexts = result.get("retrieved_contexts", [])
```

**Geänderte Dateien:**
- `src/agents/research/searcher.py` (komplett neu geschrieben, 205 Zeilen)

**Key Design:**
- Reuses FourWayHybridSearch via CoordinatorAgent
- No duplicate imports
- Deduplizierung über alle Queries
- Quality evaluation metrics

**Acceptance Criteria:**
- [x] Keine broken imports mehr
- [x] Verwendet bestehende Search-Infrastruktur
- [x] Dedupliziert Contexts korrekt
- [x] Speichert research_query metadata

---

### Feature 70.3: Deep Research Synthesizer Reuse (3 SP)

**Priority:** P0
**Status:** ✅ Completed
**Ziel:** Synthesizer verwendet AnswerGenerator statt duplicate LLM logic

**Problem:**
```python
# BROKEN (TypeError + Code Duplication):
synthesis = await llm.generate(
    prompt=synthesis_prompt,
    temperature=0.3,
    max_tokens=1500,
)  # Duplicate LLM logic!
```

**Lösung:**
```python
# FIXED (Component Reuse):
from src.agents.answer_generator import AnswerGenerator

generator = AnswerGenerator(temperature=0.2)  # Lower for research
answer_with_citations = await generator.generate_with_citations(
    query=query,
    contexts=contexts,
    intent="hybrid",
    namespace=namespace,
)
```

**Geänderte Dateien:**
- `src/agents/research/synthesizer.py` (komplett neu geschrieben, 250 Zeilen)

**Key Design:**
- Reuses AnswerGenerator for consistency
- Automatic citation generation
- Fallback synthesis bei Errors
- Quality evaluation metrics

**Acceptance Criteria:**
- [x] Keine TypeError mehr
- [x] Verwendet bestehende AnswerGenerator
- [x] Generiert Citations automatisch
- [x] Konsistente Answer Quality

---

### Feature 70.4: Deep Research Supervisor Graph (5 SP)

**Priority:** P0
**Status:** ✅ Completed
**Ziel:** LangGraph Supervisor-Pattern für multi-turn iterative research

**Architecture:**
```
START → planner → searcher → supervisor → [continue | synthesize]
                      ↑           ↓
                      └───────────┘
                   (multi-turn loop)
```

**Neue Dateien:**
- `src/agents/research/state.py` (ResearchSupervisorState)
- `src/agents/research/research_graph.py` (Supervisor graph)

**Supervisor Logic:**
```python
def should_continue_research(state: ResearchSupervisorState) -> str:
    """Decide whether to continue or synthesize."""
    if state["iteration"] >= state["max_iterations"]:
        return "synthesize"

    # Check quality of contexts
    quality = evaluate_search_quality(state["all_contexts"])
    if quality["sufficient"]:
        return "synthesize"

    return "continue"
```

**State Management:**
```python
class ResearchSupervisorState(TypedDict, total=False):
    original_query: str
    sub_queries: list[str]
    iteration: int
    max_iterations: int
    all_contexts: list[dict[str, Any]]
    synthesis: str
    should_continue: bool
    metadata: dict[str, Any]
    error: str | None
```

**Acceptance Criteria:**
- [x] StateGraph mit Supervisor pattern
- [x] Planner/Searcher/Synthesizer nodes connected
- [x] Multi-turn iteration (max 3)
- [x] Quality-based stop condition
- [x] Error handling & fallback

---

### Feature 70.5: Tool Use Integration - Normal Chat (3 SP)

**Priority:** P1
**Status:** ✅ Completed
**Ziel:** ReAct Pattern für Tool Use in normalem Chat Graph

**Architecture (ReAct Pattern):**
```
answer → should_use_tools? → [tools | END]
           ↓                    ↓
         END                  answer  (cycle back!)
```

**Implementation:**
```python
def should_use_tools(state: AgentState) -> str:
    """Check if LLM requested tool use."""
    answer = state.get("answer", "")
    if needs_external_data(answer):  # Heuristic or LLM decision
        return "tools"
    return "end"

async def tools_node(state: AgentState):
    """Execute MCP tools via ActionAgent."""
    from src.agents.action_agent import ActionAgent
    from src.components.mcp.client import get_mcp_client

    tool_request = extract_tool_request(state["answer"])
    result = await action_agent.graph.ainvoke(...)

    # Add tool result to contexts for re-generation
    tool_context = {"text": result["tool_result"], "source": "tool"}
    state["retrieved_contexts"].append(tool_context)
    return {"needs_regeneration": True}
```

**Geänderte Dateien:**
- `src/agents/graph.py` (add tools_node, should_use_tools, ReAct edges)

**Acceptance Criteria:**
- [x] ToolNode integriert
- [x] Conditional edge nach answer
- [x] Cycle von tools → answer
- [x] Tool results in contexts
- [x] Admin-configurable enablement (no feature flag)

---

### Feature 70.6: Tool Use Integration - Deep Research (2 SP)

**Priority:** P1
**Status:** ✅ Completed
**Ziel:** Tool Use auch in Deep Research verfügbar

**Architecture:**
```
supervisor → [continue | use_tools | synthesize]
                  ↓          ↓            ↓
               searcher   research_tools  END
                  ↓          ↓
              supervisor  supervisor
```

**Implementation:**
```python
def supervisor_decision(state: ResearchSupervisorState) -> str:
    """Decide next action."""
    if needs_tools(state):
        return "use_tools"
    elif should_continue(state):
        return "continue"
    return "synthesize"
```

**Acceptance Criteria:**
- [x] research_tools_node added
- [x] Supervisor routes to tools
- [x] Tools return to supervisor
- [x] Tool results in all_contexts

---

### Feature 70.7: Admin UI Toggle for Tool Use (3 SP)

**Priority:** P1
**Status:** ✅ Completed
**Ziel:** Admin-Oberfläche für Tool-Konfiguration mit Hot-Reload

**Architecture:**
```
Admin UI → PUT /api/v1/admin/tools/config → Redis
                                              ↓ (60s cache)
New Conversations → compile_graph_with_tools_config() → Graph with/without tools
```

**Implementation:**
```python
# Backend: src/components/tools_config/tools_config_service.py
class ToolsConfig(BaseModel):
    enable_chat_tools: bool = False
    enable_research_tools: bool = False
    updated_at: str | None
    version: int = 1

# Frontend: AdminLLMConfigPage.tsx
<ToggleSwitch
  label="Enable Tools in Normal Chat"
  checked={toolsConfig.enable_chat_tools}
  onChange={...}
/>
```

**Geänderte Dateien:**
- `src/api/v1/admin_tools.py` (GET/PUT endpoints)
- `src/components/tools_config/tools_config_service.py` (Redis persistence + cache)
- `src/agents/coordinator.py` (lazy graph compilation)
- `src/agents/graph.py` (compile_graph_with_tools_config)
- `frontend/src/pages/admin/AdminLLMConfigPage.tsx` (UI toggles)

**Acceptance Criteria:**
- [x] Backend API endpoints (GET/PUT)
- [x] Redis persistence with 60s TTL cache
- [x] Lazy graph compilation in CoordinatorAgent
- [x] Frontend toggle switches
- [x] Hot-reload: Config change → 60s → New graphs use new config

---

### Feature 70.8: E2E Tests for Tool Use (2 SP)

**Priority:** P2
**Status:** ✅ Completed
**Ziel:** Integration tests für kompletten Tool Use Flow

**Test Coverage:**
- Config enablement/disablement (chat + research)
- Graph compilation with config
- Cache invalidation on config save
- Coordinator lazy compilation
- Graph cache expiry
- Metrics existence

**Neue Dateien:**
- `tests/integration/test_tools_config_integration.py` (8 tests)

**Acceptance Criteria:**
- [x] 8 integration tests passing
- [x] TestToolsConfigIntegration (6 tests)
- [x] TestCoordinatorToolsIntegration (2 tests)
- [x] Verifies Admin → Config → Execution flow

---

### Feature 70.9: Tool Result Streaming (3 SP)

**Priority:** P2
**Status:** ✅ Completed
**Ziel:** Real-time Phase Events für Tool-Ausführung

**Architecture:**
```python
tools_node(state, writer: StreamWriter):
    # 1. Emit IN_PROGRESS
    writer(PhaseEvent(
        phase_type=PhaseType.TOOL_EXECUTION,
        status=PhaseStatus.IN_PROGRESS,
        metadata={"tool_action": "search", "parameters": {...}}
    ))

    # 2. Execute tool via ActionAgent
    result = await action_agent.graph.ainvoke(...)

    # 3. Emit COMPLETED or FAILED
    writer(PhaseEvent(
        phase_type=PhaseType.TOOL_EXECUTION,
        status=PhaseStatus.COMPLETED,
        duration_ms=150,
        metadata={"result_length": 1234, "result_preview": "..."}
    ))
```

**Geänderte Dateien:**
- `src/models/phase_event.py` (added TOOL_EXECUTION PhaseType)
- `src/agents/tools/tool_integration.py` (StreamWriter integration)

**Acceptance Criteria:**
- [x] PhaseType.TOOL_EXECUTION added
- [x] Emits IN_PROGRESS when starting
- [x] Emits COMPLETED with duration + result preview
- [x] Emits FAILED with error on exception
- [x] Frontend can display real-time tool progress

---

### Feature 70.10: Tool Analytics & Monitoring (3 SP)

**Priority:** P2
**Status:** ✅ Completed
**Ziel:** Prometheus Metrics für Tool Use Monitoring

**Metrics:**
```python
# Counter: Total tool executions
tool_executions_total{tool_name="search", status="success"} 42
tool_executions_total{tool_name="fetch", status="failed"} 3

# Histogram: Tool execution latency
tool_execution_duration_seconds{tool_name="search"} 0.45

# Gauge: Currently executing tools
active_tool_executions 2
```

**Implementation:**
```python
# Track execution
increment_active_tools()
try:
    result = await execute_tool(...)
    track_tool_execution(tool_name, "success", duration_seconds)
except Exception as e:
    track_tool_execution(tool_name, "failed", duration_seconds)
finally:
    decrement_active_tools()
```

**Geänderte Dateien:**
- `src/core/metrics.py` (3 new metrics + helper functions)
- `src/agents/tools/tool_integration.py` (metrics integration)

**Acceptance Criteria:**
- [x] tool_executions_total counter
- [x] tool_execution_duration_seconds histogram
- [x] active_tool_executions gauge
- [x] Helper functions: track_tool_execution, increment/decrement
- [x] Metrics tracked in tools_node success/error paths

---

### Feature 70.11: LLM-based Tool Detection (5 SP)

**Priority:** P2
**Status:** ✅ Completed
**Ziel:** Adaptive Tool Detection mit 3 konfigurierbaren Strategien

**Strategies:**
1. **Markers (Fast, ~0ms)**: String matching on explicit markers
2. **LLM (Smart, +50-200ms)**: LLM decision with structured output
3. **Hybrid (Balanced, 0-200ms)**: Markers first, then LLM if action hints

**Architecture:**
```python
async def should_use_tools(state) -> str:
    config = await get_tools_config_service().get_config()

    if config.tool_detection_strategy == "markers":
        return _should_use_tools_markers(state, config)  # Check explicit markers
    elif config.tool_detection_strategy == "llm":
        return await _should_use_tools_llm(state, config)  # LLM structured output
    else:  # "hybrid"
        # Fast path: markers
        if marker_found: return "tools"
        # Slow path: LLM if action hints present
        if action_hint_found: return await _should_use_tools_llm(...)
        return "end"
```

**Configuration:**
```python
class ToolsConfig(BaseModel):
    tool_detection_strategy: str = "markers"  # "markers" | "llm" | "hybrid"
    explicit_tool_markers: list[str] = ["[TOOL:", "[SEARCH:", "[FETCH:"]
    action_hint_phrases: list[str] = ["need to", "check", "search", "latest"]
    version: int = 2  # Schema upgraded
```

**Frontend UI:**
- Strategy selector (3 radio buttons)
- Editable marker lists (conditional: hidden if strategy="llm")
- Editable action hint phrases (conditional: only for strategy="hybrid")
- Add/Remove buttons for dynamic list editing

**Geänderte Dateien:**
- `src/components/tools_config/tools_config_service.py` (schema v2)
- `src/agents/tools/tool_integration.py` (3 strategies)
- `src/api/v1/admin_tools.py` (DRY refactor)
- `frontend/src/pages/admin/AdminLLMConfigPage.tsx` (strategy UI)
- `tests/unit/agents/tools/test_tool_integration.py` (22 tests)

**Acceptance Criteria:**
- [x] 3 detection strategies implemented
- [x] Admin UI for strategy selection
- [x] Editable marker/hint lists
- [x] Conditional rendering (markers hidden if LLM)
- [x] 22 unit tests for all strategies
- [x] Multilingual support (German/English)
- [x] Trade-off analysis documented

---

## Implementation Plan

### Phase 1: Deep Research Repair (70.1-70.4) ✅ COMPLETED

**Day 1 (2026-01-01)**
1. ✅ Fix planner.py (LLMTask API)
2. ✅ Rewrite searcher.py (CoordinatorAgent reuse)
3. ✅ Rewrite synthesizer.py (AnswerGenerator reuse)
4. ✅ Create research_graph.py (Supervisor pattern)
5. ✅ Update `/api/v1/research/query` endpoint
6. ✅ Test deep research flow

### Phase 2: Tool Use Integration (70.5-70.6) ✅ COMPLETED

**Day 1-2 (2026-01-01)**
1. ✅ Add `tools_node` to normal chat graph
2. ✅ Add `should_use_tools` conditional
3. ✅ Add ReAct cycle edges
4. ✅ Admin-configurable enablement (no feature flag)
5. ✅ Integration with research graph
6. ✅ Test tool use in both graphs

### Phase 3: Configuration & Monitoring (70.7-70.11) ✅ COMPLETED

**Day 2 (2026-01-02)**
1. ✅ Admin UI toggle with Redis persistence (70.7)
2. ✅ 8 integration tests for tool flows (70.8)
3. ✅ Phase event streaming for tools (70.9)
4. ✅ Prometheus metrics implementation (70.10)
5. ✅ LLM-based detection strategies (70.11)
6. ✅ Editable marker lists UI (70.11)
7. ✅ 22 unit tests for detection (70.11)
8. ✅ Update documentation (SPRINT_PLAN.md, SPRINT_70_PLAN.md)

---

## Technical Debt Resolved

| TD# | Description | Resolution |
|-----|-------------|------------|
| TD-070-01 | Deep Research broken LLM API | Fixed with LLMTask |
| TD-070-02 | Deep Research broken imports | Fixed with component reuse |
| TD-070-03 | Deep Research code duplication | Removed via CoordinatorAgent/AnswerGenerator |
| TD-070-04 | Action Agent not integrated | Integrated via ReAct pattern |

---

## Success Criteria

### Deep Research (Phase 1)
- [x] Planner uses LLMTask API (no TypeError)
- [x] Searcher uses CoordinatorAgent (no broken imports)
- [x] Synthesizer uses AnswerGenerator (no code duplication)
- [x] Can execute multi-turn research queries
- [x] Generates comprehensive reports with citations
- [x] < 30s latency for 3 iterations

### Tool Use (Phase 2)
- [x] Tools callable from normal chat
- [x] Tools callable from deep research
- [x] ReAct loop works (multi-turn conversations)
- [x] Tool results integrated into answer
- [x] < 5s additional latency per tool call

### Configuration & Monitoring (Phase 3)
- [x] Admin can toggle tools without service restart
- [x] Hot-reload works (60s cache TTL)
- [x] 8 integration tests verify config → execution flow
- [x] Phase events stream in real-time (IN_PROGRESS/COMPLETED/FAILED)
- [x] Prometheus metrics track all tool executions
- [x] LLM-based detection works multilingually
- [x] 3 configurable strategies (markers/LLM/hybrid)
- [x] Admin can edit marker/hint lists dynamically

---

## Testing Strategy

### Unit Tests
- `tests/unit/agents/research/test_planner.py`
- `tests/unit/agents/research/test_searcher.py`
- `tests/unit/agents/research/test_synthesizer.py`
- `tests/unit/agents/research/test_research_graph.py`

### Integration Tests
- `tests/integration/test_deep_research_flow.py`
- `tests/integration/test_tool_use_chat.py`
- `tests/integration/test_tool_use_research.py`

### E2E Tests
- `frontend/e2e/deep-research.spec.ts`
- `frontend/e2e/tool-use.spec.ts`

---

## Documentation

**Design Documents:**
- `docs/sprints/DEEP_RESEARCH_TOOL_USE_DESIGN.md` (Architecture & Best Practices)
- `docs/sprints/SPRINT_70_PLAN.md` (This file)

**Feature Summaries:**
- `docs/sprints/SPRINT_70_FEATURE_70.1_SUMMARY.md` (Planner Fix)
- `docs/sprints/SPRINT_70_FEATURE_70.2_SUMMARY.md` (Searcher Reuse)
- `docs/sprints/SPRINT_70_FEATURE_70.3_SUMMARY.md` (Synthesizer Reuse)
- `docs/sprints/SPRINT_70_FEATURE_70.4_SUMMARY.md` (Supervisor Graph)

---

## References

**LangGraph Best Practices:**
- [ReAct Pattern](https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch)
- [Supervisor Pattern](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams)
- [Subgraphs](https://langchain-ai.github.io/langgraph/concepts/agentic_concepts#subgraphs)

**Related ADRs:**
- ADR-042: LangGraph Agent Orchestration
- ADR-043: Multi-Agent Coordination Patterns

**Related Sprints:**
- Sprint 59: Tool Use Framework & Action Agent
- Sprint 69: Model Selection & Production Monitoring
