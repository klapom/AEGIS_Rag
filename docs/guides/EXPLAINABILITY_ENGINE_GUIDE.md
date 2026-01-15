# Explainability Engine - Developer Guide

## Overview

The Explainability Engine provides EU AI Act compliant decision transparency for the AegisRAG system. It captures complete decision traces and generates human-readable explanations at three levels of detail.

## Quick Start

```python
from src.governance.explainability import (
    ExplainabilityEngine,
    InMemoryTraceStorage,
    ExplanationLevel
)
from langchain_ollama import ChatOllama

# Initialize engine
storage = InMemoryTraceStorage()
llm = ChatOllama(model="llama3.2:3b")
engine = ExplainabilityEngine(storage, llm)

# Capture trace during agent execution
trace = await engine.capture_trace(
    query="User's question",
    response="Generated answer",
    skill_context={...},      # From skill framework
    retrieval_context={...},  # From retrieval pipeline
    tool_context={...}        # From tool framework
)

# Generate explanation
explanation = await engine.explain(trace.id, ExplanationLevel.USER)
print(explanation)
```

## Core Concepts

### 1. Decision Traces

A `DecisionTrace` captures everything about how a response was generated:

```python
@dataclass
class DecisionTrace:
    id: str                                    # Unique trace ID
    timestamp: datetime                        # When captured
    query: str                                 # User's question
    final_response: str                        # Generated answer

    # Skill selection
    skills_considered: List[SkillSelectionReason]
    skills_activated: List[str]

    # Retrieval
    retrieval_mode: str                        # "vector", "graph", "hybrid"
    chunks_retrieved: int
    chunks_used: int
    attributions: List[SourceAttribution]

    # Tools
    tools_invoked: List[Dict[str, Any]]

    # Confidence
    overall_confidence: float
    hallucination_risk: float

    # Performance
    total_duration_ms: float
    skill_durations: Dict[str, float]
```

### 2. Explanation Levels

Three levels for different audiences:

```python
class ExplanationLevel(Enum):
    USER = "user"       # Simple, 3-5 sentences
    EXPERT = "expert"   # Technical details with metrics
    AUDIT = "audit"     # Full JSON trace for compliance
```

**When to use each:**
- **USER**: End-user facing interfaces, chat responses
- **EXPERT**: Developer debugging, system monitoring
- **AUDIT**: Compliance reviews, regulatory audits

### 3. Source Attribution

Links response claims to source documents:

```python
@dataclass
class SourceAttribution:
    document_id: str                # Unique document ID
    document_name: str              # Human-readable name
    chunk_ids: List[str]            # Chunks used
    relevance_score: float          # 0.0-1.0
    text_excerpt: str               # First 200 chars
    page_numbers: List[int]         # Source pages
```

## Integration Patterns

### With LangGraph Agents

Capture traces at the end of agent execution:

```python
from langgraph.graph import StateGraph, MessagesState

class AgentState(MessagesState):
    query: str
    response: str
    trace_id: Optional[str] = None

async def final_node(state: AgentState):
    """Capture explainability trace before returning."""
    trace = await explainability_engine.capture_trace(
        query=state["query"],
        response=state["response"],
        skill_context={
            "activated": state.get("skills_used", []),
            "confidence": state.get("confidence", 0.5),
            "considered_skills": state.get("skill_analysis", [])
        },
        retrieval_context={
            "mode": state.get("retrieval_mode", "hybrid"),
            "total_retrieved": len(state.get("all_chunks", [])),
            "chunks_used": state.get("chunks_in_context", [])
        },
        tool_context={
            "invocations": state.get("tool_calls", [])
        }
    )

    state["trace_id"] = trace.id
    return state
```

### With API Endpoints

Add explainability to chat endpoints:

```python
from fastapi import APIRouter, Query
from src.governance.explainability import ExplanationLevel

router = APIRouter()

@router.post("/chat")
async def chat(query: str):
    # Generate response
    response = await agent.invoke(query)

    # Capture trace
    trace = await engine.capture_trace(...)

    return {
        "response": response,
        "trace_id": trace.id,
        "explanation": await engine.explain(
            trace.id,
            ExplanationLevel.USER
        )
    }

@router.get("/explain/{trace_id}")
async def get_explanation(
    trace_id: str,
    level: ExplanationLevel = Query(ExplanationLevel.USER)
):
    """Get detailed explanation for a trace."""
    return {
        "explanation": await engine.explain(trace_id, level)
    }
```

### With Frontend UI

Show explanations on demand:

```typescript
// React component
function ResponseWithExplanation({ response, traceId }) {
  const [explanation, setExplanation] = useState(null);
  const [level, setLevel] = useState('user');

  const fetchExplanation = async () => {
    const res = await fetch(`/api/explain/${traceId}?level=${level}`);
    const data = await res.json();
    setExplanation(data.explanation);
  };

  return (
    <div>
      <p>{response}</p>
      <button onClick={fetchExplanation}>
        How was this generated?
      </button>
      {explanation && (
        <div className="explanation">
          <select onChange={(e) => setLevel(e.target.value)}>
            <option value="user">Simple</option>
            <option value="expert">Technical</option>
            <option value="audit">Full Trace</option>
          </select>
          <pre>{explanation}</pre>
        </div>
      )}
    </div>
  );
}
```

## Storage Options

### In-Memory (Default)

Best for: Testing, MVP, low-volume production

```python
storage = InMemoryTraceStorage()
```

**Pros:**
- Fast (<5ms operations)
- No external dependencies
- Simple setup

**Cons:**
- Not persistent across restarts
- Limited to single instance
- Memory grows unbounded

### Redis (Future)

Best for: Production, distributed systems

```python
from redis import Redis
from src.governance.explainability.storage import RedisTraceStorage

redis_client = Redis(host='localhost', port=6379)
storage = RedisTraceStorage(
    redis_client,
    ttl_days=365 * 7  # 7 years for GDPR compliance
)
```

**Pros:**
- Persistent storage
- TTL-based expiration
- Distributed query support
- Production-ready

**Cons:**
- Requires Redis infrastructure
- Slightly slower than in-memory

## Querying Traces

### By Time Range

```python
from datetime import datetime, timedelta

# Last 24 hours
traces = await storage.query(
    start_time=datetime.now() - timedelta(hours=24)
)

# Specific time window
traces = await storage.query(
    start_time=datetime(2026, 1, 1),
    end_time=datetime(2026, 1, 31)
)
```

### By Skill

```python
# All traces using research_agent
traces = await storage.query(skill_name="research_agent")
```

### Combined Filters

```python
# Research traces in last hour
traces = await storage.query(
    start_time=datetime.now() - timedelta(hours=1),
    skill_name="research_agent",
    limit=50
)
```

### Count Operations

```python
# Total traces
count = await storage.count()

# Traces in date range
count = await storage.count(
    start_time=datetime.now() - timedelta(days=7)
)
```

## Claim Attribution

Verify which sources support specific claims:

```python
# Generate response with trace
trace = await engine.capture_trace(...)

# Later, verify a specific claim
claim = "The EU AI Act requires transparency for high-risk AI systems"
attributions = await engine.get_attribution_for_claim(
    response=trace.final_response,
    claim=claim,
    trace_id=trace.id
)

# Check sources
for attr in attributions:
    print(f"Supported by: {attr.document_name}")
    print(f"Relevance: {attr.relevance_score:.0%}")
    print(f"Excerpt: {attr.text_excerpt}")
```

**Use cases:**
- Fact-checking responses
- Citation generation
- Hallucination detection
- Source verification

## EU AI Act Compliance

### Article 13: Transparency

The engine satisfies Article 13 requirements by:

1. **Information about AI system**: Captured in `skills_activated`
2. **Logic of processing**: Explained in EXPERT level
3. **Data sources**: Listed in `attributions`
4. **Decision-making**: Detailed in `skills_considered`

### Article 14: Human Oversight

Enable oversight by:

1. **Understanding system**: EXPERT explanations
2. **Identifying inaccuracies**: Claim attribution
3. **Interpreting output**: USER explanations
4. **Intervening**: Full AUDIT traces

### Article 12: Record-Keeping

Maintain compliance records by:

1. **Training data**: Document in `attributions`
2. **Testing procedures**: Track in `metadata`
3. **Monitoring logs**: Query storage by time
4. **7-year retention**: Configure TTL in Redis

## Performance Considerations

### Optimize Trace Capture

```python
# Minimize context size
skill_context = {
    "activated": state["skills"],
    "confidence": state["confidence"],
    # Don't include: full LLM outputs, raw embeddings
}

# Limit attribution count
retrieval_context = {
    "chunks_used": state["chunks"][:20]  # Top 20 only
}
```

### Batch Explanations

```python
# Generate multiple explanations in parallel
import asyncio

trace_ids = ["trace_1", "trace_2", "trace_3"]
explanations = await asyncio.gather(*[
    engine.explain(tid, ExplanationLevel.USER)
    for tid in trace_ids
])
```

### Async Storage Operations

```python
# All storage operations are async
await storage.save(trace)          # Non-blocking
await storage.query(...)           # Non-blocking
await storage.count(...)           # Non-blocking
```

## Testing

### Mock Storage

```python
from src.governance.explainability import InMemoryTraceStorage

@pytest.fixture
def storage():
    store = InMemoryTraceStorage()
    yield store
    store.clear()  # Clean up after test
```

### Mock LLM

```python
from unittest.mock import AsyncMock

@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="0, 1"))
    return llm
```

### Example Test

```python
@pytest.mark.asyncio
async def test_capture_and_explain(storage, mock_llm):
    engine = ExplainabilityEngine(storage, mock_llm)

    trace = await engine.capture_trace(
        query="test query",
        response="test response",
        skill_context={"activated": ["test_skill"]},
        retrieval_context={"mode": "vector"},
        tool_context={"invocations": []}
    )

    explanation = await engine.explain(trace.id, ExplanationLevel.USER)
    assert "How this answer was generated" in explanation
```

## Troubleshooting

### Trace Not Found

```python
explanation = await engine.explain("nonexistent_id")
# Returns: "Trace not found"
```

**Solution:** Verify trace was saved, check storage persistence

### Empty Attributions

```python
trace = await engine.capture_trace(
    retrieval_context={"chunks_used": []}  # Empty!
)
# Attributions will be empty list
```

**Solution:** Ensure retrieval context includes chunks

### LLM Attribution Failure

```python
# LLM returns invalid format
attributions = await engine.get_attribution_for_claim(...)
# Fallback: Returns all attributions
```

**Solution:** Check LLM model, improve prompt if needed

## Best Practices

1. **Always capture traces**: Even for simple queries
2. **Use appropriate level**: USER for end-users, EXPERT for debugging
3. **Limit context size**: Only essential data
4. **Clean old traces**: Set TTL or periodic cleanup
5. **Monitor storage**: Track trace count and size
6. **Test explanations**: Verify readability and accuracy
7. **Document integration**: Note where traces are captured

## API Reference

See full API documentation:
- [Engine API](../api/governance/explainability_engine.md)
- [Storage API](../api/governance/explainability_storage.md)

## Related Documentation

- [Sprint 96 Plan](../sprints/SPRINT_96_PLAN.md)
- [EU AI Act Compliance](../compliance/EU_AI_ACT.md)
- [Skill Framework](./SKILL_FRAMEWORK_GUIDE.md)
- [Audit Trail System](./AUDIT_TRAIL_GUIDE.md)

---

**Last Updated:** 2026-01-15
**Version:** 1.0.0
**Maintainer:** Backend Agent
