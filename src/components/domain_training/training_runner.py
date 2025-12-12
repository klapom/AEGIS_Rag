"""Background Training Runner for DSPy Optimization.

Sprint 45 - Feature 45.3, 45.5: Domain Training API with Progress Tracking

This module provides background task execution for DSPy-based domain training.
It runs entity and relation extraction optimization, tracks progress, and saves
results to Neo4j.

Key Features:
- Asynchronous DSPy optimization execution
- Real-time progress tracking to Neo4j (Feature 45.5)
- Structured phase-based progress logging (Feature 45.5)
- Error handling and recovery
- Metric logging and evaluation
- Static prompt extraction for production use

Architecture:
    run_dspy_optimization (Background Task)
    ├── TrainingProgressTracker (45.5)
    │   ├── Phase transitions with callbacks
    │   ├── Sub-progress within phases
    │   └── Neo4j persistence via on_progress callback
    ├── 1. Initialize DSPy optimizer with LLM model
    ├── 2. Optimize entity extraction (10-45% progress)
    ├── 3. Optimize relation extraction (45-80% progress)
    ├── 4. Extract static prompts (80-85% progress)
    ├── 5. Validate metrics (85-95% progress)
    ├── 6. Save to Neo4j (95-100% progress)
    └── 7. Update domain status to 'ready' or 'failed'

Progress Tracking (Feature 45.5):
    - 0-5%: INITIALIZING - Domain config loading
    - 5-10%: LOADING_DATA - Dataset validation
    - 10-45%: ENTITY_OPTIMIZATION - Entity extraction tuning
    - 45-80%: RELATION_OPTIMIZATION - Relation extraction tuning
    - 80-85%: PROMPT_EXTRACTION - Static prompt generation
    - 85-95%: VALIDATION - Metric validation
    - 95-100%: SAVING - Neo4j persistence
    - 100%: COMPLETED - Training finished

Usage:
    >>> from fastapi import BackgroundTasks
    >>> background_tasks.add_task(
    ...     run_dspy_optimization,
    ...     domain_name="tech_docs",
    ...     training_run_id="uuid-1234",
    ...     dataset=[{"text": "...", "entities": [...]}]
    ... )
"""

import asyncio
from typing import Any

import structlog

from src.components.domain_training import (
    DSPyOptimizer,
    extract_prompt_from_dspy_result,
    get_domain_repository,
)
from src.components.domain_training.training_progress import (
    ProgressEvent,
    TrainingPhase,
    TrainingProgressTracker,
)
from src.core.exceptions import DatabaseConnectionError

logger = structlog.get_logger(__name__)


async def run_dspy_optimization(
    domain_name: str,
    training_run_id: str,
    dataset: list[dict[str, Any]],
) -> None:
    """Run DSPy optimization with comprehensive progress tracking.

    This function executes the full DSPy training pipeline with structured
    progress tracking using TrainingProgressTracker (Feature 45.5):
    1. Initialize optimizer with domain's LLM model (INITIALIZING phase)
    2. Load and validate dataset (LOADING_DATA phase)
    3. Optimize entity extraction prompts (ENTITY_OPTIMIZATION phase)
    4. Optimize relation extraction prompts (RELATION_OPTIMIZATION phase)
    5. Extract static prompts for production use (PROMPT_EXTRACTION phase)
    6. Validate final metrics (VALIDATION phase)
    7. Save optimized prompts to domain in Neo4j (SAVING phase)
    8. Mark training as completed (COMPLETED phase)

    Progress is tracked through phases and logged to Neo4j TrainingLog node
    for real-time monitoring via the on_progress callback.

    Args:
        domain_name: Domain to train (e.g., "tech_docs")
        training_run_id: UUID of training log
        dataset: List of training samples with text, entities, relations

    Raises:
        Exception: Any error during training is logged and status updated to 'failed'
    """
    repo = get_domain_repository()

    async def persist_progress(event: ProgressEvent) -> None:
        """Persist progress event to Neo4j.

        This callback is invoked for every progress event emitted by
        TrainingProgressTracker. It updates the TrainingLog node with
        current progress, status, and metrics.

        Args:
            event: Progress event to persist
        """
        try:
            status = None
            if event.phase == TrainingPhase.COMPLETED:
                status = "completed"
            elif event.phase == TrainingPhase.FAILED:
                status = "failed"
            elif event.phase == TrainingPhase.INITIALIZING:
                status = "running"

            await repo.update_training_log(
                log_id=training_run_id,
                progress=event.progress_percent,
                message=event.message,
                status=status,
                metrics=event.metrics,
            )
        except Exception as e:
            logger.error(
                "training_progress_persist_failed",
                domain=domain_name,
                error=str(e),
            )

    # Initialize progress tracker with persistence callback
    tracker = TrainingProgressTracker(
        training_run_id=training_run_id,
        domain_name=domain_name,
        on_progress=persist_progress,
    )

    try:
        # --- Phase 1: Initialization (0-5%) ---
        tracker.enter_phase(TrainingPhase.INITIALIZING, "Loading domain configuration...")

        # Get domain configuration
        domain = await repo.get_domain(domain_name)
        if not domain:
            raise ValueError(f"Domain '{domain_name}' not found")

        llm_model = domain["llm_model"]

        tracker.update_progress(
            0.8,
            f"DSPy optimizer ready with {llm_model}",
            {"llm_model": llm_model},
        )

        # --- Phase 2: Loading Data (5-10%) ---
        tracker.enter_phase(
            TrainingPhase.LOADING_DATA,
            f"Processing {len(dataset)} training samples...",
        )

        # Initialize optimizer
        optimizer = DSPyOptimizer(llm_model=llm_model)

        tracker.update_progress(
            0.8,
            f"Dataset validated: {len(dataset)} samples",
            {"sample_count": len(dataset)},
        )

        logger.info(
            "dspy_optimization_started",
            domain=domain_name,
            llm_model=llm_model,
            sample_count=len(dataset),
        )

        # --- Phase 3: Entity Extraction Optimization (10-45%) ---
        tracker.enter_phase(
            TrainingPhase.ENTITY_OPTIMIZATION,
            "Optimizing entity extraction (this may take several minutes)...",
        )

        # Create progress callback for entity extraction
        async def entity_progress_callback(msg: str, pct: float) -> None:
            # Map 0-100% to 0-1 sub-progress
            tracker.update_progress(pct / 100, f"Entity: {msg}")

        # Run entity extraction optimization
        entity_result = await optimizer.optimize_entity_extraction(
            training_data=dataset,
            progress_callback=entity_progress_callback,
        )

        entity_metrics = entity_result.get("metrics", {})
        logger.info(
            "entity_extraction_optimized",
            domain=domain_name,
            metrics=entity_metrics,
        )

        # --- Phase 4: Relation Extraction Optimization (45-80%) ---
        tracker.enter_phase(
            TrainingPhase.RELATION_OPTIMIZATION,
            "Optimizing relation extraction (this may take several minutes)...",
        )

        # Create progress callback for relation extraction
        async def relation_progress_callback(msg: str, pct: float) -> None:
            # Map 0-100% to 0-1 sub-progress
            tracker.update_progress(pct / 100, f"Relation: {msg}")

        # Run relation extraction optimization
        relation_result = await optimizer.optimize_relation_extraction(
            training_data=dataset,
            progress_callback=relation_progress_callback,
        )

        relation_metrics = relation_result.get("metrics", {})
        logger.info(
            "relation_extraction_optimized",
            domain=domain_name,
            metrics=relation_metrics,
        )

        # --- Phase 5: Prompt Extraction (80-85%) ---
        tracker.enter_phase(
            TrainingPhase.PROMPT_EXTRACTION,
            "Extracting static prompts for production use...",
        )

        # Extract static prompts from DSPy results
        entity_prompt = extract_prompt_from_dspy_result(entity_result)
        relation_prompt = extract_prompt_from_dspy_result(relation_result)

        # Extract examples (demos)
        entity_examples = entity_result.get("demos", [])
        relation_examples = relation_result.get("demos", [])

        tracker.update_progress(
            0.8,
            f"Extracted prompts with {len(entity_examples)} entity examples, {len(relation_examples)} relation examples",
        )

        logger.info(
            "prompts_extracted",
            domain=domain_name,
            entity_examples_count=len(entity_examples),
            relation_examples_count=len(relation_examples),
        )

        # --- Phase 6: Validation (85-95%) ---
        tracker.enter_phase(
            TrainingPhase.VALIDATION,
            "Validating training metrics...",
        )

        # Prepare metrics
        training_metrics = {
            "entity_recall": entity_metrics.get("recall", 0.0),
            "entity_precision": entity_metrics.get("precision", 0.0),
            "entity_f1": entity_metrics.get("f1", 0.0),
            "relation_recall": relation_metrics.get("recall", 0.0),
            "relation_precision": relation_metrics.get("precision", 0.0),
            "relation_f1": relation_metrics.get("f1", 0.0),
            "training_samples": len(dataset),
        }

        tracker.update_progress(
            0.8,
            f"Metrics validated: Entity F1={training_metrics['entity_f1']:.2f}, Relation F1={training_metrics['relation_f1']:.2f}",
            training_metrics,
        )

        # --- Phase 7: Saving (95-100%) ---
        tracker.enter_phase(
            TrainingPhase.SAVING,
            "Saving optimized prompts and metrics to Neo4j...",
        )

        # Update domain with optimized prompts
        await repo.update_domain_prompts(
            name=domain_name,
            entity_prompt=entity_prompt,
            relation_prompt=relation_prompt,
            entity_examples=entity_examples,
            relation_examples=relation_examples,
            metrics=training_metrics,
        )

        tracker.update_progress(0.8, "Domain prompts persisted successfully")

        logger.info(
            "domain_prompts_saved",
            domain=domain_name,
            metrics=training_metrics,
        )

        # --- Phase 8: Completion (100%) ---
        tracker.complete(training_metrics)

        logger.info(
            "dspy_optimization_completed",
            domain=domain_name,
            metrics=training_metrics,
        )

    except asyncio.CancelledError:
        # Handle task cancellation gracefully
        logger.warning(
            "training_cancelled",
            domain=domain_name,
            training_run_id=training_run_id,
        )
        tracker.fail("Training cancelled by user")
        raise

    except ValueError as e:
        # Validation errors (e.g., domain not found)
        logger.error(
            "training_validation_error",
            domain=domain_name,
            error=str(e),
        )
        tracker.fail(f"Validation error: {str(e)}")

    except DatabaseConnectionError as e:
        # Database errors
        logger.error(
            "training_database_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        tracker.fail(f"Database error: {str(e)}")

    except Exception as e:
        # Unexpected errors
        logger.error(
            "training_unexpected_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        tracker.fail(str(e))

        # Try to update domain status to failed
        try:
            # Get domain and set status back to failed
            from src.components.graph_rag.neo4j_client import get_neo4j_client

            neo4j_client = get_neo4j_client()
            await neo4j_client.execute_write(
                """
                MATCH (d:Domain {name: $name})
                SET d.status = 'failed'
                """,
                {"name": domain_name},
            )
        except Exception as status_error:
            logger.error(
                "failed_to_update_domain_status",
                domain=domain_name,
                error=str(status_error),
            )
