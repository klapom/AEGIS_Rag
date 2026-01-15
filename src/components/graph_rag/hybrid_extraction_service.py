"""Hybrid Extraction Service using SpaCy NER + LLM Relations.

Sprint 83 Feature 83.2: LLM Fallback & Retry Strategy (Rank 3)

This module provides a hybrid extraction approach:
- **Entities**: SpaCy multi-language NER (de_core_news_lg, en_core_web_lg, fr_core_news_lg, es_core_news_lg)
- **Relations**: LLM-based extraction (gpt-oss:20b with 600s timeout)

Hybrid extraction is used as the final fallback (Rank 3) when pure LLM extraction fails.
It maximizes recall by using fast, deterministic NER for entities and LLM for relations.
"""

import uuid
from typing import Any

import structlog

from src.core.models import GraphEntity, GraphRelationship

logger = structlog.get_logger(__name__)

# SpaCy model loading is deferred to avoid import errors if not installed
_SPACY_MODELS: dict[str, Any] = {}


class HybridExtractionService:
    """Hybrid extraction service combining SpaCy NER and LLM relation extraction.

    Provides methods for:
    - Multi-language entity extraction using SpaCy NER
    - LLM-based relationship extraction
    - Language auto-detection
    - Integration with ExtractionService cascade

    Attributes:
        llm_extraction_service: ExtractionService instance for LLM relation extraction
        supported_languages: List of supported languages (["de", "en", "fr", "es"])
    """

    # SpaCy model names for each supported language
    SPACY_MODELS = {
        "de": "de_core_news_lg",  # German
        "en": "en_core_web_lg",  # English
        "fr": "fr_core_news_lg",  # French
        "es": "es_core_news_lg",  # Spanish
    }

    # Map SpaCy entity labels to our entity types
    ENTITY_TYPE_MAPPING = {
        # Person names
        "PER": "PERSON",
        "PERSON": "PERSON",
        # Organizations
        "ORG": "ORGANIZATION",
        "NORP": "ORGANIZATION",  # Nationalities, religious/political groups
        # Locations
        "LOC": "LOCATION",
        "GPE": "LOCATION",  # Geopolitical entities (countries, cities)
        "FAC": "LOCATION",  # Buildings, airports, highways
        # Dates and times
        "DATE": "TEMPORAL",
        "TIME": "TEMPORAL",
        # Quantities
        "QUANTITY": "QUANTITY",
        "CARDINAL": "QUANTITY",
        "MONEY": "QUANTITY",
        "PERCENT": "QUANTITY",
        # Products and technologies
        "PRODUCT": "TECHNOLOGY",
        "WORK_OF_ART": "CONCEPT",
        # Events
        "EVENT": "EVENT",
        # Laws and documents
        "LAW": "DOCUMENT",
        "LANGUAGE": "CONCEPT",
        # Miscellaneous (map to generic ENTITY)
        "MISC": "ENTITY",
    }

    def __init__(self, llm_extraction_service: Any) -> None:
        """Initialize hybrid extraction service.

        Args:
            llm_extraction_service: ExtractionService instance for LLM relation extraction
        """
        self.llm_extraction_service = llm_extraction_service
        self.supported_languages = list(self.SPACY_MODELS.keys())

        logger.info(
            "hybrid_extraction_service_initialized",
            supported_languages=self.supported_languages,
        )

    def _load_spacy_model(self, language: str) -> Any:
        """Load SpaCy model for a given language (cached).

        Args:
            language: Language code (e.g., "de", "en", "fr", "es")

        Returns:
            SpaCy language model

        Raises:
            ImportError: If SpaCy is not installed
            OSError: If SpaCy model is not downloaded
        """
        global _SPACY_MODELS

        if language not in self.SPACY_MODELS:
            raise ValueError(
                f"Unsupported language: {language}. Supported: {self.supported_languages}"
            )

        # Return cached model if already loaded
        if language in _SPACY_MODELS:
            return _SPACY_MODELS[language]

        try:
            import spacy
        except ImportError as e:
            logger.error(
                "spacy_not_installed",
                error=str(e),
                hint="Run: pip install spacy spacy-transformers",
            )
            raise ImportError(
                "SpaCy is required for hybrid extraction. Install with: pip install spacy spacy-transformers"
            ) from e

        model_name = self.SPACY_MODELS[language]

        try:
            nlp = spacy.load(model_name)
            _SPACY_MODELS[language] = nlp

            logger.info(
                "spacy_model_loaded",
                language=language,
                model=model_name,
                pipeline=nlp.pipe_names,
            )

            return nlp

        except OSError as e:
            logger.error(
                "spacy_model_not_found",
                language=language,
                model=model_name,
                error=str(e),
                hint=f"Download with: python -m spacy download {model_name}",
            )
            raise OSError(
                f"SpaCy model '{model_name}' not found. Download with: python -m spacy download {model_name}"
            ) from e

    def _detect_language(self, text: str) -> str:
        """Detect language of text (simple heuristic-based).

        Args:
            text: Text to analyze

        Returns:
            Language code (e.g., "de", "en", "fr", "es")

        Note:
            This is a simple heuristic that checks for language-specific patterns.
            For production, consider using a language detection library (langdetect, fasttext).

        Sprint 92.18 Fix: Added English indicators - previously English had score=0 and
        other languages would win due to common substring matches ("de ", "en " etc.)
        """
        # Simple heuristic: Check for language-specific patterns
        text_lower = text.lower()

        # Sprint 92.18 Fix: English indicators (previously missing!)
        # English-specific patterns that rarely appear in other languages
        english_indicators = [
            " the ", " is ", " are ", " was ", " were ", " have ", " has ", " been ",
            " with ", " that ", " this ", " from ", " which ", " their ", " they ",
            " would ", " could ", " should ", " about ", " than ", " into "
        ]
        english_score = sum(1 for indicator in english_indicators if indicator in text_lower)

        # German indicators (unique German patterns)
        german_indicators = ["der ", "die ", "das ", "und ", "ist ", "von ", "zu ", "im ", " nicht ", " sich "]
        german_score = sum(1 for indicator in german_indicators if indicator in text_lower)

        # French indicators (unique French patterns)
        french_indicators = ["le ", "la ", "les ", " que ", " dans ", "pour ", " avec ", " mais ", " sont ", " aux "]
        french_score = sum(1 for indicator in french_indicators if indicator in text_lower)

        # Spanish indicators (unique Spanish patterns, removed "de ", "es ", "en " - too common in English)
        spanish_indicators = ["el ", "los ", "las ", " que ", " para ", " como ", " pero ", " está ", " son ", " muy "]
        spanish_score = sum(1 for indicator in spanish_indicators if indicator in text_lower)

        # Determine language by highest score
        scores = {
            "de": german_score,
            "en": english_score,  # Sprint 92.18 Fix: English now has indicators!
            "fr": french_score,
            "es": spanish_score,
        }

        detected_language = max(scores, key=scores.get)  # type: ignore

        # Default to English if no strong signal (threshold increased from 2 to 3)
        if scores[detected_language] < 3:
            detected_language = "en"

        logger.info(
            "language_detected",
            language=detected_language,
            scores=scores,
            text_preview=text[:100],
        )

        return detected_language

    async def extract_entities_with_spacy(
        self,
        text: str,
        document_id: str | None = None,
        language: str | None = None,
    ) -> list[GraphEntity]:
        """Extract entities from text using SpaCy NER.

        Args:
            text: Text to extract entities from
            document_id: Document ID (optional)
            language: Language code (e.g., "de", "en"). If None, auto-detect.

        Returns:
            List of GraphEntity objects extracted by SpaCy NER

        Example:
            >>> service = HybridExtractionService(extraction_service)
            >>> entities = await service.extract_entities_with_spacy(
            ...     "Apple Inc. is located in Cupertino, California.",
            ...     language="en"
            ... )
            >>> # Returns: [GraphEntity(name="Apple Inc.", type="ORGANIZATION"), ...]
        """
        logger.info(
            "extracting_entities_with_spacy",
            text_length=len(text),
            document_id=document_id,
            language=language,
        )

        # Auto-detect language if not provided
        if not language:
            language = self._detect_language(text)

        # Load SpaCy model
        nlp = self._load_spacy_model(language)

        # Process text with SpaCy
        doc = nlp(text)

        # Extract entities
        entities = []
        for ent in doc.ents:
            # Map SpaCy entity label to our entity type
            entity_type = self.ENTITY_TYPE_MAPPING.get(ent.label_, "ENTITY")

            entity = GraphEntity(
                id=str(uuid.uuid4()),
                name=ent.text.strip(),
                type=entity_type,
                description=f"Entity extracted by SpaCy NER ({language})",
                properties={
                    "spacy_label": ent.label_,
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                },
                source_document=document_id,
                confidence=1.0,  # SpaCy entities have fixed confidence
            )
            entities.append(entity)

        logger.info(
            "spacy_entities_extracted_raw",
            count=len(entities),
            language=language,
            document_id=document_id,
        )

        # Sprint 86.6: Apply entity quality filter to remove noise
        try:
            from src.components.graph_rag.entity_quality_filter import (
                get_entity_quality_filter,
                USE_ENTITY_FILTER,
            )

            if USE_ENTITY_FILTER:
                filter_instance = get_entity_quality_filter()

                # Convert GraphEntity to dict for filtering
                entity_dicts = [
                    {"name": e.name, "type": e.properties.get("spacy_label", e.type)}
                    for e in entities
                ]

                # Apply filter
                filtered_dicts, stats = filter_instance.filter(entity_dicts, lang=language)

                # Rebuild entity list with filtered entities
                filtered_names = {d["name"].lower() for d in filtered_dicts}
                entities = [
                    e for e in entities
                    if e.name.lower() in filtered_names or
                    # Also check normalized name (article removed)
                    filter_instance._remove_article(e.name, language).lower() in filtered_names
                ]

                logger.info(
                    "spacy_entities_quality_filtered",
                    original_count=stats.total_input,
                    filtered_count=stats.total_output,
                    filter_rate=f"{stats.filter_rate:.1f}%",
                    document_id=document_id,
                )

        except Exception as e:
            logger.warning(
                "entity_quality_filter_failed",
                error=str(e),
                document_id=document_id,
            )

        logger.info(
            "spacy_entities_extracted",
            count=len(entities),
            language=language,
            document_id=document_id,
            entity_types=[e.type for e in entities],
        )

        return entities

    async def extract_relationships_with_llm(
        self,
        text: str,
        entities: list[GraphEntity],
        document_id: str | None = None,
        domain: str | None = None,
    ) -> list[GraphRelationship]:
        """Extract relationships using LLM (delegates to ExtractionService).

        Args:
            text: Text to extract relationships from
            entities: Entities extracted by SpaCy NER
            document_id: Document ID (optional)
            domain: Domain name (optional)

        Returns:
            List of GraphRelationship objects extracted by LLM

        Note:
            This method is a thin wrapper around ExtractionService.extract_relationships
            to maintain consistency with hybrid extraction flow.
        """
        logger.info(
            "extracting_relationships_with_llm",
            text_length=len(text),
            entity_count=len(entities),
            document_id=document_id,
            domain=domain,
        )

        # Delegate to LLM extraction service
        relationships = await self.llm_extraction_service.extract_relationships(
            text=text,
            entities=entities,
            document_id=document_id,
            domain=domain,
        )

        logger.info(
            "llm_relationships_extracted",
            count=len(relationships),
            document_id=document_id,
        )

        return relationships

    async def extract_hybrid(
        self,
        text: str,
        document_id: str | None = None,
        domain: str | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Hybrid extraction: SpaCy entities + LLM relationships.

        Args:
            text: Text to extract from
            document_id: Document ID (optional)
            domain: Domain name (optional)
            language: Language code (e.g., "de", "en"). If None, auto-detect.

        Returns:
            Dictionary with extraction results:
            {
                "entities": list[GraphEntity],
                "relationships": list[GraphRelationship],
                "entity_count": int,
                "relationship_count": int,
                "extraction_method": "hybrid_spacy_ner_llm",
                "language": str
            }
        """
        logger.info(
            "hybrid_extraction_started",
            text_length=len(text),
            document_id=document_id,
            domain=domain,
            language=language,
        )

        # Step 1: Extract entities with SpaCy NER
        entities = await self.extract_entities_with_spacy(
            text=text,
            document_id=document_id,
            language=language,
        )

        # Step 2: Extract relationships with LLM
        relationships = await self.extract_relationships_with_llm(
            text=text,
            entities=entities,
            document_id=document_id,
            domain=domain,
        )

        result = {
            "entities": entities,
            "relationships": relationships,
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "extraction_method": "hybrid_spacy_ner_llm",
            "language": language or self._detect_language(text),
        }

        logger.info(
            "hybrid_extraction_complete",
            document_id=document_id,
            entities=len(entities),
            relationships=len(relationships),
            method="hybrid_spacy_ner_llm",
        )

        return result


def get_hybrid_extraction_service(llm_extraction_service: Any) -> HybridExtractionService:
    """Factory function to create HybridExtractionService.

    Args:
        llm_extraction_service: ExtractionService instance for LLM relation extraction

    Returns:
        HybridExtractionService instance

    Example:
        >>> from src.components.graph_rag.extraction_service import get_extraction_service
        >>> extraction_service = get_extraction_service()
        >>> hybrid_service = get_hybrid_extraction_service(extraction_service)
    """
    return HybridExtractionService(llm_extraction_service)
