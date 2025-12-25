"""Background Training Runner for DSPy Optimization.

Sprint 45 - Feature 45.3, 45.5, 45.13: Domain Training API with Progress Tracking & SSE

This module provides background task execution for DSPy-based domain training.
It runs entity and relation extraction optimization, tracks progress, and saves
results to Neo4j.

Key Features:
- Asynchronous DSPy optimization execution
- Real-time progress tracking to Neo4j (Feature 45.5)
- SSE streaming with full LLM interaction details (Feature 45.13)
- JSONL logging for later DSPy evaluation (Feature 45.13)
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
    ├── TrainingEventStream (45.13)
    │   ├── SSE event queue for real-time streaming
    │   ├── Full LLM interaction logging (prompts/responses)
    │   └── JSONL file export (optional)
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
    ...     dataset=[{"text": "...", "entities": [...]}],
    ...     log_path="/var/log/aegis/training/tech_docs.jsonl"
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
from src.components.domain_training.training_stream import (
    EventType,
    get_training_stream,
)
from src.core.exceptions import DatabaseConnectionError

logger = structlog.get_logger(__name__)


async def run_dspy_optimization(
    domain_name: str,
    training_run_id: str,
    dataset: list[dict[str, Any]],
    log_path: str | None = None,
    create_domain_if_not_exists: bool = False,
) -> None:
    """Run DSPy optimization with comprehensive progress tracking and SSE streaming.

    Feature 64.2 Part 2: Transactional Domain Creation

    This function executes the full DSPy training pipeline with structured
    progress tracking using TrainingProgressTracker (Feature 45.5) and
    real-time SSE streaming using TrainingEventStream (Feature 45.13):
    1. Initialize optimizer with domain's LLM model (INITIALIZING phase)
    2. Load and validate dataset (LOADING_DATA phase)
    3. Optimize entity extraction prompts (ENTITY_OPTIMIZATION phase)
    4. Optimize relation extraction prompts (RELATION_OPTIMIZATION phase)
    5. Extract static prompts for production use (PROMPT_EXTRACTION phase)
    6. Validate final metrics (VALIDATION phase)
    7. Save optimized prompts to domain in Neo4j (SAVING phase)
    8. Mark training as completed (COMPLETED phase)

    **Transactional Behavior (Feature 64.2 Part 2):**
    If `create_domain_if_not_exists=True`, the domain will be created transactionally
    as part of the training process. If training fails at any point (validation,
    database errors, optimization failures), the entire transaction is rolled back
    and no domain will persist in Neo4j.

    Progress is tracked through phases and logged to Neo4j TrainingLog node
    for real-time monitoring via the on_progress callback.

    SSE streaming (Feature 45.13) provides:
    - Full LLM prompts and responses (NOT truncated)
    - Sample processing details
    - Evaluation scores
    - Optional JSONL file export for later DSPy evaluation

    Args:
        domain_name: Domain to train (e.g., "tech_docs")
        training_run_id: UUID of training log
        dataset: List of training samples with text, entities, relations
        log_path: Optional path to save training events as JSONL
        create_domain_if_not_exists: If True, create domain transactionally with rollback support

    Raises:
        Exception: Any error during training is logged and status updated to 'failed'
    """
    repo = get_domain_repository()

    # Initialize SSE stream (Feature 45.13)
    stream = get_training_stream()
    stream.start_stream(training_run_id, domain_name, log_path)

    def emit_sse(
        event_type: EventType,
        progress: float,
        phase: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Emit an SSE event to the training stream."""
        stream.emit(
            training_run_id=training_run_id,
            event_type=event_type,
            domain=domain_name,
            progress_percent=progress,
            phase=phase,
            message=message,
            data=data,
        )

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

    # Track if we need to create domain after successful training (deferred commit)
    is_new_domain = False
    domain_config = None

    try:
        # --- Phase 1: Initialization (0-5%) ---
        tracker.enter_phase(TrainingPhase.INITIALIZING, "Loading domain configuration...")
        emit_sse(EventType.STARTED, 0.0, "initializing", "Training started")

        # Get domain configuration or prepare to create it after training
        domain = await repo.get_domain(domain_name)

        if not domain and create_domain_if_not_exists:
            logger.info(
                "new_domain_deferred_creation",
                domain=domain_name,
                training_run_id=training_run_id,
                note="Domain will be created ONLY after successful training",
            )
            # Use deferred commit pattern: Create domain AFTER training succeeds
            # This ensures rollback-like behavior without long-running transactions
            is_new_domain = True

            # Use default LLM model from settings for new domains
            from src.core.config import get_settings

            settings = get_settings()
            llm_model = settings.lightrag_llm_model

            # Store config for later domain creation (after training succeeds)
            domain_config = {
                "name": domain_name,
                "llm_model": llm_model,
                "description": f"Domain {domain_name}",  # Basic description
            }

            logger.info(
                "using_default_llm_model_for_new_domain",
                domain=domain_name,
                llm_model=llm_model,
            )
        elif not domain:
            raise ValueError(f"Domain '{domain_name}' not found")
        else:
            llm_model = domain["llm_model"]

        tracker.update_progress(
            0.8,
            f"DSPy optimizer ready with {llm_model}",
            {"llm_model": llm_model},
        )
        emit_sse(
            EventType.PROGRESS_UPDATE,
            5.0,
            "initializing",
            f"DSPy optimizer ready with {llm_model}",
            {"llm_model": llm_model},
        )

        # --- Phase 2: Loading Data (5-10%) ---
        tracker.enter_phase(
            TrainingPhase.LOADING_DATA,
            f"Processing {len(dataset)} training samples...",
        )
        emit_sse(
            EventType.PHASE_CHANGED,
            5.0,
            "loading_data",
            f"Processing {len(dataset)} training samples...",
            {"sample_count": len(dataset)},
        )

        # Initialize optimizer with stream for LLM interaction capture
        optimizer = DSPyOptimizer(llm_model=llm_model)

        # Pass stream to optimizer for detailed LLM interaction capture
        optimizer.set_event_stream(stream, training_run_id)

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
        emit_sse(
            EventType.PHASE_CHANGED,
            10.0,
            "entity_optimization",
            "Starting entity extraction optimization...",
        )

        # Create progress callback for entity extraction with SSE events
        async def entity_progress_callback(msg: str, pct: float) -> None:
            # Map 0-100% to 10-45% global progress
            global_pct = 10.0 + (pct * 0.35)
            tracker.update_progress(pct / 100, f"Entity: {msg}")
            emit_sse(
                EventType.PROGRESS_UPDATE,
                global_pct,
                "entity_optimization",
                f"Entity: {msg}",
            )

        # Run entity extraction optimization
        entity_result = await optimizer.optimize_entity_extraction(
            training_data=dataset,
            progress_callback=entity_progress_callback,
        )

        entity_metrics = entity_result.get("metrics", {})
        emit_sse(
            EventType.EVALUATION_RESULT,
            45.0,
            "entity_optimization",
            f"Entity optimization complete - F1: {entity_metrics.get('f1', 0):.3f}",
            {"metrics": entity_metrics, "type": "entity_extraction"},
        )
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
        emit_sse(
            EventType.PHASE_CHANGED,
            45.0,
            "relation_optimization",
            "Starting relation extraction optimization...",
        )

        # Create progress callback for relation extraction with SSE events
        async def relation_progress_callback(msg: str, pct: float) -> None:
            # Map 0-100% to 45-80% global progress
            global_pct = 45.0 + (pct * 0.35)
            tracker.update_progress(pct / 100, f"Relation: {msg}")
            emit_sse(
                EventType.PROGRESS_UPDATE,
                global_pct,
                "relation_optimization",
                f"Relation: {msg}",
            )

        # Run relation extraction optimization
        relation_result = await optimizer.optimize_relation_extraction(
            training_data=dataset,
            progress_callback=relation_progress_callback,
        )

        relation_metrics = relation_result.get("metrics", {})
        emit_sse(
            EventType.EVALUATION_RESULT,
            80.0,
            "relation_optimization",
            f"Relation optimization complete - F1: {relation_metrics.get('f1', 0):.3f}",
            {"metrics": relation_metrics, "type": "relation_extraction"},
        )
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
        emit_sse(
            EventType.PHASE_CHANGED,
            80.0,
            "prompt_extraction",
            "Extracting static prompts for production use...",
        )

        # Extract static prompts from DSPy results
        # extract_prompt_from_dspy_result returns a dict with prompt_template key
        entity_prompt_data = extract_prompt_from_dspy_result(entity_result)
        relation_prompt_data = extract_prompt_from_dspy_result(relation_result)

        # Get the actual prompt template strings for Neo4j storage
        entity_prompt = entity_prompt_data.get("prompt_template", "")
        relation_prompt = relation_prompt_data.get("prompt_template", "")

        # Extract examples (demos)
        entity_examples = entity_result.get("demos", [])
        relation_examples = relation_result.get("demos", [])

        tracker.update_progress(
            0.8,
            f"Extracted prompts with {len(entity_examples)} entity examples, {len(relation_examples)} relation examples",
        )
        emit_sse(
            EventType.PROGRESS_UPDATE,
            85.0,
            "prompt_extraction",
            f"Extracted {len(entity_examples)} entity examples, {len(relation_examples)} relation examples",
            {
                "entity_prompt": entity_prompt,  # FULL prompt (NOT truncated)
                "relation_prompt": relation_prompt,  # FULL prompt (NOT truncated)
                "entity_examples_count": len(entity_examples),
                "relation_examples_count": len(relation_examples),
            },
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
        emit_sse(
            EventType.PHASE_CHANGED,
            85.0,
            "validation",
            "Validating training metrics...",
        )

        # Prepare metrics (DSPy returns "val_f1" for validation F1 score)
        training_metrics = {
            "entity_recall": entity_metrics.get("recall", 0.0),
            "entity_precision": entity_metrics.get("precision", 0.0),
            "entity_f1": entity_metrics.get("val_f1", entity_metrics.get("f1", 0.0)),
            "relation_recall": relation_metrics.get("recall", 0.0),
            "relation_precision": relation_metrics.get("precision", 0.0),
            "relation_f1": relation_metrics.get("val_f1", relation_metrics.get("f1", 0.0)),
            "training_samples": len(dataset),
        }

        tracker.update_progress(
            0.8,
            f"Metrics validated: Entity F1={training_metrics['entity_f1']:.2f}, Relation F1={training_metrics['relation_f1']:.2f}",
            training_metrics,
        )
        emit_sse(
            EventType.EVALUATION_RESULT,
            95.0,
            "validation",
            f"Final metrics validated - Entity F1: {training_metrics['entity_f1']:.3f}, Relation F1: {training_metrics['relation_f1']:.3f}",
            {"final_metrics": training_metrics},
        )

        # --- Phase 7: Saving (95-100%) ---
        tracker.enter_phase(
            TrainingPhase.SAVING,
            "Saving optimized prompts and metrics to Neo4j...",
        )
        emit_sse(
            EventType.PHASE_CHANGED,
            95.0,
            "saving",
            "Saving optimized prompts and metrics to Neo4j...",
        )

        # Feature 64.2 Part 2: Transactional domain creation
        # If this is a new domain, create it atomically with training results
        # using a transaction. If save fails, domain won't be created.
        if is_new_domain and domain_config:
            logger.info(
                "creating_domain_with_training_results_transactionally",
                domain=domain_name,
            )

            # Use transaction to create domain + save training results atomically
            async with repo.transaction() as tx:
                # Step 1: Create domain with training status
                # We need to generate description embedding first
                from src.components.vector_search import EmbeddingService

                embedding_service = EmbeddingService()
                description_embedding = await embedding_service.embed_single(
                    domain_config["description"]
                )

                await repo.create_domain(
                    name=domain_config["name"],
                    description=domain_config["description"],
                    llm_model=domain_config["llm_model"],
                    description_embedding=description_embedding,
                    status="training",
                    tx=tx,
                )

                logger.info(
                    "new_domain_created_in_transaction",
                    domain=domain_name,
                )

                # Step 2: Save training results within same transaction
                await repo.save_training_results(
                    domain_name=domain_name,
                    entity_prompt=entity_prompt,
                    relation_prompt=relation_prompt,
                    entity_examples=entity_examples,
                    relation_examples=relation_examples,
                    metrics=training_metrics,
                    status="ready",
                    tx=tx,
                )

                # Transaction commits automatically on success
                logger.info(
                    "domain_and_training_results_committed_atomically",
                    domain=domain_name,
                    metrics=training_metrics,
                )
        else:
            # Existing domain: Just update prompts (non-transactional)
            await repo.update_domain_prompts(
                name=domain_name,
                entity_prompt=entity_prompt,
                relation_prompt=relation_prompt,
                entity_examples=entity_examples,
                relation_examples=relation_examples,
                metrics=training_metrics,
            )

            logger.info(
                "domain_prompts_updated",
                domain=domain_name,
                metrics=training_metrics,
            )

        tracker.update_progress(0.8, "Domain prompts persisted successfully")

        logger.info(
            "domain_prompts_saved",
            domain=domain_name,
            metrics=training_metrics,
            is_new_domain=is_new_domain,
        )

        # --- Phase 8: Completion (100%) ---
        tracker.complete(training_metrics)
        emit_sse(
            EventType.COMPLETED,
            100.0,
            "completed",
            f"Training completed successfully - Entity F1: {training_metrics['entity_f1']:.3f}, Relation F1: {training_metrics['relation_f1']:.3f}",
            {"final_metrics": training_metrics},
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
        tracker.fail("Training cancelled by user")
        emit_sse(
            EventType.FAILED,
            tracker.progress_percent,
            "cancelled",
            "Training cancelled by user",
        )
        raise

    except ValueError as e:
        # Validation errors (e.g., domain not found)
        logger.error(
            "training_validation_error",
            domain=domain_name,
            error=str(e),
        )
        tracker.fail(f"Validation error: {str(e)}")
        emit_sse(
            EventType.FAILED,
            tracker.progress_percent,
            "failed",
            f"Validation error: {str(e)}",
            {"error_type": "validation", "error_message": str(e)},
        )

    except DatabaseConnectionError as e:
        # Database errors
        logger.error(
            "training_database_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        tracker.fail(f"Database error: {str(e)}")
        emit_sse(
            EventType.FAILED,
            tracker.progress_percent,
            "failed",
            f"Database error: {str(e)}",
            {"error_type": "database", "error_message": str(e)},
        )

    except Exception as e:
        # Unexpected errors
        logger.error(
            "training_unexpected_error",
            domain=domain_name,
            error=str(e),
            exc_info=True,
        )
        tracker.fail(str(e))
        emit_sse(
            EventType.FAILED,
            tracker.progress_percent,
            "failed",
            f"Unexpected error: {str(e)}",
            {"error_type": "unexpected", "error_message": str(e)},
        )

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

    finally:
        # Keep stream open for a few seconds so late-connecting clients
        # can receive the final events (completion/failure status)
        # This handles the race condition where training completes before
        # the frontend SSE connection is established
        logger.info(
            "training_stream_closing_delayed",
            domain=domain_name,
            training_run_id=training_run_id,
            delay_seconds=5,
        )
        await asyncio.sleep(5)

        # Now close the SSE stream (Feature 45.13)
        stream.close_stream(training_run_id)
        logger.info(
            "training_stream_closed",
            domain=domain_name,
            training_run_id=training_run_id,
        )
