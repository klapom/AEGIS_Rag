"""Domain Training Component for DSPy-based Knowledge Graph Optimization.

Sprint 45 - Feature 45.1, 45.2, 45.5, 45.6, 45.9, 45.10, 45.11: Domain Registry, DSPy Integration, Progress Tracking, Domain Classifier, Auto-Discovery, Grouped Ingestion, Data Augmentation
Sprint 117 - Feature 117.5: Batch Document Ingestion (8 SP)

This component manages domain-specific extraction prompts and training configurations
for optimizing knowledge graph construction using DSPy.

Key Features:
- Domain registry stored in Neo4j with semantic search (45.1)
- DSPy-based prompt optimization for entity/relation extraction (45.2)
- Static prompt extraction for production use (45.2)
- Structured training progress tracking with phase management (45.5)
- Document-to-domain classification using BGE-M3 (45.6)
- LLM-based domain auto-discovery from sample documents (45.9)
- Grouped ingestion with per-domain processing (45.10)
- LLM-based training data augmentation (45.11)
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

    TrainingProgressTracker (45.5)
    ├── Phase-based progress tracking (0-100%)
    ├── Event emission with callbacks
    └── Structured logging integration

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

    # Training Progress Tracker (45.5)
    >>> from src.components.domain_training import TrainingProgressTracker, TrainingPhase
    >>> tracker = TrainingProgressTracker(
    ...     training_run_id="uuid-1234",
    ...     domain_name="tech_docs",
    ...     on_progress=lambda event: print(event.message)
    ... )
    >>> tracker.enter_phase(TrainingPhase.ENTITY_OPTIMIZATION, "Starting...")
    >>> tracker.update_progress(0.5, "Epoch 5/10", {"loss": 0.3})
    >>> tracker.complete({"entity_f1": 0.85})

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

    # Training Data Augmentation
    >>> from src.components.domain_training import get_training_data_augmenter
    >>> augmenter = get_training_data_augmenter()
    >>> generated = await augmenter.augment(seed_samples, target_count=20)
    >>> print(f"Generated {len(generated)} samples")

    # Batch Document Ingestion (Sprint 117.5)
    >>> from src.components.domain_training import get_batch_ingestion_service, DocumentRequest, IngestionOptions
    >>> service = get_batch_ingestion_service()
    >>> documents = [
    ...     DocumentRequest(document_id="doc_001", content="Text...", metadata={}),
    ... ]
    >>> options = IngestionOptions(parallel_workers=4, extract_entities=True)
    >>> batch_id = await service.start_batch("tech_docs", documents, options)
    >>> status = await service.get_batch_status(batch_id)
    >>> print(f"Completed: {status['progress']['completed']}/{status['total_documents']}")
"""

from src.components.domain_training.augmentation_service import (
    AugmentationService,
    AugmentationStrategy,
    get_augmentation_service,
)
from src.components.domain_training.batch_ingestion_service import (
    BatchIngestionService,
    BatchProgress,
    DocumentRequest,
    DocumentResult,
    IngestionOptions,
    get_batch_ingestion_service,
    reset_service as reset_batch_ingestion_service,
)
from src.components.domain_training.data_augmentation import (
    TrainingDataAugmenter,
    get_training_data_augmenter,
)
from src.components.domain_training.domain_analyzer import (
    DomainAnalyzer,
    get_domain_analyzer,
)
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
from src.components.domain_training.training_progress import (
    ProgressEvent,
    TrainingPhase,
    TrainingProgressTracker,
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
    # Training Progress Tracker (45.5)
    "TrainingProgressTracker",
    "TrainingPhase",
    "ProgressEvent",
    # Domain Classifier (45.6)
    "DomainClassifier",
    "get_domain_classifier",
    "reset_classifier",
    # Domain Analyzer (46.4)
    "DomainAnalyzer",
    "get_domain_analyzer",
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
    # Training Data Augmentation (45.11, Sprint 117.4)
    "TrainingDataAugmenter",
    "get_training_data_augmenter",
    "AugmentationService",
    "AugmentationStrategy",
    "get_augmentation_service",
    # Batch Ingestion Service (Sprint 117.5)
    "BatchIngestionService",
    "DocumentRequest",
    "DocumentResult",
    "IngestionOptions",
    "BatchProgress",
    "get_batch_ingestion_service",
    "reset_batch_ingestion_service",
]
