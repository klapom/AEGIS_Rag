"""Domain Training Component for DSPy-based Knowledge Graph Optimization.

Sprint 45 - Feature 45.1, 45.2, 45.6, 45.9: Domain Registry, DSPy Integration, Domain Classifier, Auto-Discovery

This component manages domain-specific extraction prompts and training configurations
for optimizing knowledge graph construction using DSPy.

Key Features:
- Domain registry stored in Neo4j with semantic search (45.1)
- DSPy-based prompt optimization for entity/relation extraction (45.2)
- Static prompt extraction for production use (45.2)
- Document-to-domain classification using BGE-M3 (45.6)
- LLM-based domain auto-discovery from sample documents (45.9)
- Training log tracking with progress and metrics
- Default "general" domain fallback
- BGE-M3 embeddings for domain matching (1024-dim)

Architecture:
    DomainRepository → Neo4j (Domain + TrainingLog nodes)
    ├── Domain nodes with entity/relation prompts
    ├── Description embeddings for semantic matching
    └── Training logs with metrics and progress

    DSPyOptimizer → Ollama LLM (qwen3:32b)
    ├── Entity extraction optimization (BootstrapFewShot)
    ├── Relation extraction optimization
    └── Progress tracking and evaluation metrics

    DomainClassifier → BGE-M3 Embeddings → Cosine Similarity
    ├── Load domain descriptions from Neo4j
    ├── Compute domain embeddings (cached)
    └── Classify documents via similarity ranking

    DomainDiscoveryService → Ollama LLM (qwen3:32b) → DomainSuggestion
    ├── Analyze 3-10 sample documents
    ├── Suggest domain name and description
    └── Predict entity/relation types

Usage:
    # Domain Repository
    >>> from src.components.domain_training import get_domain_repository
    >>> repo = get_domain_repository()
    >>> domain = await repo.get_domain("tech_docs")
    >>> if domain:
    ...     print(domain["entity_prompt"])

    # DSPy Optimizer
    >>> from src.components.domain_training import DSPyOptimizer, extract_prompt_from_dspy_result
    >>> optimizer = DSPyOptimizer(llm_model="qwen3:32b")
    >>> result = await optimizer.optimize_entity_extraction(training_data)
    >>> prompt = extract_prompt_from_dspy_result(result)

    # Domain Classifier
    >>> from src.components.domain_training import get_domain_classifier
    >>> classifier = get_domain_classifier()
    >>> await classifier.load_domains()
    >>> matches = classifier.classify_document(text, top_k=3)
    >>> print(matches[0])  # {"domain": "tech_docs", "score": 0.89}

    # Domain Discovery
    >>> from src.components.domain_training import get_domain_discovery_service
    >>> service = get_domain_discovery_service()
    >>> suggestion = await service.discover_domain(sample_texts)
    >>> print(f"Domain: {suggestion.name}, Confidence: {suggestion.confidence}")
"""

from src.components.domain_training.domain_classifier import (
    DomainClassifier,
    get_domain_classifier,
    reset_classifier,
)
from src.components.domain_training.domain_discovery import (
    DomainDiscoveryService,
    DomainSuggestion,
    get_domain_discovery_service,
)
from src.components.domain_training.domain_repository import (
    DomainRepository,
    get_domain_repository,
)
from src.components.domain_training.dspy_optimizer import (
    DSPyOptimizer,
    EntityExtractionSignature,
    RelationExtractionSignature,
)
from src.components.domain_training.grouped_ingestion import (
    GroupedIngestionProcessor,
    IngestionBatch,
    IngestionItem,
    get_grouped_ingestion_processor,
    reset_processor,
)
from src.components.domain_training.prompt_extractor import (
    extract_prompt_from_dspy_result,
    format_prompt_for_production,
    save_prompt_template,
)

__all__ = [
    # Domain Repository (45.1)
    "DomainRepository",
    "get_domain_repository",
    # DSPy Optimizer (45.2)
    "DSPyOptimizer",
    "EntityExtractionSignature",
    "RelationExtractionSignature",
    # Prompt Extractor (45.2)
    "extract_prompt_from_dspy_result",
    "format_prompt_for_production",
    "save_prompt_template",
    # Domain Classifier (45.6)
    "DomainClassifier",
    "get_domain_classifier",
    "reset_classifier",
    # Domain Discovery (45.9)
    "DomainDiscoveryService",
    "DomainSuggestion",
    "get_domain_discovery_service",
    # Grouped Ingestion (45.10)
    "GroupedIngestionProcessor",
    "IngestionItem",
    "IngestionBatch",
    "get_grouped_ingestion_processor",
    "reset_processor",
]
