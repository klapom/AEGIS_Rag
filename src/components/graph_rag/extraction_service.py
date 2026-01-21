"""Entity and relationship extraction service using Ollama LLM.

Sprint 5: Feature 5.3 - Entity & Relationship Extraction
Sprint 83: Feature 83.2 - LLM Fallback & Retry Strategy (3-Rank Cascade)
Sprint 83: Feature 83.3 - Gleaning Multi-Pass Extraction (TD-100)
Sprint 86: Feature 86.7 - Coreference Resolution for improved relation recall

This module provides extraction services for building knowledge graphs from text documents.
Uses a 3-rank cascade fallback strategy for robust extraction:
- Rank 1: Nemotron3 (LLM-Only) - Fast, local
- Rank 2: GPT-OSS:20b (LLM-Only) - Larger model, more accurate
- Rank 3: Hybrid SpaCy NER + LLM - Maximum recall with NER + LLM relations

Each rank has retry logic with exponential backoff (3 attempts).
Falls back to next rank on timeout/error/parsing failure.

Gleaning Multi-Pass Extraction (Microsoft GraphRAG approach):
- Round 1: Initial entity extraction
- Completeness Check: LLM with logit bias determines if extraction is complete
- Rounds 2+: Extract "missing" entities with continuation prompt
- Merge & Deduplicate: Combine all entities from all rounds

Coreference Resolution (Sprint 86.7):
- Resolves pronouns (he, she, it, they) to their antecedents
- Improves relation recall by ~15-20% on pronoun-heavy text
- Enable via AEGIS_USE_COREFERENCE=1 (default: enabled)
- Disable via AEGIS_USE_COREFERENCE=0 if causing issues
"""

import asyncio
import json
import os
import re
import time
import uuid
from typing import Any

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.components.ingestion.logging_utils import log_llm_cost_summary
from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy
from src.components.llm_proxy.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.config.extraction_cascade import (
    CascadeRankConfig,
    ExtractionMethod,
    PipelineStageConfig,
    get_cascade_for_domain,
    get_pipeline_config,
    log_cascade_fallback,
    should_use_spacy_first_pipeline,
)
from src.core.config import settings
from src.core.models import GraphEntity, GraphRelationship
from src.prompts.extraction_prompts import (
    COMPLETENESS_CHECK_PROMPT,
    CONTINUATION_EXTRACTION_PROMPT,
    DSPY_OPTIMIZED_ENTITY_PROMPT,
    DSPY_OPTIMIZED_RELATION_PROMPT,
    ENTITY_ENRICHMENT_PROMPT,
    ENTITY_EXTRACTION_PROMPT,
    GENERIC_ENTITY_EXTRACTION_PROMPT,
    GENERIC_RELATION_EXTRACTION_PROMPT,
    RELATION_EXTRACTION_FROM_ENTITIES_PROMPT,
    RELATIONSHIP_COMPLETENESS_CHECK_PROMPT,
    RELATIONSHIP_CONTINUATION_PROMPT,
    RELATIONSHIP_EXTRACTION_PROMPT,
    USE_DSPY_PROMPTS,
    get_active_extraction_prompts,
)

logger = structlog.get_logger(__name__)

# Sprint 86.7: Coreference Resolution Feature Flag
# Default: enabled (1) - resolves pronouns to antecedents before extraction
# Disable: AEGIS_USE_COREFERENCE=0 if causing issues
USE_COREFERENCE = os.environ.get("AEGIS_USE_COREFERENCE", "1") == "1"

# Sprint 86.8: Cross-Sentence Extraction Feature Flag
# Default: enabled (1) - uses sliding windows for texts > 5 sentences
# Disable: AEGIS_USE_CROSS_SENTENCE=0 for sentence-by-sentence extraction
USE_CROSS_SENTENCE = os.environ.get("AEGIS_USE_CROSS_SENTENCE", "1") == "1"
CROSS_SENTENCE_THRESHOLD = 5  # Minimum sentences to trigger windowed extraction

# Lazy import to avoid circular dependency
_coreference_resolver = None


def _get_coreference_resolver():
    """Get coreference resolver (lazy load)."""
    global _coreference_resolver
    if _coreference_resolver is None and USE_COREFERENCE:
        try:
            from src.components.graph_rag.coreference_resolver import (
                get_coreference_resolver,
            )

            _coreference_resolver = get_coreference_resolver("en")
            logger.info(
                "coreference_resolver_loaded",
                lang="en",
            )
        except Exception as e:
            logger.warning(
                "coreference_resolver_load_failed",
                error=str(e),
                fallback="disabled",
            )
            return None
    return _coreference_resolver


def _apply_coreference_resolution(text: str) -> tuple[str, dict]:
    """Apply coreference resolution to text before extraction.

    Sprint 86.7: Resolves pronouns (he, she, it, they) to their antecedents.
    This improves relation extraction recall by ~15-20% on pronoun-heavy text.

    Example:
        Input:  "Microsoft was founded in 1975. It later acquired GitHub."
        Output: "Microsoft was founded in 1975. Microsoft later acquired GitHub."

    Args:
        text: Original text with potential pronouns

    Returns:
        Tuple of (resolved_text, metadata_dict)
        metadata_dict contains: {"coreference_enabled", "resolutions_count", "original_length", "resolved_length"}
    """
    if not USE_COREFERENCE:
        return text, {"coreference_enabled": False, "resolutions_count": 0}

    resolver = _get_coreference_resolver()
    if resolver is None:
        return text, {
            "coreference_enabled": False,
            "resolutions_count": 0,
            "error": "resolver_not_loaded",
        }

    try:
        result = resolver.resolve(text)

        metadata = {
            "coreference_enabled": True,
            "resolutions_count": result.resolution_count,
            "original_length": len(text),
            "resolved_length": len(result.resolved_text),
        }

        if result.resolution_count > 0:
            logger.info(
                "coreference_resolution_applied",
                resolutions=result.resolution_count,
                text_delta=len(result.resolved_text) - len(text),
                chains=[
                    {"antecedent": c.antecedent, "type": c.antecedent_type}
                    for c in result.chains[:5]  # Log first 5 chains only
                ],
            )

        return result.resolved_text, metadata

    except Exception as e:
        logger.warning(
            "coreference_resolution_failed",
            error=str(e),
            text_length=len(text),
        )
        return text, {"coreference_enabled": False, "resolutions_count": 0, "error": str(e)}


def _should_use_cross_sentence(text: str) -> bool:
    """Check if text should use cross-sentence windowed extraction.

    Sprint 86.8: Only use windowed extraction for texts with >5 sentences.
    Shorter texts don't benefit from windowing and single-pass is faster.

    Args:
        text: Input text

    Returns:
        True if cross-sentence extraction should be used
    """
    if not USE_CROSS_SENTENCE:
        return False

    # Quick heuristic: count sentence-ending punctuation followed by whitespace or end
    # Handles both ". " and ".\n" patterns
    import re

    sentence_endings = re.findall(r"[.!?][\s\n]", text)
    sentence_count = len(sentence_endings)
    # Add 1 for the last sentence (no trailing whitespace)
    if text.rstrip().endswith((".", "!", "?")):
        sentence_count += 1

    return sentence_count > CROSS_SENTENCE_THRESHOLD


def _get_cross_sentence_windows(text: str) -> list[str]:
    """Get cross-sentence windows for extraction.

    Sprint 86.8: Uses sliding window approach for relation extraction.

    Args:
        text: Input text

    Returns:
        List of window texts (or [text] if windowing not needed)
    """
    if not _should_use_cross_sentence(text):
        return [text]

    try:
        from src.components.graph_rag.cross_sentence_extractor import (
            get_cross_sentence_extractor,
        )

        extractor = get_cross_sentence_extractor(
            lang="en",
            window_size=3,
            overlap=1,
        )

        windows = list(extractor.create_windows(text))

        if not windows:
            return [text]

        window_texts = [w.text for w in windows]

        logger.info(
            "cross_sentence_windows_created",
            original_length=len(text),
            window_count=len(windows),
            avg_window_length=sum(len(w) for w in window_texts) / len(window_texts),
        )

        return window_texts

    except Exception as e:
        logger.warning(
            "cross_sentence_windowing_failed",
            error=str(e),
            fallback="single_window",
        )
        return [text]


# JSON repair utilities for malformed LLM responses (Sprint 32 Enhancement)


def _repair_json_string(json_str: str) -> str:
    """Apply common repairs to malformed JSON from LLM responses.

    Handles:
    - Trailing commas before ] or }
    - Missing commas between objects
    - Unescaped newlines in strings
    - Single quotes as JSON delimiters (NOT apostrophes inside strings)
    - Python None/True/False instead of null/true/false
    - Apostrophes inside strings (escape them properly)

    Args:
        json_str: Raw JSON string that may be malformed

    Returns:
        Repaired JSON string
    """
    # IMPORTANT: Don't blindly replace all single quotes!
    # Only replace single quotes used as JSON delimiters, not apostrophes in text.
    #
    # Problem case: {"source": "L'Histoire du soldat"}
    # Blind replace creates: {"source": "L"Histoire du soldat"} ← INVALID JSON!
    #
    # Solution: Escape apostrophes inside double-quoted strings first,
    # then only replace single quotes that are JSON delimiters.

    # Step 1: First, try to detect if this is single-quote delimited JSON
    # Check for patterns like: [{'key or {'key - single quotes used as JSON delimiters
    # Match: [{' or {' at the start (with optional whitespace)
    is_single_quote_json = bool(re.search(r"[\[{]\s*{?\s*'", json_str[:50]))

    if is_single_quote_json:
        # This JSON uses single quotes as delimiters - need smart replacement
        # Replace single-quote delimiters with double quotes
        # Pattern: 'key': 'value' → "key": "value"
        # But preserve apostrophes inside values like "L'Histoire"

        # Strategy: Replace structural single quotes only
        # Order matters! Process from inside-out patterns first
        json_str = re.sub(r"'\s*:", '":', json_str)  # 'key': → "key":
        json_str = re.sub(r":\s*'", ': "', json_str)  # : 'value → : "value
        json_str = re.sub(r"'\s*,", '",', json_str)  # 'value', → "value",
        json_str = re.sub(r",\s*'", ', "', json_str)  # , 'key → , "key
        json_str = re.sub(r"'\s*}", '"}', json_str)  # 'value'} → "value"}
        json_str = re.sub(r"'\s*\]", '"]', json_str)  # 'value'] → "value"]
        json_str = re.sub(r"\[\s*'", '["', json_str)  # ['value → ["value
        json_str = re.sub(r"{\s*'", '{"', json_str)  # {'key → {"key

    # Fix Python literals
    json_str = re.sub(r"\bNone\b", "null", json_str)
    json_str = re.sub(r"\bTrue\b", "true", json_str)
    json_str = re.sub(r"\bFalse\b", "false", json_str)

    # Remove trailing commas before ] or }
    json_str = re.sub(r",\s*]", "]", json_str)
    json_str = re.sub(r",\s*}", "}", json_str)

    # Fix missing commas between objects: }{ -> },{
    json_str = re.sub(r"}\s*{", "},{", json_str)

    # Fix missing commas between array elements: ]["name" -> ],["name" or ]{ -> ],{
    json_str = re.sub(r"]\s*\[", "],[", json_str)
    json_str = re.sub(r"]\s*{", "],{", json_str)

    # Remove control characters that break JSON (except \n, \r, \t)
    json_str = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", json_str)

    return json_str


def _normalize_predicate_to_type(predicate: str) -> str:
    """Normalize a natural language predicate to an uppercase relationship type.

    Sprint 85 Fix: Convert predicates like "is a setting that can be tried"
    to relationship types like "HAS_SETTING".

    Args:
        predicate: Natural language predicate from LLM

    Returns:
        Uppercase relationship type with underscores
    """
    if not predicate:
        return "RELATES_TO"

    # Common predicate patterns to relationship types
    predicate_lower = predicate.lower().strip()

    # Direct mappings for common patterns
    mapping = {
        "works at": "WORKS_AT",
        "works for": "WORKS_FOR",
        "created": "CREATED",
        "created by": "CREATED_BY",
        "directed": "DIRECTED",
        "directed by": "DIRECTED_BY",
        "produced": "PRODUCED",
        "produced by": "PRODUCED_BY",
        "stars": "STARS",
        "stars in": "STARS_IN",
        "voiced by": "VOICED_BY",
        "founded": "FOUNDED",
        "founded by": "FOUNDED_BY",
        "born in": "BORN_IN",
        "located in": "LOCATED_IN",
        "part of": "PART_OF",
        "member of": "MEMBER_OF",
        "contains": "CONTAINS",
        "uses": "USES",
        "has": "HAS",
        "is a": "IS_A",
        "is an": "IS_A",
        "based on": "BASED_ON",
        "released": "RELEASED",
        "published": "PUBLISHED",
        "wrote": "WROTE",
        "written by": "WRITTEN_BY",
    }

    # Check for direct match
    for pattern, rel_type in mapping.items():
        if predicate_lower.startswith(pattern):
            return rel_type

    # Fallback: Convert first few words to uppercase type
    # "is a setting that can be tried" → "IS_SETTING"
    words = predicate_lower.split()[:3]
    if words:
        type_str = "_".join(words).upper()
        # Clean up non-alphanumeric characters
        type_str = re.sub(r"[^A-Z0-9_]", "", type_str)
        return type_str if type_str else "RELATES_TO"

    return "RELATES_TO"


def _extract_json_objects_individually(
    text: str, data_type: str = "entity"
) -> list[dict[str, Any]]:
    """Extract individual JSON objects when array parsing fails.

    When the full JSON array is malformed, try to extract each valid object individually.

    Args:
        text: Text containing JSON objects (potentially malformed array)
        data_type: Type of data ("entity" or "relationship")

    Returns:
        List of successfully parsed objects
    """
    objects = []

    # Pattern to match individual JSON objects
    # This is more lenient than full array parsing
    object_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"

    matches = re.finditer(object_pattern, text, re.DOTALL)

    for match in matches:
        obj_str = match.group(0)
        try:
            # Try to repair and parse individual object
            repaired = _repair_json_string(obj_str)
            obj = json.loads(repaired)

            if isinstance(obj, dict):
                # Validate required fields
                if data_type == "entity":
                    if "name" in obj and "type" in obj:
                        objects.append(obj)
                elif data_type == "relationship":
                    # Sprint 85 Fix: Accept both formats and normalize
                    # Format 1: {source, target, type} (standard)
                    # Format 2: {subject, predicate, object} (generic prompt)
                    if "source" in obj and "target" in obj and "type" in obj:
                        objects.append(obj)
                    elif "subject" in obj and "object" in obj:
                        # Map subject/predicate/object to source/target/type
                        normalized = {
                            "source": obj["subject"],
                            "target": obj["object"],
                            "type": _normalize_predicate_to_type(
                                obj.get("predicate", "RELATES_TO")
                            ),
                            "description": obj.get("predicate", ""),
                        }
                        objects.append(normalized)
                else:
                    objects.append(obj)

        except json.JSONDecodeError:
            # Individual object also malformed, skip it
            continue

    return objects


# Constants
MAX_ENTITIES_PER_DOC = 50
MAX_RELATIONSHIPS_PER_DOC = 100


class ExtractionService:
    """Entity and relationship extraction service using AegisLLMProxy.

    Provides methods for:
    - Entity extraction from text
    - Relationship extraction between entities
    - Batch processing of multiple documents
    - Integration with LightRAG and Neo4j
    """

    def __init__(
        self,
        llm_model: str | None = None,
        ollama_base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        """Initialize extraction service.

        Sprint 64 Feature 64.6: LLM model now respects Admin UI configuration

        Args:
            llm_model: Explicit LLM model name (overrides Admin UI config)
            ollama_base_url: DEPRECATED - kept for backward compatibility
            temperature: LLM temperature for extraction (default: 0.1 for consistency)
            max_tokens: Max tokens for LLM response
        """
        # Store explicit model or None (fetch from Admin UI config on first use)
        self._explicit_llm_model = llm_model
        self.temperature = (
            temperature if temperature is not None else settings.lightrag_llm_temperature
        )
        self.max_tokens = max_tokens or settings.lightrag_llm_max_tokens

        # Initialize AegisLLMProxy for multi-cloud routing
        self.llm_proxy = AegisLLMProxy()

        logger.info(
            "extraction_service_initialized",
            explicit_model=self._explicit_llm_model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    async def _extract_with_timeout(
        self,
        extraction_func: Any,
        timeout_s: int,
        rank_config: CascadeRankConfig,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute extraction with timeout wrapper.

        Args:
            extraction_func: Async extraction function to call
            timeout_s: Timeout in seconds
            rank_config: Current cascade rank configuration
            *args: Positional arguments for extraction_func
            **kwargs: Keyword arguments for extraction_func

        Returns:
            Extraction result from extraction_func

        Raises:
            asyncio.TimeoutError: If extraction exceeds timeout
        """
        try:
            result = await asyncio.wait_for(
                extraction_func(*args, **kwargs),
                timeout=timeout_s,
            )
            return result

        except asyncio.TimeoutError as e:
            logger.error(
                "extraction_timeout",
                rank=rank_config.rank,
                model=rank_config.model,
                timeout_s=timeout_s,
                method=rank_config.method.value,
            )
            raise

    async def get_extraction_prompts(self, domain: str | None = None) -> tuple[str, str]:
        """Get extraction prompts for a given domain.

        Sprint 45 Feature 45.8: Domain-specific or generic fallback prompts.
        Sprint 86 Feature 86.2: DSPy MIPROv2 optimized prompts with feature flag.

        Priority order:
        1. DSPy-optimized prompts (if AEGIS_USE_DSPY_PROMPTS=1)
        2. Domain-specific prompts (if domain is provided and has custom prompts)
        3. Generic extraction prompts (fallback)

        Args:
            domain: Domain name (e.g., "tech_docs", "legal_contracts")

        Returns:
            Tuple of (entity_prompt, relation_prompt)

        Example:
            >>> service = get_extraction_service()
            >>> entity_prompt, relation_prompt = await service.get_extraction_prompts("tech_docs")
            >>> # If tech_docs domain exists with custom prompts, returns those
            >>> # Otherwise returns generic prompts
        """
        # Sprint 86.3: DSPy-optimized prompts are now the DEFAULT for all domains
        # Domain-specific prompts are stored in domain training config (see below)
        # Set AEGIS_USE_LEGACY_PROMPTS=1 to revert to old generic prompts
        if USE_DSPY_PROMPTS:
            logger.debug(
                "using_dspy_optimized_prompts",
                domain=domain,
                note="DSPy prompts default since Sprint 86.3",
            )
            return get_active_extraction_prompts(domain or "technical")

        # Import here to avoid circular dependency
        from src.components.domain_training import get_domain_repository

        # If no domain specified, use generic prompts
        if not domain:
            logger.info("using_generic_prompts", reason="no_domain_specified")
            return (GENERIC_ENTITY_EXTRACTION_PROMPT, GENERIC_RELATION_EXTRACTION_PROMPT)

        try:
            # Try to get domain-specific prompts
            domain_repo = get_domain_repository()
            domain_config = await domain_repo.get_domain(domain)

            if (
                domain_config
                and domain_config.get("entity_prompt")
                and domain_config.get("relation_prompt")
            ):
                logger.info(
                    "using_domain_specific_prompts",
                    domain=domain,
                    status=domain_config.get("status"),
                )
                return (
                    domain_config["entity_prompt"],
                    domain_config["relation_prompt"],
                )
            else:
                logger.info(
                    "using_generic_prompts",
                    reason="domain_not_found_or_no_prompts",
                    domain=domain,
                )
                return (GENERIC_ENTITY_EXTRACTION_PROMPT, GENERIC_RELATION_EXTRACTION_PROMPT)

        except Exception as e:
            # If anything goes wrong, fall back to generic prompts
            logger.warning(
                "domain_prompt_lookup_failed_using_generic",
                domain=domain,
                error=str(e),
            )
            return (GENERIC_ENTITY_EXTRACTION_PROMPT, GENERIC_RELATION_EXTRACTION_PROMPT)

    async def _get_llm_model(self) -> str:
        """Get LLM model from explicit config or Admin UI configuration.

        Sprint 64 Feature 64.6: Lazy fetch from Admin UI config

        Returns the explicitly provided model if set, otherwise fetches from
        the centralized LLM config service (respecting Admin UI settings).

        Returns:
            Model name (without provider prefix, e.g., "qwen3:32b")

        Example:
            >>> service = ExtractionService()  # No explicit model
            >>> model = await service._get_llm_model()
            >>> # Returns "qwen3:32b" from Admin UI config, not hardcoded "nemotron-3-nano"
        """
        if self._explicit_llm_model:
            return self._explicit_llm_model

        # Fetch from Admin UI config
        from src.components.llm_config import LLMUseCase, get_llm_config_service

        config_service = get_llm_config_service()
        model = await config_service.get_model_for_use_case(LLMUseCase.ENTITY_EXTRACTION)

        logger.debug(
            "using_admin_ui_configured_model",
            model=model,
            use_case="entity_extraction",
        )

        return model

    def _parse_json_response(
        self, response: str, data_type: str = "entity"
    ) -> list[dict[str, Any]]:
        """Parse JSON from LLM response with multiple fallback strategies.

        Sprint 13 Enhancement: Robust parsing for llama3.2:3b output variations.
        Sprint 32 Enhancement: Added JSON repair for malformed LLM responses.

        Handles various response formats:
        - Markdown code fences: ```json [...] ```
        - Plain JSON array: [...]
        - Text before/after JSON: "Here are the entities: [...] Hope this helps!"
        - Full response as JSON
        - Malformed JSON with trailing commas, missing commas, etc.

        Args:
            response: Raw LLM response text
            data_type: Type of data being parsed ("entity" or "relationship")

        Returns:
            Parsed JSON as list of dicts

        Raises:
            ValueError: If JSON parsing fails after all strategies
        """
        # ENHANCED LOGGING: Log full response for debugging
        logger.info(
            "parsing_llm_response",
            response_length=len(response),
            response_preview=response[:500],
            response_full=response,  # Full response for debugging
        )

        json_str = None
        strategy_used = None

        # Strategy 1: Extract from markdown code fence (```json [...] ``` or ``` [...] ```)
        code_fence_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", response, re.DOTALL)
        if code_fence_match:
            json_str = code_fence_match.group(1)
            strategy_used = "code_fence"
            logger.info("json_extraction_strategy", strategy=strategy_used)

        # Strategy 2: Extract JSON array pattern (current approach)
        if not json_str:
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                strategy_used = "regex_array"
                logger.info("json_extraction_strategy", strategy=strategy_used)

        # Strategy 3: Try entire response as-is
        if not json_str:
            json_str = response.strip()
            strategy_used = "full_response"
            logger.info("json_extraction_strategy", strategy=strategy_used)

        # Clean up common JSON issues
        json_str = json_str.strip()
        # NOTE: Don't blindly replace single quotes here!
        # _repair_json_string handles this intelligently to preserve apostrophes in text.

        # Sprint 32: Apply JSON repair before parsing (handles single quotes, apostrophes, etc.)
        json_str = _repair_json_string(json_str)

        try:
            data = json.loads(json_str)

            # Validate structure: must be list of dicts with required fields
            if isinstance(data, list):
                valid_items = []
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        # Check for required fields based on data type
                        if data_type == "entity":
                            required_fields = ["name", "type"]
                            is_valid = all(field in item for field in required_fields)
                            if is_valid:
                                valid_items.append(item)
                        elif data_type == "relationship":
                            # Sprint 85 Fix: Accept both formats
                            # Format 1: {source, target, type} (standard)
                            if "source" in item and "target" in item and "type" in item:
                                valid_items.append(item)
                            # Format 2: {subject, predicate, object} (generic prompt)
                            elif "subject" in item and "object" in item:
                                normalized = {
                                    "source": item["subject"],
                                    "target": item["object"],
                                    "type": _normalize_predicate_to_type(item.get("predicate", "")),
                                    "description": item.get("predicate", ""),
                                }
                                valid_items.append(normalized)
                                logger.debug(
                                    "relationship_format_normalized",
                                    index=i,
                                    original=item,
                                    normalized=normalized,
                                )
                            else:
                                logger.warning(
                                    "invalid_relationship_structure",
                                    index=i,
                                    item=item,
                                    missing_fields="source/target/type or subject/object",
                                )
                            is_valid = True  # Already handled above
                        else:
                            # Unknown data type - accept all dicts
                            is_valid = True
                            valid_items.append(item)

                        if data_type == "entity" and not is_valid:
                            logger.warning(
                                f"invalid_{data_type}_structure",
                                index=i,
                                item=item,
                                missing_fields=["name", "type"],
                            )
                    else:
                        logger.warning(
                            f"invalid_{data_type}_type",
                            index=i,
                            item_type=type(item).__name__,
                        )

                logger.info(
                    "json_parse_success",
                    strategy=strategy_used,
                    data_type=data_type,
                    total_items=len(data),
                    valid_items=len(valid_items),
                )

                return valid_items

            elif isinstance(data, dict):
                # Single item as dict (not array)
                logger.warning(
                    f"json_not_array_single_{data_type}",
                    data_type=type(data).__name__,
                )
                # Wrap in list if it has required fields
                if data_type == "entity":
                    required_fields = ["name", "type"]
                elif data_type == "relationship":
                    required_fields = ["source", "target", "type"]
                else:
                    required_fields = []

                if all(field in data for field in required_fields):
                    logger.info(f"wrapping_single_{data_type}_in_array")
                    return [data]
                else:
                    logger.error(f"single_{data_type}_missing_fields", data=data)
                    return []

            else:
                logger.warning("json_unexpected_type", data_type=type(data).__name__)
                return []

        except json.JSONDecodeError as e:
            logger.warning(
                "json_parse_failed_trying_individual_extraction",
                response_preview=response[:500],
                json_str_preview=json_str[:500] if json_str else "NONE",
                strategy=strategy_used,
                error=str(e),
                error_position=e.pos if hasattr(e, "pos") else None,
            )

            # Sprint 32: Fallback - try to extract individual JSON objects
            # This handles cases where the array structure is broken but individual objects are valid
            individual_objects = _extract_json_objects_individually(response, data_type)

            if individual_objects:
                logger.info(
                    "json_individual_extraction_success",
                    extracted_count=len(individual_objects),
                    data_type=data_type,
                    original_strategy=strategy_used,
                )
                return individual_objects

            # All strategies failed
            logger.error(
                "json_parse_failed_all_strategies",
                response_preview=response[:500],
                json_str_preview=json_str[:500] if json_str else "NONE",
                strategy=strategy_used,
                error=str(e),
            )

            # Sprint 13 CHANGE: Raise error instead of silent failure
            # This triggers retry logic (3 attempts with exponential backoff)
            # If all retries fail, test will show clear error message
            raise ValueError(
                f"Failed to parse JSON from LLM response after trying strategy '{strategy_used}' and individual extraction: {str(e)}"
            ) from e

    async def _extract_entities_with_rank(
        self,
        text: str,
        rank_config: CascadeRankConfig,
        document_id: str | None = None,
        domain: str | None = None,
    ) -> list[GraphEntity]:
        """Extract entities using a specific cascade rank.

        Sprint 83 Feature 83.2: Single-rank extraction with retry logic.

        Args:
            text: Document text to extract entities from
            rank_config: Cascade rank configuration
            document_id: Source document ID (optional)
            domain: Domain name for domain-specific prompts (Sprint 76 TD-085)

        Returns:
            list of extracted entities as GraphEntity objects

        Raises:
            Exception: If extraction fails after retries for this rank
        """
        logger.info(
            "extracting_entities_with_rank",
            rank=rank_config.rank,
            model=rank_config.model,
            method=rank_config.method.value,
            text_length=len(text),
            document_id=document_id,
        )

        # Hybrid extraction: SpaCy NER for entities
        if rank_config.method == ExtractionMethod.HYBRID_NER_LLM:
            from src.components.graph_rag.hybrid_extraction_service import (
                get_hybrid_extraction_service,
            )

            hybrid_service = get_hybrid_extraction_service(self)

            # SpaCy NER extraction (no timeout needed - synchronous)
            entities = await hybrid_service.extract_entities_with_spacy(
                text=text,
                document_id=document_id,
                language=None,  # Auto-detect
            )

            logger.info(
                "entities_extracted_with_hybrid_spacy",
                rank=rank_config.rank,
                count=len(entities),
                document_id=document_id,
            )

            return entities

        # LLM-Only extraction
        # Sprint 86: DSPy prompts require domain parameter
        entity_prompt, _ = await self.get_extraction_prompts(domain)
        try:
            prompt = entity_prompt.format(text=text, domain=domain or "technical")
        except KeyError:
            # Fallback for prompts without domain placeholder
            prompt = entity_prompt.format(text=text)

        # Create LLM task with rank-specific model
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt=prompt,
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            model_local=rank_config.model,  # Use rank-specific model
        )

        # Add retry decorator dynamically with rank-specific config
        @retry(
            stop=stop_after_attempt(rank_config.max_retries),
            wait=wait_exponential(
                multiplier=rank_config.retry_backoff_multiplier,
                min=1,
                max=8,
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        async def extract_with_retry() -> Any:
            result = await self.llm_proxy.generate(task)

            # Parse JSON response
            entities_data = self._parse_json_response(result.content)

            # Limit entities per document
            if len(entities_data) > MAX_ENTITIES_PER_DOC:
                logger.warning(
                    "max_entities_exceeded",
                    count=len(entities_data),
                    max_allowed=MAX_ENTITIES_PER_DOC,
                )
                entities_data = entities_data[:MAX_ENTITIES_PER_DOC]

            # Create GraphEntity objects
            entities = []
            for entity_dict in entities_data:
                try:
                    entity = GraphEntity(
                        id=str(uuid.uuid4()),
                        name=entity_dict.get("name", ""),
                        type=entity_dict.get("type", "UNKNOWN"),
                        description=entity_dict.get("description", ""),
                        properties={},
                        source_document=document_id,
                        confidence=1.0,
                    )
                    entities.append(entity)
                except Exception as e:
                    logger.warning(
                        "entity_creation_failed",
                        entity_dict=entity_dict,
                        error=str(e),
                    )

            # Log LLM cost summary
            if document_id:
                # Sprint 84: Handle both old (prompt_tokens) and new (tokens_input) SDK formats
                prompt_tokens = getattr(result, "prompt_tokens", None) or getattr(
                    result, "tokens_input", 0
                )
                completion_tokens = getattr(result, "completion_tokens", None) or getattr(
                    result, "tokens_output", 0
                )
                model = getattr(result, "model", "unknown")
                cost_usd = getattr(result, "cost_usd", 0.0)
                log_llm_cost_summary(
                    document_id=document_id,
                    phase="entity_extraction",
                    total_tokens=prompt_tokens + completion_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    model=model,
                    estimated_cost_usd=cost_usd,
                )

            return entities

        # Execute with timeout
        entities = await self._extract_with_timeout(
            extract_with_retry,
            rank_config.entity_timeout_s,
            rank_config,
        )

        logger.info(
            "entities_extracted_with_llm",
            rank=rank_config.rank,
            model=rank_config.model,
            count=len(entities),
            document_id=document_id,
        )

        return entities

    # =========================================================================
    # Sprint 89: SpaCy-First Pipeline (TD-102 Iteration 1)
    # =========================================================================

    async def extract_with_spacy_first_pipeline(
        self,
        text: str,
        document_id: str | None = None,
        domain: str | None = None,
    ) -> tuple[list[GraphEntity], list[GraphRelationship]]:
        """Extract entities AND relations using SpaCy-First 3-stage pipeline.

        Sprint 89 Feature 89.1: SpaCy-First Pipeline (TD-102 Iteration 1)

        This pipeline is 10-20x faster than the legacy LLM-first cascade:
        - Stage 1: SpaCy NER (~50ms) - Deterministic entity baseline
        - Stage 2: LLM Entity Enrichment (~5-15s) - Add CONCEPT, TECHNOLOGY, etc.
        - Stage 3: LLM Relation Extraction (~10-30s) - Extract all relations

        Args:
            text: Document text to extract from
            document_id: Source document ID (optional)
            domain: Domain name for prompts (optional)

        Returns:
            Tuple of (entities, relations)
        """
        from src.components.graph_rag.extraction_debug_logger import get_debug_logger

        pipeline_start = time.time()
        pipeline = get_pipeline_config()

        # Sprint 92 Feature 92.17: Comprehensive debug logging
        debug_logger = get_debug_logger(document_id or "unknown", chunk_index=0)
        debug_logger.log_input_text(text)

        logger.info(
            "spacy_first_pipeline_started",
            document_id=document_id,
            text_length=len(text),
            stages=len(pipeline),
        )

        # Stage 1: SpaCy NER Entities
        debug_logger.start_stage("spacy_ner", model="spacy")
        stage1_start = time.time()
        spacy_entities = await self._pipeline_stage1_spacy_ner(text, document_id, pipeline[0])
        stage1_duration = (time.time() - stage1_start) * 1000
        debug_logger.end_stage("spacy_ner", entities_count=len(spacy_entities))
        debug_logger.log_entities(spacy_entities, source="spacy")

        logger.info(
            "pipeline_stage1_complete",
            stage="SpaCy NER",
            entities_found=len(spacy_entities),
            duration_ms=round(stage1_duration, 2),
            document_id=document_id,
        )

        # Stage 2: LLM Entity Enrichment (MANDATORY)
        debug_logger.start_stage("llm_entity_enrichment", model=self._explicit_llm_model)
        stage2_start = time.time()
        enriched_entities = await self._pipeline_stage2_entity_enrichment(
            text, spacy_entities, document_id, domain, pipeline[1], debug_logger=debug_logger
        )
        stage2_duration = (time.time() - stage2_start) * 1000
        debug_logger.end_stage("llm_entity_enrichment", entities_count=len(enriched_entities))
        debug_logger.log_entities(enriched_entities, source="llm_enrichment")

        logger.info(
            "pipeline_stage2_complete",
            stage="LLM Entity Enrichment",
            spacy_entities=len(spacy_entities),
            enriched_entities=len(enriched_entities),
            duration_ms=round(stage2_duration, 2),
            document_id=document_id,
        )

        # Sprint 92 Feature 92.14: Entity Consolidation (NEW STEP!)
        # Consolidate entities BEFORE relation extraction:
        # - Filter invalid types (reject generic "ENTITY")
        # - Filter by length (max 80 chars to remove sentence-like entities)
        # - Deduplicate (prefer SpaCy over LLM)
        consolidation_start = time.time()
        from src.components.graph_rag.entity_consolidator import get_entity_consolidator

        consolidator = get_entity_consolidator()
        all_entities, consolidation_stats = await consolidator.consolidate(
            spacy_entities=spacy_entities,
            llm_entities=enriched_entities,
        )
        consolidation_duration = (time.time() - consolidation_start) * 1000

        logger.info(
            "pipeline_consolidation_complete",
            stage="Entity Consolidation",
            spacy_input=consolidation_stats.spacy_input,
            llm_input=consolidation_stats.llm_input,
            filtered_by_type=consolidation_stats.filtered_by_type,
            filtered_by_length=consolidation_stats.filtered_by_length,
            filtered_by_duplicate=consolidation_stats.filtered_by_duplicate,
            total_output=len(all_entities),
            filter_rate=f"{consolidation_stats.filter_rate:.1f}%",
            duration_ms=round(consolidation_duration, 2),
            document_id=document_id,
        )

        # Stage 3: LLM Relation Extraction
        debug_logger.start_stage("llm_relation_extraction", model=self._explicit_llm_model)
        stage3_start = time.time()
        relations = await self._pipeline_stage3_relation_extraction(
            text, all_entities, document_id, domain, pipeline[2], debug_logger=debug_logger
        )
        stage3_duration = (time.time() - stage3_start) * 1000
        debug_logger.end_stage("llm_relation_extraction", relations_count=len(relations))
        debug_logger.log_relations(relations, source="llm")

        pipeline_duration = (time.time() - pipeline_start) * 1000

        # Sprint 92.17: Log final summary
        debug_logger.log_entities(all_entities, source="consolidated_final")
        summary = debug_logger.log_summary()

        logger.info(
            "spacy_first_pipeline_complete",
            document_id=document_id,
            total_entities=len(all_entities),
            total_relations=len(relations),
            er_ratio=round(len(relations) / max(1, len(all_entities)), 2),
            stage1_ms=round(stage1_duration, 2),
            stage2_ms=round(stage2_duration, 2),
            consolidation_ms=round(consolidation_duration, 2),
            stage3_ms=round(stage3_duration, 2),
            total_ms=round(pipeline_duration, 2),
        )

        return all_entities, relations

    async def _pipeline_stage1_spacy_ner(
        self,
        text: str,
        document_id: str | None,
        stage_config: PipelineStageConfig,
    ) -> list[GraphEntity]:
        """Stage 1: Extract entities using SpaCy NER.

        Args:
            text: Text to extract from
            document_id: Document ID
            stage_config: Stage configuration

        Returns:
            List of GraphEntity from SpaCy NER
        """
        try:
            # Lazy import HybridExtractionService for SpaCy
            from src.components.graph_rag.hybrid_extraction_service import (
                HybridExtractionService,
            )

            hybrid_service = HybridExtractionService(self)
            entities = await hybrid_service.extract_entities_with_spacy(
                text=text,
                document_id=document_id,
            )

            return entities

        except Exception as e:
            logger.warning(
                "spacy_ner_failed",
                error=str(e),
                document_id=document_id,
                fallback="llm_entity_extraction" if stage_config.fallback_to_llm else "empty",
            )

            # Fallback to LLM entity extraction if configured
            if stage_config.fallback_to_llm:
                logger.info("falling_back_to_llm_entity_extraction", document_id=document_id)
                return await self._extract_entities_llm_only(
                    text=text,
                    document_id=document_id,
                    model="nemotron-3-nano:latest",
                    timeout_s=120,
                )

            return []

    async def _pipeline_stage2_entity_enrichment(
        self,
        text: str,
        spacy_entities: list[GraphEntity],
        document_id: str | None,
        domain: str | None,
        stage_config: PipelineStageConfig,
        debug_logger: any = None,  # Sprint 92.17: Debug logger
    ) -> list[GraphEntity]:
        """Stage 2: Enrich SpaCy entities with LLM (find CONCEPT, TECHNOLOGY, etc.).

        Args:
            text: Text to extract from
            spacy_entities: Entities already found by SpaCy
            document_id: Document ID
            domain: Domain for prompts
            stage_config: Stage configuration
            debug_logger: Optional debug logger for comprehensive logging

        Returns:
            List of NEW entities found by LLM (not in SpaCy list)
        """
        logger.info(
            "stage2_entity_enrichment_started",
            document_id=document_id,
            spacy_entity_count=len(spacy_entities),
            text_length=len(text),
            model=stage_config.model,
            timeout=stage_config.timeout_s,
        )

        # Format SpaCy entities for prompt
        spacy_entities_str = (
            ", ".join([f"{e.name} ({e.type})" for e in spacy_entities]) or "None found"
        )

        prompt = ENTITY_ENRICHMENT_PROMPT.format(
            spacy_entities=spacy_entities_str,
            text=text[:8000],  # Limit text length for LLM
        )

        # Sprint 92.17: Log full prompt for debugging
        if debug_logger:
            debug_logger.log_llm_request(
                "llm_entity_enrichment",
                prompt,
                stage_config.model,
                system_prompt=None,
            )

        logger.info(
            "stage2_prompt_formatted",
            document_id=document_id,
            prompt_length=len(prompt),
            spacy_entities_preview=spacy_entities_str[:200],
        )

        try:
            logger.info("stage2_calling_llm_proxy", document_id=document_id)
            llm_start = time.time()
            # Use LLM for enrichment
            response = await asyncio.wait_for(
                self.llm_proxy.generate(
                    LLMTask(
                        task_type=TaskType.EXTRACTION,
                        complexity=Complexity.MEDIUM,
                        quality=QualityRequirement.MEDIUM,
                        prompt=prompt,
                        model_override=stage_config.model,
                        max_tokens=2000,
                        temperature=0.1,
                    )
                ),
                timeout=stage_config.timeout_s,
            )

            llm_duration_ms = (time.time() - llm_start) * 1000

            # Sprint 92.17: Log full response for debugging
            if debug_logger:
                debug_logger.log_llm_response(
                    "llm_entity_enrichment",
                    response.content if response else "",
                    llm_duration_ms,
                    is_valid_json=True,  # Will be updated if parsing fails
                )

            logger.info(
                "stage2_llm_response_received",
                document_id=document_id,
                response_length=len(response.content) if response else 0,
                response_preview=response.content[:200] if response else "None",
                duration_ms=round(llm_duration_ms, 2),
            )

            # Parse enriched entities
            enriched = self._parse_entity_response(response.content, document_id)

            logger.info(
                "stage2_entities_parsed",
                document_id=document_id,
                enriched_count=len(enriched),
            )

            # Filter out any entities that duplicate SpaCy entities
            spacy_names_lower = {e.name.lower() for e in spacy_entities}
            new_entities = [e for e in enriched if e.name.lower() not in spacy_names_lower]

            logger.info(
                "stage2_entities_filtered",
                document_id=document_id,
                new_entities_count=len(new_entities),
                filtered_duplicates=len(enriched) - len(new_entities),
            )

            return new_entities

        except asyncio.TimeoutError:
            logger.warning(
                "entity_enrichment_timeout",
                timeout_s=stage_config.timeout_s,
                document_id=document_id,
            )
            return []

        except Exception as e:
            logger.warning(
                "entity_enrichment_failed",
                error=str(e),
                document_id=document_id,
            )
            return []

    async def _pipeline_stage3_relation_extraction(
        self,
        text: str,
        all_entities: list[GraphEntity],
        document_id: str | None,
        domain: str | None,
        stage_config: PipelineStageConfig,
        debug_logger: any = None,  # Sprint 92.17: Debug logger
    ) -> list[GraphRelationship]:
        """Stage 3: Extract relations between all entities using LLM.

        Args:
            text: Text to extract from
            all_entities: All entities (SpaCy + enriched)
            document_id: Document ID
            domain: Domain for prompts
            stage_config: Stage configuration
            debug_logger: Optional debug logger for comprehensive logging

        Returns:
            List of GraphRelationship
        """
        logger.info(
            "stage3_relation_extraction_started",
            document_id=document_id,
            entity_count=len(all_entities),
            text_length=len(text),
            model=stage_config.model,
            timeout=stage_config.timeout_s,
        )

        if not all_entities:
            logger.warning(
                "no_entities_for_relation_extraction",
                document_id=document_id,
            )
            return []

        # Format entities for prompt
        entities_str = "\n".join(
            [f"- {e.name} ({e.type}): {e.description or 'No description'}" for e in all_entities]
        )

        prompt = RELATION_EXTRACTION_FROM_ENTITIES_PROMPT.format(
            entities=entities_str,
            text=text[:8000],  # Limit text length for LLM
        )

        # Sprint 92.17: Log full prompt for debugging
        if debug_logger:
            debug_logger.log_llm_request(
                "llm_relation_extraction",
                prompt,
                stage_config.model,
                system_prompt=None,
            )

        logger.info(
            "stage3_prompt_formatted",
            document_id=document_id,
            prompt_length=len(prompt),
            entities_preview=entities_str[:200],
        )

        try:
            logger.info("stage3_calling_llm_proxy", document_id=document_id)
            llm_start = time.time()
            response = await asyncio.wait_for(
                self.llm_proxy.generate(
                    LLMTask(
                        task_type=TaskType.EXTRACTION,
                        complexity=Complexity.HIGH,
                        quality=QualityRequirement.HIGH,
                        prompt=prompt,
                        model_override=stage_config.model,
                        max_tokens=4000,
                        temperature=0.1,
                    )
                ),
                timeout=stage_config.timeout_s,
            )

            llm_duration_ms = (time.time() - llm_start) * 1000

            # Sprint 92.17: Log full response for debugging
            if debug_logger:
                debug_logger.log_llm_response(
                    "llm_relation_extraction",
                    response.content if response else "",
                    llm_duration_ms,
                    is_valid_json=True,  # Will be updated if parsing fails
                )

            logger.info(
                "stage3_llm_response_received",
                document_id=document_id,
                response_length=len(response.content) if response else 0,
                response_preview=response.content[:200] if response else "None",
                duration_ms=round(llm_duration_ms, 2),
            )

            # Parse relations
            relations = self._parse_relationship_response(
                response.content,
                all_entities,
                document_id,
            )

            logger.info(
                "stage3_relations_parsed",
                document_id=document_id,
                relations_count=len(relations),
            )

            return relations

        except asyncio.TimeoutError:
            logger.error(
                "relation_extraction_timeout",
                timeout_s=stage_config.timeout_s,
                document_id=document_id,
                entity_count=len(all_entities),
            )
            return []

        except Exception as e:
            logger.error(
                "relation_extraction_failed",
                error=str(e),
                document_id=document_id,
            )
            return []

    def _merge_entities(
        self,
        spacy_entities: list[GraphEntity],
        enriched_entities: list[GraphEntity],
    ) -> list[GraphEntity]:
        """Merge SpaCy and enriched entities, removing duplicates.

        Args:
            spacy_entities: Entities from SpaCy NER
            enriched_entities: Additional entities from LLM enrichment

        Returns:
            Merged list with duplicates removed
        """
        # Use lowercase name as key for deduplication
        seen = set()
        merged = []

        # Add SpaCy entities first (they have priority)
        for entity in spacy_entities:
            key = entity.name.lower()
            if key not in seen:
                seen.add(key)
                merged.append(entity)

        # Add enriched entities
        for entity in enriched_entities:
            key = entity.name.lower()
            if key not in seen:
                seen.add(key)
                merged.append(entity)

        return merged

    def _parse_entity_response(
        self, response_content: str, document_id: str | None = None
    ) -> list[GraphEntity]:
        """Parse LLM response into GraphEntity objects.

        Args:
            response_content: Raw LLM response text
            document_id: Optional document ID for provenance

        Returns:
            List of GraphEntity objects
        """
        try:
            logger.info(
                "parse_entity_response_start",
                document_id=document_id,
                response_length=len(response_content),
                response_content=response_content,
            )

            # Use existing _parse_json_response method
            entities_dicts = self._parse_json_response(response_content, data_type="entity")

            logger.info(
                "parse_entity_response_json_extracted",
                document_id=document_id,
                entities_dicts_count=len(entities_dicts),
                entities_dicts=entities_dicts,
            )

            # Convert dicts to GraphEntity objects
            entities = []
            for i, entity_dict in enumerate(entities_dicts):
                logger.info(
                    "parse_entity_response_creating_entity",
                    document_id=document_id,
                    index=i,
                    entity_dict=entity_dict,
                )

                # Generate entity ID from name
                entity_name = entity_dict.get("name", "")
                entity_id = f"{entity_name.lower().replace(' ', '_')}_{i}"

                entity = GraphEntity(
                    id=entity_id,
                    name=entity_name,
                    type=entity_dict.get("type", "ENTITY"),
                    description=entity_dict.get("description", ""),
                    source_document=document_id or entity_dict.get("source_id", ""),
                )
                entities.append(entity)

            logger.info(
                "parse_entity_response_complete",
                document_id=document_id,
                entities_count=len(entities),
            )

            return entities

        except Exception as e:
            logger.warning(
                "entity_response_parse_failed",
                error=str(e),
                document_id=document_id,
                response_preview=response_content[:200],
            )
            return []

    def _parse_relationship_response(
        self,
        response_content: str,
        entities: list[GraphEntity],
        document_id: str | None = None,
    ) -> list[GraphRelationship]:
        """Parse LLM response into GraphRelationship objects.

        Args:
            response_content: Raw LLM response text
            entities: List of entities for validation
            document_id: Optional document ID for provenance

        Returns:
            List of GraphRelationship objects
        """
        try:
            logger.info(
                "parse_relationship_response_start",
                document_id=document_id,
                response_length=len(response_content),
                response_content=response_content,
                entities_count=len(entities),
                entity_names=[e.name for e in entities],
            )

            # Use existing _parse_json_response method
            relations_dicts = self._parse_json_response(response_content, data_type="relationship")

            logger.info(
                "parse_relationship_response_json_extracted",
                document_id=document_id,
                relations_dicts_count=len(relations_dicts),
                relations_dicts=relations_dicts,
            )

            # Convert dicts to GraphRelationship objects
            relationships = []
            entity_names = {e.name.lower() for e in entities}

            for i, rel_dict in enumerate(relations_dicts):
                # Get source/target (handle both formats)
                source = rel_dict.get("source") or rel_dict.get("subject", "")
                target = rel_dict.get("target") or rel_dict.get("object", "")
                rel_type = rel_dict.get("type") or rel_dict.get("predicate", "RELATES_TO")

                logger.info(
                    "parse_relationship_response_processing",
                    document_id=document_id,
                    index=i,
                    rel_dict=rel_dict,
                    source=source,
                    target=target,
                    rel_type=rel_type,
                )

                # Validate entities exist
                if source.lower() not in entity_names or target.lower() not in entity_names:
                    logger.warning(
                        "relation_skipped_unknown_entity",
                        source=source,
                        target=target,
                        available_entities=len(entity_names),
                        entity_names_sample=list(entity_names)[:10],
                    )
                    continue

                # Generate relationship ID from source/target/type
                rel_id = f"{source.lower().replace(' ', '_')}__{rel_type}__{target.lower().replace(' ', '_')}_{i}"

                relationship = GraphRelationship(
                    id=rel_id,
                    source=source,
                    target=target,
                    type=rel_type,
                    description=rel_dict.get("description", ""),
                    source_document=document_id or rel_dict.get("source_id", ""),
                )
                relationships.append(relationship)
                logger.info(
                    "parse_relationship_response_added",
                    document_id=document_id,
                    index=i,
                    relationship=relationship,
                )

            logger.info(
                "parse_relationship_response_complete",
                document_id=document_id,
                relationships_count=len(relationships),
            )

            return relationships

        except Exception as e:
            logger.warning(
                "relationship_response_parse_failed",
                error=str(e),
                document_id=document_id,
                response_preview=response_content[:200],
            )
            return []

    async def _extract_entities_llm_only(
        self,
        text: str,
        document_id: str | None,
        model: str,
        timeout_s: int,
    ) -> list[GraphEntity]:
        """Extract entities using LLM only (fallback for SpaCy failures).

        Args:
            text: Text to extract from
            document_id: Document ID
            model: LLM model to use
            timeout_s: Timeout in seconds

        Returns:
            List of GraphEntity
        """
        prompt = DSPY_OPTIMIZED_ENTITY_PROMPT.format(
            text=text[:8000],
            domain="general",
        )

        try:
            response = await asyncio.wait_for(
                self.llm_proxy.generate(
                    LLMTask(
                        task_type=TaskType.EXTRACTION,
                        complexity=Complexity.MEDIUM,
                        quality=QualityRequirement.BALANCED,
                        prompt=prompt,
                        model_override=model,
                        max_tokens=2000,
                        temperature=0.1,
                    )
                ),
                timeout=timeout_s,
            )

            return self._parse_entity_response(response.content, document_id)

        except Exception as e:
            logger.error("llm_only_entity_extraction_failed", error=str(e))
            return []

    # =========================================================================
    # End Sprint 89: SpaCy-First Pipeline
    # =========================================================================

    async def extract_entities(
        self,
        text: str,
        document_id: str | None = None,
        domain: str | None = None,
        gleaning_steps: int | None = None,
    ) -> list[GraphEntity]:
        """Extract entities from text using 3-rank cascade fallback.

        Sprint 83 Feature 83.2: Cascade fallback strategy.
        Sprint 83 Feature 83.3: Optional gleaning multi-pass extraction.
        Sprint 89 Feature 89.1: SpaCy-First Pipeline (when enabled).

        Tries each cascade rank in order until success:
        - Rank 1: Nemotron3 (LLM-Only)
        - Rank 2: GPT-OSS:20b (LLM-Only)
        - Rank 3: Hybrid SpaCy NER + LLM

        Args:
            text: Document text to extract entities from
            document_id: Source document ID (optional)
            domain: Domain name for domain-specific prompts (Sprint 76 TD-085)
            gleaning_steps: Number of gleaning rounds (0=disabled, 1-3=enabled)
                           If None, will try to fetch from ChunkingConfig

        Returns:
            list of extracted entities as GraphEntity objects

        Raises:
            Exception: If extraction fails on all ranks

        Note:
            Sprint 89: When SpaCy-First Pipeline is enabled (default), consider using
            extract_with_spacy_first_pipeline() instead, which extracts both entities
            AND relations in a single optimized flow.
        """
        # Sprint 89: Check if SpaCy-First Pipeline is enabled
        # Note: This method only returns entities. For the full pipeline with relations,
        # use extract_with_spacy_first_pipeline() from the ingestion layer.
        if should_use_spacy_first_pipeline():
            logger.debug(
                "spacy_first_pipeline_enabled_but_extract_entities_called",
                document_id=document_id,
                hint="Consider using extract_with_spacy_first_pipeline() for better performance",
            )

        # Sprint 86.7: Apply coreference resolution as preprocessing
        # This resolves pronouns (he, she, it) to their antecedents
        text, coref_metadata = _apply_coreference_resolution(text)

        if coref_metadata.get("resolutions_count", 0) > 0:
            logger.info(
                "coreference_preprocessing_complete",
                document_id=document_id,
                resolutions=coref_metadata["resolutions_count"],
                text_delta=coref_metadata.get("resolved_length", len(text))
                - coref_metadata.get("original_length", len(text)),
            )

        # Get gleaning_steps from ChunkingConfig if not provided
        if gleaning_steps is None:
            try:
                from src.components.chunking_config import get_chunking_config_service

                chunking_service = get_chunking_config_service()
                config = await chunking_service.get_config()
                gleaning_steps = config.gleaning_steps

                logger.debug(
                    "gleaning_steps_from_config",
                    gleaning_steps=gleaning_steps,
                    document_id=document_id,
                )
            except Exception as e:
                logger.warning(
                    "failed_to_load_gleaning_config",
                    error=str(e),
                    using_default=0,
                )
                gleaning_steps = 0

        # If gleaning is enabled, use extract_entities_with_gleaning
        if gleaning_steps > 0:
            logger.info(
                "using_gleaning_extraction",
                gleaning_steps=gleaning_steps,
                document_id=document_id,
                domain=domain,
            )
            return await self.extract_entities_with_gleaning(
                text=text,
                document_id=document_id,
                domain=domain,
                gleaning_steps=gleaning_steps,
            )

        # Standard extraction (no gleaning) - use cascade fallback
        logger.info(
            "extracting_entities_with_cascade",
            text_length=len(text),
            document_id=document_id,
            domain=domain,
        )

        # Get cascade configuration for domain
        cascade = get_cascade_for_domain(domain)

        last_error: Exception | None = None

        # Try each rank in cascade
        for rank_config in cascade:
            try:
                logger.info(
                    "trying_cascade_rank",
                    rank=rank_config.rank,
                    model=rank_config.model,
                    method=rank_config.method.value,
                )

                entities = await self._extract_entities_with_rank(
                    text=text,
                    rank_config=rank_config,
                    document_id=document_id,
                    domain=domain,
                )

                logger.info(
                    "cascade_rank_success",
                    rank=rank_config.rank,
                    model=rank_config.model,
                    entity_count=len(entities),
                )

                return entities

            except Exception as e:
                last_error = e

                # Log fallback if not last rank
                if rank_config.rank < len(cascade):
                    next_rank = cascade[rank_config.rank]  # rank_config.rank is 1-indexed
                    log_cascade_fallback(
                        from_rank=rank_config.rank,
                        to_rank=next_rank.rank,
                        reason=type(e).__name__,
                        document_id=document_id,
                    )
                else:
                    logger.error(
                        "all_cascade_ranks_failed",
                        document_id=document_id,
                        error=str(e),
                    )

        # All ranks failed
        raise last_error or Exception("Extraction failed on all cascade ranks")

    async def _check_extraction_completeness(
        self,
        text: str,
        entities: list[GraphEntity],
        rank_config: CascadeRankConfig,
    ) -> bool:
        """Check if entity extraction is complete using LLM with logit bias.

        Sprint 83 Feature 83.3: Completeness check for gleaning.

        Args:
            text: Document text
            entities: Entities extracted so far
            rank_config: Cascade rank configuration

        Returns:
            True if extraction is complete (no more entities needed)
            False if there are likely missing entities
        """
        # Format extracted entities for prompt
        entity_list = "\n".join([f"- {e.name} ({e.type})" for e in entities])

        # Create completeness check prompt
        prompt = COMPLETENESS_CHECK_PROMPT.format(
            extracted_entities=entity_list,
            document_text=text[:2000],  # Limit text length to avoid token overflow
        )

        # Create LLM task with logit bias for YES/NO
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt=prompt,
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.LOW,
            max_tokens=10,  # Only need YES or NO
            temperature=0.0,  # Deterministic
            model_local=rank_config.model,
        )

        try:
            result = await self.llm_proxy.generate(task)
            response = result.content.strip().upper()

            # Check if response contains "YES" or "NO"
            if "YES" in response:
                logger.info(
                    "gleaning_completeness_check_incomplete",
                    entities_count=len(entities),
                )
                return False
            else:
                logger.info(
                    "gleaning_completeness_check_complete",
                    entities_count=len(entities),
                )
                return True

        except Exception as e:
            logger.warning(
                "gleaning_completeness_check_failed",
                error=str(e),
                assuming_incomplete=True,
            )
            # On error, assume incomplete to continue gleaning
            return False

    async def _extract_missing_entities(
        self,
        text: str,
        existing_entities: list[GraphEntity],
        rank_config: CascadeRankConfig,
        document_id: str | None = None,
    ) -> list[GraphEntity]:
        """Extract entities that were missed in previous rounds.

        Sprint 83 Feature 83.3: Continuation extraction for gleaning.

        Args:
            text: Document text
            existing_entities: Entities already extracted
            rank_config: Cascade rank configuration
            document_id: Source document ID (optional)

        Returns:
            List of newly extracted entities
        """
        # Format existing entities for prompt
        entity_list = "\n".join(
            [f"- {e.name} ({e.type}): {e.description}" for e in existing_entities]
        )

        # Create continuation prompt
        prompt = CONTINUATION_EXTRACTION_PROMPT.format(
            extracted_entities=entity_list,
            document_text=text,
        )

        # Create LLM task
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt=prompt,
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            model_local=rank_config.model,
        )

        # Add retry decorator dynamically
        @retry(
            stop=stop_after_attempt(rank_config.max_retries),
            wait=wait_exponential(
                multiplier=rank_config.retry_backoff_multiplier,
                min=1,
                max=8,
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        async def extract_with_retry() -> Any:
            result = await self.llm_proxy.generate(task)

            # Parse JSON response
            entities_data = self._parse_json_response(result.content)

            # Create GraphEntity objects
            new_entities = []
            for entity_dict in entities_data:
                try:
                    entity = GraphEntity(
                        id=str(uuid.uuid4()),
                        name=entity_dict.get("name", ""),
                        type=entity_dict.get("type", "UNKNOWN"),
                        description=entity_dict.get("description", ""),
                        properties={},
                        source_document=document_id,
                        confidence=1.0,
                    )
                    new_entities.append(entity)
                except Exception as e:
                    logger.warning(
                        "entity_creation_failed_gleaning",
                        entity_dict=entity_dict,
                        error=str(e),
                    )

            # Log LLM cost summary
            if document_id:
                log_llm_cost_summary(
                    document_id=document_id,
                    phase="entity_extraction_gleaning",
                    total_tokens=result.tokens_used,
                    prompt_tokens=result.tokens_input,
                    completion_tokens=result.tokens_output,
                    model=result.model,
                    estimated_cost_usd=result.cost_usd,
                )

            return new_entities

        # Execute with timeout
        new_entities = await self._extract_with_timeout(
            extract_with_retry,
            rank_config.entity_timeout_s,
            rank_config,
        )

        return new_entities

    def _merge_and_deduplicate_entities(
        self,
        entities: list[GraphEntity],
    ) -> list[GraphEntity]:
        """Merge and deduplicate entities from multiple gleaning rounds.

        Sprint 83 Feature 83.3: Deduplication for gleaning.

        Uses semantic similarity (name matching) to deduplicate entities.
        Preserves highest-confidence entity on duplicate.

        Args:
            entities: All entities from all gleaning rounds

        Returns:
            Deduplicated list of entities
        """
        if not entities:
            return []

        # Track unique entities by normalized name
        unique_entities: dict[str, GraphEntity] = {}
        duplicate_count = 0

        for entity in entities:
            # Normalize name for comparison (lowercase, strip whitespace)
            normalized_name = entity.name.lower().strip()

            # Check for exact match or substring match
            found_duplicate = False
            for existing_name, existing_entity in list(unique_entities.items()):
                # Case 1: Exact match (case-insensitive)
                if normalized_name == existing_name:
                    duplicate_count += 1
                    found_duplicate = True
                    # Keep entity with higher confidence
                    if entity.confidence > existing_entity.confidence:
                        unique_entities[existing_name] = entity
                    break

                # Case 2: Substring match (one is subset of other)
                if normalized_name in existing_name or existing_name in normalized_name:
                    duplicate_count += 1
                    found_duplicate = True
                    # Keep the longer, more specific entity name
                    if len(normalized_name) > len(existing_name):
                        del unique_entities[existing_name]
                        unique_entities[normalized_name] = entity
                    break

            if not found_duplicate:
                unique_entities[normalized_name] = entity

        logger.info(
            "gleaning_deduplication_complete",
            total_entities=len(entities),
            unique_entities=len(unique_entities),
            duplicates_removed=duplicate_count,
            deduplication_rate=duplicate_count / len(entities) if entities else 0,
        )

        return list(unique_entities.values())

    async def extract_entities_with_gleaning(
        self,
        text: str,
        document_id: str | None = None,
        domain: str | None = None,
        gleaning_steps: int = 0,
    ) -> list[GraphEntity]:
        """Extract entities with optional multi-pass gleaning.

        Sprint 83 Feature 83.3: Gleaning multi-pass extraction (TD-100).

        Implements Microsoft GraphRAG-style gleaning:
        1. Round 1: Initial entity extraction
        2. Completeness Check: LLM determines if extraction is complete
        3. Rounds 2+: Extract missing entities with continuation prompt
        4. Merge & Deduplicate: Combine all entities from all rounds

        Args:
            text: Document text to extract entities from
            document_id: Source document ID (optional)
            domain: Domain name for domain-specific prompts
            gleaning_steps: Number of gleaning rounds (0=disabled, 1-3=enabled)

        Returns:
            List of extracted entities (deduplicated)

        Raises:
            Exception: If extraction fails on all ranks

        Example:
            >>> service = ExtractionService()
            >>> entities = await service.extract_entities_with_gleaning(
            ...     text="Tesla was founded by Elon Musk in 2003.",
            ...     gleaning_steps=1,
            ... )
            >>> # Round 1: Extracts "Tesla", "Elon Musk"
            >>> # Completeness Check: LLM says "YES" (2003 is missing)
            >>> # Round 2: Extracts "2003"
            >>> # Result: 3 entities total
        """
        logger.info(
            "extracting_entities_with_gleaning",
            text_length=len(text),
            document_id=document_id,
            domain=domain,
            gleaning_steps=gleaning_steps,
        )

        # Get cascade configuration for domain
        cascade = get_cascade_for_domain(domain)
        rank_config = cascade[0]  # Use first rank for gleaning

        # Round 1: Initial entity extraction
        logger.info("gleaning_round_1_start", document_id=document_id)
        all_entities = await self._extract_entities_with_rank(
            text=text,
            rank_config=rank_config,
            document_id=document_id,
            domain=domain,
        )
        logger.info(
            "gleaning_round_1_complete",
            document_id=document_id,
            entities_found=len(all_entities),
        )

        # If gleaning disabled, return initial entities
        if gleaning_steps == 0:
            logger.info(
                "gleaning_disabled",
                document_id=document_id,
                total_entities=len(all_entities),
            )
            return all_entities

        # Gleaning rounds 2..N
        for gleaning_round in range(1, gleaning_steps + 1):
            logger.info(
                f"gleaning_round_{gleaning_round + 1}_start",
                document_id=document_id,
                entities_so_far=len(all_entities),
            )

            # Check completeness with logit bias
            is_complete = await self._check_extraction_completeness(
                text=text,
                entities=all_entities,
                rank_config=rank_config,
            )

            if is_complete:
                logger.info(
                    "gleaning_complete_early",
                    document_id=document_id,
                    round=gleaning_round + 1,
                    total_entities=len(all_entities),
                )
                break

            # Extract missing entities
            try:
                new_entities = await self._extract_missing_entities(
                    text=text,
                    existing_entities=all_entities,
                    rank_config=rank_config,
                    document_id=document_id,
                )

                logger.info(
                    f"gleaning_round_{gleaning_round + 1}_complete",
                    document_id=document_id,
                    new_entities_found=len(new_entities),
                    total_entities=len(all_entities) + len(new_entities),
                )

                # Add new entities to collection
                all_entities.extend(new_entities)

            except Exception as e:
                logger.error(
                    f"gleaning_round_{gleaning_round + 1}_failed",
                    document_id=document_id,
                    error=str(e),
                )
                # Continue with existing entities

        # Merge and deduplicate entities from all rounds
        deduplicated_entities = self._merge_and_deduplicate_entities(all_entities)

        logger.info(
            "gleaning_extraction_complete",
            document_id=document_id,
            total_rounds=gleaning_steps + 1,
            total_entities_before_dedup=len(all_entities),
            total_entities_after_dedup=len(deduplicated_entities),
        )

        return deduplicated_entities

    async def _extract_relationships_with_rank(
        self,
        text: str,
        entities: list[GraphEntity],
        rank_config: CascadeRankConfig,
        document_id: str | None = None,
        domain: str | None = None,
    ) -> list[GraphRelationship]:
        """Extract relationships using a specific cascade rank.

        Sprint 83 Feature 83.2: Single-rank relationship extraction with retry logic.

        Args:
            text: Document text to extract relationships from
            entities: Extracted entities from the same text
            rank_config: Cascade rank configuration
            document_id: Source document ID (optional)
            domain: Domain name for domain-specific prompts

        Returns:
            list of extracted relationships as GraphRelationship objects

        Raises:
            Exception: If extraction fails after retries for this rank
        """
        logger.info(
            "extracting_relationships_with_rank",
            rank=rank_config.rank,
            model=rank_config.model,
            method=rank_config.method.value,
            entity_count=len(entities),
            document_id=document_id,
        )

        if not entities:
            logger.warning("no_entities_for_relationship_extraction")
            return []

        # Get domain-specific or generic prompts
        _, relation_prompt = await self.get_extraction_prompts(domain)

        # Format entity list for prompt
        entity_list = "\n".join([f"- {e.name} ({e.type})" for e in entities])

        # Format prompt
        prompt = relation_prompt.format(
            entities=entity_list,
            text=text,
        )

        # Create LLM task with rank-specific model
        # Note: Both LLM-Only and Hybrid use LLM for relationship extraction
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt=prompt,
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            model_local=rank_config.model,  # Use rank-specific model
        )

        # Add retry decorator dynamically with rank-specific config
        @retry(
            stop=stop_after_attempt(rank_config.max_retries),
            wait=wait_exponential(
                multiplier=rank_config.retry_backoff_multiplier,
                min=1,
                max=8,
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        async def extract_with_retry() -> Any:
            result = await self.llm_proxy.generate(task)

            # Parse JSON response
            relationships_data = self._parse_json_response(result.content, data_type="relationship")

            # Limit relationships per document
            if len(relationships_data) > MAX_RELATIONSHIPS_PER_DOC:
                logger.warning(
                    "max_relationships_exceeded",
                    count=len(relationships_data),
                    max_allowed=MAX_RELATIONSHIPS_PER_DOC,
                )
                relationships_data = relationships_data[:MAX_RELATIONSHIPS_PER_DOC]

            # Create GraphRelationship objects
            relationships = []
            for rel_dict in relationships_data:
                try:
                    relationship = GraphRelationship(
                        id=str(uuid.uuid4()),
                        source=rel_dict.get("source", ""),
                        target=rel_dict.get("target", ""),
                        type=rel_dict.get("type", "RELATED_TO"),
                        description=rel_dict.get("description", ""),
                        properties={},
                        source_document=document_id,
                        confidence=1.0,
                    )
                    relationships.append(relationship)
                except Exception as e:
                    logger.warning(
                        "relationship_creation_failed",
                        rel_dict=rel_dict,
                        error=str(e),
                    )

            # Log LLM cost summary
            if document_id:
                # Sprint 84: Handle both old (prompt_tokens) and new (tokens_input) SDK formats
                prompt_tokens = getattr(result, "prompt_tokens", None) or getattr(
                    result, "tokens_input", 0
                )
                completion_tokens = getattr(result, "completion_tokens", None) or getattr(
                    result, "tokens_output", 0
                )
                model = getattr(result, "model", "unknown")
                cost_usd = getattr(result, "cost_usd", 0.0)
                log_llm_cost_summary(
                    document_id=document_id,
                    phase="relation_extraction",
                    total_tokens=prompt_tokens + completion_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    model=model,
                    estimated_cost_usd=cost_usd,
                )

            return relationships

        # Execute with timeout
        relationships = await self._extract_with_timeout(
            extract_with_retry,
            rank_config.relation_timeout_s,
            rank_config,
        )

        logger.info(
            "relationships_extracted_with_llm",
            rank=rank_config.rank,
            model=rank_config.model,
            count=len(relationships),
            document_id=document_id,
        )

        return relationships

    async def _extract_relationships_windowed(
        self,
        text: str,
        entities: list[GraphEntity],
        document_id: str | None = None,
        domain: str | None = None,
    ) -> list[GraphRelationship]:
        """Extract relationships using cross-sentence windows.

        Sprint 86.8: Windowed extraction for long texts.

        Splits text into overlapping 3-sentence windows, extracts relations
        from each window, then merges and deduplicates the results.

        Args:
            text: Document text
            entities: Extracted entities
            document_id: Source document ID
            domain: Domain for prompts

        Returns:
            Merged and deduplicated relationships
        """
        # Get windows
        windows = _get_cross_sentence_windows(text)

        if len(windows) <= 1:
            # No windowing needed, use standard extraction
            cascade = get_cascade_for_domain(domain)
            return await self._extract_relationships_with_rank(
                text=text,
                entities=entities,
                rank_config=cascade[0],
                document_id=document_id,
                domain=domain,
            )

        logger.info(
            "cross_sentence_windowed_extraction_start",
            window_count=len(windows),
            entity_count=len(entities),
            document_id=document_id,
        )

        all_relationships: list[GraphRelationship] = []
        seen_triples: set[tuple[str, str, str]] = set()

        cascade = get_cascade_for_domain(domain)
        rank_config = cascade[0]  # Use first rank for windowed extraction

        for i, window_text in enumerate(windows):
            try:
                # Extract from window
                window_relations = await self._extract_relationships_with_rank(
                    text=window_text,
                    entities=entities,
                    rank_config=rank_config,
                    document_id=f"{document_id}_window_{i}" if document_id else None,
                    domain=domain,
                )

                # Deduplicate: add only new (source, target, type) triples
                for rel in window_relations:
                    triple = (
                        rel.source.lower().strip(),
                        rel.target.lower().strip(),
                        rel.type.upper().strip(),
                    )
                    if triple not in seen_triples:
                        seen_triples.add(triple)
                        all_relationships.append(rel)

                logger.debug(
                    "cross_sentence_window_extracted",
                    window_index=i,
                    window_relations=len(window_relations),
                    total_unique=len(all_relationships),
                )

            except Exception as e:
                logger.warning(
                    "cross_sentence_window_extraction_failed",
                    window_index=i,
                    error=str(e),
                )
                # Continue with other windows

        logger.info(
            "cross_sentence_windowed_extraction_complete",
            window_count=len(windows),
            total_relations=len(all_relationships),
            document_id=document_id,
        )

        return all_relationships

    async def extract_relationships(
        self,
        text: str,
        entities: list[GraphEntity],
        document_id: str | None = None,
        domain: str | None = None,
    ) -> list[GraphRelationship]:
        """Extract relationships from text using 3-rank cascade fallback.

        Sprint 83 Feature 83.2: Cascade fallback strategy.

        Tries each cascade rank in order until success:
        - Rank 1: Nemotron3 (LLM-Only)
        - Rank 2: GPT-OSS:20b (LLM-Only)
        - Rank 3: Hybrid SpaCy NER + LLM (uses gpt-oss:20b for relations)

        Args:
            text: Document text to extract relationships from
            entities: Extracted entities from the same text
            document_id: Source document ID (optional)
            domain: Domain name for domain-specific prompts

        Returns:
            list of extracted relationships as GraphRelationship objects

        Raises:
            Exception: If extraction fails on all ranks
        """
        # Sprint 86.7: Apply coreference resolution for better relation extraction
        # Pronouns like "it", "they" are resolved to entity names
        text, coref_metadata = _apply_coreference_resolution(text)

        # Sprint 86.8: Check if cross-sentence windowing should be used
        use_windows = _should_use_cross_sentence(text)

        logger.info(
            "extracting_relationships_with_cascade",
            entity_count=len(entities),
            document_id=document_id,
            domain=domain,
            coreference_resolutions=coref_metadata.get("resolutions_count", 0),
            cross_sentence_enabled=use_windows,
        )

        if not entities:
            logger.warning("no_entities_for_relationship_extraction")
            return []

        # Sprint 86.8: Use windowed extraction for long texts
        if use_windows:
            return await self._extract_relationships_windowed(
                text=text,
                entities=entities,
                document_id=document_id,
                domain=domain,
            )

        # Get cascade configuration for domain
        cascade = get_cascade_for_domain(domain)

        last_error: Exception | None = None

        # Try each rank in cascade
        for rank_config in cascade:
            try:
                logger.info(
                    "trying_cascade_rank_relationships",
                    rank=rank_config.rank,
                    model=rank_config.model,
                    method=rank_config.method.value,
                )

                relationships = await self._extract_relationships_with_rank(
                    text=text,
                    entities=entities,
                    rank_config=rank_config,
                    document_id=document_id,
                    domain=domain,
                )

                logger.info(
                    "cascade_rank_success_relationships",
                    rank=rank_config.rank,
                    model=rank_config.model,
                    relationship_count=len(relationships),
                )

                return relationships

            except Exception as e:
                last_error = e

                # Log fallback if not last rank
                if rank_config.rank < len(cascade):
                    next_rank = cascade[rank_config.rank]  # rank_config.rank is 1-indexed
                    log_cascade_fallback(
                        from_rank=rank_config.rank,
                        to_rank=next_rank.rank,
                        reason=type(e).__name__,
                        document_id=document_id,
                    )
                else:
                    logger.error(
                        "all_cascade_ranks_failed_relationships",
                        document_id=document_id,
                        error=str(e),
                    )

        # All ranks failed
        raise last_error or Exception("Relationship extraction failed on all cascade ranks")

    async def _check_relationship_completeness(
        self,
        text: str,
        entities: list[GraphEntity],
        relationships: list[GraphRelationship],
        document_id: str | None = None,
    ) -> bool:
        """Check if relationship extraction is complete using LLM.

        Sprint 85 Feature 85.8: Relationship Gleaning Completeness Check.

        Args:
            text: Document text
            entities: Extracted entities
            relationships: Current relationships
            document_id: Source document ID

        Returns:
            True if extraction is INCOMPLETE (need more relationships), False if complete
        """
        # Format relationships for prompt
        rel_strs = []
        for rel in relationships:
            rel_strs.append(f"{rel.source} --[{rel.type}]--> {rel.target}")
        relationship_list = "\n".join(rel_strs) if rel_strs else "(no relationships extracted yet)"

        # Format entities for prompt
        entity_strs = [f"- {e.name} ({e.type})" for e in entities]
        entity_list = "\n".join(entity_strs)

        prompt = RELATIONSHIP_COMPLETENESS_CHECK_PROMPT.format(
            extracted_relationships=relationship_list,
            entities=entity_list,
            document_text=text[:3000],  # Limit text length
        )

        try:
            result = await self.llm_proxy.generate(
                task=LLMTask(
                    task_type=TaskType.GENERATION,  # Sprint 85 Fix: CLASSIFICATION doesn't exist
                    prompt=prompt,
                    complexity=Complexity.LOW,
                    quality_requirement=QualityRequirement.LOW,  # Sprint 85 Hotfix: STANDARD doesn't exist
                ),
            )

            response = result.content.strip().upper() if result.content else ""

            if response.startswith("YES"):
                logger.debug(
                    "relationship_gleaning_completeness_check_incomplete",
                    document_id=document_id,
                    current_relationships=len(relationships),
                )
                return True  # Incomplete - need more relationships

            logger.debug(
                "relationship_gleaning_completeness_check_complete",
                document_id=document_id,
                current_relationships=len(relationships),
            )
            return False  # Complete

        except Exception as e:
            logger.warning(
                "relationship_gleaning_completeness_check_failed",
                document_id=document_id,
                error=str(e),
            )
            # On error, assume incomplete to try gleaning
            return True

    async def _extract_missing_relationships(
        self,
        text: str,
        entities: list[GraphEntity],
        existing_relationships: list[GraphRelationship],
        document_id: str | None = None,
    ) -> list[GraphRelationship]:
        """Extract relationships that were missed in the initial pass.

        Sprint 85 Feature 85.8: Relationship Gleaning Continuation.

        Args:
            text: Document text
            entities: Extracted entities
            existing_relationships: Already extracted relationships
            document_id: Source document ID

        Returns:
            List of newly extracted relationships (excluding duplicates)
        """
        # Format existing relationships for prompt
        rel_strs = []
        for rel in existing_relationships:
            rel_strs.append(
                f'{{"source": "{rel.source}", "target": "{rel.target}", "type": "{rel.type}"}}'
            )
        relationship_list = "\n".join(rel_strs) if rel_strs else "(no relationships extracted yet)"

        # Format entities for prompt
        entity_strs = [f"- {e.name} ({e.type})" for e in entities]
        entity_list = "\n".join(entity_strs)

        prompt = RELATIONSHIP_CONTINUATION_PROMPT.format(
            extracted_relationships=relationship_list,
            entities=entity_list,
            document_text=text[:3000],  # Limit text length
        )

        try:
            result = await self.llm_proxy.generate(
                task=LLMTask(
                    task_type=TaskType.EXTRACTION,
                    prompt=prompt,
                    complexity=Complexity.MEDIUM,
                    quality_requirement=QualityRequirement.HIGH,  # Sprint 85 Hotfix: correct param name
                ),
            )

            # Parse the response
            relationships_data = self._parse_json_response(result.content, data_type="relationship")

            # Create GraphRelationship objects
            new_relationships = []
            existing_pairs = {
                (r.source.lower(), r.target.lower(), r.type.upper()) for r in existing_relationships
            }

            for rel_dict in relationships_data:
                try:
                    source = rel_dict.get("source", "")
                    target = rel_dict.get("target", "")
                    rel_type = rel_dict.get("type", "RELATES_TO")

                    # Skip duplicates
                    key = (source.lower(), target.lower(), rel_type.upper())
                    if key in existing_pairs:
                        continue

                    relationship = GraphRelationship(
                        id=str(uuid.uuid4()),
                        source=source,
                        target=target,
                        type=rel_type,
                        evidence=rel_dict.get("description", ""),
                    )
                    new_relationships.append(relationship)
                    existing_pairs.add(key)  # Avoid duplicates within this batch

                except Exception as e:
                    logger.debug(
                        "relationship_creation_failed_gleaning",
                        error=str(e),
                        rel_dict=rel_dict,
                    )

            logger.info(
                "relationship_gleaning_extracted",
                document_id=document_id,
                new_relationships=len(new_relationships),
            )

            return new_relationships

        except Exception as e:
            logger.warning(
                "relationship_gleaning_extraction_failed",
                document_id=document_id,
                error=str(e),
            )
            return []

    async def extract_relationships_with_gleaning(
        self,
        text: str,
        entities: list[GraphEntity],
        document_id: str | None = None,
        domain: str | None = None,
        gleaning_steps: int = 1,
    ) -> list[GraphRelationship]:
        """Extract relationships with multi-pass gleaning for improved ER ratio.

        Sprint 85 Feature 85.8: Relationship Gleaning for ER Ratio >= 1.0.

        Similar to entity gleaning (Microsoft GraphRAG), this method:
        1. Initial extraction of relationships
        2. Completeness check using LLM
        3. If incomplete, extract missing relationships
        4. Repeat for gleaning_steps rounds
        5. Merge and deduplicate all relationships

        Args:
            text: Document text
            entities: Extracted entities
            document_id: Source document ID
            domain: Domain name for domain-specific prompts
            gleaning_steps: Number of gleaning rounds (0=disabled, 1-2 recommended)

        Returns:
            List of all extracted relationships (deduplicated)
        """
        logger.info(
            "extracting_relationships_with_gleaning",
            entity_count=len(entities),
            document_id=document_id,
            gleaning_steps=gleaning_steps,
        )

        if not entities:
            logger.warning("no_entities_for_relationship_gleaning")
            return []

        # Initial extraction
        logger.info("relationship_gleaning_round_1_start", document_id=document_id)
        all_relationships = await self.extract_relationships(text, entities, document_id, domain)
        logger.info(
            "relationship_gleaning_round_1_complete",
            document_id=document_id,
            relationships=len(all_relationships),
        )

        # If gleaning disabled, return initial results
        if gleaning_steps == 0:
            return all_relationships

        # Gleaning rounds
        for gleaning_round in range(1, gleaning_steps + 1):
            logger.info(
                f"relationship_gleaning_round_{gleaning_round + 1}_start",
                document_id=document_id,
                current_relationships=len(all_relationships),
            )

            # Check completeness
            is_incomplete = await self._check_relationship_completeness(
                text=text,
                entities=entities,
                relationships=all_relationships,
                document_id=document_id,
            )

            if not is_incomplete:
                logger.info(
                    "relationship_gleaning_complete_early",
                    document_id=document_id,
                    round=gleaning_round + 1,
                    total_relationships=len(all_relationships),
                )
                break

            # Extract missing relationships
            new_relationships = await self._extract_missing_relationships(
                text=text,
                entities=entities,
                existing_relationships=all_relationships,
                document_id=document_id,
            )

            if new_relationships:
                all_relationships.extend(new_relationships)
                logger.info(
                    f"relationship_gleaning_round_{gleaning_round + 1}_complete",
                    document_id=document_id,
                    new_relationships=len(new_relationships),
                    total_relationships=len(all_relationships),
                )
            else:
                logger.info(
                    f"relationship_gleaning_round_{gleaning_round + 1}_no_new",
                    document_id=document_id,
                )
                break

        # Calculate ER ratio
        er_ratio = len(all_relationships) / len(entities) if entities else 0.0

        logger.info(
            "relationship_gleaning_extraction_complete",
            document_id=document_id,
            total_relationships=len(all_relationships),
            entity_count=len(entities),
            er_ratio=round(er_ratio, 2),
            gleaning_rounds_used=gleaning_round if gleaning_steps > 0 else 0,
        )

        return all_relationships

    async def extract_and_store(
        self,
        text: str,
        document_id: str,
    ) -> dict[str, Any]:
        """Extract entities and relationships from a document.

        This is the main extraction method that combines entity and relationship extraction.

        Args:
            text: Document text
            document_id: Document ID

        Returns:
            Dictionary with extraction results:
            {
                "entities": list[GraphEntity],
                "relationships": list[GraphRelationship],
                "entity_count": int,
                "relationship_count": int
            }
        """
        logger.info("extracting_from_document", document_id=document_id)

        # Extract entities first
        entities = await self.extract_entities(text, document_id)

        # Extract relationships based on entities
        relationships = await self.extract_relationships(text, entities, document_id)

        result = {
            "entities": entities,
            "relationships": relationships,
            "entity_count": len(entities),
            "relationship_count": len(relationships),
        }

        logger.info(
            "extraction_complete",
            document_id=document_id,
            entities=len(entities),
            relationships=len(relationships),
        )

        return result

    async def extract_batch(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Batch extraction from multiple documents.

        Args:
            documents: list of {"id": str, "text": str} dicts

        Returns:
            Dictionary with batch extraction results:
            {
                "total_documents": int,
                "success_count": int,
                "failed_count": int,
                "entities": list[GraphEntity],
                "relationships": list[GraphRelationship],
                "results": list[dict]
            }
        """
        logger.info("batch_extraction_started", document_count=len(documents))

        all_entities: list[GraphEntity] = []
        all_relationships: list[GraphRelationship] = []
        results = []

        for i, doc in enumerate(documents):
            try:
                extraction_result = await self.extract_and_store(
                    doc["text"],
                    doc["id"],
                )
                all_entities.extend(extraction_result["entities"])
                all_relationships.extend(extraction_result["relationships"])
                results.append(
                    {
                        "document_id": doc["id"],
                        "status": "success",
                        "entity_count": extraction_result["entity_count"],
                        "relationship_count": extraction_result["relationship_count"],
                    }
                )

                logger.info(
                    "batch_extraction_progress",
                    progress=f"{i+1}/{len(documents)}",
                )

            except Exception as e:
                logger.error(
                    "batch_extraction_document_failed",
                    document_id=doc["id"],
                    error=str(e),
                )
                results.append(
                    {
                        "document_id": doc["id"],
                        "status": "error",
                        "error": str(e),
                    }
                )

        success_count = sum(1 for r in results if r["status"] == "success")

        logger.info(
            "batch_extraction_complete",
            documents=len(documents),
            success=success_count,
            failed=len(documents) - success_count,
            total_entities=len(all_entities),
            total_relationships=len(all_relationships),
        )

        return {
            "total_documents": len(documents),
            "success_count": success_count,
            "failed_count": len(documents) - success_count,
            "entities": all_entities,
            "relationships": all_relationships,
            "results": results,
        }


# Global instance (singleton pattern)
_extraction_service: ExtractionService | None = None


def get_extraction_service() -> ExtractionService:
    """Get global extraction service instance (singleton).

    Returns:
        ExtractionService instance
    """
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService()
    return _extraction_service
