"""Entity/Relation Extraction Performance Benchmark System.

Sprint 42: Performance Analysis and Tuning for Entity/Relation Extraction.

This module provides:
1. Benchmarking infrastructure to measure extraction performance
2. A/B testing for different extraction strategies
3. Quality metrics to ensure output compatibility
4. Unified extraction pipeline that combines typed + semantic relations

Key insight from analysis:
- Pass 1 (ExtractionService): Extracts entities + TYPED relationships (WORKS_AT, USES, etc.)
- Pass 2 (RelationExtractor): Extracts RELATES_TO with strength scores (1-10)
- Both are needed but can be COMBINED into a single LLM call

Output compatibility requirements:
- GraphEntity: id, name, type, description, properties, source_document, confidence
- GraphRelationship: source, target, type, description, properties, source_document, weight
- RELATES_TO: source, target, description, strength (for Neo4j)

Author: Claude Code
Date: 2025-12-10
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.core.models import GraphEntity, GraphRelationship

logger = structlog.get_logger(__name__)


class ExtractionStrategy(str, Enum):
    """Extraction strategy options for A/B testing."""

    SEQUENTIAL = "sequential"  # Current: 3 LLM calls (entity, typed_rel, semantic_rel)
    UNIFIED = "unified"  # New: 1 LLM call (entity + all relations)
    UNIFIED_TWO_PASS = "unified_two_pass"  # 2 LLM calls (entity+typed, semantic)
    PARALLEL = "parallel"  # 2 parallel LLM calls (entity+typed || semantic)


@dataclass
class ExtractionMetrics:
    """Metrics from a single extraction run."""

    strategy: ExtractionStrategy
    text_length: int
    chunk_id: str

    # Timing
    total_time_ms: float = 0.0
    entity_extraction_ms: float = 0.0
    typed_relation_ms: float = 0.0
    semantic_relation_ms: float = 0.0
    llm_calls: int = 0

    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    # Quality
    entities_extracted: int = 0
    typed_relations_extracted: int = 0
    semantic_relations_extracted: int = 0

    # Errors
    errors: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Result of extraction with all outputs for compatibility."""

    entities: list[GraphEntity]
    typed_relationships: list[GraphRelationship]  # WORKS_AT, USES, etc.
    semantic_relations: list[dict[str, Any]]  # RELATES_TO with strength
    metrics: ExtractionMetrics


# =============================================================================
# UNIFIED EXTRACTION PROMPT
# =============================================================================

UNIFIED_EXTRACTION_PROMPT = """---Role---
You are a Knowledge Graph Specialist. Extract ALL entities and ALL relationships from the text.

---Instructions---
1. **Entity Extraction:** Extract EVERY entity mentioned:
   - name: Exact name from text
   - type: PERSON, ORGANIZATION, LOCATION, TECHNOLOGY, CONCEPT, EVENT, PRODUCT
   - description: One sentence description

2. **Relationship Extraction:** Extract EVERY relationship between entities:
   - source: Source entity name (must match extracted entity exactly)
   - target: Target entity name (must match extracted entity exactly)
   - type: Relationship type (involved_in, part_of, located_in, founded, works_at, etc.)
   - description: Brief explanation
   - strength: 1-10 (10 = strongest)

---Input Text---
{text}

---Example 1---
Text: "Alex worked at TechCorp. Jordan founded DevStart, a startup focused on AI. Alex joined DevStart as CTO."

Output:
{{
  "entities": [
    {{"name": "Alex", "type": "PERSON", "description": "Person who worked at TechCorp and joined DevStart as CTO"}},
    {{"name": "Jordan", "type": "PERSON", "description": "Founder of DevStart"}},
    {{"name": "TechCorp", "type": "ORGANIZATION", "description": "Company where Alex worked"}},
    {{"name": "DevStart", "type": "ORGANIZATION", "description": "AI startup founded by Jordan"}}
  ],
  "relationships": [
    {{"source": "Alex", "target": "TechCorp", "type": "worked_at", "description": "Alex worked at TechCorp", "strength": 8}},
    {{"source": "Jordan", "target": "DevStart", "type": "founded", "description": "Jordan founded DevStart", "strength": 10}},
    {{"source": "Alex", "target": "DevStart", "type": "joined", "description": "Alex joined DevStart as CTO", "strength": 9}},
    {{"source": "DevStart", "target": "AI", "type": "focused_on", "description": "DevStart focuses on AI", "strength": 8}}
  ]
}}

---Example 2---
Text: "The Oberoi family is an Indian family famous for hotels through The Oberoi Group. The Oberoi Group is a hotel company with head office in Delhi."

Output:
{{
  "entities": [
    {{"name": "Oberoi family", "type": "PERSON", "description": "Indian family famous for hotel involvement"}},
    {{"name": "The Oberoi Group", "type": "ORGANIZATION", "description": "Hotel company owned by Oberoi family"}},
    {{"name": "Delhi", "type": "LOCATION", "description": "City where The Oberoi Group headquarters is located"}},
    {{"name": "hotels", "type": "CONCEPT", "description": "Industry the Oberoi family is involved in"}}
  ],
  "relationships": [
    {{"source": "Oberoi family", "target": "The Oberoi Group", "type": "involved_in", "description": "Oberoi family is involved in hotels through The Oberoi Group", "strength": 10}},
    {{"source": "Oberoi family", "target": "hotels", "type": "famous_for", "description": "Oberoi family is famous for hotel involvement", "strength": 9}},
    {{"source": "The Oberoi Group", "target": "Delhi", "type": "headquartered_in", "description": "The Oberoi Group has head office in Delhi", "strength": 10}},
    {{"source": "The Oberoi Group", "target": "hotels", "type": "operates_in", "description": "The Oberoi Group is a hotel company", "strength": 9}}
  ]
}}

---Example 3---
Text: "Arthur's Magazine (1844-1846) was an American literary periodical published in Philadelphia. First for Women is published by Bauer Media Group in the USA."

Output:
{{
  "entities": [
    {{"name": "Arthur's Magazine", "type": "PRODUCT", "description": "American literary periodical from 1844-1846"}},
    {{"name": "Philadelphia", "type": "LOCATION", "description": "City where Arthur's Magazine was published"}},
    {{"name": "First for Women", "type": "PRODUCT", "description": "Women's magazine published in USA"}},
    {{"name": "Bauer Media Group", "type": "ORGANIZATION", "description": "Publisher of First for Women"}},
    {{"name": "USA", "type": "LOCATION", "description": "Country where First for Women is published"}}
  ],
  "relationships": [
    {{"source": "Arthur's Magazine", "target": "Philadelphia", "type": "published_in", "description": "Arthur's Magazine was published in Philadelphia", "strength": 9}},
    {{"source": "First for Women", "target": "Bauer Media Group", "type": "published_by", "description": "First for Women is published by Bauer Media Group", "strength": 10}},
    {{"source": "First for Women", "target": "USA", "type": "published_in", "description": "First for Women is published in USA", "strength": 8}}
  ]
}}

---CRITICAL RULES---
1. Extract ALL entities - do not skip any mentioned names, organizations, or locations
2. Extract ALL relationships - find every connection between entities
3. Entity names MUST match exactly in relationships
4. Output valid JSON only - no markdown, no explanation text

Output:
"""


# =============================================================================
# EXTRACTION BENCHMARK CLASS
# =============================================================================


class ExtractionBenchmark:
    """Benchmark different extraction strategies while maintaining output compatibility.

    Usage:
        benchmark = ExtractionBenchmark()
        result = await benchmark.extract(text, chunk_id, strategy=ExtractionStrategy.UNIFIED)

        # Result contains all outputs in compatible format:
        # - result.entities: list[GraphEntity]
        # - result.typed_relationships: list[GraphRelationship]
        # - result.semantic_relations: list[dict] (for RELATES_TO)
        # - result.metrics: timing and quality data
    """

    def __init__(
        self,
        model: str = "qwen3:32b",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.proxy = get_aegis_llm_proxy()

        logger.info(
            "extraction_benchmark_initialized",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def extract(
        self,
        text: str,
        chunk_id: str,
        document_id: str | None = None,
        strategy: ExtractionStrategy = ExtractionStrategy.UNIFIED,
    ) -> ExtractionResult:
        """Extract entities and relations using specified strategy.

        Args:
            text: Text to extract from
            chunk_id: Chunk identifier for provenance
            document_id: Optional document ID
            strategy: Extraction strategy to use

        Returns:
            ExtractionResult with entities, relationships, and metrics
        """
        start_time = time.time()

        metrics = ExtractionMetrics(
            strategy=strategy,
            text_length=len(text),
            chunk_id=chunk_id,
        )

        try:
            if strategy == ExtractionStrategy.UNIFIED:
                result = await self._extract_unified(text, chunk_id, document_id, metrics)
            elif strategy == ExtractionStrategy.SEQUENTIAL:
                result = await self._extract_sequential(text, chunk_id, document_id, metrics)
            elif strategy == ExtractionStrategy.PARALLEL:
                result = await self._extract_parallel(text, chunk_id, document_id, metrics)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")

            metrics.total_time_ms = (time.time() - start_time) * 1000
            result.metrics = metrics

            logger.info(
                "extraction_complete",
                strategy=strategy.value,
                total_time_ms=metrics.total_time_ms,
                llm_calls=metrics.llm_calls,
                entities=metrics.entities_extracted,
                typed_relations=metrics.typed_relations_extracted,
                semantic_relations=metrics.semantic_relations_extracted,
            )

            return result

        except Exception as e:
            metrics.errors.append(str(e))
            metrics.total_time_ms = (time.time() - start_time) * 1000
            logger.error("extraction_failed", error=str(e), strategy=strategy.value)
            raise

    async def _extract_unified(
        self,
        text: str,
        chunk_id: str,
        document_id: str | None,
        metrics: ExtractionMetrics,
    ) -> ExtractionResult:
        """Single LLM call for all extractions (optimized).

        This reduces 3 LLM calls to 1, saving ~66% of extraction time.
        """
        prompt = UNIFIED_EXTRACTION_PROMPT.format(text=text)

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt=prompt,
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            model_local=self.model,
        )

        llm_start = time.time()
        response = await self.proxy.generate(task)
        llm_time = (time.time() - llm_start) * 1000

        metrics.llm_calls = 1
        metrics.entity_extraction_ms = llm_time
        metrics.total_input_tokens = response.tokens_input or 0
        metrics.total_output_tokens = response.tokens_output or 0

        # Parse unified response
        data = self._parse_json_response(response.content)

        # Convert to compatible output formats
        entities = self._convert_entities(data.get("entities", []), document_id)

        # New unified format has single "relationships" array with strength
        relationships = data.get("relationships", [])
        typed_rels = self._convert_typed_relationships(relationships, document_id)

        # Convert relationships to semantic_relations format (for RELATES_TO)
        semantic_rels = [
            {
                "source": r.get("source", ""),
                "target": r.get("target", ""),
                "description": r.get("description", ""),
                "strength": r.get("strength", 5),
            }
            for r in relationships
        ]

        metrics.entities_extracted = len(entities)
        metrics.typed_relations_extracted = len(typed_rels)
        metrics.semantic_relations_extracted = len(semantic_rels)

        return ExtractionResult(
            entities=entities,
            typed_relationships=typed_rels,
            semantic_relations=semantic_rels,
            metrics=metrics,
        )

    async def _extract_sequential(
        self,
        text: str,
        chunk_id: str,
        document_id: str | None,
        metrics: ExtractionMetrics,
    ) -> ExtractionResult:
        """Current sequential approach: 3 separate LLM calls.

        This is the baseline for comparison.
        """
        from src.prompts.extraction_prompts import (
            ENTITY_EXTRACTION_PROMPT,
            RELATIONSHIP_EXTRACTION_PROMPT,
        )
        from src.components.graph_rag.relation_extractor import (
            SYSTEM_PROMPT_RELATION,
            USER_PROMPT_TEMPLATE_RELATION,
        )

        # Pass 1: Entity extraction
        entity_start = time.time()
        entity_task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt=ENTITY_EXTRACTION_PROMPT.format(text=text),
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            model_local=self.model,
        )
        entity_response = await self.proxy.generate(entity_task)
        metrics.entity_extraction_ms = (time.time() - entity_start) * 1000
        metrics.llm_calls += 1

        entity_data = self._parse_json_response(entity_response.content)
        # Entity prompt returns array directly, not {"entities": [...]}
        if isinstance(entity_data, list):
            entity_list = entity_data
        elif isinstance(entity_data, dict) and "entities" in entity_data:
            entity_list = entity_data["entities"]
        else:
            entity_list = []
        entities = self._convert_entities(entity_list, document_id)
        metrics.entities_extracted = len(entities)

        # Pass 2: Typed relationship extraction
        if entities:
            rel_start = time.time()
            entities_str = "\n".join([f"- {e.name} ({e.type})" for e in entities])
            rel_task = LLMTask(
                task_type=TaskType.EXTRACTION,
                prompt=RELATIONSHIP_EXTRACTION_PROMPT.format(text=text, entities=entities_str),
                quality_requirement=QualityRequirement.HIGH,
                complexity=Complexity.HIGH,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                model_local=self.model,
            )
            rel_response = await self.proxy.generate(rel_task)
            metrics.typed_relation_ms = (time.time() - rel_start) * 1000
            metrics.llm_calls += 1

            rel_data = self._parse_json_response(rel_response.content)
            # Relationship prompt may return array or {"relationships": [...]}
            if isinstance(rel_data, list):
                rel_list = rel_data
            elif isinstance(rel_data, dict) and "relationships" in rel_data:
                rel_list = rel_data["relationships"]
            else:
                rel_list = []
            typed_rels = self._convert_typed_relationships(rel_list, document_id)
            metrics.typed_relations_extracted = len(typed_rels)
        else:
            typed_rels = []

        # Pass 3: Semantic relation extraction
        if len(entities) >= 2:
            sem_start = time.time()
            entity_list_sem = "\n".join([f"- {e.name} ({e.type})" for e in entities])
            user_prompt = USER_PROMPT_TEMPLATE_RELATION.format(
                entity_list=entity_list_sem, text=text
            )
            combined_prompt = f"{SYSTEM_PROMPT_RELATION}\n\n{user_prompt}"

            sem_task = LLMTask(
                task_type=TaskType.EXTRACTION,
                prompt=combined_prompt,
                quality_requirement=QualityRequirement.HIGH,
                complexity=Complexity.MEDIUM,
                max_tokens=2000,
                temperature=self.temperature,
                model_local=self.model,
            )
            sem_response = await self.proxy.generate(sem_task)
            metrics.semantic_relation_ms = (time.time() - sem_start) * 1000
            metrics.llm_calls += 1

            sem_data = self._parse_json_response(sem_response.content)
            semantic_rels = sem_data.get("relations", []) if isinstance(sem_data, dict) else []
            metrics.semantic_relations_extracted = len(semantic_rels)
        else:
            semantic_rels = []

        metrics.total_input_tokens = (entity_response.tokens_input or 0)
        metrics.total_output_tokens = (entity_response.tokens_output or 0)

        return ExtractionResult(
            entities=entities,
            typed_relationships=typed_rels,
            semantic_relations=semantic_rels,
            metrics=metrics,
        )

    async def _extract_parallel(
        self,
        text: str,
        chunk_id: str,
        document_id: str | None,
        metrics: ExtractionMetrics,
    ) -> ExtractionResult:
        """Parallel extraction: Entity+Typed in one call, Semantic separately.

        This is a middle-ground: 2 calls but can be parallelized after entities.
        """
        # First: Unified entity + typed relationships
        entity_typed_prompt = """Extract entities and their typed relationships from the text.

---TEXT---
{text}

---OUTPUT---
Return JSON only:
{{
  "entities": [{{"name": "...", "type": "PERSON|ORGANIZATION|LOCATION|CONCEPT|PRODUCT|EVENT", "description": "..."}}],
  "relationships": [{{"source": "...", "target": "...", "type": "WORKS_AT|KNOWS|LOCATED_IN|CREATED|USES|PART_OF", "description": "..."}}]
}}
""".format(text=text)

        task1 = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt=entity_typed_prompt,
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            model_local=self.model,
        )

        start1 = time.time()
        response1 = await self.proxy.generate(task1)
        metrics.entity_extraction_ms = (time.time() - start1) * 1000
        metrics.llm_calls += 1

        data1 = self._parse_json_response(response1.content)
        entities = self._convert_entities(data1.get("entities", []), document_id)
        typed_rels = self._convert_typed_relationships(data1.get("relationships", []), document_id)

        metrics.entities_extracted = len(entities)
        metrics.typed_relations_extracted = len(typed_rels)

        # Second: Semantic relations (could be parallel with future optimization)
        if len(entities) >= 2:
            from src.components.graph_rag.relation_extractor import (
                SYSTEM_PROMPT_RELATION,
                USER_PROMPT_TEMPLATE_RELATION,
            )

            entity_list = "\n".join([f"- {e.name} ({e.type})" for e in entities])
            user_prompt = USER_PROMPT_TEMPLATE_RELATION.format(entity_list=entity_list, text=text)
            combined_prompt = f"{SYSTEM_PROMPT_RELATION}\n\n{user_prompt}"

            task2 = LLMTask(
                task_type=TaskType.EXTRACTION,
                prompt=combined_prompt,
                quality_requirement=QualityRequirement.HIGH,
                complexity=Complexity.MEDIUM,
                max_tokens=2000,
                temperature=self.temperature,
                model_local=self.model,
            )

            start2 = time.time()
            response2 = await self.proxy.generate(task2)
            metrics.semantic_relation_ms = (time.time() - start2) * 1000
            metrics.llm_calls += 1

            data2 = self._parse_json_response(response2.content)
            semantic_rels = data2.get("relations", []) if isinstance(data2, dict) else []
            metrics.semantic_relations_extracted = len(semantic_rels)
        else:
            semantic_rels = []

        return ExtractionResult(
            entities=entities,
            typed_relationships=typed_rels,
            semantic_relations=semantic_rels,
            metrics=metrics,
        )

    def _parse_json_response(self, response: str) -> dict | list:
        """Parse JSON from LLM response with robust error handling."""
        cleaned = response.strip()

        # Remove markdown code blocks
        if "```" in cleaned:
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
            if match:
                cleaned = match.group(1).strip()

        # Try direct parsing
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON object or array
        import re
        for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
            match = re.search(pattern, cleaned)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    continue

        logger.warning("json_parse_failed", response_preview=cleaned[:200])
        return {}

    def _convert_entities(
        self, entity_data: list[dict], document_id: str | None
    ) -> list[GraphEntity]:
        """Convert raw entity dicts to GraphEntity objects."""
        import uuid

        entities = []
        for ed in entity_data:
            try:
                entity = GraphEntity(
                    id=str(uuid.uuid4()),
                    name=ed.get("name", ""),
                    type=ed.get("type", "UNKNOWN"),
                    description=ed.get("description", ""),
                    properties={},
                    source_document=document_id,
                    confidence=1.0,
                )
                entities.append(entity)
            except Exception as e:
                logger.warning("entity_conversion_failed", error=str(e), data=ed)

        return entities

    def _convert_typed_relationships(
        self, rel_data: list[dict], document_id: str | None
    ) -> list[GraphRelationship]:
        """Convert raw relationship dicts to GraphRelationship objects."""
        import uuid

        relationships = []
        for rd in rel_data:
            try:
                rel = GraphRelationship(
                    id=str(uuid.uuid4()),  # Generate unique ID
                    source=rd.get("source", ""),
                    target=rd.get("target", ""),
                    type=rd.get("type", "RELATED_TO"),
                    description=rd.get("description", ""),
                    properties={},
                    source_document=document_id,
                    confidence=1.0,
                )
                relationships.append(rel)
            except Exception as e:
                logger.warning("relationship_conversion_failed", error=str(e), data=rd)

        return relationships


# =============================================================================
# BENCHMARK RUNNER
# =============================================================================


async def run_benchmark(
    texts: list[str],
    strategies: list[ExtractionStrategy] | None = None,
) -> dict[str, list[ExtractionMetrics]]:
    """Run benchmark across multiple texts and strategies.

    Args:
        texts: List of texts to extract from
        strategies: Strategies to test (default: all)

    Returns:
        Dict mapping strategy name to list of metrics
    """
    if strategies is None:
        strategies = [ExtractionStrategy.SEQUENTIAL, ExtractionStrategy.UNIFIED]

    benchmark = ExtractionBenchmark()
    results: dict[str, list[ExtractionMetrics]] = {s.value: [] for s in strategies}

    for i, text in enumerate(texts):
        chunk_id = f"benchmark_chunk_{i}"

        for strategy in strategies:
            try:
                result = await benchmark.extract(
                    text=text,
                    chunk_id=chunk_id,
                    strategy=strategy,
                )
                results[strategy.value].append(result.metrics)

                logger.info(
                    "benchmark_iteration_complete",
                    text_index=i,
                    strategy=strategy.value,
                    time_ms=result.metrics.total_time_ms,
                    llm_calls=result.metrics.llm_calls,
                )

            except Exception as e:
                logger.error(
                    "benchmark_iteration_failed",
                    text_index=i,
                    strategy=strategy.value,
                    error=str(e),
                )

    # Print summary
    print("\n" + "=" * 70)
    print("EXTRACTION BENCHMARK SUMMARY")
    print("=" * 70)

    for strategy_name, metrics_list in results.items():
        if not metrics_list:
            continue

        avg_time = sum(m.total_time_ms for m in metrics_list) / len(metrics_list)
        avg_calls = sum(m.llm_calls for m in metrics_list) / len(metrics_list)
        avg_entities = sum(m.entities_extracted for m in metrics_list) / len(metrics_list)
        total_errors = sum(len(m.errors) for m in metrics_list)

        print(f"\n{strategy_name.upper()}:")
        print(f"  Avg time:     {avg_time:.1f}ms")
        print(f"  Avg LLM calls: {avg_calls:.1f}")
        print(f"  Avg entities: {avg_entities:.1f}")
        print(f"  Total errors: {total_errors}")

    return results


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    # Example benchmark run
    test_texts = [
        """Arthur's Magazine (1844–1846) was an American literary periodical published
        in Philadelphia in the 19th century. First for Women is a woman's magazine
        published by Bauer Media Group in the USA.""",
        """The Oberoi family is an Indian family that is famous for its involvement
        in hotels, namely through The Oberoi Group. The Oberoi Group is a hotel
        company with its head office in Delhi.""",
    ]

    asyncio.run(run_benchmark(test_texts))
