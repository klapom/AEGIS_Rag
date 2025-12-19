"""Entity and Relation Extraction.

Sprint 56.2: Extraction subdomain of knowledge_graph.

Usage:
    from src.domains.knowledge_graph.extraction import (
        RelationExtractor,
        ParallelExtractor,
        ExtractionService,
    )
"""

# Re-export from components/graph_rag
from src.components.graph_rag.relation_extractor import (
    RelationExtractor,
    create_relation_extractor_from_config,
)
from src.components.graph_rag.parallel_extractor import (
    ParallelExtractor,
    get_parallel_extractor,
    extract_parallel,
)
from src.components.graph_rag.extraction_factory import (
    ExtractionPipelineFactory,
    create_extraction_pipeline_from_config,
)
from src.components.graph_rag.extraction_service import (
    ExtractionService,
    get_extraction_service,
)
from src.components.graph_rag.extraction_benchmark import (
    ExtractionBenchmark,
    run_benchmark,
)

__all__ = [
    # Relation Extractor
    "RelationExtractor",
    "create_relation_extractor_from_config",
    # Parallel Extractor
    "ParallelExtractor",
    "get_parallel_extractor",
    "extract_parallel",
    # Extraction Pipeline Factory
    "ExtractionPipelineFactory",
    "create_extraction_pipeline_from_config",
    # Extraction Service
    "ExtractionService",
    "get_extraction_service",
    # Benchmark
    "ExtractionBenchmark",
    "run_benchmark",
]
