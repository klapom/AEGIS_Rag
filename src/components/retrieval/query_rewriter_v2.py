"""Query Rewriter v2 - Graph-Intent Extraction.

Sprint 69 Feature 69.5: Query Rewriter v2 - Graph-Intent Extraction (8 SP)

This module extends query rewriting with LLM-based graph intent extraction
to improve graph reasoning accuracy for complex queries. It identifies:
- Entity relationships that require graph traversal
- Multi-hop reasoning patterns
- Community discovery queries
- Temporal patterns in knowledge graphs

The extracted intents are used to generate Cypher query hints that guide
the graph query agent toward more targeted and accurate graph traversal.

Architecture:
    User Query → QueryRewriterV2 → GraphIntents + CypherHints → GraphQueryAgent

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
    - Latency: +80ms per extraction (LLM overhead)
    - Graph query accuracy: +25% on complex queries
    - Precision: >0.85 for intent classification

References:
    - Sprint 67 Feature 67.9: Query Rewriter v1
    - Sprint 69 Feature 69.5: Graph-Intent Extraction
    - ADR-040: RELATES_TO semantic relationships
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

from src.domains.llm_integration.models import LLMTask, QualityRequirement, TaskType
from src.domains.llm_integration.proxy import get_aegis_llm_proxy

if TYPE_CHECKING:
    from src.components.retrieval.intent_classifier import IntentClassifier

logger = structlog.get_logger(__name__)


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

        self.logger.info(
            "query_rewriter_v2_initialized",
            has_intent_classifier=intent_classifier is not None,
            temperature=self._temperature,
        )

    async def extract_graph_intents(self, query: str) -> GraphIntentResult:
        """Extract graph reasoning intents from query.

        This is the main entry point for graph intent extraction. It:
        1. Uses LLM to identify graph reasoning patterns
        2. Extracts entities and relationship types mentioned
        3. Generates Cypher query hints based on intents
        4. Returns structured result with hints and metadata

        Args:
            query: User query to analyze

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
        """
        start_time = time.perf_counter()

        self.logger.info(
            "graph_intent_extraction_started",
            query=query[:100],
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

        # Create LLM task
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            quality_requirement=QualityRequirement.MEDIUM,
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
]
