# Sprint 63: Conversational Intelligence & Temporal Tracking

**Sprint Duration:** 2 weeks
**Total Story Points:** 29 SP
**Priority:** HIGH (User Experience + Audit Trail)
**Dependencies:** Sprint 61-62 Complete

---

## Executive Summary

Sprint 63 delivers **advanced conversational intelligence** and **basic temporal tracking**:

**Conversational Intelligence:**
- **Multi-Turn RAG Template** (13 SP) - Memory summary, conversation history, contradiction detection
- Context-aware conversations (memory + chat history + retrieved docs)
- Intelligent conflict resolution (System > Memory > Docs > Chat)

**Temporal Tracking:**
- **Basic Audit Trail** (8 SP) - "Who changed what and when"
- Entity/relation change logs
- Simple temporal queries

**Performance Optimization:**
- **Redis Prompt Caching** (5 SP, conditional) - Cache frequent prompts for +20% speedup

**Expected Impact:**
- Multi-turn context retention: **0% → 95%** (LLM sees conversation history)
- Citation accuracy: **+30%** (contradiction detection highlights conflicts)
- Audit trail coverage: **100%** (all entity/relation changes logged)
- Prompt cache hit rate: **40-60%** for common queries (conditional feature)

---

## Feature 63.1: Multi-Turn RAG Template (13 SP)

**Priority:** P0 (Critical for UX)
**Rationale:** Current answer generator is stateless - LLM sees **only** retrieved docs, not conversation history

### Current Problem

**File:** `src/prompts/answer_prompts.py` (lines 8-15)

```python
ANSWER_GENERATION_PROMPT = """Du bist ein hilfreicher KI-Assistent.
Beantworte die Frage basierend auf den bereitgestellten Dokumenten.

**Dokumente:**
{context}

**Frage:** {query}

**Antwort:**"""
```

**What's Missing:**
1. ❌ No conversation history (LLM can't reference previous turns)
2. ❌ No memory summary (no context from earlier in conversation)
3. ❌ No priority system (what to trust when sources conflict)
4. ❌ No contradiction detection (conflicts between sources not highlighted)

### Target: Multi-Turn RAG Template

```python
MULTI_TURN_RAG_PROMPT = """Du bist ein Assistenzsystem. Halte Kontext knapp, vermeide Wiederholungen.

SYSTEM-REGELN:
- Antworte präzise und faktisch
- Zitiere Quellen mit [1], [2], [3]
- Bei Widersprüchen: weise explizit darauf hin und zitiere beide Seiten

KURZ-MEMORY (Gesprächszusammenfassung, vom System gepflegt):
{memory_summary}

CHAT-VERLAUF (letzte {n_turns} Turns):
{conversation_history}

RETRIEVED KONTEXT (nach Relevanz sortiert):
{retrieved_context}

PRIORITÄT BEI WIDERSPRÜCHEN:
1. System-Regeln (absolute Wahrheit)
2. KURZ-MEMORY (Kontext aus diesem Gespräch)
3. RETRIEVED KONTEXT (Dokumente aus Wissensbank)
4. CHAT-VERLAUF (historische Aussagen)

Bei Konflikt: "**Widerspruch:** [Quelle A] sagt X [1], aber [Quelle B] sagt Y [2]."

USER: {current_question}

ASSISTANT:"""
```

---

### Sub-Feature 63.1.1: Memory Summarizer (5 SP)

#### Task 1: Implement ConversationSummarizer (3 SP)

**File:** `src/components/memory/summarizer.py` (new)

```python
"""Conversation memory summarizer for Multi-Turn RAG.

Sprint 63 Feature 63.1.1: Condense conversation history into concise summaries.
"""

import structlog
from src.components.llm_proxy import AegisLLMProxy
from src.components.memory import get_redis_memory

logger = structlog.get_logger(__name__)


class ConversationSummarizer:
    """Summarize conversation history for efficient context inclusion.

    Reduces conversation history from 5-10 turns (1000+ tokens)
    to concise summary (100-200 tokens).
    """

    def __init__(self):
        self.proxy = AegisLLMProxy()
        self.redis_memory = get_redis_memory()

    async def summarize_conversation(
        self,
        session_id: str,
        max_turns: int = 5,
        max_summary_tokens: int = 200,
    ) -> str:
        """Create concise summary of recent conversation turns.

        Args:
            session_id: Session ID
            max_turns: Maximum turns to include in summary
            max_summary_tokens: Target summary length

        Returns:
            Summary string (e.g., "User fragte nach RAG-Systemen.
            Assistant erklärte Hybrid-Search mit Vector+Graph.
            User bat um Beispiel...")
        """
        # Retrieve conversation history
        conversation = await self.redis_memory.retrieve(
            key=session_id,
            namespace="conversation",
        )

        if not conversation or not isinstance(conversation, dict):
            return "Keine bisherige Konversation."

        if "value" in conversation:
            conversation = conversation["value"]

        messages = conversation.get("messages", [])

        # Take last N turns
        recent_messages = messages[-max_turns * 2 :]  # Each turn = user + assistant

        if not recent_messages:
            return "Keine bisherige Konversation."

        # Build conversation text
        conversation_text = ""
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role.upper()}: {content}\n\n"

        # Summarize with LLM
        summary_prompt = f"""Fasse diese Konversation in 2-3 Sätzen zusammen.
Fokus auf Themen und Kernaussagen, nicht Details.

KONVERSATION:
{conversation_text}

ZUSAMMENFASSUNG (max {max_summary_tokens} tokens):"""

        try:
            from src.components.llm_proxy.models import LLMTask, TaskType, QualityRequirement, Complexity

            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt=summary_prompt,
                quality_requirement=QualityRequirement.LOW,  # Summary is forgiving
                complexity=Complexity.LOW,
                temperature=0.3,
                max_tokens=max_summary_tokens,
            )

            response = await self.proxy.generate(task)
            summary = response.content.strip()

            logger.info(
                "conversation_summarized",
                session_id=session_id,
                turns_included=len(recent_messages) // 2,
                summary_length=len(summary),
            )

            return summary

        except Exception as e:
            logger.error("conversation_summary_failed", session_id=session_id, error=str(e))
            return f"Bisherige Konversation: {len(recent_messages) // 2} Nachrichten."
```

#### Task 2: Cache Summaries in Redis (1 SP)

```python
async def get_or_create_summary(
    self,
    session_id: str,
    invalidate_after_turns: int = 2,
) -> str:
    """Get cached summary or create new one.

    Cache key: f"summary:{session_id}"
    TTL: Invalidate after N new turns
    """
    # Check cache
    cache_key = f"summary:{session_id}"
    cached = await self.redis_memory.retrieve(key=cache_key, namespace="cache")

    if cached:
        return cached.get("value", {}).get("summary", "")

    # Generate new summary
    summary = await self.summarize_conversation(session_id)

    # Cache for 5 minutes
    await self.redis_memory.store(
        key=cache_key,
        value={"summary": summary},
        namespace="cache",
        ttl_seconds=300,
    )

    return summary
```

#### Task 3: Test Summarizer (1 SP)

**File:** `tests/unit/components/memory/test_summarizer.py`

```python
@pytest.mark.asyncio
async def test_conversation_summarization():
    """Test conversation summarizer produces concise summaries."""
    summarizer = ConversationSummarizer()

    # Mock conversation with 5 turns
    mock_conversation = {
        "messages": [
            {"role": "user", "content": "Was ist RAG?"},
            {"role": "assistant", "content": "RAG ist Retrieval-Augmented Generation..."},
            {"role": "user", "content": "Wie funktioniert Hybrid-Search?"},
            {"role": "assistant", "content": "Hybrid-Search kombiniert Vector + BM25..."},
            {"role": "user", "content": "Zeige ein Beispiel"},
            {"role": "assistant", "content": "Beispiel: query='ML' → vector=[0.1,0.2,...]"},
        ]
    }

    # Summarize
    summary = await summarizer.summarize_conversation("test-session")

    # Verify summary is concise
    assert len(summary) < 500  # Less than 500 chars
    assert "RAG" in summary or "Hybrid" in summary  # Contains topics
```

---

### Sub-Feature 63.1.2: Enhanced Prompt Template (3 SP)

#### Task 1: Implement Multi-Turn Prompt (1 SP)

**File:** `src/prompts/answer_prompts.py` (update)

```python
# Sprint 63 Feature 63.1.2: Multi-Turn RAG Template
MULTI_TURN_RAG_PROMPT = """Du bist ein Assistenzsystem. Halte Kontext knapp, vermeide Wiederholungen.

SYSTEM-REGELN:
- Antworte präzise und faktisch
- Zitiere Quellen mit [1], [2], [3]
- Bei Widersprüchen: weise explizit darauf hin und zitiere beide Seiten

KURZ-MEMORY (Gesprächszusammenfassung, vom System gepflegt):
{memory_summary}

CHAT-VERLAUF (letzte {n_turns} Turns):
{conversation_history}

RETRIEVED KONTEXT (nach Relevanz sortiert):
{retrieved_context}

PRIORITÄT BEI WIDERSPRÜCHEN:
1. System-Regeln (absolute Wahrheit)
2. KURZ-MEMORY (Kontext aus diesem Gespräch)
3. RETRIEVED KONTEXT (Dokumente aus Wissensbank)
4. CHAT-VERLAUF (historische Aussagen)

Bei Konflikt: "**Widerspruch:** [Quelle A] sagt X [1], aber [Quelle B] sagt Y [2]."

USER: {current_question}

ASSISTANT:"""
```

#### Task 2: Conversation History Formatter (1 SP)

**File:** `src/agents/answer_generator.py` (update)

```python
def _format_conversation_history(
    self,
    messages: list[dict] | None,
    max_turns: int = 3,
) -> str:
    """Format last N conversation turns for prompt.

    Args:
        messages: Conversation messages
        max_turns: Number of turns to include

    Returns:
        Formatted string (e.g., "USER: Was ist RAG?\nASSISTANT: RAG ist...")
    """
    if not messages:
        return "Keine bisherige Konversation."

    # Take last N*2 messages (each turn = user + assistant)
    recent = messages[-(max_turns * 2) :]

    formatted = []
    for msg in recent:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")[:200]  # Truncate long messages
        formatted.append(f"{role}: {content}")

    return "\n".join(formatted)
```

#### Task 3: Integration Test (1 SP)

Test that prompt includes all components (memory, history, context).

---

### Sub-Feature 63.1.3: Contradiction Detection (3 SP)

#### Task 1: Implement Contradiction Detector (2 SP)

**File:** `src/agents/contradiction_detector.py` (new)

```python
"""Contradiction detection between memory, retrieved docs, and chat history.

Sprint 63 Feature 63.1.3: Detect and highlight source conflicts.
"""

import structlog
from typing import Any

logger = structlog.get_logger(__name__)


class ContradictionDetector:
    """Detect contradictions between different information sources.

    Checks for conflicts between:
    1. Memory summary
    2. Retrieved documents
    3. Conversation history
    """

    def __init__(self):
        pass

    async def detect_contradictions(
        self,
        memory_summary: str,
        retrieved_contexts: list[dict[str, Any]],
        conversation_history: list[dict] | None = None,
    ) -> list[dict]:
        """Detect contradictions between sources.

        Simple heuristic approach:
        - Extract key claims from each source
        - Look for negations or opposite statements
        - Flag potential conflicts for LLM to handle

        Args:
            memory_summary: Conversation summary
            retrieved_contexts: Retrieved documents
            conversation_history: Chat messages

        Returns:
            List of potential contradictions:
            [
                {
                    "source_a": "Memory: User asked about X",
                    "source_b": "Document [1]: Says Y about X",
                    "conflict_type": "factual_mismatch",
                    "confidence": 0.8,
                }
            ]
        """
        contradictions = []

        # Extract key statements from memory
        memory_claims = self._extract_claims(memory_summary)

        # Extract key statements from retrieved docs
        doc_claims = []
        for i, ctx in enumerate(retrieved_contexts[:3], 1):
            text = ctx.get("text", "")
            claims = self._extract_claims(text)
            doc_claims.append({"source_id": i, "claims": claims})

        # Simple contradiction detection: look for negations
        for memory_claim in memory_claims:
            for doc in doc_claims:
                for doc_claim in doc["claims"]:
                    if self._is_contradiction(memory_claim, doc_claim):
                        contradictions.append(
                            {
                                "source_a": f"Memory: {memory_claim}",
                                "source_b": f"Document [{doc['source_id']}]: {doc_claim}",
                                "conflict_type": "potential_contradiction",
                                "confidence": 0.7,
                            }
                        )

        logger.info("contradiction_detection_complete", count=len(contradictions))

        return contradictions

    def _extract_claims(self, text: str) -> list[str]:
        """Extract factual claims from text.

        Simple approach: Split into sentences, filter short ones.
        """
        sentences = text.split(". ")
        claims = [s.strip() for s in sentences if len(s.strip()) > 20]
        return claims[:5]  # Limit to 5 key claims

    def _is_contradiction(self, claim_a: str, claim_b: str) -> bool:
        """Simple heuristic: Check for negation keywords.

        More sophisticated: Use NLI model or LLM.
        """
        negations = ["nicht", "kein", "nie", "falsch", "incorrect", "wrong", "not", "no"]

        claim_a_lower = claim_a.lower()
        claim_b_lower = claim_b.lower()

        # Check if one has negation and they share keywords
        shared_keywords = set(claim_a_lower.split()) & set(claim_b_lower.split())

        if len(shared_keywords) >= 3:  # At least 3 words in common
            has_negation_a = any(neg in claim_a_lower for neg in negations)
            has_negation_b = any(neg in claim_b_lower for neg in negations)

            # One has negation, other doesn't = potential contradiction
            if has_negation_a != has_negation_b:
                return True

        return False
```

#### Task 2: Integrate with Answer Generator (1 SP)

Update `generate_answer()` to detect and report contradictions.

---

### Sub-Feature 63.1.4: Answer Generator Integration (2 SP)

#### Task 1: Update Answer Generator (1 SP)

**File:** `src/agents/answer_generator.py` (update `generate_answer`)

```python
async def generate_answer(
    self,
    query: str,
    contexts: list[dict],
    session_id: str | None = None,  # NEW
    conversation_history: list[dict] | None = None,  # NEW
    mode: str = "multi_turn",  # NEW default
) -> str:
    """Generate answer with multi-turn RAG support.

    Sprint 63 Feature 63.1.4: Integrate memory, history, contradiction detection.

    Args:
        query: User question
        contexts: Retrieved document contexts
        session_id: Session ID for memory retrieval
        conversation_history: Recent messages
        mode: "simple" (old) or "multi_turn" (new default)

    Returns:
        Generated answer with citations
    """
    if not contexts:
        return self._no_context_answer(query)

    # Mode selection
    if mode == "simple":
        # Legacy mode (no memory/history)
        return await self._generate_simple(query, contexts)

    # Multi-turn RAG mode (Sprint 63)
    # 1. Get memory summary
    summarizer = ConversationSummarizer()
    memory_summary = ""
    if session_id:
        memory_summary = await summarizer.get_or_create_summary(session_id)

    # 2. Format conversation history
    conv_history_text = self._format_conversation_history(conversation_history, max_turns=3)

    # 3. Detect contradictions
    detector = ContradictionDetector()
    contradictions = await detector.detect_contradictions(
        memory_summary=memory_summary,
        retrieved_contexts=contexts,
        conversation_history=conversation_history,
    )

    # 4. Format retrieved context
    context_text = self._format_contexts(contexts)

    # 5. Build multi-turn prompt
    prompt = MULTI_TURN_RAG_PROMPT.format(
        memory_summary=memory_summary or "Keine bisherige Konversation.",
        n_turns=len(conversation_history) // 2 if conversation_history else 0,
        conversation_history=conv_history_text,
        retrieved_context=context_text,
        current_question=query,
    )

    # 6. Add contradiction warnings if found
    if contradictions:
        contradiction_text = "\n\n**ACHTUNG - Widersprüche gefunden:**\n"
        for c in contradictions[:3]:  # Top 3
            contradiction_text += f"- {c['source_a']} vs {c['source_b']}\n"
        prompt = contradiction_text + prompt

    # 7. Generate answer
    try:
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            quality_requirement=QualityRequirement.MEDIUM,
            complexity=Complexity.MEDIUM,
            temperature=self.temperature,
        )

        response = await self.proxy.generate(task)
        answer = response.content.strip()

        logger.info(
            "multi_turn_answer_generated",
            query=query[:100],
            answer_length=len(answer),
            contexts_used=len(contexts),
            memory_used=bool(memory_summary),
            contradictions_found=len(contradictions),
        )

        return answer

    except Exception as e:
        logger.error("multi_turn_answer_generation_failed", query=query[:100], error=str(e))
        return self._fallback_answer(query, contexts)
```

#### Task 2: Update API to Pass Session ID & History (1 SP)

**File:** `src/api/v1/chat.py` (update `chat` endpoint)

```python
# Update coordinator.process_query call to include session_id
result = await coordinator.process_query(
    query=request.query,
    session_id=session_id,  # Already passed
    intent=request.intent,
    namespaces=request.namespaces,
)

# Retrieve conversation history for answer generation
conversation = await redis_memory.retrieve(key=session_id, namespace="conversation")
messages = conversation.get("value", {}).get("messages", []) if conversation else []

# Pass to answer generator (update coordinator to forward)
```

---

## Feature 63.2: Basic Temporal Audit Trail (8 SP)

**Priority:** P1
**Rationale:** "Wer hat wann was geändert" - Minimum viable temporal tracking

### Tasks

#### 1. Add Temporal Fields to Entities/Relations (2 SP)

**File:** `src/components/graph_rag/neo4j_client.py`

Update entity/relation creation to include temporal fields:
```python
# Add to entity properties
created_at: datetime
updated_at: datetime
created_by: str  # user_id
updated_by: str  # user_id
version: int
```

#### 2. Change Log Table (3 SP)

**File:** `src/components/graph_rag/change_log.py` (new)

```python
class ChangeLog:
    """Log all entity/relation changes for audit trail.

    Stores in Neo4j as separate (:ChangeEvent) nodes.
    """

    async def log_change(
        self,
        entity_id: str,
        change_type: str,  # "created", "updated", "deleted"
        changed_by: str,
        changes: dict,  # {"field": {"old": "...", "new": "..."}}
    ):
        """Log entity change.

        Cypher:
            CREATE (change:ChangeEvent {
                entity_id: $entity_id,
                change_type: $change_type,
                changed_by: $changed_by,
                changed_at: datetime(),
                changes: $changes
            })
            MATCH (e:Entity {id: $entity_id})
            CREATE (e)-[:HAS_CHANGE]->(change)
        """
```

#### 3. Temporal Query API (2 SP)

**File:** `src/api/v1/temporal.py` (new)

```python
@router.get("/temporal/changes/{entity_id}")
async def get_entity_changes(entity_id: str) -> list[dict]:
    """Get change history for entity.

    Returns:
        [
            {
                "changed_at": "2025-12-21T10:00:00Z",
                "changed_by": "user123",
                "change_type": "updated",
                "changes": {"name": {"old": "X", "new": "Y"}}
            },
            ...
        ]
    """
```

#### 4. Test Audit Trail (1 SP)

Verify changes are logged and queryable.

---

## Feature 63.3: Redis Prompt Caching (5 SP, Conditional)

**Priority:** P3 (Optional - only if >100 QPS)
**Rationale:** Cache frequent prompts for +20% speedup

### Tasks

#### 1. Implement Prompt Cache (3 SP)

**File:** `src/components/llm_proxy/prompt_cache.py` (new)

```python
class PromptCache:
    """Cache LLM responses for identical prompts.

    Use only for deterministic prompts (temperature=0).
    """

    def __init__(self):
        self.redis = get_redis_memory()

    async def get(self, prompt_hash: str) -> str | None:
        """Get cached response for prompt."""
        cached = await self.redis.retrieve(
            key=f"prompt_cache:{prompt_hash}",
            namespace="cache",
        )
        return cached.get("value", {}).get("response") if cached else None

    async def set(self, prompt_hash: str, response: str, ttl_seconds: int = 3600):
        """Cache prompt response."""
        await self.redis.store(
            key=f"prompt_cache:{prompt_hash}",
            value={"response": response},
            namespace="cache",
            ttl_seconds=ttl_seconds,
        )
```

#### 2. Integration & Testing (2 SP)

Test cache hit rate and latency reduction.

---

## Success Criteria

| Feature | Success Metric | Target | Verification |
|---------|---------------|--------|--------------|
| 63.1 | Multi-turn context in prompts | 100% | Prompt inspection |
| 63.1 | Memory summary generated | <500ms | Performance test |
| 63.1 | Contradictions detected | >80% precision | Manual review |
| 63.2 | Changes logged | 100% | Audit query |
| 63.2 | Change queries work | <100ms | API test |
| 63.3 | Prompt cache hit rate | 40-60% | Metrics |

---

## Timeline

| Day | Tasks | Deliverables |
|-----|-------|--------------|
| 1-3 | Feature 63.1.1-63.1.2 | Memory summarizer + prompt template |
| 4-6 | Feature 63.1.3-63.1.4 | Contradiction detection + integration |
| 7-9 | Feature 63.2 | Temporal audit trail |
| 10-12 | Feature 63.3 | Prompt caching (conditional) |
| 13-14 | Testing & integration | All tests passing |

**Total Duration:** 14 days (2 weeks)

---

## Dependencies

- ✅ Sprint 61-62 Complete
- ✅ Redis conversation storage exists
- ✅ Answer generator exists
- ✅ Neo4j entity/relation creation exists

---

## Deferred to Sprint 64+

**Feature 64.1: Multihop Agent Use Cases (3 SP)**
- Research potential agent-to-agent use cases after endpoint removal
- Design new multihop patterns if needed

**Feature 64.2: Full Bi-Temporal Queries**
- Advanced temporal: time-travel queries, temporal joins
- Only if minimum approach (Sprint 63) proves insufficient

---

## Final Note

This completes the Sprint 61-63 reorganization:
- **Sprint 61:** Performance (25 SP)
- **Sprint 62:** Section-Aware (30 SP)
- **Sprint 63:** Conversational + Temporal (29 SP)
- **Total:** 84 SP across 3 focused sprints
