"""Prompts for LLM-based extraction and generation.

Sprint 5: Entity & Relationship Extraction
Sprint 45: Generic prompts for domain fallback
"""

from src.prompts.extraction_prompts import (
    ENTITY_EXTRACTION_PROMPT,
    GENERIC_ENTITY_EXTRACTION_PROMPT,
    GENERIC_RELATION_EXTRACTION_PROMPT,
    RELATIONSHIP_EXTRACTION_PROMPT,
)

__all__ = [
    "ENTITY_EXTRACTION_PROMPT",
    "RELATIONSHIP_EXTRACTION_PROMPT",
    "GENERIC_ENTITY_EXTRACTION_PROMPT",
    "GENERIC_RELATION_EXTRACTION_PROMPT",
]
