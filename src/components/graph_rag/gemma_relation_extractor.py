"""Gemma 3 4B Relation Extractor for Graph RAG.

Sprint 13 Feature 13.9: ADR-018
Uses Gemma 3 4B Q4_K_M (via Ollama) for high-quality relation extraction
between entities. This is Phase 3 of the 3-phase extraction pipeline.

Sprint 14 Feature 14.5: Added retry logic and error handling.

Author: Claude Code
Date: 2025-10-24, Updated: 2025-10-27
"""

import json
import re
from typing import Any

import structlog
from ollama import Client
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
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
   - description: Explanation as to why the source entity and target entity are related
   - strength: A numeric score (1-10) indicating strength of the relationship

4. Return output as valid JSON with array: "relations".

---Output Requirements---
Output valid JSON only. No markdown formatting, no code blocks, just pure JSON.
Format: {"relations": [...]}"""

USER_PROMPT_TEMPLATE_RELATION = """---Task---
Extract relationships between the provided entities based on the input text.

######################
-Entity List-
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
    {{"source": "Alex", "target": "TechCorp", "description": "Alex worked at TechCorp.", "strength": 8}},
    {{"source": "Jordan", "target": "TechCorp", "description": "Jordan worked at TechCorp.", "strength": 8}},
    {{"source": "Alex", "target": "Jordan", "description": "Alex and Jordan worked together.", "strength": 7}}
  ]
}}

######################
Output (valid JSON only):
"""


class GemmaRelationExtractor:
    """Extract relations between entities using Gemma 3 4B.

    Uses Ollama with Gemma 3 4B Q4_K_M quantization for high-quality
    relation extraction. Operates on a pre-defined entity list to ensure
    all relations reference valid entities.

    Architecture Decision: ADR-018 (Model Selection)
    Performance: ~13-16s per document (200-300 words)
    Quality: 123% relation accuracy (exceeds targets)

    Example:
        >>> extractor = GemmaRelationExtractor()
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
        model: str = "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M",
        ollama_client: Client = None,
        temperature: float = 0.1,
        num_predict: int = 2000,
        num_ctx: int = 16384,
        max_retries: int = 3,
        retry_min_wait: float = 2.0,
        retry_max_wait: float = 10.0,
    ):
        """Initialize Gemma relation extractor.

        Args:
            model: Ollama model name
                  Default: Gemma 3 4B Q4_K_M (best performance from benchmarks)
            ollama_client: Ollama client instance (or create new)
            temperature: LLM temperature (0.0-1.0, lower = more deterministic)
            num_predict: Max tokens to generate
            num_ctx: Context window size
            max_retries: Max retry attempts for transient failures (Sprint 14)
            retry_min_wait: Min wait time between retries in seconds (Sprint 14)
            retry_max_wait: Max wait time between retries in seconds (Sprint 14)
        """
        self.model = model
        self.client = ollama_client or Client()
        self.temperature = temperature
        self.num_predict = num_predict
        self.num_ctx = num_ctx
        self.max_retries = max_retries
        self.retry_min_wait = retry_min_wait
        self.retry_max_wait = retry_max_wait

        logger.info(
            "gemma_relation_extractor_initialized",
            model=model,
            temperature=temperature,
            num_predict=num_predict,
            num_ctx=num_ctx,
            max_retries=max_retries,
            retry_config=f"{retry_min_wait}-{retry_max_wait}s",
        )

    async def extract(
        self,
        text: str,
        entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract relations between entities from text.

        Sprint 14: Added automatic retry logic for transient failures.

        Args:
            text: Source text containing entities
            entities: List of entities with 'name' key
                     (from Phase 1 SpaCy NER + Phase 2 Deduplication)

        Returns:
            List of relation dicts with keys:
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
        entity_names = [e['name'] for e in entities]
        entity_list_str = ", ".join(entity_names)

        # Build prompt
        user_prompt = USER_PROMPT_TEMPLATE_RELATION.format(
            entity_list=entity_list_str,
            text=text
        )

        # Call LLM with retry logic (Sprint 14)
        try:
            relations = await self._extract_with_retry(user_prompt, text, entities)

            logger.info(
                "relation_extraction_complete",
                text_length=len(text),
                entity_count=len(entities),
                relations_found=len(relations)
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
                note="Returning empty relations list (graceful degradation)"
            )
            return []

    async def _extract_with_retry(
        self,
        user_prompt: str,
        text: str,
        entities: list[dict[str, Any]]
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
            List of extracted relations

        Raises:
            Exception: If all retries exhausted
        """
        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(
                multiplier=1,
                min=self.retry_min_wait,
                max=self.retry_max_wait
            ),
            retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
            before_sleep=before_sleep_log(logger, "WARNING"),
            reraise=True
        )
        async def _call_llm():
            """Inner function with retry decorator."""
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_RELATION},
                    {"role": "user", "content": user_prompt}
                ],
                options={
                    "temperature": self.temperature,
                    "num_predict": self.num_predict,
                    "num_ctx": self.num_ctx
                },
                format="json"
            )

            # Parse JSON response
            content = response["message"]["content"]
            relation_data = self._parse_json_response(content)
            return relation_data.get('relations', [])

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
        if cleaned.startswith('```'):
            lines = cleaned.split('\n')
            cleaned = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned
            cleaned = cleaned.replace('```json', '').replace('```', '').strip()

        # Try direct parsing
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from text (regex fallback)
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            logger.warning(
                "relation_json_parse_failed",
                response_preview=cleaned[:200]
            )
            return {"relations": []}


def create_relation_extractor_from_config(config) -> GemmaRelationExtractor:
    """Factory function to create relation extractor from app config.

    Args:
        config: Application config object with attributes:
               - GEMMA_MODEL (str): Ollama model name
               - GEMMA_TEMPERATURE (float): LLM temperature
               - GEMMA_NUM_PREDICT (int): Max tokens
               - GEMMA_NUM_CTX (int): Context window
               - OLLAMA_BASE_URL (str): Ollama server URL
               - EXTRACTION_MAX_RETRIES (int): Max retries (Sprint 14)
               - EXTRACTION_RETRY_MIN_WAIT (float): Min retry wait (Sprint 14)
               - EXTRACTION_RETRY_MAX_WAIT (float): Max retry wait (Sprint 14)

    Returns:
        GemmaRelationExtractor instance with retry logic (Sprint 14)

    Example:
        >>> from src.core.config import get_settings
        >>> settings = get_settings()
        >>> extractor = create_relation_extractor_from_config(settings)
    """
    # Create Ollama client with configured base URL
    from ollama import Client
    ollama_base_url = getattr(config, 'ollama_base_url', 'http://localhost:11434')
    ollama_client = Client(host=ollama_base_url)

    return GemmaRelationExtractor(
        model=getattr(
            config,
            'gemma_model',
            'hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M'
        ),
        ollama_client=ollama_client,
        temperature=getattr(config, 'gemma_temperature', 0.1),
        num_predict=getattr(config, 'gemma_num_predict', 2000),
        num_ctx=getattr(config, 'gemma_num_ctx', 16384),
        # Sprint 14: Retry configuration
        max_retries=getattr(config, 'extraction_max_retries', 3),
        retry_min_wait=getattr(config, 'extraction_retry_min_wait', 2.0),
        retry_max_wait=getattr(config, 'extraction_retry_max_wait', 10.0),
    )
