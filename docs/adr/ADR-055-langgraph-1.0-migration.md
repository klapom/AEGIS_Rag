# ADR-055: LangGraph 1.0 Migration for Agentic Framework

**Status:** Accepted
**Date:** 2026-01-15
**Sprint:** 93 (Preparation)
**Authors:** Claude Opus 4.5

---

## Context

AegisRAG's Agentic Framework Transformation (Sprint 90-96) requires advanced multi-agent orchestration capabilities. The project was using LangGraph 0.6.x, which lacks production-grade features needed for:

- **Sprint 93:** Tool Composition & Skill-Tool Mapping
- **Sprint 94:** Multi-Agent Communication
- **Sprint 95:** Hierarchical Agents & Skill Libraries
- **Sprint 96:** EU-Governance & Compliance (Audit Trail, Human-in-Loop)

## Decision

**Upgrade LangGraph from 0.6.11 to 1.0.6** (GA release October 2025).

### Version Changes

| Package | Before | After |
|---------|--------|-------|
| `langgraph` | 0.6.11 | 1.0.6 |
| `langgraph-prebuilt` | 0.6.5 | 1.0.6 |
| `langgraph-sdk` | 0.2.14 | 0.3.3 |

### Key Features Enabled

1. **Durable Execution** - Agent state persistence across restarts
2. **Built-in Memory** - Short-term (state) + Long-term (checkpointers)
3. **Human-in-the-Loop APIs** - First-class support for approval workflows
4. **Stable API Guarantee** - No breaking changes until 2.0

### Migration Assessment

LangGraph 1.0 shipped with **zero breaking changes**:

- `langgraph.prebuilt` module deprecated but fully functional
- All existing AegisRAG graph code works unchanged
- `ToolNode`, `create_react_agent`, `StateGraph` APIs identical

## Alternatives Considered

### 1. Stay on LangGraph 0.6.x

**Rejected** - Missing critical features:
- No Durable Execution (needed for Sprint 96 Audit Trail)
- No Human-in-Loop APIs (needed for Sprint 96 Compliance)
- No stable API guarantee

### 2. langgraph-supervisor Library

**Deferred** - LangChain team recommends tool-based supervisor pattern:

> "We now recommend using the supervisor pattern directly via tools rather than this library for most use cases."

Tool-based pattern provides more control for Sprint 96 governance requirements.

### 3. Alternative Frameworks (AutoGen, CrewAI)

**Rejected** - Would require complete rewrite of existing agent code.

## Implementation

### pyproject.toml Change

```toml
# LangGraph & LangChain (Sprint 4: Multi-Agent Orchestration)
# UPGRADED Sprint 93: LangGraph 1.0 - Durable Execution, Memory, Human-in-Loop
# Migration: Zero breaking changes (langgraph.prebuilt deprecated but functional)
langgraph = "^1.0.0"  # LangGraph 1.0 GA (Oct 2025) - Production-ready, stable API
```

### Validation Tests

```python
# All tests passed:
✅ src.agents.graph imports work
✅ src.agents.coordinator imports work
✅ src.agents.skills.registry imports work
✅ src.agents.skills.lifecycle imports work
✅ StateGraph compilation works
✅ MemorySaver (LangGraph 1.0 feature) works
✅ ToolNode (langgraph.prebuilt) works
✅ create_react_agent (langgraph.prebuilt) works
```

## Consequences

### Positive

1. **Production-Ready Foundation** - LangGraph 1.0 is battle-tested (Uber, LinkedIn, Klarna)
2. **Sprint 93-96 Enablement** - All required features now available
3. **API Stability** - No breaking changes until 2.0
4. **Audit Compliance** - Human-in-Loop + Durable Execution for EU AI Act

### Negative

1. **Deprecation Warnings** - `langgraph.prebuilt` will show warnings (non-blocking)
2. **Learning Curve** - Team needs to learn new 1.0 patterns

### Neutral

1. **No Code Changes Required** - Existing code works as-is
2. **Optional Migration Path** - Can gradually adopt new patterns

## Sprint 93-96 Pattern Adoptions

Based on LangGraph community research, the following patterns will be adopted:

| Sprint | Pattern | Implementation |
|--------|---------|----------------|
| 93 | `ToolNode` with `handle_tool_errors=True` | Automatic error recovery |
| 94 | `InjectedState` for state injection | Agent communication |
| 95 | Multi-level Supervisors | Hierarchical agents |
| 96 | `output_mode="full_history"` | Audit trail preservation |

## References

- [LangGraph 1.0 GA Announcement](https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available)
- [LangGraph 1.0 Release Notes](https://medium.com/@romerorico.hugo/langgraph-1-0-released-no-breaking-changes-all-the-hard-won-lessons-8939d500ca7c)
- [LangGraph Supervisor Library](https://github.com/langchain-ai/langgraph-supervisor-py)
- [Hierarchical Agent Teams Tutorial](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams/)

---

**Document:** ADR-055-langgraph-1.0-migration.md
**Related:** ADR-049 (Agentic Framework Architecture)
