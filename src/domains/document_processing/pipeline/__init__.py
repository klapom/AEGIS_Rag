"""LangGraph Ingestion Pipeline.

Sprint 56.3: Pipeline subdomain of document_processing.

Usage:
    from src.domains.document_processing.pipeline import (
        run_ingestion_pipeline,
        run_ingestion_pipeline_streaming,
        create_ingestion_graph,
    )
"""

# OPL-010: Re-export from components/ingestion until Sprint 58
from src.components.ingestion.ingestion_state import (
    IngestionState,
    add_error,
    calculate_progress,
    create_initial_state,
    increment_retry,
    should_retry,
)
from src.components.ingestion.langgraph_pipeline import (
    create_ingestion_graph,
    initialize_pipeline_router,
    run_batch_ingestion,
    run_ingestion_pipeline,
    run_ingestion_pipeline_streaming,
)
from src.components.ingestion.streaming_pipeline import (
    StreamingPipelineOrchestrator,
)

__all__ = [
    # State Management
    "IngestionState",
    "create_initial_state",
    "calculate_progress",
    "add_error",
    "should_retry",
    "increment_retry",
    # LangGraph Pipeline
    "create_ingestion_graph",
    "run_ingestion_pipeline",
    "run_ingestion_pipeline_streaming",
    "initialize_pipeline_router",
    "run_batch_ingestion",
    # Streaming Pipeline
    "StreamingPipelineOrchestrator",
]
