# ADR-050: Intent-Based Skill Router Architecture

**Status:** ✅ Accepted
**Date:** 2026-01-14
**Sprint:** 91 (Agentic Skills & Planning)
**Deciders:** Architecture Team
**Related ADRs:** ADR-001 (LangGraph), ADR-047 (Hybrid Agent Memory)
**Related Features:** 91.1-91.4 (Planner Skill, Intent Classifier, Skill Router)

---

## Context

**Problem:** Current agent architecture loads ALL capabilities into every query context window.

**Current State:**
- Every query receives full skill list: retrieval, graph reasoning, synthesis, reflection, etc.
- Typical capability context: 4,000-8,000 tokens just for tool definitions
- Wasted tokens: ~30-40% of initial context consumed before answering
- No intelligent capability routing based on query intent

**Impact:**
- Reduced context for actual retrieval (top_k must be lower)
- Higher latency (LLM processes irrelevant capabilities)
- Lower quality answers (less room for relevant documents)
- Inefficient use of token budget

**Research Baseline:**
- HuggingFace Tools benchmark: Routing reduces context by 30-35%
- Tool selection systems improve latency by 15-20% (fewer irrelevant capabilities to reason about)
- Intent-based routing matches human reasoning patterns

---

## Decision

Implement **3-tier Intent-Based Skill Router** architecture:

### Tier 1: Intent Classification (C-LARA SetFit)

**Model:** C-LARA SetFit classifier (5 classes, 95.22% accuracy on edge cases)

**Intent Classes:**
```python
SEARCH = "User wants to find/retrieve documents"
REASONING = "User wants analysis, synthesis, or reasoning"
PLANNING = "User wants task decomposition or strategy"
MEMORY = "User wants to recall past interactions"
ACTION = "User wants to execute tools or scripts"
```

**Confidence Threshold:** 0.75 (if below, default to SEARCH + REASONING)

**Latency:** ~40ms (on CPU, cached model)

### Tier 2: Skill Activation via Intent

**Mapping:**

```yaml
SEARCH:
  skills: [retrieval, reflection]
  reasoning: User queries documents, needs verification
  estimated_context: 2000 tokens

REASONING:
  skills: [retrieval, synthesis, reflection]
  reasoning: User wants analysis, needs docs + generation
  estimated_context: 3000 tokens

PLANNING:
  skills: [retrieval, planner, synthesis]
  reasoning: User wants task breakdown, needs planning + retrieval
  estimated_context: 3500 tokens

MEMORY:
  skills: [memory, reflection]
  reasoning: User references past interactions
  estimated_context: 1500 tokens

ACTION:
  skills: [action, reflection]
  reasoning: User executes tools, needs tool definitions
  estimated_context: 2500 tokens
```

### Tier 3: Permission-Based Filtering

**RBAC Model:**
```python
User Role Permissions:
- researcher: [retrieval, graph, memory, synthesis] ✓
- analyst: [retrieval, synthesis, planner] ✓
- admin: [ALL] ✓
- viewer: [retrieval] ✓

Skill Permissions:
- retrieval: [read_documents] ✓
- graph: [read_knowledge_graph] ✓
- memory: [read_memory, write_memory] ✓
- action: [execute_tools] ✓ (requires explicit user confirmation)
```

---

## Decision Drivers

1. **Token Budget Optimization:** 30-35% context savings → more room for retrieval
2. **Latency Reduction:** Fewer irrelevant skills to reason about → 15-20% faster
3. **Quality Improvement:** More context for actual documents → better answers
4. **Maintainability:** Clearer capability structure as system grows
5. **Security:** Permission-based filtering prevents unauthorized tool access

---

## Considered Options

### Option 1: Always-On Skills (Current)

**Description:** Load all skills for every query, LLM decides which to use

**Pros:**
- Simplest implementation
- LLM has full visibility into all capabilities
- No routing overhead

**Cons:**
- 4,000+ tokens wasted per query
- 30-35% context bloat
- Slower inference (more irrelevant content to process)
- No security boundary

**Trade-off:** Simplicity vs. efficiency

---

### Option 2: Manual Skill Activation

**Description:** User explicitly specifies which skills to use via API parameter

**Pros:**
- Explicit control
- Zero routing latency
- Clear intent from user

**Cons:**
- User burden (must know available skills)
- Error-prone (users forget or misselect)
- Not practical for chat interface
- Worse UX

**Trade-off:** Precision vs. usability

---

### Option 3: Embedding-Based Routing

**Description:** Embed user query and skill descriptions, compute similarity

**Pros:**
- More sophisticated than keyword matching
- Learns query-skill associations

**Cons:**
- Slower (~200-300ms for embedding + inference)
- Requires training data
- Hard to interpret routing decisions
- Not real-time suitable

**Trade-off:** Sophistication vs. latency

---

### Option 4: Intent-Based Routing (Selected)

**Description:** Classify user intent (search/reasoning/planning/etc.), activate skills for that intent

**Pros:**
- Fast (~40ms inference)
- Interpretable (intent clearly mapped to skills)
- Uses proven classifier (C-LARA 95.22% accuracy)
- 30-35% context savings
- Clear security boundary (permission filtering)

**Cons:**
- Requires accurate intent classification (handled by C-LARA)
- Fixed skill mappings (less flexible than always-on)
- Cold start for new intent classes

---

## Decision Rationale

**Why Intent-Based Routing?**

1. **Proven Accuracy:** C-LARA SetFit achieves 95.22% intent classification on edge cases (Sprint 81)
   - Misclassification rate only 4.78%
   - Fallback to SEARCH + REASONING on low confidence

2. **Token Efficiency:**
   - Current: 8,000 token context window, 4,000 tokens for skills → 4,000 tokens for docs
   - With routing: 8,000 tokens, 2,500 tokens for skills → 5,500 tokens for docs
   - **Result: 38% more room for actual documents**

3. **Latency Impact:**
   - Intent classification: 40ms (cached)
   - Traditional skill reasoning: saved ~150-200ms
   - **Net: 110-160ms faster overall**

4. **Quality Improvement:**
   - More context for retrieval → higher top_k (from 5 to 8 on average)
   - More relevant documents → 8-12% improvement in Context Recall

5. **Maintainability:**
   - Clear separation of concerns (intent → skills → LLM)
   - Easy to add new skills (just add to mapping)
   - Audit trail for which skills were used why

---

## Consequences

### Positive

- **Token Efficiency:** 30-35% reduction in skill definition tokens
  - Average query: 4,000 → 2,500 tokens for skills
  - More room for documents: 4,000 → 5,500 tokens

- **Latency Improvement:** 15-20% faster inference
  - Reduced context for LLM to process
  - C-LARA classification adds 40ms but saves 150ms+ in inference
  - Net benefit: 110-160ms faster responses

- **Quality Gains:** 8-12% improvement in Context Recall
  - More documents fit in context window
  - Better ranked documents due to more refined search

- **Security Boundary:** Permission-based filtering
  - Prevents unauthorized tool access
  - Audit trail for each skill activation
  - Role-based access control (researcher vs viewer)

- **Scalability:** Easy to add new intents/skills
  - Skill definitions decoupled from LLM context
  - Can add 10+ new skills without impacting token budget

### Negative

- **Classification Errors:** 4.78% misclassification rate
  - Wrong intent → wrong skills activated
  - Mitigated by fallback (SEARCH + REASONING covers 95%+ of queries)

- **Rigidity:** Fixed intent mappings
  - Some queries span multiple intents (e.g., search + planning)
  - Mitigated by multi-intent detection (if confidence < 0.75, use multiple intents)

- **Cold Start:** New intent classes need classifier retraining
  - Not expected to be frequent
  - Mitigated by inclusive fallback behavior

### Neutral

- **Complexity:** Slight increase in architecture
  - Router component adds ~200 LOC
  - Offset by clarity of intent-based design

---

## Implementation Notes

### Architecture

```
User Query
    ↓
[Intent Classifier - C-LARA SetFit]
    ↓
Intent: SEARCH (conf: 0.92)
    ↓
[Skill Router]
    ├─ retrieval (required)
    ├─ reflection (optional)
    └─ [permission check] ✓
    ↓
[Permission Filter]
    ├─ User role: researcher
    ├─ Skills allowed: retrieval ✓
    ├─ Skills denied: action ✗
    ↓
[Agent with Selected Skills]
```

### Configuration

```python
# src/config/skill_router.py

INTENT_TO_SKILLS = {
    Intent.SEARCH: [
        SkillConfig(name="retrieval", required=True),
        SkillConfig(name="reflection", required=False),
    ],
    Intent.REASONING: [
        SkillConfig(name="retrieval", required=True),
        SkillConfig(name="synthesis", required=True),
        SkillConfig(name="reflection", required=False),
    ],
    Intent.PLANNING: [
        SkillConfig(name="retrieval", required=True),
        SkillConfig(name="planner", required=True),
        SkillConfig(name="synthesis", required=True),
    ],
    Intent.MEMORY: [
        SkillConfig(name="memory", required=True),
        SkillConfig(name="reflection", required=False),
    ],
    Intent.ACTION: [
        SkillConfig(name="action", required=True),
        SkillConfig(name="reflection", required=False),
    ],
}

ROLE_PERMISSIONS = {
    UserRole.RESEARCHER: [Skill.RETRIEVAL, Skill.GRAPH, Skill.MEMORY, Skill.SYNTHESIS],
    UserRole.ANALYST: [Skill.RETRIEVAL, Skill.SYNTHESIS, Skill.PLANNER],
    UserRole.ADMIN: [Skill.ALL],
    UserRole.VIEWER: [Skill.RETRIEVAL],
}
```

### Testing Strategy

```python
# tests/unit/routing/test_skill_router.py

def test_search_intent_activates_retrieval():
    """SEARCH intent should activate retrieval + reflection."""
    router = SkillRouter()
    skills = router.route_query("Find documents about embeddings", intent=Intent.SEARCH)
    assert Skill.RETRIEVAL in skills
    assert Skill.REFLECTION in skills

def test_planning_intent_activates_planner():
    """PLANNING intent should activate planner + retrieval + synthesis."""
    router = SkillRouter()
    skills = router.route_query("How do I improve recall?", intent=Intent.PLANNING)
    assert Skill.PLANNER in skills
    assert Skill.RETRIEVAL in skills
    assert Skill.SYNTHESIS in skills

def test_permission_filtering():
    """User with VIEWER role should not access ACTION skill."""
    router = SkillRouter()
    user = User(role=UserRole.VIEWER)
    skills = router.route_query("Execute script", user=user, intent=Intent.ACTION)
    assert Skill.ACTION not in skills  # Filtered by permission check

def test_misclassification_fallback():
    """If intent confidence < 0.75, use SEARCH + REASONING fallback."""
    classifier = MockIntentClassifier(confidence=0.60)
    router = SkillRouter(classifier=classifier)
    skills = router.route_query("What is RAG?")
    assert Skill.RETRIEVAL in skills  # Always included
    assert Skill.SYNTHESIS in skills  # Fallback
```

---

## Migration Strategy

**Phase 1 (Sprint 91):** Router implementation
- Build router component
- Integrate C-LARA classifier
- Update agent to use selected skills

**Phase 2 (Sprint 92):** Monitoring & tuning
- Monitor intent classification accuracy
- A/B test token efficiency gains
- Adjust skill mappings based on metrics

**Phase 3 (Sprint 93+):** Multi-intent support
- Handle queries spanning multiple intents
- Implement intelligent fallback

---

## Metrics & Success Criteria

| Metric | Target | Baseline |
|--------|--------|----------|
| Intent classification accuracy | >93% | 95.22% (C-LARA) |
| Token savings | >30% | 0% (current) |
| Latency improvement | >15% | 0ms baseline |
| Context Recall improvement | >8% | 0.65 (current) |
| Skills loaded per query | <3 | 5 (current) |

---

## References

- [ADR-001: LangGraph Orchestration](./ADR-001-langgraph.md)
- [ADR-047: Hybrid Agent Memory](./ADR-047-hybrid-agent-memory.md)
- [Sprint 81: C-LARA SetFit Classifier](../sprints/SPRINT_81_PLAN.md)
- [C-LARA Classifier Accuracy Report](../ragas/C-LARA_ACCURACY.md)
- [LangGraph Agent Architecture](https://langchain-ai.github.io/langgraph/how-tos/agent-architecture/)

---

## Revision History

- 2026-01-14: Initial proposal (Status: Accepted)
  - Intent-based routing design
  - C-LARA classifier integration
  - RBAC permission filtering
  - Migration strategy

---

## Approval

- Architecture Team: ✅ Approved 2026-01-14
- Backend Team: ✅ Approved 2026-01-14
- Suggested Implementation Sprint: Sprint 91 (Features 91.1-91.4)
