"""Background Training Runner for DSPy Optimization.

Sprint 45 - Feature 45.3: Domain Training API

This module provides background task execution for DSPy-based domain training.
It runs entity and relation extraction optimization, tracks progress, and saves
results to Neo4j.

Key Features:
- Asynchronous DSPy optimization execution
- Real-time progress tracking to Neo4j
- Error handling and recovery
- Metric logging and evaluation
- Static prompt extraction for production use

Architecture:
    run_dspy_optimization (Background Task)
    ├── 1. Initialize DSPy optimizer with LLM model
    ├── 2. Optimize entity extraction (20-50% progress)
    ├── 3. Optimize relation extraction (50-90% progress)
    ├── 4. Extract static prompts
    ├── 5. Save to Neo4j (90-100% progress)
    └── 6. Update domain status to 'ready' or 'failed'

Progress Tracking:
    - 0-5%: Initialization
    - 5-20%: DSPy setup
    - 20-50%: Entity extraction optimization
    - 50-90%: Relation extraction optimization
    - 90-100%: Saving results

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
from src.core.exceptions import DatabaseConnectionError

logger = structlog.get_logger(__name__)


async def run_dspy_optimization(
    domain_name: str,
    training_run_id: str,
    dataset: list[dict[str, Any]],
) -> None:
    """Run DSPy optimization in background with progress logging.

    This function executes the full DSPy training pipeline:
    1. Initialize optimizer with domain's LLM model
    2. Optimize entity extraction prompts
    3. Optimize relation extraction prompts
    4. Extract static prompts for production use
    5. Save optimized prompts to domain in Neo4j
    6. Update domain status and training metrics

    Progress is logged to Neo4j TrainingLog node for real-time monitoring.

    Args:
        domain_name: Domain to train
        training_run_id: UUID of training log
        dataset: List of training samples with text, entities, relations

    Raises:
        Exception: Any error during training is logged and status updated to 'failed'
    """
    repo = get_domain_repository()

    async def log_progress(
        msg: str,
        progress: float | None = None,
        status: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Helper to log progress to Neo4j.

        Args:
            msg: Progress message
            progress: Progress percentage (0-100)
            status: Training status (pending/running/completed/failed)
            metrics: Training metrics dictionary
        """
        try:
            await repo.update_training_log(
                log_id=training_run_id,
                progress=progress or 0.0,
                message=msg,
                status=status,
                metrics=metrics,
            )
            logger.info(
                "training_progress_logged",
                domain=domain_name,
                message=msg,
                progress=progress,
                status=status,
            )
        except Exception as e:
            logger.error(
                "training_progress_log_failed",
                domain=domain_name,
                error=str(e),
            )

    try:
        # --- Phase 1: Initialization (0-5%) ---
        await log_progress("Starting DSPy optimization", progress=0.0, status="running")

        # Get domain configuration
        domain = await repo.get_domain(domain_name)
        if not domain:
            raise ValueError(f"Domain '{domain_name}' not found")

        llm_model = domain["llm_model"]

        await log_progress(
            f"Initializing DSPy optimizer with {llm_model}",
            progress=5.0,
        )

        # --- Phase 2: DSPy Setup (5-20%) ---
        optimizer = DSPyOptimizer(llm_model=llm_model)

        await log_progress(
            f"Optimizer initialized with {len(dataset)} samples",
            progress=10.0,
        )

        logger.info(
            "dspy_optimization_started",
            domain=domain_name,
            llm_model=llm_model,
            sample_count=len(dataset),
        )

        # --- Phase 3: Entity Extraction Optimization (20-50%) ---
        await log_progress(
            "Optimizing entity extraction prompts (this may take a few minutes)...",
            progress=20.0,
        )

        # Create progress callback for entity extraction
        async def entity_progress_callback(msg: str, pct: float) -> None:
            # Map 0-100% to 20-50% overall progress
            overall_pct = 20.0 + (pct * 0.30)
            await log_progress(f"Entity extraction: {msg}", progress=overall_pct)

        # Run entity extraction optimization
        entity_result = await optimizer.optimize_entity_extraction(
            training_data=dataset,
            progress_callback=entity_progress_callback,
        )

        logger.info(
            "entity_extraction_optimized",
            domain=domain_name,
            metrics=entity_result.get("metrics", {}),
        )

        await log_progress(
            "Entity extraction optimization completed",
            progress=50.0,
        )

        # --- Phase 4: Relation Extraction Optimization (50-90%) ---
        await log_progress(
            "Optimizing relation extraction prompts (this may take a few minutes)...",
            progress=55.0,
        )

        # Create progress callback for relation extraction
        async def relation_progress_callback(msg: str, pct: float) -> None:
            # Map 0-100% to 55-90% overall progress
            overall_pct = 55.0 + (pct * 0.35)
            await log_progress(f"Relation extraction: {msg}", progress=overall_pct)

        # Run relation extraction optimization
        relation_result = await optimizer.optimize_relation_extraction(
            training_data=dataset,
            progress_callback=relation_progress_callback,
        )

        logger.info(
            "relation_extraction_optimized",
            domain=domain_name,
            metrics=relation_result.get("metrics", {}),
        )

        await log_progress(
            "Relation extraction optimization completed",
            progress=90.0,
        )

        # --- Phase 5: Extract Static Prompts (90-95%) ---
        await log_progress(
            "Extracting static prompts for production use...",
            progress=92.0,
        )

        # Extract static prompts from DSPy results
        entity_prompt = extract_prompt_from_dspy_result(entity_result)
        relation_prompt = extract_prompt_from_dspy_result(relation_result)

        # Extract examples (demos)
        entity_examples = entity_result.get("demos", [])
        relation_examples = relation_result.get("demos", [])

        logger.info(
            "prompts_extracted",
            domain=domain_name,
            entity_examples_count=len(entity_examples),
            relation_examples_count=len(relation_examples),
        )

        # --- Phase 6: Save Results to Neo4j (95-100%) ---
        await log_progress(
            "Saving optimized prompts and metrics to domain...",
            progress=95.0,
        )

        # Prepare metrics
        training_metrics = {
            "entity_recall": entity_result.get("metrics", {}).get("recall", 0.0),
            "entity_precision": entity_result.get("metrics", {}).get("precision", 0.0),
            "entity_f1": entity_result.get("metrics", {}).get("f1", 0.0),
            "relation_recall": relation_result.get("metrics", {}).get("recall", 0.0),
            "relation_precision": relation_result.get("metrics", {}).get("precision", 0.0),
            "relation_f1": relation_result.get("metrics", {}).get("f1", 0.0),
            "training_samples": len(dataset),
        }

        # Update domain with optimized prompts
        await repo.update_domain_prompts(
            name=domain_name,
            entity_prompt=entity_prompt,
            relation_prompt=relation_prompt,
            entity_examples=entity_examples,
            relation_examples=relation_examples,
            metrics=training_metrics,
        )

        logger.info(
            "domain_prompts_saved",
            domain=domain_name,
            metrics=training_metrics,
        )

        # --- Phase 7: Completion (100%) ---
        await log_progress(
            "Training completed successfully!",
            progress=100.0,
            status="completed",
            metrics=training_metrics,
        )

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
        await log_progress(
            "Training cancelled by user",
            status="failed",
        )
        raise

    except ValueError as e:
        # Validation errors (e.g., domain not found)
        logger.error(
            "training_validation_error",
            domain=domain_name,
            error=str(e),
        )
        await log_progress(
            f"Training failed: {str(e)}",
            status="failed",
        )

    except DatabaseConnectionError as e:
        # Database errors
        logger.error(
            "training_database_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        await log_progress(
            f"Training failed: Database error - {str(e)}",
            status="failed",
        )

    except Exception as e:
        # Unexpected errors
        logger.error(
            "training_unexpected_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        await log_progress(
            f"Training failed: {str(e)}",
            status="failed",
        )

        # Try to update domain status to failed
        try:
            # Get domain and set status back to pending
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
