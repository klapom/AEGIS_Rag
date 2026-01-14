# Sprint 91 Plan: Agentic Skills & Planning Framework

**Epic:** Agent Skills Framework v1.0
**Phase:** Planning & Decomposition System
**ADR References:** [ADR-050](../adr/ADR-050-skill-router-architecture.md), [ADR-001](../adr/ADR-001-langgraph.md)
**Prerequisites:** Sprint 90 (Skill System Foundations)
**Estimated Duration:** 7-10 days
**Total Story Points:** 18 SP
**Status:** 📝 Planned

---

## Sprint Goal

Build **Intent-Based Skill Router** and **Planner Skill** to enable intelligent capability loading and complex task decomposition. This enables agents to scale from simple queries to multi-step research and analysis.

**Key Objectives:**
1. Implement skill router based on intent classification (ADR-050)
2. Create Planner Skill for task decomposition
3. Integrate C-LARA classifier for intent detection
4. Add multi-skill orchestration to LangGraph agents

---

## Context

### Current State (End of Sprint 90)
- Skills system exists: retrieval, synthesis, reflection, hallucination_monitor
- All skills loaded for every query (~4,000 tokens wasted)
- No task decomposition capability
- LangGraph agents lack multi-skill orchestration

### Target State (Sprint 91)
- Intent-based skill router activated for each query
- Only relevant skills loaded (30-35% token savings)
- Planner skill decomposes complex queries into 3-10 subtasks
- Multi-skill orchestration in agents

### Impact
- **Token Savings:** 4,000 → 2,500 tokens for skills (+1,500 tokens for documents)
- **Quality:** 8-12% improvement in Context Recall
- **Latency:** 15-20% faster responses
- **Capabilities:** Enable research agents, planning agents, analysis agents

---

## Features

| # | Feature | SP | Priority | Status | Description |
|---|---------|-----|----------|--------|-------------|
| 91.1 | C-LARA Intent Router | 3 | P0 | 📝 Planned | Intent classification + skill mapping |
| 91.2 | Skill Router Component | 4 | P0 | 📝 Planned | Route queries to relevant skills |
| 91.3 | Planner Skill | 6 | P0 | 📝 Planned | Task decomposition + orchestration |
| 91.4 | Multi-Skill Orchestration | 4 | P0 | 📝 Planned | LangGraph multi-skill agents |
| 91.5 | Documentation & Examples | 1 | P1 | 📝 Planned | API docs, guides, examples |

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| Planner Skill | `skills/planner/` | Task decomposition SKILL.md |
| Intent Router | `src/components/intent/` | Intent classification |
| Skill Router | `src/components/agents/` | Intent-to-skills routing |
| ADR-050 | `docs/adr/` | Skill Router Architecture |
| ADR-051 | `docs/adr/` | Recursive LLM Context |
| Examples | `docs/examples/` | Research agent, planning agent |
| Tests | `tests/unit/`, `tests/integration/` | 50+ tests |

---

## Success Criteria

| Criterion | Target |
|-----------|--------|
| Intent classification accuracy | >93% |
| Token savings | >30% reduction |
| Multi-skill latency | <5000ms P95 |
| Quality improvement | >8% Context Recall |
| Documentation | 100% complete |

---

## References

- [ADR-050: Skill Router Architecture](../adr/ADR-050-skill-router-architecture.md)
- [ADR-051: Recursive LLM Context](../adr/ADR-051-recursive-llm-context.md)
- [Sprint 81: C-LARA SetFit](./SPRINT_81_PLAN.md)
- [Sprint 90: Skill System](./SPRINT_90_PLAN.md)
