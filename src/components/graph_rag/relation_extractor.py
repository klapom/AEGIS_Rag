"""Relation Extractor for Graph RAG with Multi-Cloud LLM Support.

Sprint 13 Feature 13.9: ADR-018 - Initial implementation with Gemma 3 4B
Sprint 14 Feature 14.5: Added retry logic and error handling
Sprint 23 Feature 23.6: AegisLLMProxy Integration
Sprint 124: Configurable model via LIGHTRAG_LLM_MODEL env var (no hardcoding)
Migrated from Ollama Client to multi-cloud LLM proxy (Local → Alibaba Cloud → OpenAI).
Default model: Uses LIGHTRAG_LLM_MODEL env var, fallback to nemotron-3-nano.

Author: Claude Code
Date: 2025-10-24, Updated: 2026-02-05
"""

import json
import os
import re
from typing import Any

import structlog
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import (
    Complexity,
    DataClassification,
    LLMTask,
    QualityRequirement,
    TaskType,
)

logger = structlog.get_logger(__name__)

# ============================================================================
# PROMPTS (from benchmarking)
# ============================================================================

SYSTEM_PROMPT_RELATION = """---Role---
You are an intelligent assistant that identifies relationships between entities in a text document.

---Goal---
Given a text document and a list of entities found in that text, identify all relationships among the entities.

---Steps---
1. Review the provided entity list.
2. From the entities in the list, identify all pairs of (source, target) that are *clearly related* to each other in the text.
3. For each pair of related entities, extract the following information:
   - source: name of the source entity (must match an entity from the provided list)
   - target: name of the target entity (must match an entity from the provided list)
   - type: the relationship type from this list: USES, CREATES, PART_OF, LOCATED_IN, WORKS_FOR, ASSOCIATED_WITH, DERIVED_FROM, INFLUENCES, CONTAINS, MEASURES, FUNDED_BY, AUTHORED_BY, MANAGES, DEPENDS_ON, PRODUCES, COMPETES_WITH, REGULATES, SUPPORTS, TEACHES, PRECEDED_BY, RELATED_TO
   - description: Explanation as to why the source entity and target entity are related
   - strength: A numeric score (1-10) indicating strength of the relationship

4. Return output as valid JSON with array: "relations".

---Output Requirements---
Output valid JSON only. No markdown formatting, no code blocks, just pure JSON.
Format: {"relations": [...]}"""

USER_PROMPT_TEMPLATE_RELATION = """---Task---
Extract relationships between the provided entities based on the input text.

######################
-Entity list-
######################
{entity_list}

######################
-Input Text-
######################
{text}

######################
-Example-
######################
If entity list contains ["Alex", "Jordan", "TechCorp"] and text says "Alex and Jordan worked at TechCorp together", output:
{{
  "relations": [
    {{"source": "Alex", "target": "TechCorp", "type": "WORKS_FOR", "description": "Alex worked at TechCorp.", "strength": 8}},
    {{"source": "Jordan", "target": "TechCorp", "type": "WORKS_FOR", "description": "Jordan worked at TechCorp.", "strength": 8}},
    {{"source": "Alex", "target": "Jordan", "type": "ASSOCIATED_WITH", "description": "Alex and Jordan worked together.", "strength": 7}}
  ]
}}

######################
Output (valid JSON only):
"""


class RelationExtractor:
    """Extract relations between entities using multi-cloud LLM routing.

    Uses AegisLLMProxy for intelligent routing across providers:
    - Local: Gemma 3 4B Q4_K_M (default, free)
    - Alibaba Cloud: Qwen models (medium complexity)
    - OpenAI: GPT-4o (critical quality + high complexity)

    Operates on a pre-defined entity list to ensure all relations
    reference valid entities.

    Architecture Decision: ADR-018 (Model Selection), ADR-033 (Multi-Cloud Routing)
    Performance: ~13-16s per document (200-300 words) local
    Quality: 123% relation accuracy (exceeds targets)

    Example:
        >>> extractor = RelationExtractor()
        >>> entities = [
        ...     {"name": "Alex", "type": "PERSON"},
        ...     {"name": "TechCorp", "type": "ORGANIZATION"}
        ... ]
        >>> relations = await extractor.extract(text, entities)
        >>> relations
        [{"source": "Alex", "target": "TechCorp", "description": "...", "strength": 8}]
    """

    def __init__(
        self,
        model: str | None = None,  # Sprint 124: Read from LIGHTRAG_LLM_MODEL env var
        temperature: float = 0.1,
        num_predict: int = 8192,
        num_ctx: int = 32768,
        max_retries: int = 3,
        retry_min_wait: float = 2.0,
        retry_max_wait: float = 10.0,
    ) -> None:
        """Initialize relation extractor with configurable model.

        Sprint 124: Model is now configurable via LIGHTRAG_LLM_MODEL env var.
        This ensures RelationExtractor uses the same model as entity extraction.

        Args:
            model: Preferred local model name. If None, reads from LIGHTRAG_LLM_MODEL
                  env var, falling back to 'nemotron-3-nano' if not set.
            temperature: LLM temperature (0.0-1.0, lower = more deterministic)
            num_predict: Max tokens to generate
            num_ctx: Context window size
            max_retries: Max retry attempts for transient failures (Sprint 14)
            retry_min_wait: Min wait time between retries in seconds (Sprint 14)
            retry_max_wait: Max wait time between retries in seconds (Sprint 14)
        """
        # Sprint 124: Use LIGHTRAG_LLM_MODEL env var for consistency with entity extraction
        if model is None:
            model = os.environ.get("LIGHTRAG_LLM_MODEL", "nemotron-3-nano")
        self.model = model
        # Sprint 23: Use AegisLLMProxy instead of direct Ollama client
        self.proxy = get_aegis_llm_proxy()
        self.temperature = temperature
        self.num_predict = num_predict
        self.num_ctx = num_ctx
        self.max_retries = max_retries
        self.retry_min_wait = retry_min_wait
        self.retry_max_wait = retry_max_wait

        # Sprint 124: Log model source for debugging
        model_source = "LIGHTRAG_LLM_MODEL env" if os.environ.get("LIGHTRAG_LLM_MODEL") else "default"
        logger.info(
            "relation_extractor_initialized",
            model=model,
            model_source=model_source,
            temperature=temperature,
            num_predict=num_predict,
            num_ctx=num_ctx,
            max_retries=max_retries,
            retry_config=f"{retry_min_wait}-{retry_max_wait}s",
            proxy="AegisLLMProxy",
        )

    async def extract(self, text: str, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract relations between entities from text.

        Sprint 14: Added automatic retry logic for transient failures.

        Args:
            text: Source text containing entities
            entities: list of entities with 'name' key
                     (from Phase 1 SpaCy NER + Phase 2 Deduplication)

        Returns:
            list of relation dicts with keys:
            - source (str): Source entity name
            - target (str): Target entity name
            - description (str): Why they are related
            - strength (int): Relationship strength (1-10)

        Example:
            >>> extractor = GemmaRelationExtractor()
            >>> entities = [{"name": "Alex"}, {"name": "Jordan"}, {"name": "TechCorp"}]
            >>> text = "Alex and Jordan worked at TechCorp together."
            >>> relations = await extractor.extract(text, entities)
            >>> len(relations)
            3
        """
        if not entities:
            logger.warning("relation_extraction_skipped", reason="no_entities")
            return []

        # Format entity list for prompt
        entity_names = [e["name"] for e in entities]
        entity_list_str = ", ".join(entity_names)

        # Build prompt
        user_prompt = USER_PROMPT_TEMPLATE_RELATION.format(entity_list=entity_list_str, text=text)

        # Call LLM with retry logic (Sprint 14)
        try:
            relations = await self._extract_with_retry(user_prompt, text, entities)

            logger.info(
                "relation_extraction_complete",
                text_length=len(text),
                entity_count=len(entities),
                relations_found=len(relations),
            )

            return relations

        except Exception as e:
            # All retries exhausted - graceful degradation
            logger.error(
                "relation_extraction_failed_all_retries",
                error=str(e),
                text_length=len(text),
                entity_count=len(entities),
                max_retries=self.max_retries,
                note="Returning empty relations list (graceful degradation)",
            )
            return []

    async def _extract_with_retry(
        self, user_prompt: str, text: str, entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Call Gemma LLM with automatic retry on transient failures.

        Sprint 14 Feature 14.5: Retry Logic

        Retries on:
        - ConnectionError (Ollama server unreachable)
        - TimeoutError (Request timeout)
        - General exceptions (with backoff)

        Args:
            user_prompt: Formatted prompt for LLM
            text: Source text
            entities: Entity list

        Returns:
            list of extracted relations

        Raises:
            Exception: If all retries exhausted
        """

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=self.retry_min_wait, max=self.retry_max_wait),
            retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
            before_sleep=before_sleep_log(logger, "WARNING"),
            reraise=True,
        )
        async def _call_llm() -> None:
            """Inner function with retry decorator."""
            # Sprint 23: Use AegisLLMProxy with combined system + user prompt
            combined_prompt = f"{SYSTEM_PROMPT_RELATION}\n\n{user_prompt}"

            # Sprint 124: Use CONFIDENTIAL to force local-only execution (no cloud fallbacks)
            task = LLMTask(
                task_type=TaskType.EXTRACTION,
                prompt=combined_prompt,
                data_classification=DataClassification.CONFIDENTIAL,  # Force local only
                quality_requirement=QualityRequirement.HIGH,
                complexity=Complexity.MEDIUM,
                temperature=self.temperature,
                max_tokens=self.num_predict,
                model_local=self.model,
            )

            response = await self.proxy.generate(task)

            # Parse JSON response
            content = response.content
            relation_data = self._parse_json_response(content)
            return relation_data.get("relations", [])  # type: ignore[no-any-return]

        return await _call_llm()

    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON response from LLM, handling markdown and errors.

        Args:
            response: Raw LLM response (may contain markdown)

        Returns:
            Parsed JSON dict or empty structure on failure
        """
        cleaned = response.strip()

        # Remove markdown code blocks
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        # Try direct parsing
        try:
            return json.loads(cleaned)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            # Try to extract JSON from text (regex fallback)
            json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))  # type: ignore[no-any-return]
                except json.JSONDecodeError:
                    pass

            logger.warning("relation_json_parse_failed", response_preview=cleaned[:200])
            return {"relations": []}

    async def extract_with_gleaning(
        self,
        text: str,
        entities: list[dict[str, Any]],
        gleaning_steps: int = 1,
    ) -> list[dict[str, Any]]:
        """Extract relations with multi-pass gleaning for improved ER ratio.

        Sprint 85 Feature 85.8: Relationship Gleaning for ER Ratio >= 1.0.

        Similar to entity gleaning (Microsoft GraphRAG), this method:
        1. Initial extraction of relationships
        2. Completeness check using LLM
        3. If incomplete, extract missing relationships
        4. Merge and deduplicate all relationships

        Args:
            text: Source text containing entities
            entities: List of entities with 'name' key
            gleaning_steps: Number of gleaning rounds (0=disabled, 1-2 recommended)

        Returns:
            List of relation dicts (deduplicated)
        """
        if not entities or len(entities) < 2:
            logger.warning("relation_gleaning_skipped", reason="insufficient_entities")
            return []

        # Initial extraction
        logger.info(
            "relation_gleaning_round_1_start",
            entity_count=len(entities),
            gleaning_steps=gleaning_steps,
        )
        all_relations = await self.extract(text, entities)
        logger.info(
            "relation_gleaning_round_1_complete",
            relations_found=len(all_relations),
        )

        # If gleaning disabled, return initial results
        if gleaning_steps == 0:
            return all_relations

        # Gleaning rounds
        for gleaning_round in range(1, gleaning_steps + 1):
            logger.info(
                f"relation_gleaning_round_{gleaning_round + 1}_start",
                current_relations=len(all_relations),
            )

            # Check completeness
            is_incomplete = await self._check_completeness(text, entities, all_relations)

            if not is_incomplete:
                logger.info(
                    "relation_gleaning_complete_early",
                    round=gleaning_round + 1,
                    total_relations=len(all_relations),
                )
                break

            # Extract missing relationships
            new_relations = await self._extract_missing(text, entities, all_relations)

            if new_relations:
                all_relations.extend(new_relations)
                logger.info(
                    f"relation_gleaning_round_{gleaning_round + 1}_complete",
                    new_relations=len(new_relations),
                    total_relations=len(all_relations),
                )
            else:
                logger.info(
                    f"relation_gleaning_round_{gleaning_round + 1}_no_new",
                )
                break

        # Calculate ER ratio
        er_ratio = len(all_relations) / len(entities) if entities else 0.0

        logger.info(
            "relation_gleaning_complete",
            total_relations=len(all_relations),
            entity_count=len(entities),
            er_ratio=round(er_ratio, 2),
        )

        return all_relations

    async def _check_completeness(
        self,
        text: str,
        entities: list[dict[str, Any]],
        relations: list[dict[str, Any]],
    ) -> bool:
        """Check if relationship extraction is complete.

        Args:
            text: Source text
            entities: Entity list
            relations: Current relations

        Returns:
            True if INCOMPLETE (need more), False if complete
        """
        # Format relations for prompt
        rel_strs = []
        for rel in relations:
            rel_strs.append(f"{rel.get('source', '?')} --[RELATES_TO]--> {rel.get('target', '?')}")
        relationship_list = "\n".join(rel_strs) if rel_strs else "(no relationships extracted yet)"

        # Format entities for prompt
        entity_strs = [f"- {e['name']}" for e in entities]
        entity_list = "\n".join(entity_strs)

        prompt = f"""You have extracted the following relationships:
{relationship_list}

From entities:
{entity_list}

Text (excerpt):
{text[:2000]}

Are there any significant RELATIONSHIPS between the entities that were MISSED?
Answer with ONLY "YES" or "NO".

Answer:"""

        try:
            # Sprint 124: Use CONFIDENTIAL for local-only execution
            task = LLMTask(
                task_type=TaskType.GENERATION,  # Sprint 85 Fix: Use GENERATION for yes/no
                prompt=prompt,
                data_classification=DataClassification.CONFIDENTIAL,  # Force local only
                complexity=Complexity.LOW,
                quality_requirement=QualityRequirement.LOW,  # Sprint 85 Hotfix: STANDARD doesn't exist
                temperature=0.1,
                max_tokens=10,
                model_local=self.model,
            )
            response = await self.proxy.generate(task)
            result = response.content.strip().upper() if response.content else ""

            if result.startswith("YES"):
                return True  # Incomplete
            return False  # Complete

        except Exception as e:
            logger.warning("relation_completeness_check_failed", error=str(e))
            return True  # Assume incomplete on error

    async def _extract_missing(
        self,
        text: str,
        entities: list[dict[str, Any]],
        existing_relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract relationships that were missed.

        Args:
            text: Source text
            entities: Entity list
            existing_relations: Already extracted relations

        Returns:
            List of new relations (excluding duplicates)
        """
        # Format existing relations
        rel_strs = []
        for rel in existing_relations:
            rel_strs.append(f'- {rel.get("source", "?")} -> {rel.get("target", "?")}')
        existing_list = "\n".join(rel_strs) if rel_strs else "(none)"

        # Format entities
        entity_names = [e["name"] for e in entities]
        entity_list_str = ", ".join(entity_names)

        prompt = f"""{SYSTEM_PROMPT_RELATION}

Previously extracted relationships:
{existing_list}

Entity list: {entity_list_str}

Text:
{text[:2000]}

IMPORTANT: Extract ONLY relationships that were MISSED above.
Do NOT repeat already extracted relationships.
Focus on CAUSAL, HIERARCHICAL, and SEMANTIC relationships.

Output (valid JSON only):"""

        try:
            # Sprint 124: Use CONFIDENTIAL for local-only execution
            task = LLMTask(
                task_type=TaskType.EXTRACTION,
                prompt=prompt,
                data_classification=DataClassification.CONFIDENTIAL,  # Force local only
                complexity=Complexity.MEDIUM,
                quality_requirement=QualityRequirement.HIGH,
                temperature=self.temperature,
                max_tokens=self.num_predict,
                model_local=self.model,
            )
            response = await self.proxy.generate(task)

            # Parse response
            relation_data = self._parse_json_response(response.content)
            new_relations = relation_data.get("relations", [])

            # Deduplicate against existing
            existing_pairs = {
                (r.get("source", "").lower(), r.get("target", "").lower())
                for r in existing_relations
            }

            unique_relations = []
            for rel in new_relations:
                pair = (rel.get("source", "").lower(), rel.get("target", "").lower())
                if pair not in existing_pairs:
                    unique_relations.append(rel)
                    existing_pairs.add(pair)

            return unique_relations

        except Exception as e:
            logger.warning("relation_continuation_failed", error=str(e))
            return []


def create_relation_extractor_from_config(config) -> RelationExtractor:
    """Factory function to create relation extractor from app config.

    Args:
        config: Application config object with attributes:
               - GEMMA_MODEL (str): Preferred local model name
               - GEMMA_TEMPERATURE (float): LLM temperature
               - GEMMA_NUM_PREDICT (int): Max tokens
               - GEMMA_NUM_CTX (int): Context window
               - EXTRACTION_MAX_RETRIES (int): Max retries (Sprint 14)
               - EXTRACTION_RETRY_MIN_WAIT (float): Min retry wait (Sprint 14)
               - EXTRACTION_RETRY_MAX_WAIT (float): Max retry wait (Sprint 14)

    Returns:
        RelationExtractor instance with retry logic (Sprint 14) and AegisLLMProxy (Sprint 23)

    Example:
        >>> from src.core.config import get_settings
        >>> settings = get_settings()
        >>> extractor = create_relation_extractor_from_config(settings)
    """
    # Sprint 23: No longer need Ollama client - AegisLLMProxy handles routing
    # Sprint 124: Env var LIGHTRAG_LLM_MODEL takes precedence over config
    model = os.environ.get("LIGHTRAG_LLM_MODEL") or getattr(config, "gemma_model", None)
    return RelationExtractor(
        model=model,  # Sprint 124: None triggers env var lookup in __init__
        temperature=getattr(config, "gemma_temperature", 0.1),
        num_predict=getattr(config, "gemma_num_predict", 8192),
        num_ctx=getattr(config, "gemma_num_ctx", 32768),
        # Sprint 14: Retry configuration
        max_retries=getattr(config, "extraction_max_retries", 3),
        retry_min_wait=getattr(config, "extraction_retry_min_wait", 2.0),
        retry_max_wait=getattr(config, "extraction_retry_max_wait", 10.0),
    )
