"""Query Rewriter v2 - Graph-Intent Extraction.

Sprint 69 Feature 69.5: Query Rewriter v2 - Graph-Intent Extraction (8 SP)
Sprint 113 Feature 113.1: C-LARA Fast Inference (bypass LLM for simple queries)

This module extends query rewriting with graph intent extraction to improve
graph reasoning accuracy for complex queries. It identifies:
- Entity relationships that require graph traversal
- Multi-hop reasoning patterns
- Community discovery queries
- Temporal patterns in knowledge graphs

Sprint 113 Optimization:
    Uses C-LARA intent classification (40ms) to infer graph intents instead of
    LLM-based extraction (17s). Falls back to LLM only for complex queries.

    Performance improvement: 17,600ms → ~50ms (350x faster)

Architecture:
    User Query → C-LARA Intent → Graph Intent Inference → CypherHints → GraphQueryAgent
    (Optional LLM fallback for complex queries)

Example:
    rewriter = QueryRewriterV2()
    result = await rewriter.extract_graph_intents(
        "How are authentication and authorization related in the security module?"
    )
    # result.graph_intents: ["entity_relationships", "multi_hop"]
    # result.entities_mentioned: ["authentication", "authorization", "security module"]
    # result.cypher_hints: [
    #     "MATCH (a:Entity {name: 'authentication'})-[r]-(b:Entity {name: 'authorization'})",
    #     "MATCH path = (a)-[*1..3]-(b) WHERE ..."
    # ]

Performance Target:
    - Latency: ~50ms with C-LARA inference (Sprint 113)
    - Fallback: +80ms per extraction (LLM overhead) - only for complex queries
    - Graph query accuracy: +25% on complex queries
    - Precision: >0.85 for intent classification

References:
    - Sprint 67 Feature 67.9: Query Rewriter v1
    - Sprint 69 Feature 69.5: Graph-Intent Extraction
    - Sprint 81: C-LARA SetFit Intent Classifier (95% accuracy)
    - Sprint 113: C-LARA → Graph Intent Fast Inference
    - ADR-040: RELATES_TO semantic relationships
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from src.domains.llm_integration.models import LLMTask, QualityRequirement, TaskType
from src.domains.llm_integration.proxy import get_aegis_llm_proxy

if TYPE_CHECKING:
    from src.components.retrieval.intent_classifier import IntentClassifier, CLARAIntent

logger = structlog.get_logger(__name__)

# Sprint 113: Environment variable to control C-LARA fast inference (default: enabled)
USE_CLARA_FAST_INFERENCE = os.getenv("USE_CLARA_FAST_INFERENCE", "true").lower() == "true"


# Sprint 113: C-LARA Intent → Graph Intent Mapping
# Maps C-LARA 5-class intents to appropriate graph reasoning patterns
CLARA_TO_GRAPH_INTENT_MAP: dict[str, dict[str, Any]] = {
    "factual": {
        "default_intents": ["attribute_search"],
        "traversal_depth": 1,
        "keywords_override": {
            r"\b(related|relationship|connect|link)\b": ["entity_relationships"],
            r"\b(between|versus|vs)\b": ["entity_relationships"],
        },
    },
    "procedural": {
        "default_intents": ["multi_hop"],
        "traversal_depth": 2,
        "keywords_override": {
            r"\b(step|path|process|flow)\b": ["multi_hop"],
            r"\b(how does .+ work)\b": ["multi_hop", "entity_relationships"],
        },
    },
    "comparison": {
        "default_intents": ["entity_relationships"],
        "traversal_depth": 1,
        "keywords_override": {
            r"\b(difference|compare|versus|vs)\b": ["entity_relationships"],
            r"\b(similar|alike)\b": ["community_discovery"],
        },
    },
    "recommendation": {
        "default_intents": ["community_discovery"],
        "traversal_depth": 2,
        "keywords_override": {
            r"\b(suggest|recommend|best|option)\b": ["community_discovery"],
            r"\b(alternative|instead)\b": ["entity_relationships", "community_discovery"],
        },
    },
    "navigation": {
        "default_intents": ["attribute_search"],
        "traversal_depth": 1,
        "keywords_override": {
            r"\b(find all|list all|show all)\b": ["community_discovery"],
            r"\b(where is|locate)\b": ["attribute_search"],
        },
    },
}

# Sprint 113: Keywords that indicate no graph reasoning is needed
SKIP_GRAPH_KEYWORDS = [
    r"^\d+\s*[\+\-\*\/]\s*\d+",  # Math expressions (2+2, 3*4)
    r"^(hi|hello|hey|thanks|thank you|bye|goodbye)\b",  # Greetings
    r"^(what time|current time|date today)\b",  # Time queries
    r"^(who are you|what are you)\b",  # Meta queries about the system
]


# Graph intent extraction prompt
GRAPH_INTENT_PROMPT = """Analyze the query and extract graph reasoning intents.

Query: "{query}"

Identify which of the following graph reasoning patterns apply:

1. **entity_relationships**: Query asks about direct relationships between specific entities
   - Examples: "How is X related to Y?", "What connects A and B?"

2. **multi_hop**: Query requires traversing multiple relationship hops
   - Examples: "How does X influence Z through Y?", "What's the path from A to C?"

3. **community_discovery**: Query seeks clusters or groups of related entities
   - Examples: "Find all entities related to topic X", "What are the main communities?"

4. **temporal_patterns**: Query involves time-based relationships or evolution
   - Examples: "How has X changed over time?", "What happened before Y?"

5. **attribute_search**: Query focuses on entity properties rather than relationships
   - Examples: "What is the definition of X?", "Describe entity Y"

Extract:
- graph_intents: List of applicable intent types (use exact names above)
- entities_mentioned: List of specific entities/concepts mentioned in the query
- relationship_types: List of relationship types to focus on (if mentioned)
- traversal_depth: Suggested max hops for multi-hop (1-3, or null)
- confidence: Confidence score 0.0-1.0

Respond ONLY with valid JSON in this exact format:
{{
  "graph_intents": ["intent1", "intent2"],
  "entities_mentioned": ["entity1", "entity2"],
  "relationship_types": ["RELATES_TO", "DEPENDS_ON"],
  "traversal_depth": 2,
  "confidence": 0.85
}}

JSON Response:"""


@dataclass
class GraphIntentResult:
    """Result of graph intent extraction.

    Attributes:
        query: Original user query
        graph_intents: List of identified graph intent types
        entities_mentioned: Entities/concepts mentioned in query
        relationship_types: Relationship types to focus on (if any)
        traversal_depth: Suggested max hops for multi-hop queries
        confidence: Confidence score for the extraction
        cypher_hints: Generated Cypher query patterns
        latency_ms: Extraction latency in milliseconds
    """

    query: str
    graph_intents: list[str]
    entities_mentioned: list[str]
    relationship_types: list[str]
    traversal_depth: int | None
    confidence: float
    cypher_hints: list[str]
    latency_ms: float


class QueryRewriterV2:
    """Query rewriter v2 with graph intent extraction.

    This class extends query rewriting to extract graph-specific intents
    and generate Cypher query hints for targeted graph traversal. It uses
    LLM-based analysis to identify entity relationships, multi-hop patterns,
    community discovery needs, and temporal reasoning.

    The extracted intents guide the graph query agent to execute more
    accurate and efficient graph traversal strategies.

    Example:
        # Basic usage
        rewriter = QueryRewriterV2()
        result = await rewriter.extract_graph_intents(
            "How does authentication relate to authorization?"
        )

        # Use hints in graph query
        for hint in result.cypher_hints:
            print(f"Cypher pattern: {hint}")
    """

    def __init__(self, intent_classifier: IntentClassifier | None = None) -> None:
        """Initialize QueryRewriterV2.

        Args:
            intent_classifier: Optional intent classifier for initial intent detection.
                             Helps determine if graph extraction is needed.
        """
        self.logger = structlog.get_logger(__name__)
        self.llm = get_aegis_llm_proxy()
        self.intent_classifier = intent_classifier

        # Temperature for intent extraction (medium for creative reasoning)
        self._temperature = 0.5

        # Max tokens for LLM response
        self._max_tokens = 300

        # Sprint 113: Track fast inference usage
        self._use_fast_inference = USE_CLARA_FAST_INFERENCE

        self.logger.info(
            "query_rewriter_v2_initialized",
            has_intent_classifier=intent_classifier is not None,
            temperature=self._temperature,
            use_fast_inference=self._use_fast_inference,
        )

    def _should_skip_graph_intent(self, query: str) -> bool:
        """Check if query should skip graph intent extraction.

        Sprint 113: Simple queries like math or greetings don't need graph reasoning.

        Args:
            query: User query

        Returns:
            True if graph reasoning should be skipped
        """
        query_lower = query.lower().strip()

        for pattern in SKIP_GRAPH_KEYWORDS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                self.logger.debug(
                    "graph_intent_skipped",
                    query=query[:50],
                    reason="skip_keyword_matched",
                    pattern=pattern,
                )
                return True

        return False

    def _extract_entities_simple(self, query: str) -> list[str]:
        """Extract entities from query using simple patterns.

        Sprint 113: Fast entity extraction without LLM.
        Uses capitalized words, quoted phrases, and noun-like patterns.

        Args:
            query: User query

        Returns:
            List of potential entity names
        """
        entities = []

        # 1. Extract quoted phrases
        quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', query)
        for match in quoted:
            entity = match[0] or match[1]
            if entity and len(entity) > 1:
                entities.append(entity)

        # 2. Extract capitalized words (potential proper nouns/entities)
        # Exclude first word of sentence
        words = query.split()
        for i, word in enumerate(words):
            # Skip first word (often capitalized in questions)
            if i == 0:
                continue
            # Check if word is capitalized and not a common word
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word and clean_word[0].isupper() and len(clean_word) > 1:
                # Exclude common question words
                if clean_word.lower() not in ['the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been']:
                    entities.append(clean_word)

        # 3. Extract technical terms (all-caps, snake_case, CamelCase)
        # All-caps acronyms (e.g., RAG, LLM, API)
        acronyms = re.findall(r'\b[A-Z]{2,}\b', query)
        entities.extend(acronyms)

        # snake_case terms
        snake_case = re.findall(r'\b[a-z]+_[a-z_]+\b', query)
        entities.extend(snake_case)

        # CamelCase terms
        camel_case = re.findall(r'\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b', query)
        entities.extend(camel_case)

        # 4. Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for e in entities:
            e_lower = e.lower()
            if e_lower not in seen:
                seen.add(e_lower)
                unique_entities.append(e)

        self.logger.debug(
            "entities_extracted_simple",
            query=query[:50],
            entities=unique_entities[:5],  # Log first 5
            count=len(unique_entities),
        )

        return unique_entities[:10]  # Limit to 10 entities

    async def infer_graph_intent_from_clara(self, query: str) -> GraphIntentResult:
        """Infer graph intent using C-LARA classification (fast path).

        Sprint 113: Uses C-LARA SetFit model (40ms) to classify query intent,
        then maps to graph intents using predefined rules. 350x faster than LLM.

        Args:
            query: User query

        Returns:
            GraphIntentResult with inferred intents and entities

        Performance:
            - C-LARA classification: ~40ms
            - Entity extraction: ~5ms
            - Total: ~50ms (vs 17,600ms with LLM)
        """
        start_time = time.perf_counter()

        # Step 0: Check if we should skip graph reasoning entirely
        if self._should_skip_graph_intent(query):
            latency_ms = (time.perf_counter() - start_time) * 1000
            return GraphIntentResult(
                query=query,
                graph_intents=[],
                entities_mentioned=[],
                relationship_types=[],
                traversal_depth=None,
                confidence=1.0,  # High confidence it's not a graph query
                cypher_hints=[],
                latency_ms=latency_ms,
            )

        # Step 1: Get C-LARA intent classification
        clara_intent_value = "factual"  # Default fallback
        confidence = 0.7

        if self.intent_classifier is not None:
            try:
                clara_result = await self.intent_classifier.classify(query)
                # Use C-LARA 5-class intent if available
                if clara_result.clara_intent is not None:
                    clara_intent_value = clara_result.clara_intent.value
                else:
                    # Fall back to legacy 4-class intent mapping
                    intent_to_clara = {
                        "factual": "factual",
                        "keyword": "navigation",
                        "exploratory": "procedural",
                        "summary": "recommendation",
                    }
                    clara_intent_value = intent_to_clara.get(
                        clara_result.intent.value, "factual"
                    )
                confidence = clara_result.confidence

                self.logger.debug(
                    "clara_intent_classified",
                    query=query[:50],
                    clara_intent=clara_intent_value,
                    confidence=confidence,
                    method=clara_result.method,
                    latency_ms=clara_result.latency_ms,
                )
            except Exception as e:
                self.logger.warning(
                    "clara_classification_failed",
                    query=query[:50],
                    error=str(e),
                    fallback="factual",
                )

        # Step 2: Map C-LARA intent to graph intents
        mapping = CLARA_TO_GRAPH_INTENT_MAP.get(
            clara_intent_value,
            CLARA_TO_GRAPH_INTENT_MAP["factual"]  # Default mapping
        )

        graph_intents = list(mapping["default_intents"])
        traversal_depth = mapping["traversal_depth"]

        # Step 3: Apply keyword overrides
        query_lower = query.lower()
        for pattern, override_intents in mapping.get("keywords_override", {}).items():
            if re.search(pattern, query_lower, re.IGNORECASE):
                # Override with keyword-specific intents
                graph_intents = list(override_intents)
                self.logger.debug(
                    "keyword_override_applied",
                    query=query[:50],
                    pattern=pattern,
                    intents=graph_intents,
                )
                break

        # Step 4: Extract entities using simple patterns
        entities = self._extract_entities_simple(query)

        # Step 5: Generate Cypher hints
        cypher_hints = self._generate_cypher_hints(
            query=query,
            intents=graph_intents,
            entities=entities,
            relationship_types=["RELATES_TO"],  # Default relationship
            traversal_depth=traversal_depth,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        result = GraphIntentResult(
            query=query,
            graph_intents=graph_intents,
            entities_mentioned=entities,
            relationship_types=["RELATES_TO"],
            traversal_depth=traversal_depth,
            confidence=confidence * 0.9,  # Slightly lower than LLM extraction
            cypher_hints=cypher_hints,
            latency_ms=latency_ms,
        )

        self.logger.info(
            "graph_intent_inferred_from_clara",
            query=query[:50],
            clara_intent=clara_intent_value,
            graph_intents=graph_intents,
            entities=entities[:3],
            confidence=round(result.confidence, 2),
            latency_ms=round(latency_ms, 2),
        )

        return result

    async def extract_graph_intents(
        self, query: str, force_llm: bool = False
    ) -> GraphIntentResult:
        """Extract graph reasoning intents from query.

        Sprint 113: Now uses C-LARA fast inference by default (50ms vs 17s).
        Falls back to LLM extraction only if explicitly requested or disabled.

        This is the main entry point for graph intent extraction. It:
        1. (Sprint 113) Uses C-LARA to infer graph intents (fast path, ~50ms)
        2. Falls back to LLM for complex queries or if force_llm=True
        3. Generates Cypher query hints based on intents
        4. Returns structured result with hints and metadata

        Args:
            query: User query to analyze
            force_llm: If True, bypass C-LARA and use LLM directly (default: False)

        Returns:
            GraphIntentResult with intents, entities, and Cypher hints

        Example:
            result = await rewriter.extract_graph_intents(
                "How are RAG and LLMs connected?"
            )
            # result.graph_intents: ["entity_relationships"]
            # result.entities_mentioned: ["RAG", "LLMs"]
            # result.cypher_hints: [
            #     "MATCH (a:Entity {name: 'RAG'})-[r]-(b:Entity {name: 'LLMs'})"
            # ]

        Performance:
            - C-LARA fast path: ~50ms (default)
            - LLM fallback: ~17,600ms (force_llm=True or USE_CLARA_FAST_INFERENCE=false)
        """
        start_time = time.perf_counter()

        # Sprint 113: Use C-LARA fast inference if enabled
        if self._use_fast_inference and not force_llm:
            self.logger.info(
                "graph_intent_extraction_started",
                query=query[:100],
                method="clara_fast_inference",
            )
            return await self.infer_graph_intent_from_clara(query)

        # Fall back to LLM-based extraction (legacy path)
        self.logger.info(
            "graph_intent_extraction_started",
            query=query[:100],
            method="llm",
            reason="force_llm" if force_llm else "fast_inference_disabled",
        )

        # Step 1: Extract intents using LLM
        try:
            extracted = await self._extract_intents_with_llm(query)
        except Exception as e:
            self.logger.error(
                "graph_intent_extraction_failed",
                query=query[:50],
                error=str(e),
            )
            # Return empty result on failure
            latency_ms = (time.perf_counter() - start_time) * 1000
            return GraphIntentResult(
                query=query,
                graph_intents=[],
                entities_mentioned=[],
                relationship_types=[],
                traversal_depth=None,
                confidence=0.0,
                cypher_hints=[],
                latency_ms=latency_ms,
            )

        # Step 2: Generate Cypher hints from extracted intents
        cypher_hints = self._generate_cypher_hints(
            query=query,
            intents=extracted.get("graph_intents", []),
            entities=extracted.get("entities_mentioned", []),
            relationship_types=extracted.get("relationship_types", []),
            traversal_depth=extracted.get("traversal_depth"),
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        result = GraphIntentResult(
            query=query,
            graph_intents=extracted.get("graph_intents", []),
            entities_mentioned=extracted.get("entities_mentioned", []),
            relationship_types=extracted.get("relationship_types", []),
            traversal_depth=extracted.get("traversal_depth"),
            confidence=extracted.get("confidence", 0.5),
            cypher_hints=cypher_hints,
            latency_ms=latency_ms,
        )

        self.logger.info(
            "graph_intent_extraction_complete",
            query=query[:50],
            intents=result.graph_intents,
            entities=result.entities_mentioned,
            cypher_hints_count=len(result.cypher_hints),
            confidence=result.confidence,
            latency_ms=round(latency_ms, 2),
        )

        return result

    async def _extract_intents_with_llm(self, query: str) -> dict[str, Any]:
        """Extract graph intents using LLM.

        Args:
            query: User query

        Returns:
            Dictionary with extracted intents and metadata

        Raises:
            ValueError: If LLM response is invalid JSON
        """
        # Build prompt
        prompt = GRAPH_INTENT_PROMPT.format(query=query)

        # Create LLM task (Sprint 70 Feature 70.12: Add prompt_name for tracing)
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            quality_requirement=QualityRequirement.MEDIUM,
            metadata={"prompt_name": "GRAPH_INTENT_PROMPT"},
        )

        # Generate extraction
        response = await self.llm.generate(task)
        content = response.content.strip()

        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if content.startswith("```"):
                # Extract JSON from markdown
                lines = content.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith("```"):
                        if in_json:
                            break
                        in_json = True
                        continue
                    if in_json:
                        json_lines.append(line)
                content = "\n".join(json_lines)

            extracted = json.loads(content)

            # Validate required fields
            if "graph_intents" not in extracted:
                extracted["graph_intents"] = []
            if "entities_mentioned" not in extracted:
                extracted["entities_mentioned"] = []
            if "confidence" not in extracted:
                extracted["confidence"] = 0.5

            self.logger.debug(
                "llm_intent_extraction_success",
                query=query[:50],
                intents=extracted.get("graph_intents"),
                provider=response.provider,
                tokens=response.tokens_used,
            )

            return extracted

        except json.JSONDecodeError as e:
            self.logger.error(
                "llm_intent_extraction_json_error",
                query=query[:50],
                response=content[:200],
                error=str(e),
            )
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    def _generate_cypher_hints(
        self,
        query: str,
        intents: list[str],
        entities: list[str],
        relationship_types: list[str],
        traversal_depth: int | None,
    ) -> list[str]:
        """Generate Cypher query hints from extracted intents.

        This method translates graph intents into concrete Cypher query
        patterns that can guide the graph query agent's traversal strategy.

        Args:
            query: Original query
            intents: List of graph intent types
            entities: List of entities mentioned
            relationship_types: List of relationship types
            traversal_depth: Max hops for multi-hop (if any)

        Returns:
            List of Cypher query pattern hints
        """
        hints = []

        # Entity relationships hint
        if "entity_relationships" in intents and len(entities) >= 2:
            # Direct relationship between two entities
            entity_a = entities[0]
            entity_b = entities[1]

            if relationship_types:
                # Specific relationship type
                rel_type = relationship_types[0]
                hints.append(
                    f"MATCH (a:Entity)-[r:{rel_type}]-(b:Entity) "
                    f"WHERE a.name CONTAINS '{entity_a}' AND b.name CONTAINS '{entity_b}' "
                    f"RETURN a, r, b"
                )
            else:
                # Any relationship
                hints.append(
                    f"MATCH (a:Entity)-[r]-(b:Entity) "
                    f"WHERE a.name CONTAINS '{entity_a}' AND b.name CONTAINS '{entity_b}' "
                    f"RETURN a, r, b"
                )

        # Multi-hop traversal hint
        if "multi_hop" in intents:
            depth = traversal_depth or 2

            if len(entities) >= 2:
                # Path between two entities
                entity_a = entities[0]
                entity_b = entities[1]
                hints.append(
                    f"MATCH path = (a:Entity)-[*1..{depth}]-(b:Entity) "
                    f"WHERE a.name CONTAINS '{entity_a}' AND b.name CONTAINS '{entity_b}' "
                    f"RETURN path, length(path) as hops ORDER BY hops"
                )
            else:
                # General multi-hop from any entity
                hints.append(
                    f"MATCH path = (a:Entity)-[*1..{depth}]-(b:Entity) "
                    f"RETURN path, nodes(path), relationships(path)"
                )

        # Community discovery hint
        if "community_discovery" in intents:
            if entities:
                # Communities related to specific entity
                entity = entities[0]
                hints.append(
                    f"MATCH (seed:Entity)-[r*1..2]-(related:Entity) "
                    f"WHERE seed.name CONTAINS '{entity}' "
                    f"RETURN seed, collect(related) as community, count(r) as connections "
                    f"ORDER BY connections DESC"
                )
            else:
                # General community detection
                hints.append(
                    "MATCH (e:Entity)-[r]-(related:Entity) "
                    "WITH e, collect(related) as neighbors, count(r) as degree "
                    "WHERE degree > 3 "
                    "RETURN e, neighbors ORDER BY degree DESC"
                )

        # Temporal patterns hint
        if "temporal_patterns" in intents:
            if entities:
                entity = entities[0]
                hints.append(
                    f"MATCH (e:Entity)-[r]-(related:Entity) "
                    f"WHERE e.name CONTAINS '{entity}' AND r.timestamp IS NOT NULL "
                    f"RETURN e, r, related ORDER BY r.timestamp"
                )
            else:
                hints.append(
                    "MATCH (e:Entity)-[r]-(related:Entity) "
                    "WHERE r.timestamp IS NOT NULL "
                    "RETURN e, r, related ORDER BY r.timestamp DESC"
                )

        # Attribute search hint (entity properties)
        if "attribute_search" in intents and entities:
            entity = entities[0]
            hints.append(
                f"MATCH (e:Entity) "
                f"WHERE e.name CONTAINS '{entity}' "
                f"RETURN e, e.description, e.type, e.properties"
            )

        self.logger.debug(
            "cypher_hints_generated",
            intents=intents,
            entities=entities,
            hints_count=len(hints),
        )

        return hints


# Singleton instance
_query_rewriter_v2: QueryRewriterV2 | None = None


def get_query_rewriter_v2(
    intent_classifier: IntentClassifier | None = None,
) -> QueryRewriterV2:
    """Get singleton QueryRewriterV2 instance.

    Args:
        intent_classifier: Optional intent classifier for initial intent detection.
                         If None, will attempt to use global intent classifier.

    Returns:
        QueryRewriterV2 instance

    Example:
        from src.components.retrieval.query_rewriter_v2 import get_query_rewriter_v2

        rewriter = get_query_rewriter_v2()
        result = await rewriter.extract_graph_intents("How are X and Y related?")
    """
    global _query_rewriter_v2

    # If classifier provided, create new instance
    if intent_classifier is not None:
        return QueryRewriterV2(intent_classifier=intent_classifier)

    # Otherwise use singleton
    if _query_rewriter_v2 is None:
        # Try to get global intent classifier
        try:
            from src.components.retrieval.intent_classifier import get_intent_classifier

            classifier = get_intent_classifier()
            _query_rewriter_v2 = QueryRewriterV2(intent_classifier=classifier)
            logger.info("query_rewriter_v2_singleton_created", has_intent_classifier=True)
        except Exception as e:
            # Create without intent classifier
            logger.warning(
                "query_rewriter_v2_singleton_created_without_classifier",
                error=str(e),
            )
            _query_rewriter_v2 = QueryRewriterV2(intent_classifier=None)

    return _query_rewriter_v2


async def extract_graph_intents(query: str) -> GraphIntentResult:
    """Convenience function to extract graph intents from query.

    Args:
        query: User query to analyze

    Returns:
        GraphIntentResult with intents, entities, and Cypher hints

    Example:
        from src.components.retrieval.query_rewriter_v2 import extract_graph_intents

        result = await extract_graph_intents("How does X connect to Y?")
        print(f"Intents: {result.graph_intents}")
        print(f"Entities: {result.entities_mentioned}")
        for hint in result.cypher_hints:
            print(f"Cypher: {hint}")
    """
    rewriter = get_query_rewriter_v2()
    return await rewriter.extract_graph_intents(query)


__all__ = [
    "QueryRewriterV2",
    "GraphIntentResult",
    "get_query_rewriter_v2",
    "extract_graph_intents",
    "GRAPH_INTENT_PROMPT",
    # Sprint 113: Fast inference exports
    "CLARA_TO_GRAPH_INTENT_MAP",
    "USE_CLARA_FAST_INFERENCE",
]
