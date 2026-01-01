# Sprint 70: Deep Research & Tool Use Integration

**Status:** IN_PROGRESS
**Branch:** `main` (direct commits - Bug Fixes)
**Start Date:** 2026-01-01
**Estimated Duration:** 2-3 Tage
**Total Story Points:** 21 SP

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
| 70.1 | Deep Research - Planner Fix (LLMTask API) | 3 | P0 | ✅ Done |
| 70.2 | Deep Research - Searcher Reuse (CoordinatorAgent) | 5 | P0 | ✅ Done |
| 70.3 | Deep Research - Synthesizer Reuse (AnswerGenerator) | 3 | P0 | ✅ Done |
| 70.4 | Deep Research - Supervisor Graph Creation | 5 | P0 | In Progress |
| 70.5 | Tool Use - ReAct Integration (Normal Chat) | 3 | P1 | Pending |
| 70.6 | Tool Use - ReAct Integration (Deep Research) | 2 | P1 | Pending |

**Total: 21 SP**

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
**Status:** In Progress
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
- [ ] StateGraph mit Supervisor pattern
- [ ] Planner/Searcher/Synthesizer nodes connected
- [ ] Multi-turn iteration (max 3)
- [ ] Quality-based stop condition
- [ ] Error handling & fallback

---

### Feature 70.5: Tool Use Integration - Normal Chat (3 SP)

**Priority:** P1
**Status:** Pending
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
- [ ] ToolNode integriert
- [ ] Conditional edge nach answer
- [ ] Cycle von tools → answer
- [ ] Tool results in contexts
- [ ] Feature flag `ENABLE_TOOL_USE`

---

### Feature 70.6: Tool Use Integration - Deep Research (2 SP)

**Priority:** P1
**Status:** Pending
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
- [ ] research_tools_node added
- [ ] Supervisor routes to tools
- [ ] Tools return to supervisor
- [ ] Tool results in all_contexts

---

## Implementation Plan

### Phase 1: Deep Research Repair (70.1-70.4) ✅ Mostly Done

**Week 1, Day 1-2**
1. ✅ Fix planner.py (LLMTask API)
2. ✅ Rewrite searcher.py (CoordinatorAgent reuse)
3. ✅ Rewrite synthesizer.py (AnswerGenerator reuse)
4. 🚧 Create research_graph.py (Supervisor pattern)
5. 🚧 Update `/api/v1/research/query` endpoint
6. 🚧 Test deep research flow

### Phase 2: Tool Use Integration (70.5-70.6)

**Week 1, Day 3**
1. Add `tools_node` to normal chat graph
2. Add `should_use_tools` conditional
3. Add ReAct cycle edges
4. Feature flag `ENABLE_TOOL_USE=false`
5. Test with flag enabled

### Phase 3: Testing & Documentation

**Week 1, Day 4-5**
1. Unit tests for research nodes
2. Integration tests for deep research
3. Integration tests for tool use
4. Update documentation
5. E2E tests

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

### Deep Research
- [x] Planner uses LLMTask API (no TypeError)
- [x] Searcher uses CoordinatorAgent (no broken imports)
- [x] Synthesizer uses AnswerGenerator (no code duplication)
- [ ] Can execute multi-turn research queries
- [ ] Generates comprehensive reports with citations
- [ ] < 30s latency for 3 iterations

### Tool Use
- [ ] Tools callable from normal chat
- [ ] Tools callable from deep research
- [ ] ReAct loop works (multi-turn conversations)
- [ ] Tool results integrated into answer
- [ ] < 5s additional latency per tool call

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
