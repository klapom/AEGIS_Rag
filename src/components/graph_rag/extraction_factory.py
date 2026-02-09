"""Extraction Pipeline Factory - Sprint 14 Feature 14.2.

Factory pattern for creating entity/relation extraction pipelines
with configurable backend selection (ThreePhase vs LightRAG Legacy).

Sprint 89: Added SpaCy-First Pipeline support (TD-102 Iteration 1)
- Default: SpaCy-First Pipeline (10-20x faster)
- Legacy: LLM-first cascade (set AEGIS_USE_LEGACY_CASCADE=1)

Author: Claude Code
Date: 2025-10-27
"""

from typing import Any, Protocol

import structlog

from src.config.extraction_cascade import should_use_spacy_first_pipeline

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
    - "llm_extraction": Pure LLM extraction via ExtractionService (Sprint 20) - DEFAULT

    Sprint 25 Feature 25.7: Removed "three_phase" option (deprecated per ADR-026)
    Sprint 127: Removed "lightrag_default" option (LightRAG module removed)

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
        pipeline_type = getattr(config, "extraction_pipeline", "llm_extraction")

        logger.info(
            "extraction_factory_creating_pipeline",
            pipeline_type=pipeline_type,
        )

        # Sprint 25 Feature 25.7: Removed three_phase option (deprecated per ADR-026)
        if pipeline_type == "three_phase":
            logger.warning(
                "three_phase_deprecated",
                note="three_phase extraction was removed in Sprint 25 (ADR-026). "
                "Falling back to llm_extraction.",
            )
            pipeline_type = "llm_extraction"

        if pipeline_type == "llm_extraction":
            return ExtractionPipelineFactory._create_llm_extraction(config)
        elif pipeline_type == "lightrag_default":
            logger.warning(
                "lightrag_default_deprecated",
                note="lightrag_default extraction was removed in Sprint 127. "
                "Falling back to llm_extraction.",
            )
            return ExtractionPipelineFactory._create_llm_extraction(config)
        else:
            raise ValueError(
                f"Unsupported extraction pipeline: {pipeline_type}. Must be 'llm_extraction'"
            )

    @staticmethod
    def _create_llm_extraction(config) -> ExtractionPipeline:
        """Create LLM-based extraction pipeline using ExtractionService.

        Sprint 20 Feature: Option 3 - Pure LLM entity/relation extraction
        Uses Few-Shot prompts with llama3.2:8b or gemma-3-4b for high-quality
        domain-specific extraction.

        Sprint 51: Now reads model from llm_config.yml via LLMProxyConfig

        Performance: ~200-300s/doc (slower but better quality)
        Quality: High - LLM understands technical context and German terms

        Returns:
            LLMExtractionPipeline adapter instance
        """
        from src.components.graph_rag.extraction_service import ExtractionService
        from src.components.llm_proxy.config import LLMProxyConfig

        # Sprint 51: Read extraction model from YAML config
        try:
            llm_config = LLMProxyConfig()
            extraction_model = llm_config.get_default_model("local_ollama", "extraction")
            if not extraction_model:
                extraction_model = getattr(config, "extraction_llm_model", "nemotron-3-nano")
            logger.info(
                "extraction_model_from_yaml_config",
                model=extraction_model,
                source="llm_config.yml",
            )
        except Exception as e:
            extraction_model = getattr(config, "extraction_llm_model", "nemotron-3-nano")
            logger.warning(
                "extraction_model_yaml_fallback",
                model=extraction_model,
                error=str(e),
            )

        logger.info(
            "llm_extraction_pipeline_creating",
            llm_model=extraction_model,
            temperature=0.1,
            note="Using ExtractionService with Few-Shot prompts for high-quality extraction",
        )

        class LLMExtractionPipeline:
            """Adapter: ExtractionService → LightRAG format."""

            def __init__(self, config, model_override: str = None):
                # Sprint 51: Use model from YAML config
                model = model_override or getattr(config, "extraction_llm_model", "nemotron-3-nano")
                self.service = ExtractionService(
                    llm_model=model,
                    ollama_base_url=getattr(config, "ollama_base_url", "http://localhost:11434"),
                    temperature=0.1,  # Low for consistent results
                    max_tokens=4000,
                )

                logger.info(
                    "llm_extraction_pipeline_initialized",
                    llm_model=self.service._explicit_llm_model,
                    temperature=self.service.temperature,
                )

            async def extract(
                self, text: str, document_id: str = None, domain: str | None = None
            ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
                """Extract entities and relations using LLM.

                Sprint 89: Routes to SpaCy-First Pipeline by default (10-20x faster).
                Set AEGIS_USE_LEGACY_CASCADE=1 to use legacy LLM-first cascade.

                Args:
                    text: Source text to extract from
                    document_id: Optional document ID for provenance
                    domain: Optional domain for DSPy-optimized prompts (Sprint 76 TD-085)

                Returns:
                    Tuple of (entities, relations) in LightRAG format
                """
                use_spacy_first = should_use_spacy_first_pipeline()

                logger.info(
                    "llm_extraction_starting",
                    document_id=document_id,
                    text_length=len(text),
                    domain=domain,
                    pipeline="spacy_first" if use_spacy_first else "legacy_cascade",
                )

                # Sprint 89: Route to SpaCy-First Pipeline if enabled (default)
                if use_spacy_first:
                    # SpaCy-First Pipeline: 3 stages
                    # Stage 1: SpaCy NER (~50ms)
                    # Stage 2: LLM Entity Enrichment (MANDATORY, ~5-15s)
                    # Stage 3: LLM Relation Extraction (~10-30s)
                    (
                        entities_graph,
                        relationships_graph,
                    ) = await self.service.extract_with_spacy_first_pipeline(
                        text, document_id, domain
                    )
                    logger.info(
                        "spacy_first_pipeline_complete",
                        document_id=document_id,
                        entities=len(entities_graph),
                        relations=len(relationships_graph),
                    )
                else:
                    # Legacy LLM-first cascade (slower, 300-600s per doc)
                    # Step 1: Extract entities using ExtractionService
                    # Sprint 76 Feature 76.2 (TD-085): Pass domain for prompt selection
                    entities_graph = await self.service.extract_entities(text, document_id, domain)

                    # Step 2: Extract relationships using ExtractionService
                    # Sprint 76 Feature 76.2 (TD-085): Pass domain for prompt selection
                    relationships_graph = await self.service.extract_relationships(
                        text, entities_graph, document_id, domain
                    )

                # Step 3: Convert GraphEntity → LightRAG format
                # Sprint 126: Propagate entity_sub_type for Neo4j storage
                lightrag_entities = []
                for entity in entities_graph:
                    entity_dict = {
                        "entity_name": entity.name,
                        "entity_type": entity.type,
                        "description": entity.description or f"{entity.type}: {entity.name}",
                        "source_id": entity.source_document or document_id or "unknown",
                    }
                    if entity.sub_type:
                        entity_dict["entity_sub_type"] = entity.sub_type
                    lightrag_entities.append(entity_dict)

                # Step 4: Convert GraphRelationship → LightRAG format
                # Sprint 125: Include relation type for S-P-O triples (ADR-060)
                lightrag_relations = []
                for rel in relationships_graph:
                    lightrag_relations.append(
                        {
                            "source": rel.source,
                            "target": rel.target,
                            "type": rel.type or "RELATES_TO",
                            "relation_type": rel.type or "RELATES_TO",
                            "description": rel.description
                            or f"{rel.source} {rel.type} {rel.target}",
                            "strength": 8,  # Default strength (LightRAG uses 1-10)
                        }
                    )

                logger.info(
                    "llm_extraction_complete",
                    document_id=document_id,
                    entities_extracted=len(lightrag_entities),
                    relations_extracted=len(lightrag_relations),
                    pipeline="spacy_first" if use_spacy_first else "legacy_cascade",
                )

                return (lightrag_entities, lightrag_relations)

        return LLMExtractionPipeline(config, model_override=extraction_model)


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
