"""Coreference Resolution for improved relation extraction.

Sprint 86 Feature 86.7: Heuristic-based coreference resolution.

Note: coreferee is not compatible with Python 3.12+, so we implement
a simple heuristic-based approach using SpaCy NER and POS tags.

This module resolves pronouns to their antecedents, improving relation
extraction recall by ~15-20% (estimated).

Example:
    Input:  "Microsoft was founded in 1975. It later acquired GitHub."
    Output: "Microsoft was founded in 1975. Microsoft later acquired GitHub."

    Without resolution: Only {Microsoft → FOUNDED_IN → 1975}
    With resolution:    {Microsoft → FOUNDED_IN → 1975}, {Microsoft → ACQUIRED → GitHub}
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache

import spacy
import structlog
from spacy.tokens import Doc, Span, Token

logger = structlog.get_logger(__name__)


# Pronoun categories for different entity types
PRONOUNS = {
    "person_singular": {"he", "she", "him", "her", "his", "hers", "himself", "herself"},
    "person_plural": {"they", "them", "their", "theirs", "themselves"},
    "thing_singular": {"it", "its", "itself"},
    "relative": {"who", "whom", "whose", "which", "that"},
}

# All pronouns (flat set for quick lookup)
ALL_PRONOUNS = set().union(*PRONOUNS.values())

# Entity types that can be antecedents for pronouns
PERSON_TYPES = {"PERSON", "PER", "PEOPLE"}
ORG_TYPES = {"ORGANIZATION", "ORG", "COMPANY", "GPE", "NORP"}
THING_TYPES = {"PRODUCT", "WORK_OF_ART", "EVENT", "LAW", "TECHNOLOGY", "SOFTWARE"}

# German pronouns (for multilingual support)
GERMAN_PRONOUNS = {
    "person": {"er", "sie", "ihm", "ihr", "sein", "seine", "ihrer", "dessen", "deren"},
    "thing": {"es", "sein", "seine"},
}

# French pronouns
FRENCH_PRONOUNS = {
    "person": {"il", "elle", "lui", "leur", "eux", "elles", "son", "sa", "ses", "leur", "leurs"},
    "thing": {"il", "elle", "ce", "ça", "cela", "ceci"},
    "relative": {"qui", "que", "dont", "lequel", "laquelle", "lesquels", "lesquelles"},
}

# Spanish pronouns
SPANISH_PRONOUNS = {
    "person": {"él", "ella", "ellos", "ellas", "le", "les", "lo", "la", "los", "las", "su", "sus", "suyo", "suya"},
    "thing": {"ello", "lo", "la", "esto", "eso", "aquello"},
    "relative": {"que", "quien", "quienes", "cual", "cuales", "cuyo", "cuya"},
}

# All pronouns by language
PRONOUNS_BY_LANG = {
    "en": ALL_PRONOUNS,
    "de": set().union(*GERMAN_PRONOUNS.values()),
    "fr": set().union(*FRENCH_PRONOUNS.values()),
    "es": set().union(*SPANISH_PRONOUNS.values()),
}


@dataclass
class CoreferenceChain:
    """A chain of coreferent mentions."""

    antecedent: str  # The main entity name
    antecedent_type: str  # Entity type (PERSON, ORG, etc.)
    mentions: list[tuple[int, int, str]] = field(default_factory=list)  # (start, end, text)


@dataclass
class CoreferenceResult:
    """Result of coreference resolution."""

    original_text: str
    resolved_text: str
    chains: list[CoreferenceChain] = field(default_factory=list)
    resolution_count: int = 0  # Number of pronouns resolved


class HeuristicCoreferenceResolver:
    """Heuristic-based coreference resolution using SpaCy.

    This resolver uses simple heuristics to resolve pronouns:
    1. Find pronouns in text
    2. Look for the most recent named entity of appropriate type
    3. Replace pronoun with entity name

    Limitations:
    - Does not handle complex anaphora (e.g., "the company" → "Microsoft")
    - May incorrectly resolve in ambiguous contexts
    - Best for simple, well-structured text

    Attributes:
        nlp: SpaCy language model
        lang: Language code ('en', 'de', 'fr', or 'es')
        max_distance: Maximum sentence distance for antecedent search
    """

    SUPPORTED_LANGS = {"en", "de", "fr", "es"}

    def __init__(
        self,
        lang: str = "en",
        max_distance: int = 3,  # Look back max 3 sentences
        nlp: spacy.Language | None = None,
    ):
        """Initialize the resolver.

        Args:
            lang: Language code ('en', 'de', 'fr', or 'es')
            max_distance: Maximum sentences to look back for antecedent
            nlp: Optional pre-loaded SpaCy model
        """
        self.lang = lang
        self.max_distance = max_distance
        self.nlp = nlp or self._load_model(lang)

        # Select pronoun set based on language
        self._pronouns = PRONOUNS_BY_LANG.get(lang, ALL_PRONOUNS)

        logger.info(
            "coreference_resolver_initialized",
            lang=lang,
            max_distance=max_distance,
            model=self.nlp.meta.get("name", "unknown"),
        )

    @staticmethod
    @lru_cache(maxsize=4)
    def _load_model(lang: str) -> spacy.Language:
        """Load SpaCy model for language."""
        model_map = {
            "en": ["en_core_web_sm", "en_core_web_md", "en_core_web_lg"],
            "de": ["de_core_news_sm", "de_core_news_md", "de_core_news_lg"],
            "fr": ["fr_core_news_sm", "fr_core_news_md", "fr_core_news_lg"],
            "es": ["es_core_news_sm", "es_core_news_md", "es_core_news_lg"],
        }

        models = model_map.get(lang, model_map["en"])

        for model_name in models:
            try:
                return spacy.load(model_name)
            except OSError:
                continue

        # Fallback to blank model with basic components
        logger.warning(f"No SpaCy model found for {lang}, using blank model")
        return spacy.blank(lang)

    def resolve(self, text: str) -> CoreferenceResult:
        """Resolve coreferences in text.

        Args:
            text: Input text with potential pronouns

        Returns:
            CoreferenceResult with resolved text and chain information
        """
        if not text or not text.strip():
            return CoreferenceResult(original_text=text, resolved_text=text)

        doc = self.nlp(text)

        # Collect named entities with their positions
        entities = self._collect_entities(doc)

        if not entities:
            # No entities found, nothing to resolve
            return CoreferenceResult(original_text=text, resolved_text=text)

        # Find pronouns and their potential antecedents
        resolutions = []
        chains = []

        for sent_idx, sent in enumerate(doc.sents):
            for token in sent:
                if self._is_pronoun(token):
                    antecedent = self._find_antecedent(
                        token, sent_idx, entities, doc
                    )

                    if antecedent:
                        resolutions.append({
                            "start": token.idx,
                            "end": token.idx + len(token.text),
                            "pronoun": token.text,
                            "replacement": antecedent["name"],
                            "antecedent_type": antecedent["type"],
                        })

        # Apply resolutions (in reverse order to maintain positions)
        resolved_text = text
        for res in sorted(resolutions, key=lambda x: x["start"], reverse=True):
            resolved_text = (
                resolved_text[:res["start"]] +
                res["replacement"] +
                resolved_text[res["end"]:]
            )

            # Track chain
            chain = CoreferenceChain(
                antecedent=res["replacement"],
                antecedent_type=res["antecedent_type"],
                mentions=[(res["start"], res["end"], res["pronoun"])],
            )
            chains.append(chain)

        result = CoreferenceResult(
            original_text=text,
            resolved_text=resolved_text,
            chains=chains,
            resolution_count=len(resolutions),
        )

        if resolutions:
            logger.debug(
                "coreference_resolved",
                resolution_count=len(resolutions),
                text_length_change=len(resolved_text) - len(text),
            )

        return result

    def _collect_entities(self, doc: Doc) -> list[dict]:
        """Collect named entities with sentence indices."""
        entities = []

        for sent_idx, sent in enumerate(doc.sents):
            for ent in sent.ents:
                entities.append({
                    "name": ent.text,
                    "type": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "sent_idx": sent_idx,
                })

        return entities

    def _is_pronoun(self, token: Token) -> bool:
        """Check if token is a resolvable pronoun."""
        # Check POS tag and text
        if token.pos_ != "PRON":
            return False

        # Check against pronoun list
        text_lower = token.text.lower()
        return text_lower in self._pronouns

    def _find_antecedent(
        self,
        pronoun: Token,
        sent_idx: int,
        entities: list[dict],
        doc: Doc,
    ) -> dict | None:
        """Find the most likely antecedent for a pronoun.

        Uses these heuristics:
        1. Look for entity in same sentence before pronoun
        2. Look back up to max_distance sentences
        3. Prefer entities matching pronoun gender/number
        4. Prefer most recent entity
        """
        pronoun_text = pronoun.text.lower()

        # Determine entity type preference based on pronoun
        preferred_types = self._get_preferred_types(pronoun_text)

        # Search for candidates
        candidates = []

        for entity in entities:
            # Must be before pronoun
            if entity["end"] >= pronoun.idx:
                continue

            # Must be within max_distance sentences
            if sent_idx - entity["sent_idx"] > self.max_distance:
                continue

            # Calculate score
            score = 0

            # Prefer matching entity types
            if entity["type"] in preferred_types:
                score += 10

            # Prefer closer entities (recency)
            distance = sent_idx - entity["sent_idx"]
            score += (self.max_distance - distance) * 2

            # Prefer entities in same sentence
            if distance == 0:
                score += 5

            candidates.append((score, entity))

        if not candidates:
            return None

        # Return highest scoring candidate
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def _get_preferred_types(self, pronoun: str) -> set[str]:
        """Get preferred entity types for a pronoun."""
        if pronoun in PRONOUNS["person_singular"] | PRONOUNS["person_plural"]:
            return PERSON_TYPES | ORG_TYPES  # "They" can refer to orgs
        elif pronoun in PRONOUNS["thing_singular"]:
            return ORG_TYPES | THING_TYPES  # "It" for companies/products
        elif pronoun in PRONOUNS["relative"]:
            return PERSON_TYPES | ORG_TYPES | THING_TYPES
        else:
            return PERSON_TYPES | ORG_TYPES | THING_TYPES


class CoreferenceAwareExtractor:
    """Wrapper that adds coreference resolution to extraction.

    This class wraps an extraction service/function and applies
    coreference resolution before extraction.

    Usage:
        resolver = HeuristicCoreferenceResolver()
        extractor = CoreferenceAwareExtractor(resolver, base_extractor)
        result = await extractor.extract(text)
    """

    def __init__(
        self,
        resolver: HeuristicCoreferenceResolver,
        enabled: bool = True,
    ):
        """Initialize the wrapper.

        Args:
            resolver: Coreference resolver instance
            enabled: Whether resolution is enabled (can be toggled)
        """
        self.resolver = resolver
        self.enabled = enabled

    def preprocess(self, text: str) -> tuple[str, CoreferenceResult | None]:
        """Preprocess text with coreference resolution.

        Args:
            text: Original text

        Returns:
            Tuple of (processed_text, resolution_result)
        """
        if not self.enabled:
            return text, None

        result = self.resolver.resolve(text)

        if result.resolution_count > 0:
            logger.info(
                "coreference_preprocessing_applied",
                original_length=len(text),
                resolved_length=len(result.resolved_text),
                resolutions=result.resolution_count,
            )

        return result.resolved_text, result


# Module-level singleton for easy access
_resolver_cache: dict[str, HeuristicCoreferenceResolver] = {}


def get_coreference_resolver(lang: str = "en") -> HeuristicCoreferenceResolver:
    """Get or create a coreference resolver for the given language.

    This function caches resolvers to avoid repeated model loading.

    Args:
        lang: Language code ('en' or 'de')

    Returns:
        HeuristicCoreferenceResolver instance
    """
    if lang not in _resolver_cache:
        _resolver_cache[lang] = HeuristicCoreferenceResolver(lang=lang)
    return _resolver_cache[lang]


def resolve_coreferences(text: str, lang: str = "en") -> str:
    """Convenience function to resolve coreferences in text.

    Args:
        text: Input text
        lang: Language code

    Returns:
        Text with pronouns replaced by antecedents
    """
    resolver = get_coreference_resolver(lang)
    result = resolver.resolve(text)
    return result.resolved_text
