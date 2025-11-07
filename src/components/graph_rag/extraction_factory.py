"""Extraction Pipeline Factory - Sprint 14 Feature 14.2.

Factory pattern for creating entity/relation extraction pipelines
with configurable backend selection (ThreePhase vs LightRAG Legacy).

Author: Claude Code
Date: 2025-10-27
"""

from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)


class ExtractionPipeline(Protocol):
    """Protocol defining extraction pipeline interface."""

    async def extract(
        self, text: str, document_id: str = None
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract entities and relations from text.

        Args:
            text: Source text
            document_id: Optional document ID for logging

        Returns:
            Tuple of (entities, relations)
        """
        ...


class ExtractionPipelineFactory:
    """Factory for creating extraction pipelines based on configuration.

    Supports:
    - "three_phase": ThreePhaseExtractor (SpaCy + Dedup + Gemma) - Sprint 13
    - "llm_extraction": Pure LLM extraction via ExtractionService (Sprint 20)
    - "lightrag_default": Legacy LightRAG extraction (for comparison)

    Example:
        >>> from src.core.config import get_settings
        >>> settings = get_settings()
        >>> pipeline = ExtractionPipelineFactory.create(settings)
        >>> entities, relations = await pipeline.extract(text)
    """

    @staticmethod
    def create(config) -> ExtractionPipeline:
        """Create extraction pipeline from config.

        Args:
            config: Application config with extraction_pipeline attribute

        Returns:
            ExtractionPipeline instance

        Raises:
            ValueError: If unsupported pipeline type requested
        """
        pipeline_type = getattr(config, "extraction_pipeline", "three_phase")

        logger.info(
            "extraction_factory_creating_pipeline",
            pipeline_type=pipeline_type,
            enable_legacy=getattr(config, "enable_legacy_extraction", False),
        )

        if pipeline_type == "three_phase":
            return ExtractionPipelineFactory._create_three_phase(config)
        elif pipeline_type == "llm_extraction":
            return ExtractionPipelineFactory._create_llm_extraction(config)
        elif pipeline_type == "lightrag_default":
            return ExtractionPipelineFactory._create_lightrag_legacy(config)
        else:
            raise ValueError(
                f"Unsupported extraction pipeline: {pipeline_type}. "
                f"Must be 'three_phase', 'llm_extraction', or 'lightrag_default'"
            )

    @staticmethod
    def _create_three_phase(config) -> ExtractionPipeline:
        """Create ThreePhaseExtractor pipeline.

        Returns:
            ThreePhaseExtractor instance with retry logic
        """
        from src.components.graph_rag.three_phase_extractor import ThreePhaseExtractor

        extractor = ThreePhaseExtractor(
            config=config,
            spacy_model="en_core_web_trf",
            enable_dedup=getattr(config, "enable_semantic_dedup", True),
        )

        logger.info(
            "three_phase_pipeline_created",
            spacy_model="en_core_web_trf",
            enable_dedup=getattr(config, "enable_semantic_dedup", True),
            max_retries=getattr(config, "extraction_max_retries", 3),
        )

        return extractor

    @staticmethod
    def _create_llm_extraction(config) -> ExtractionPipeline:
        """Create LLM-based extraction pipeline using ExtractionService.

        Sprint 20 Feature: Option 3 - Pure LLM entity/relation extraction
        Uses Few-Shot prompts with llama3.2:8b or gemma-3-4b for high-quality
        domain-specific extraction.

        Performance: ~200-300s/doc (slower but better quality)
        Quality: High - LLM understands technical context and German terms

        Returns:
            LLMExtractionPipeline adapter instance
        """
        from src.components.graph_rag.extraction_service import ExtractionService

        logger.info(
            "llm_extraction_pipeline_creating",
            llm_model=getattr(config, "lightrag_llm_model", "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M"),
            temperature=0.1,
            note="Using ExtractionService with Few-Shot prompts for high-quality extraction",
        )

        class LLMExtractionPipeline:
            """Adapter: ExtractionService → LightRAG format."""

            def __init__(self, config):
                # Use Gemma-3-4b (currently loaded in Ollama)
                self.service = ExtractionService(
                    llm_model=getattr(
                        config,
                        "lightrag_llm_model",
                        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M",
                    ),
                    ollama_base_url=getattr(config, "ollama_base_url", "http://localhost:11434"),
                    temperature=0.1,  # Low for consistent results
                    max_tokens=getattr(config, "lightrag_llm_max_tokens", 4000),
                )

                logger.info(
                    "llm_extraction_pipeline_initialized",
                    llm_model=self.service.llm_model,
                    temperature=self.service.temperature,
                )

            async def extract(
                self, text: str, document_id: str = None
            ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
                """Extract entities and relations using LLM.

                Args:
                    text: Source text to extract from
                    document_id: Optional document ID for provenance

                Returns:
                    Tuple of (entities, relations) in LightRAG format
                """
                logger.info(
                    "llm_extraction_starting",
                    document_id=document_id,
                    text_length=len(text),
                )

                # Step 1: Extract entities using ExtractionService
                entities_graph = await self.service.extract_entities(text, document_id)

                # Step 2: Extract relationships using ExtractionService
                relationships_graph = await self.service.extract_relationships(
                    text, entities_graph, document_id
                )

                # Step 3: Convert GraphEntity → LightRAG format
                lightrag_entities = []
                for entity in entities_graph:
                    lightrag_entities.append(
                        {
                            "entity_name": entity.name,
                            "entity_type": entity.type,
                            "description": entity.description or f"{entity.type}: {entity.name}",
                            "source_id": entity.source_document or document_id or "unknown",
                        }
                    )

                # Step 4: Convert GraphRelationship → LightRAG format
                lightrag_relations = []
                for rel in relationships_graph:
                    lightrag_relations.append(
                        {
                            "source": rel.source,
                            "target": rel.target,
                            "description": rel.description or f"{rel.source} {rel.type} {rel.target}",
                            "strength": 8,  # Default strength (LightRAG uses 1-10)
                        }
                    )

                logger.info(
                    "llm_extraction_complete",
                    document_id=document_id,
                    entities_extracted=len(lightrag_entities),
                    relations_extracted=len(lightrag_relations),
                )

                return (lightrag_entities, lightrag_relations)

        return LLMExtractionPipeline(config)

    @staticmethod
    def _create_lightrag_legacy(config) -> ExtractionPipeline:
        """Create legacy LightRAG extraction wrapper.

        Note: This is a compatibility wrapper for A/B testing.
        The legacy pipeline uses llama3.2:3b for extraction which is
        slower (~300s/doc) but can be useful for quality comparisons.

        Returns:
            LegacyLightRAGExtractor instance
        """
        # Import here to avoid circular dependencies
        from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper

        logger.warning(
            "legacy_lightrag_pipeline_created",
            note="This pipeline is slower (~300s/doc vs ~15s for three_phase). "
            "Only use for A/B testing or quality comparison.",
        )

        # Create wrapper that adapts LightRAGWrapper to ExtractionPipeline protocol
        class LegacyLightRAGExtractor:
            def __init__(self, config):
                self.wrapper = LightRAGWrapper(
                    llm_model=getattr(config, "lightrag_llm_model", "llama3.2:3b"),
                    embedding_model=getattr(config, "lightrag_embedding_model", "nomic-embed-text"),
                    working_dir=str(getattr(config, "lightrag_working_dir", "./data/lightrag")),
                    neo4j_uri=getattr(config, "neo4j_uri", "bolt://localhost:7687"),
                    neo4j_user=getattr(config, "neo4j_user", "neo4j"),
                    neo4j_password=config.neo4j_password.get_secret_value(),
                )

            async def extract(
                self, text: str, document_id: str = None
            ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
                """Extract using legacy LightRAG pipeline."""
                logger.warning(
                    "legacy_extraction_invoked",
                    document_id=document_id,
                    text_length=len(text),
                    note="Using slow legacy pipeline",
                )

                # Use LightRAG's default extraction (slow but comprehensive)
                # Note: This is a simplified wrapper - full implementation would
                # require extracting entities/relations from LightRAG's internal state
                # For now, we raise NotImplementedError to prevent accidental use
                raise NotImplementedError(
                    "Legacy LightRAG extraction not fully implemented. "
                    "Use three_phase pipeline instead."
                )

        return LegacyLightRAGExtractor(config)


def create_extraction_pipeline_from_config(config=None) -> ExtractionPipeline:
    """Convenience function to create extraction pipeline from config.

    Args:
        config: Application config (or use get_settings())

    Returns:
        ExtractionPipeline instance

    Example:
        >>> pipeline = create_extraction_pipeline_from_config()
        >>> entities, relations = await pipeline.extract(text)
    """
    if config is None:
        from src.core.config import get_settings

        config = get_settings()

    return ExtractionPipelineFactory.create(config)
