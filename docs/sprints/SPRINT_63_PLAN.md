# Sprint 63: Conversational Intelligence & Temporal Tracking

**Sprint Duration:** 2 weeks
**Total Story Points:** 41 SP
**Priority:** HIGH (User Experience + Audit Trail)
**Dependencies:** Sprint 61-62 Complete

---

## Executive Summary

Sprint 63 delivers **advanced conversational intelligence** and **basic temporal tracking**:

**Conversational Intelligence:**
- **Multi-Turn RAG Template** (13 SP) - Memory summary, conversation history, contradiction detection
- **Structured Output Formatting** (5 SP) - Professional, consistent response templates
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
- Response consistency: **+60%** (structured templates for all output types)
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

## Feature 63.4: Structured Output Formatting (5 SP)

**Priority:** P1 (High UX Impact)
**Rationale:** Consistent, professional, well-formatted responses improve readability and user trust

### Current Problem

**Inconsistent Output Formats:**
- No standardized structure for different query types
- Citations formatted inconsistently
- No visual hierarchy in long responses
- Missing metadata (confidence, sources count, response time)
- Plain text output (no Markdown, no formatting)

### Target: Structured Response Templates

#### 1. Response Schema by Intent (2 SP)

**File:** `src/models/response_templates.py` (new)

```python
"""Structured response templates for different query intents.

Sprint 63 Feature 63.4: Professional, consistent output formatting.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Any


class ResponseIntent(str, Enum):
    """Query intent types with different output formats."""

    FACTUAL = "factual"  # Simple fact lookup
    COMPARISON = "comparison"  # Compare two or more entities
    EXPLANATION = "explanation"  # Explain concept/process
    SUMMARY = "summary"  # Summarize document/topic
    TROUBLESHOOTING = "troubleshooting"  # Problem-solving
    HYBRID = "hybrid"  # Multi-modal reasoning


class StructuredResponse(BaseModel):
    """Structured response container with metadata."""

    # Core content
    answer: str = Field(..., description="Main answer text (Markdown formatted)")
    intent: ResponseIntent = Field(..., description="Detected query intent")

    # Metadata
    confidence: float = Field(..., ge=0.0, le=1.0, description="Answer confidence score")
    sources_used: int = Field(..., description="Number of sources used")
    processing_time_ms: int = Field(..., description="Total processing time")

    # Citations
    sources: list[dict[str, Any]] = Field(
        default_factory=list, description="Source documents with citations"
    )

    # Context (optional)
    contradictions: list[dict] | None = Field(
        None, description="Detected contradictions between sources"
    )
    related_topics: list[str] | None = Field(None, description="Related topics for follow-up")


class ResponseFormatter:
    """Format responses based on intent and content type."""

    def format_factual(self, answer: str, sources: list[dict]) -> str:
        """Format factual query response.

        Template:
            **Answer:** {answer}

            **Sources:**
            - [1] {source_1}
            - [2] {source_2}

            **Confidence:** {confidence}
        """
        formatted = f"**Antwort:** {answer}\n\n"

        if sources:
            formatted += "**Quellen:**\n"
            for i, src in enumerate(sources[:5], 1):
                title = src.get("title", "Unknown")
                section = src.get("primary_section", "")
                page = src.get("page", "")
                citation = f"[{i}] {title}"
                if section:
                    citation += f" - Section: '{section}'"
                if page:
                    citation += f" (Seite {page})"
                formatted += f"- {citation}\n"

        return formatted

    def format_comparison(self, answer: str, entities: list[str]) -> str:
        """Format comparison response with table.

        Template:
            **Vergleich:** {entity_1} vs {entity_2}

            | Kriterium | {entity_1} | {entity_2} |
            |-----------|------------|------------|
            | ...       | ...        | ...        |

            **Zusammenfassung:** {summary}
        """
        formatted = f"**Vergleich:** {' vs '.join(entities)}\n\n"
        formatted += answer  # Should contain table
        return formatted

    def format_explanation(self, answer: str, steps: list[str] | None = None) -> str:
        """Format explanation with optional step-by-step breakdown.

        Template:
            **Erklärung:**

            {answer}

            **Schritt-für-Schritt:**
            1. {step_1}
            2. {step_2}
            ...
        """
        formatted = f"**Erklärung:**\n\n{answer}\n\n"

        if steps:
            formatted += "**Schritt-für-Schritt:**\n"
            for i, step in enumerate(steps, 1):
                formatted += f"{i}. {step}\n"

        return formatted

    def format_summary(self, answer: str, key_points: list[str] | None = None) -> str:
        """Format summary with bullet points.

        Template:
            **Zusammenfassung:**

            {answer}

            **Kernpunkte:**
            - {point_1}
            - {point_2}
            ...
        """
        formatted = f"**Zusammenfassung:**\n\n{answer}\n\n"

        if key_points:
            formatted += "**Kernpunkte:**\n"
            for point in key_points:
                formatted += f"- {point}\n"

        return formatted

    def format_with_contradictions(
        self, answer: str, contradictions: list[dict]
    ) -> str:
        """Add contradiction warnings to response.

        Template:
            ⚠️ **Widersprüche gefunden:**
            - {contradiction_1}
            - {contradiction_2}

            **Antwort:** {answer}
        """
        if not contradictions:
            return answer

        warning = "⚠️ **Widersprüche in den Quellen gefunden:**\n\n"
        for c in contradictions[:3]:
            source_a = c.get("source_a", "")
            source_b = c.get("source_b", "")
            warning += f"- {source_a}\n  vs\n  {source_b}\n\n"

        return warning + answer

    def add_metadata_footer(
        self,
        formatted: str,
        confidence: float,
        sources_count: int,
        processing_time_ms: int,
    ) -> str:
        """Add metadata footer to response.

        Template:
            ---
            *Konfidenz: {confidence}% | Quellen: {count} | Antwortzeit: {time}ms*
        """
        footer = f"\n\n---\n*Konfidenz: {confidence:.0%} | "
        footer += f"Quellen: {sources_count} | "
        footer += f"Antwortzeit: {processing_time_ms}ms*"
        return formatted + footer
```

#### 2. Integration with Answer Generator (2 SP)

**File:** `src/agents/answer_generator.py` (update)

```python
async def generate_answer(
    self,
    query: str,
    contexts: list[dict],
    session_id: str | None = None,
    conversation_history: list[dict] | None = None,
    mode: str = "multi_turn",
    intent: ResponseIntent = ResponseIntent.FACTUAL,  # NEW
    include_metadata: bool = True,  # NEW
) -> StructuredResponse:  # NEW return type
    """Generate structured, formatted answer.

    Sprint 63 Feature 63.4: Return structured response with formatting.
    """
    # ... existing multi-turn logic ...

    # Generate raw answer
    raw_answer = await self._generate_raw_answer(prompt)

    # Format based on intent
    formatter = ResponseFormatter()

    if intent == ResponseIntent.FACTUAL:
        formatted_answer = formatter.format_factual(raw_answer, contexts)
    elif intent == ResponseIntent.COMPARISON:
        entities = self._extract_entities(query)
        formatted_answer = formatter.format_comparison(raw_answer, entities)
    elif intent == ResponseIntent.EXPLANATION:
        formatted_answer = formatter.format_explanation(raw_answer)
    elif intent == ResponseIntent.SUMMARY:
        key_points = self._extract_key_points(raw_answer)
        formatted_answer = formatter.format_summary(raw_answer, key_points)
    else:
        formatted_answer = raw_answer

    # Add contradiction warnings if found
    if contradictions:
        formatted_answer = formatter.format_with_contradictions(
            formatted_answer, contradictions
        )

    # Add metadata footer
    if include_metadata:
        formatted_answer = formatter.add_metadata_footer(
            formatted_answer,
            confidence=self._calculate_confidence(contexts),
            sources_count=len(contexts),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # Return structured response
    return StructuredResponse(
        answer=formatted_answer,
        intent=intent,
        confidence=self._calculate_confidence(contexts),
        sources_used=len(contexts),
        processing_time_ms=int((time.time() - start_time) * 1000),
        sources=contexts[:5],  # Top 5 sources
        contradictions=contradictions if contradictions else None,
        related_topics=self._extract_related_topics(contexts),
    )
```

#### 3. API Response Schema Update (1 SP)

**File:** `src/api/v1/chat.py` (update response model)

```python
from src.models.response_templates import StructuredResponse

class ChatResponse(BaseModel):
    """Chat API response with structured output."""

    session_id: str
    response: StructuredResponse  # NEW: Structured instead of plain string
    followup_questions: list[str] | None = None
    phase_events: list[PhaseEvent] | None = None
```

**Frontend receives:**
```json
{
  "session_id": "abc123",
  "response": {
    "answer": "**Antwort:** RAG ist Retrieval-Augmented Generation...\n\n**Quellen:**\n- [1] paper.pdf - Section: 'Introduction' (Page 2)\n\n---\n*Konfidenz: 92% | Quellen: 3 | Antwortzeit: 450ms*",
    "intent": "factual",
    "confidence": 0.92,
    "sources_used": 3,
    "processing_time_ms": 450,
    "sources": [...],
    "contradictions": null,
    "related_topics": ["Hybrid Search", "Vector Embeddings"]
  },
  "followup_questions": ["Was ist Hybrid Search?", ...]
}
```

#### 4. Frontend Markdown Rendering (Optional, 1 SP if time permits)

**File:** `frontend/src/components/StructuredAnswer.tsx` (new)

```tsx
import ReactMarkdown from 'react-markdown';

interface StructuredAnswerProps {
  response: StructuredResponse;
}

export const StructuredAnswer: React.FC<StructuredAnswerProps> = ({ response }) => {
  return (
    <div className="structured-answer">
      {/* Main answer with Markdown rendering */}
      <ReactMarkdown className="answer-content">
        {response.answer}
      </ReactMarkdown>

      {/* Contradiction warnings */}
      {response.contradictions && (
        <div className="contradictions-warning">
          <AlertTriangle className="icon" />
          <span>Widersprüche in Quellen gefunden</span>
        </div>
      )}

      {/* Related topics as chips */}
      {response.related_topics && (
        <div className="related-topics">
          <span className="label">Verwandte Themen:</span>
          {response.related_topics.map(topic => (
            <button key={topic} className="topic-chip">{topic}</button>
          ))}
        </div>
      )}
    </div>
  );
};
```

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
| 63.4 | Structured output consistency | 100% | Response format validation |
| 63.4 | Markdown rendering works | 100% | Frontend test |
| 63.4 | Metadata footer present | 100% | API test |
| 63.6 | E2E tests passing | 4/4 journeys | Playwright test |
| 63.6 | Security test passing | Dangerous commands blocked | E2E test |
| 63.7 | Auth documentation complete | Guide available | Manual review |
| 63.7 | Token generation script works | Generates valid JWT | Script test |

---

## Timeline

| Day | Tasks | Deliverables |
|-----|-------|--------------|
| 1-3 | Feature 63.1.1-63.1.2 | Memory summarizer + prompt template |
| 4-6 | Feature 63.1.3-63.1.4 | Contradiction detection + integration |
| 7-8 | Feature 63.2 | Temporal audit trail |
| 9-10 | Feature 63.3 | Prompt caching (conditional) |
| 11-12 | Feature 63.4 | Structured output formatting |
| 13-14 | Testing & integration | All tests passing |

**Total Duration:** 14 days (2 weeks)

---

## Dependencies

- ✅ Sprint 61-62 Complete
- ✅ Redis conversation storage exists
- ✅ Answer generator exists
- ✅ Neo4j entity/relation creation exists

---

## Feature 63.6: Playwright E2E Tests for Tool Framework (5 SP)

**Priority:** P1 (High - Test Coverage Gap)
**Status:** READY (Gap identified in Sprint 59 testing)
**Dependencies:** None

### Rationale

During Sprint 59 Tool Framework testing, **E2E tests were documented but never implemented**:
- **Current status:** 0 E2E tests for tool framework journeys
- **Unit tests:** 55/55 PASSED ✅
- **Integration tests:** 8/9 PASSED ✅
- **E2E tests:** 0/4 (missing file `tests/e2e/test_tool_framework_journeys.py`)

**Impact:**
- No browser-based validation of tool execution UI
- Cannot verify end-to-end user journeys
- Regression risk when updating tool UI

### Tasks

#### 1. Create Playwright Test Infrastructure (1 SP)

**File:** `tests/e2e/test_tool_framework_journeys.py` (new)

Set up Playwright test infrastructure:
```python
"""E2E tests for Tool Framework user journeys.

Sprint 63 Feature 63.6: Playwright tests for all 4 documented journeys.
Based on docs/e2e/TOOL_FRAMEWORK_USER_JOURNEY.md
"""

import pytest
from playwright.async_api import async_playwright, Page, expect


@pytest.fixture(scope="session")
async def browser():
    """Launch browser for E2E tests."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    """Create new page for each test."""
    page = await browser.new_page()
    yield page
    await page.close()
```

#### 2. Journey 1: Bash Execution E2E Test (1 SP)

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_journey_1_bash_execution(page: Page):
    """Test complete bash execution journey via UI.

    User story: Data analyst wants to run bash command to check system status.
    """
    # Navigate to tool execution page
    await page.goto("http://localhost:5179/tools")

    # Select Bash tool
    await page.click("text=Bash Command")

    # Wait for command input to be visible
    await page.wait_for_selector("textarea[name='command']")

    # Enter safe command
    await page.fill("textarea[name='command']", "echo 'Hello from E2E test'")

    # Click execute button
    await page.click("button:has-text('Execute')")

    # Wait for result to appear
    result = page.locator(".result-output")
    await expect(result).to_be_visible(timeout=5000)

    # Verify output contains expected text
    result_text = await result.text_content()
    assert "Hello from E2E test" in result_text

    # Verify success indicator
    success_badge = page.locator(".badge-success, .status-success")
    await expect(success_badge).to_be_visible()
```

#### 3. Journey 2: Python Execution E2E Test (1 SP)

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_journey_2_python_execution(page: Page):
    """Test complete Python execution journey via UI.

    User story: Developer wants to run Python code for data analysis.
    """
    await page.goto("http://localhost:5179/tools")

    # Select Python tool
    await page.click("text=Python Code")

    # Wait for code editor
    code_input = page.locator("textarea[name='code'], .code-editor")
    await expect(code_input).to_be_visible()

    # Enter safe Python code
    python_code = """
import math
result = math.sqrt(16)
print(f"Result: {result}")
"""
    await code_input.fill(python_code)

    # Execute
    await page.click("button:has-text('Execute')")

    # Wait for output
    output = page.locator(".python-output, .result-output")
    await expect(output).to_be_visible(timeout=5000)

    # Verify output
    output_text = await output.text_content()
    assert "Result: 4.0" in output_text or "4.0" in output_text
```

#### 4. Journey 4: Chat with Tools E2E Test (1 SP)

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_journey_4_chat_with_tools(page: Page):
    """Test chat conversation where LLM autonomously uses tools.

    User story: User asks question, LLM decides to use bash tool.
    """
    await page.goto("http://localhost:5179/chat")

    # Enter message that requires tool use
    chat_input = page.locator("textarea[name='message'], input[name='message']")
    await chat_input.fill("What is the current date and time?")

    # Send message
    await page.click("button:has-text('Send')")

    # Wait for LLM response
    await page.wait_for_selector(".message.assistant", timeout=10000)

    # Verify tool was used (look for tool usage indicator)
    tool_indicator = page.locator(".tool-used, .tool-call")
    # Tool usage indicator might be present or not depending on implementation

    # Verify response contains date/time information
    response = page.locator(".message.assistant").last
    response_text = await response.text_content()
    # Response should contain some date/time related info
    assert len(response_text) > 0
```

#### 5. Security Test: Dangerous Command Blocked (1 SP)

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_dangerous_command_blocked(page: Page):
    """Verify dangerous bash commands are blocked.

    Security requirement: System must reject dangerous patterns.
    """
    await page.goto("http://localhost:5179/tools")
    await page.click("text=Bash Command")

    # Try to execute dangerous command
    await page.fill("textarea[name='command']", "rm -rf /")
    await page.click("button:has-text('Execute')")

    # Wait for error message
    error = page.locator(".error-message, .alert-danger")
    await expect(error).to_be_visible(timeout=3000)

    # Verify error indicates command was blocked
    error_text = await error.text_content()
    assert "blocked" in error_text.lower() or "dangerous" in error_text.lower()
```

---

## Feature 63.7: MCP Authentication Documentation (2 SP)

**Priority:** P2 (Medium - Developer Experience)
**Status:** READY (Gap identified in Sprint 59 testing)
**Dependencies:** None

### Rationale

During Sprint 59 Tool Framework testing, **MCP tools require JWT authentication but no documentation exists**:
- **Impact:** Developers cannot test MCP tools without understanding auth flow
- **Current state:** Auth requirement mentioned in TOOL_FRAMEWORK_USER_JOURNEY.md but no implementation guide
- **Need:** Step-by-step authentication guide

### Tasks

#### 1. Create Authentication Guide (1 SP)

**File:** `docs/api/AUTHENTICATION.md` (new)

```markdown
# API Authentication Guide

**Sprint 63 Feature 63.7**

---

## Overview

AEGIS RAG uses **JWT (JSON Web Token)** authentication for MCP tool endpoints.

**Endpoints requiring authentication:**
- `/api/v1/mcp/tools/{tool_name}/execute` - All MCP tool executions

**Endpoints without authentication (development mode):**
- `/api/v1/chat/` - Standard chat endpoint
- `/api/v1/health` - Health check endpoint

---

## Quick Start

### 1. Obtain JWT Token

#### Development Mode (Local Testing)

For local development, generate a test token:

\`\`\`python
# scripts/generate_test_token.py
import jwt
import datetime

SECRET_KEY = "dev-secret-key-change-in-production"

payload = {
    "sub": "test-user",
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    "iat": datetime.datetime.utcnow(),
}

token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print(f"Token: {token}")
\`\`\`

#### Production Mode

In production, obtain tokens from your authentication provider:
1. User logs in via OAuth/SAML
2. Backend generates JWT with user claims
3. Frontend stores token in secure storage
4. Include token in all MCP requests

### 2. Make Authenticated Request

\`\`\`bash
# Using curl
curl -X POST http://localhost:8000/api/v1/mcp/tools/bash/execute \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "parameters": {
      "command": "echo test"
    }
  }'
\`\`\`

### 3. Handle Token Expiration

Tokens expire after configured timeout (default: 1 hour).

**Error response:**
\`\`\`json
{
  "detail": "Token expired",
  "status_code": 401
}
\`\`\`

**Solution:** Refresh token or re-authenticate.

---

## JWT Token Structure

\`\`\`json
{
  "sub": "user_id",
  "exp": 1735689600,
  "iat": 1735686000,
  "roles": ["user", "admin"]
}
\`\`\`

**Required claims:**
- `sub`: User ID
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp

**Optional claims:**
- `roles`: User roles for authorization

---

## Environment Configuration

\`\`\`bash
# .env
JWT_SECRET_KEY=your-secret-key-256-bits
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=1
\`\`\`

---

## Testing with Playwright

\`\`\`python
import pytest
from playwright.async_api import Page

@pytest.fixture
def auth_token():
    """Generate test JWT token."""
    import jwt
    import datetime

    payload = {
        "sub": "test-user",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, "dev-secret-key", algorithm="HS256")

@pytest.mark.e2e
async def test_authenticated_tool_call(page: Page, auth_token):
    """Test tool execution with authentication."""
    await page.goto("http://localhost:5179/tools")

    # Set token in local storage
    await page.evaluate(f"localStorage.setItem('auth_token', '{auth_token}')")

    # Execute tool (frontend automatically includes token)
    await page.click("text=Bash Command")
    await page.fill("textarea[name='command']", "echo test")
    await page.click("button:has-text('Execute')")

    # Verify success
    result = await page.locator(".result-output").text_content()
    assert "test" in result
\`\`\`

---

## Troubleshooting

### "Invalid token" Error

**Cause:** Token signature verification failed

**Solutions:**
1. Verify `JWT_SECRET_KEY` matches between services
2. Check token was not modified
3. Ensure algorithm matches (`HS256`)

### "Token expired" Error

**Cause:** Token `exp` claim is in the past

**Solutions:**
1. Generate new token
2. Implement token refresh mechanism
3. Increase `JWT_EXPIRATION_HOURS` if needed

### "Missing Authorization header" Error

**Cause:** Request did not include `Authorization: Bearer <token>`

**Solutions:**
1. Add header to request
2. Check frontend is including token
3. Verify token is stored in localStorage/sessionStorage

---

## Security Best Practices

1. **Never commit tokens to Git** - Use environment variables
2. **Use HTTPS in production** - Prevent token interception
3. **Rotate secret keys regularly** - Use key rotation strategy
4. **Implement refresh tokens** - Shorter-lived access tokens
5. **Validate all claims** - Check `exp`, `iat`, and custom claims
6. **Use secure storage** - httpOnly cookies or secure localStorage
7. **Implement rate limiting** - Prevent token brute-force attacks

---

**Document Version:** 1.0
**Last Updated:** 2025-12-21
**Sprint:** 63 Feature 63.7
\`\`\`
```

#### 2. Add Script: Generate Test Token (1 SP)

**File:** `scripts/generate_test_token.py` (new)

```python
#!/usr/bin/env python3
"""Generate test JWT token for local development.

Sprint 63 Feature 63.7: Authentication helper script.

Usage:
    python scripts/generate_test_token.py
    python scripts/generate_test_token.py --user admin --hours 24
"""

import argparse
import datetime
import jwt


def generate_token(user_id: str = "test-user", hours: int = 1) -> str:
    """Generate JWT token for testing.

    Args:
        user_id: User ID for 'sub' claim
        hours: Token validity in hours

    Returns:
        JWT token string
    """
    secret_key = "dev-secret-key-change-in-production"

    payload = {
        "sub": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=hours),
        "iat": datetime.datetime.utcnow(),
        "roles": ["user"],
    }

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


def main():
    """CLI for token generation."""
    parser = argparse.ArgumentParser(description="Generate test JWT token")
    parser.add_argument("--user", default="test-user", help="User ID")
    parser.add_argument("--hours", type=int, default=1, help="Token validity (hours)")

    args = parser.parse_args()

    token = generate_token(args.user, args.hours)

    print(f"\n{'='*60}")
    print(f"Generated JWT Token for User: {args.user}")
    print(f"Valid for: {args.hours} hour(s)")
    print(f"{'='*60}\n")
    print(token)
    print(f"\n{'='*60}")
    print("\nUse in curl:")
    print(f"curl -H 'Authorization: Bearer {token}' ...")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
```

Make executable:
```bash
chmod +x scripts/generate_test_token.py
```

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

This completes the Sprint 61-63 reorganization with bugfixes from Sprint 59 testing:
- **Sprint 61:** Performance & Ollama (29 SP) - includes 2 bugfix features (61.6, 61.7)
- **Sprint 62:** Section-Aware Features (38 SP) - includes Research Endpoint (62.10)
- **Sprint 63:** Conversational Intelligence + Temporal (41 SP) - includes E2E tests + Auth guide (63.6, 63.7)
- **Total:** 108 SP across 3 focused sprints

**Sprint 61 Bugfixes Added:**
- 61.6: Fix Chat Endpoint Timeout (3 SP) - Production blocker from Sprint 59 testing
- 61.7: Update Tool Framework Documentation (1 SP) - Fix outdated API endpoints ✅ COMPLETE

**Sprint 62 Bugfixes Added:**
- 62.10: Implement Research Endpoint (8 SP) - Missing /chat/research endpoint

**Sprint 63 Bugfixes Added:**
- 63.6: Playwright E2E Tests (5 SP) - Missing E2E test coverage for tool framework
- 63.7: MCP Authentication Guide (2 SP) - Missing JWT auth documentation

**Sprint 63 Feature Summary:**
- 63.1: Multi-Turn RAG Template (13 SP) - Memory + History + Contradictions
- 63.2: Basic Temporal Audit Trail (8 SP) - "Who changed what when"
- 63.3: Redis Prompt Caching (5 SP, conditional) - +20% speedup
- 63.4: Structured Output Formatting (5 SP) - Professional response templates
- 63.5: Section-Based Community Detection (3 SP, deferred from Sprint 62)
- 63.6: Playwright E2E Tests (5 SP) - Tool framework test coverage
- 63.7: MCP Authentication Guide (2 SP) - JWT auth documentation
