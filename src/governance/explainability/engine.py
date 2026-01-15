"""
Explainability Engine for AI Decision Transparency.

Provides EU AI Act compliant decision traces and explanations.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel


class ExplanationLevel(Enum):
    """Level of explanation detail for different audiences."""

    USER = "user"  # Simple, non-technical explanations
    EXPERT = "expert"  # Technical details and metrics
    AUDIT = "audit"  # Full trace for EU AI Act compliance


@dataclass
class SkillSelectionReason:
    """Reasoning for selecting or rejecting a skill."""

    skill_name: str
    confidence: float
    trigger_matched: Optional[str] = None
    intent_classification: Optional[str] = None
    alternative_skills: List[str] = field(default_factory=list)


@dataclass
class SourceAttribution:
    """Attribution to source document for transparency."""

    document_id: str
    document_name: str
    chunk_ids: List[str]
    relevance_score: float
    text_excerpt: str
    page_numbers: List[int] = field(default_factory=list)


@dataclass
class DecisionTrace:
    """
    Complete trace of AI decision/response generation.

    Captures all components required for EU AI Act Article 13 transparency.
    """

    id: str
    timestamp: datetime
    query: str
    final_response: str

    # Skill selection
    skills_considered: List[SkillSelectionReason]
    skills_activated: List[str]

    # Context retrieval
    retrieval_mode: str  # "vector", "graph", "hybrid"
    chunks_retrieved: int
    chunks_used: int

    # Source attribution
    attributions: List[SourceAttribution]

    # Tool usage
    tools_invoked: List[Dict[str, Any]]

    # Confidence metrics
    overall_confidence: float
    hallucination_risk: float  # From reflection/validation

    # Performance metrics
    total_duration_ms: float
    skill_durations: Dict[str, float] = field(default_factory=dict)


class ExplainabilityEngine:
    """
    Generate explanations for AI decisions.

    Supports EU AI Act requirements for:
    - Transparency (Article 13)
    - Human oversight (Article 14)
    - Record-keeping (Article 12)

    Provides 3-level explanations:
    - USER: Simple, non-technical (3-5 sentences)
    - EXPERT: Technical details with metrics
    - AUDIT: Full JSON trace for compliance review
    """

    def __init__(self, trace_storage: "TraceStorage", llm: BaseChatModel):
        """
        Initialize explainability engine.

        Args:
            trace_storage: Storage backend for decision traces
            llm: Language model for claim attribution
        """
        self.storage = trace_storage
        self.llm = llm

    async def capture_trace(
        self,
        query: str,
        response: str,
        skill_context: Dict[str, Any],
        retrieval_context: Dict[str, Any],
        tool_context: Dict[str, Any],
    ) -> DecisionTrace:
        """
        Capture decision trace from execution context.

        Args:
            query: User query
            response: Generated response
            skill_context: Skill selection data
            retrieval_context: Retrieved chunks/docs data
            tool_context: Tool invocations data

        Returns:
            Complete decision trace
        """
        trace = DecisionTrace(
            id=f"trace_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            query=query,
            final_response=response,
            skills_considered=self._extract_skill_reasons(skill_context),
            skills_activated=skill_context.get("activated", []),
            retrieval_mode=retrieval_context.get("mode", "unknown"),
            chunks_retrieved=retrieval_context.get("total_retrieved", 0),
            chunks_used=retrieval_context.get("used_in_response", 0),
            attributions=self._extract_attributions(retrieval_context),
            tools_invoked=tool_context.get("invocations", []),
            overall_confidence=skill_context.get("confidence", 0.5),
            hallucination_risk=skill_context.get("hallucination_risk", 0.0),
            total_duration_ms=skill_context.get("total_ms", 0.0),
            skill_durations=skill_context.get("skill_times", {}),
        )

        await self.storage.save(trace)
        return trace

    def _extract_skill_reasons(
        self, skill_context: Dict[str, Any]
    ) -> List[SkillSelectionReason]:
        """
        Extract skill selection reasoning from context.

        Args:
            skill_context: Skill selection metadata

        Returns:
            List of skill selection reasons
        """
        reasons = []
        for skill_data in skill_context.get("considered_skills", []):
            reasons.append(
                SkillSelectionReason(
                    skill_name=skill_data["name"],
                    confidence=skill_data.get("confidence", 0.0),
                    trigger_matched=skill_data.get("trigger"),
                    intent_classification=skill_data.get("intent"),
                    alternative_skills=skill_data.get("alternatives", []),
                )
            )
        return reasons

    def _extract_attributions(
        self, retrieval_context: Dict[str, Any]
    ) -> List[SourceAttribution]:
        """
        Extract source attributions from retrieval context.

        Args:
            retrieval_context: Retrieved chunks metadata

        Returns:
            List of source attributions
        """
        attributions = []
        for chunk in retrieval_context.get("chunks_used", []):
            attributions.append(
                SourceAttribution(
                    document_id=chunk.get("doc_id", ""),
                    document_name=chunk.get("doc_name", "Unknown"),
                    chunk_ids=[chunk.get("chunk_id", "")],
                    relevance_score=chunk.get("score", 0.0),
                    text_excerpt=chunk.get("text", "")[:200],
                    page_numbers=chunk.get("pages", []),
                )
            )
        return attributions

    async def explain(
        self, trace_id: str, level: ExplanationLevel = ExplanationLevel.USER
    ) -> str:
        """
        Generate human-readable explanation for a decision.

        Args:
            trace_id: ID of decision trace
            level: Detail level for explanation

        Returns:
            Natural language explanation
        """
        trace = await self.storage.get(trace_id)
        if not trace:
            return "Trace not found"

        if level == ExplanationLevel.USER:
            return await self._explain_user(trace)
        elif level == ExplanationLevel.EXPERT:
            return await self._explain_expert(trace)
        else:
            return await self._explain_audit(trace)

    async def _explain_user(self, trace: DecisionTrace) -> str:
        """
        Generate user-friendly explanation.

        Args:
            trace: Decision trace

        Returns:
            Simple, non-technical explanation
        """
        # Build sources list (top 3)
        sources = "\n".join(
            [
                f"- {attr.document_name} (relevance: {attr.relevance_score:.0%})"
                for attr in trace.attributions[:3]
            ]
        )

        # Determine confidence level in natural language
        if trace.overall_confidence > 0.8:
            confidence_text = "high confidence"
        elif trace.overall_confidence > 0.5:
            confidence_text = "moderate confidence"
        else:
            confidence_text = "lower confidence"

        return f"""**How this answer was generated:**

This response was created with {confidence_text} using information from:

{sources}

The system used {len(trace.skills_activated)} specialized capabilities to find and synthesize the relevant information.

If you'd like more details about how this answer was derived, please ask for an expert explanation."""

    async def _explain_expert(self, trace: DecisionTrace) -> str:
        """
        Generate technical explanation with metrics.

        Args:
            trace: Decision trace

        Returns:
            Detailed technical explanation
        """
        # Skills considered (top 5)
        skills_text = "\n".join(
            [
                f"- **{s.skill_name}**: {s.confidence:.1%} confidence "
                f"(trigger: {s.trigger_matched or 'intent-based'})"
                for s in trace.skills_considered[:5]
            ]
        )

        # Tools invoked (top 5)
        tools_text = "\n".join(
            [
                f"- {t.get('tool', 'unknown')}: {t.get('outcome', 'completed')}"
                for t in trace.tools_invoked[:5]
            ]
        )

        if not tools_text:
            tools_text = "- None"

        return f"""**Technical Decision Trace:**

**Query Analysis:**
- Retrieval mode: {trace.retrieval_mode}
- Chunks retrieved: {trace.chunks_retrieved}
- Chunks used: {trace.chunks_used}

**Skill Selection:**
{skills_text}

**Tools Invoked:**
{tools_text}

**Confidence Metrics:**
- Overall confidence: {trace.overall_confidence:.1%}
- Hallucination risk: {trace.hallucination_risk:.1%}

**Performance:**
- Total duration: {trace.total_duration_ms:.0f}ms
- Skill breakdown: {trace.skill_durations}"""

    async def _explain_audit(self, trace: DecisionTrace) -> str:
        """
        Generate full audit explanation for compliance.

        Args:
            trace: Decision trace

        Returns:
            Full JSON-serializable audit trace
        """
        # Full JSON-serializable trace for EU AI Act compliance
        audit_data = {
            "trace_id": trace.id,
            "timestamp": trace.timestamp.isoformat(),
            "query_hash": str(hash(trace.query))[:16],
            "skills": {
                "considered": [
                    {"name": s.skill_name, "confidence": s.confidence}
                    for s in trace.skills_considered
                ],
                "activated": trace.skills_activated,
            },
            "retrieval": {
                "mode": trace.retrieval_mode,
                "chunks_retrieved": trace.chunks_retrieved,
                "chunks_used": trace.chunks_used,
            },
            "attributions": [
                {"document_id": a.document_id, "relevance": a.relevance_score}
                for a in trace.attributions
            ],
            "tools": trace.tools_invoked,
            "confidence": {
                "overall": trace.overall_confidence,
                "hallucination_risk": trace.hallucination_risk,
            },
            "timing": {
                "total_ms": trace.total_duration_ms,
                "by_skill": trace.skill_durations,
            },
        }

        return f"""**Audit Trail - Full Decision Trace**

```json
{json.dumps(audit_data, indent=2)}
```

This trace provides complete transparency for EU AI Act compliance (Article 13).
All skill selections, tool invocations, and source attributions are recorded."""

    async def get_attribution_for_claim(
        self, response: str, claim: str, trace_id: str
    ) -> List[SourceAttribution]:
        """
        Find source attribution for specific claim in response.

        Used for fact-checking and grounding verification.

        Args:
            response: Full response text
            claim: Specific claim to verify
            trace_id: ID of decision trace

        Returns:
            List of source attributions supporting the claim
        """
        trace = await self.storage.get(trace_id)
        if not trace:
            return []

        if not trace.attributions:
            return []

        # Use LLM to match claim to sources
        prompt = f"""Given the claim: "{claim}"

And these source excerpts:
{chr(10).join([f'[{i}] {a.text_excerpt}' for i, a in enumerate(trace.attributions)])}

Which source(s) support this claim? Return source numbers (0-indexed) separated by commas.
If no source supports the claim, return "UNSUPPORTED".

Answer with just the numbers or "UNSUPPORTED"."""

        result = await self.llm.ainvoke(prompt)

        # Parse response and return matching attributions
        try:
            response_text = result.content if hasattr(result, "content") else str(result)
            if "UNSUPPORTED" in response_text.upper():
                return []

            indices = [int(i.strip()) for i in response_text.split(",")]
            return [
                trace.attributions[i] for i in indices if i < len(trace.attributions)
            ]
        except (ValueError, IndexError):
            # Fallback: return all attributions if parsing fails
            return trace.attributions
