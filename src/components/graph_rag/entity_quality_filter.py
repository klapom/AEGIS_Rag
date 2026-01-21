"""Entity Quality Filter for noise reduction.

Sprint 86 Feature 86.6: Multilingual entity noise filtering.

Problem (Sprint 85 Discovery):
- SpaCy extracts 3.5x more entities than LLM, but includes noise:
  - CARDINAL: "20", "1000" (numbers)
  - ORDINAL: "first", "second"
  - MONEY: ".236 per cent"
  - Partial entities: "the Kotayk Province" (with article)

Solution:
- Filter noise SpaCy types (CARDINAL, ORDINAL, etc.)
- Remove leading articles (multilingual)
- Apply minimum length rules
- Normalize entity names

Usage:
    from src.components.graph_rag.entity_quality_filter import EntityQualityFilter

    filter = EntityQualityFilter()
    filtered_entities = filter.filter(raw_entities, lang="en")
"""

import os
import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)

# Feature flag for entity quality filtering
# Default: enabled (1) - filters noise entities
# Disable: AEGIS_USE_ENTITY_FILTER=0 if issues arise
USE_ENTITY_FILTER = os.environ.get("AEGIS_USE_ENTITY_FILTER", "1") == "1"


@dataclass
class FilterStats:
    """Statistics from entity filtering."""

    total_input: int = 0
    total_output: int = 0
    filtered_by_type: int = 0
    filtered_by_length: int = 0
    filtered_by_max_length: int = 0  # Sprint 92: Too long entities (sentences)
    filtered_by_conditional: int = 0
    articles_removed: int = 0

    @property
    def filter_rate(self) -> float:
        """Percentage of entities filtered."""
        if self.total_input == 0:
            return 0.0
        return (self.total_input - self.total_output) / self.total_input * 100


class EntityQualityFilter:
    """Multilingual entity noise filtering.

    This filter removes low-quality entities from SpaCy NER output:
    - Noise types: CARDINAL, ORDINAL, MONEY, PERCENT, QUANTITY, TIME
    - Very short entities (< min_length characters)
    - Entities that are just articles or stopwords
    - Leading articles from entity names

    Attributes:
        min_length: Minimum entity name length (default: 2)
        noise_types: SpaCy entity types to always filter
        conditional_types: Types with conditional filtering rules
        article_patterns: Language-specific article patterns
    """

    # SpaCy types to ALWAYS filter (language-agnostic!)
    NOISE_TYPES = {
        "CARDINAL",  # Numbers: "3", "100", "twenty"
        "ORDINAL",  # Ordinals: "first", "second", "3rd"
        "MONEY",  # Currency: "$100", "€50"
        "PERCENT",  # Percentages: "20%", ".236 per cent"
        "QUANTITY",  # Quantities: "3 kg", "100 meters"
        "TIME",  # Time expressions: "3 pm", "noon"
    }

    # Types to keep only if they meet conditions
    CONDITIONAL_TYPES = {
        "DATE": {"min_length": 8},  # "December 31, 2009" ✓, "2009" ✗
        "LANGUAGE": {"min_length": 3},  # "English" ✓, "EN" ✗
    }

    # Article patterns (multilingual)
    ARTICLE_PATTERNS = {
        "en": ["the ", "a ", "an "],
        "de": [
            "der ",
            "die ",
            "das ",
            "den ",
            "dem ",
            "des ",
            "ein ",
            "eine ",
            "einer ",
            "einem ",
            "einen ",
        ],
        "fr": ["le ", "la ", "les ", "l'", "un ", "une ", "des ", "du ", "de la ", "de l'"],
        "es": ["el ", "la ", "los ", "las ", "un ", "una ", "unos ", "unas ", "lo "],
        "it": ["il ", "lo ", "la ", "i ", "gli ", "le ", "un ", "uno ", "una ", "un'"],
        "pt": ["o ", "a ", "os ", "as ", "um ", "uma ", "uns ", "umas "],
    }

    # Stopwords that should never be entity names
    STOPWORD_NAMES = {
        "en": {
            "it",
            "he",
            "she",
            "they",
            "them",
            "this",
            "that",
            "these",
            "those",
            "which",
            "who",
            "what",
            "where",
            "when",
            "how",
            "all",
            "some",
            "any",
            "none",
            "each",
            "every",
            "both",
            "either",
            "neither",
        },
        "de": {
            "es",
            "er",
            "sie",
            "sie",
            "dies",
            "das",
            "diese",
            "jene",
            "welche",
            "wer",
            "was",
            "wo",
            "wann",
            "wie",
            "alle",
            "einige",
            "manche",
            "keine",
        },
    }

    def __init__(
        self,
        min_length: int = 2,
        max_length: int = 80,  # Sprint 92: Filter sentences masquerading as entities
        remove_articles: bool = True,
        filter_stopwords: bool = True,
    ):
        """Initialize the entity quality filter.

        Args:
            min_length: Minimum entity name length after normalization
            max_length: Maximum entity name length (entities longer are likely sentences).
                       Sprint 92: Added to filter out full sentences being extracted as entities.
                       Default: 80 chars (longest real entities: ~50-60 chars)
            remove_articles: Whether to remove leading articles from names
            filter_stopwords: Whether to filter pure stopword entities
        """
        self.min_length = min_length
        self.max_length = max_length
        self.remove_articles = remove_articles
        self.filter_stopwords = filter_stopwords

        logger.info(
            "entity_quality_filter_initialized",
            min_length=min_length,
            max_length=max_length,
            remove_articles=remove_articles,
            filter_stopwords=filter_stopwords,
            noise_types=list(self.NOISE_TYPES),
        )

    def filter(
        self,
        entities: list[dict],
        lang: str = "en",
    ) -> tuple[list[dict], FilterStats]:
        """Filter noise entities from SpaCy output.

        Args:
            entities: List of entity dictionaries with 'name' and 'type' keys
            lang: Language code for article removal

        Returns:
            Tuple of (filtered_entities, filter_stats)
        """
        if not USE_ENTITY_FILTER:
            return entities, FilterStats(total_input=len(entities), total_output=len(entities))

        stats = FilterStats(total_input=len(entities))
        filtered = []

        for entity in entities:
            name = entity.get("name", "").strip()
            etype = entity.get("type", "").upper()

            # Skip noise types
            if etype in self.NOISE_TYPES:
                stats.filtered_by_type += 1
                continue

            # Conditional types (e.g., DATE)
            if etype in self.CONDITIONAL_TYPES:
                rules = self.CONDITIONAL_TYPES[etype]
                if len(name) < rules.get("min_length", 0):
                    stats.filtered_by_conditional += 1
                    continue

            # Remove leading articles
            original_name = name
            if self.remove_articles:
                name = self._remove_article(name, lang)
                if name != original_name:
                    stats.articles_removed += 1

            # Check minimum length
            if len(name) < self.min_length:
                stats.filtered_by_length += 1
                continue

            # Sprint 92: Check maximum length (filter sentences masquerading as entities)
            # Entities like "Reboot the connected device by disconnecting..." are sentences
            if len(name) > self.max_length:
                logger.debug(
                    "entity_filtered_too_long",
                    name=name[:50] + "..." if len(name) > 50 else name,
                    length=len(name),
                    max_length=self.max_length,
                )
                stats.filtered_by_max_length += 1
                continue

            # Filter stopword-only entities
            if self.filter_stopwords and self._is_stopword(name, lang):
                stats.filtered_by_length += 1  # Count as length filter
                continue

            # Create filtered entity with normalized name
            filtered_entity = entity.copy()
            filtered_entity["name"] = name

            filtered.append(filtered_entity)

        stats.total_output = len(filtered)

        if stats.total_input > 0:
            logger.info(
                "entity_quality_filter_applied",
                input_count=stats.total_input,
                output_count=stats.total_output,
                filter_rate=f"{stats.filter_rate:.1f}%",
                by_type=stats.filtered_by_type,
                by_length=stats.filtered_by_length,
                by_max_length=stats.filtered_by_max_length,  # Sprint 92: Sentences
                by_conditional=stats.filtered_by_conditional,
                articles_removed=stats.articles_removed,
            )

        return filtered, stats

    def _remove_article(self, name: str, lang: str) -> str:
        """Remove leading article from entity name.

        Args:
            name: Entity name
            lang: Language code

        Returns:
            Name without leading article
        """
        patterns = self.ARTICLE_PATTERNS.get(lang, self.ARTICLE_PATTERNS.get("en", []))
        name_lower = name.lower()

        for pattern in patterns:
            if name_lower.startswith(pattern):
                # Preserve original casing for the rest
                return name[len(pattern) :].strip()

        return name

    def _is_stopword(self, name: str, lang: str) -> bool:
        """Check if name is just a stopword.

        Args:
            name: Entity name
            lang: Language code

        Returns:
            True if name is a stopword
        """
        stopwords = self.STOPWORD_NAMES.get(lang, self.STOPWORD_NAMES.get("en", set()))
        return name.lower() in stopwords


# Module-level singleton
_filter_instance = None


def get_entity_quality_filter() -> EntityQualityFilter:
    """Get or create the entity quality filter singleton."""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = EntityQualityFilter()
    return _filter_instance


def filter_entities(
    entities: list[dict],
    lang: str = "en",
) -> list[dict]:
    """Convenience function to filter entities.

    Args:
        entities: List of entity dictionaries
        lang: Language code

    Returns:
        Filtered entity list
    """
    if not USE_ENTITY_FILTER:
        return entities

    filter_instance = get_entity_quality_filter()
    filtered, stats = filter_instance.filter(entities, lang)
    return filtered
