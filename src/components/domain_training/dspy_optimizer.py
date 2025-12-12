"""DSPy-based Prompt Optimization for Knowledge Graph Extraction.

Sprint 45 - Feature 45.2: DSPy Integration Service

This module provides DSPy-based optimization for entity and relation extraction prompts.
It uses BootstrapFewShot to automatically generate optimized prompts with examples
from training data.

Key Features:
- Entity extraction optimization with automatic prompt tuning
- Relation extraction optimization with entity-aware prompts
- Progress tracking via callbacks
- Evaluation metrics (precision, recall, F1)
- Ollama LLM backend (local, cost-free)

Architecture:
    DSPyOptimizer → Ollama LLM (qwen3:32b)
    ├── EntityExtractionSignature (Chain-of-Thought)
    ├── RelationExtractionSignature (Entity-aware)
    └── BootstrapFewShot optimizer with validation metrics

Usage:
    >>> optimizer = DSPyOptimizer(llm_model="qwen3:32b")
    >>> training_data = [
    ...     {"text": "Apple acquired Siri in 2010.", "entities": ["Apple", "Siri"]},
    ...     {"text": "Tesla builds electric cars.", "entities": ["Tesla", "electric cars"]}
    ... ]
    >>> result = await optimizer.optimize_entity_extraction(training_data)
    >>> print(result["instructions"])
"""

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Union

import structlog

from src.components.domain_training.semantic_matcher import get_semantic_matcher

logger = structlog.get_logger(__name__)


class EntityExtractionSignature:
    """Extract key entities from the source text.

    This signature defines the input/output schema for entity extraction.
    DSPy will optimize the instructions and examples automatically.
    """

    def __init__(self) -> None:
        self.source_text: str = ""
        self.entities: list[str] = []

    @staticmethod
    def get_input_fields() -> list[str]:
        """Return list of input field names."""
        return ["source_text"]

    @staticmethod
    def get_output_fields() -> list[str]:
        """Return list of output field names."""
        return ["entities"]

    @staticmethod
    def get_instructions() -> str:
        """Return default instructions for entity extraction."""
        return "Extract a THOROUGH list of key entities from the source text."


class RelationExtractionSignature:
    """Extract subject-predicate-object triples from the source text.

    This signature uses entities as additional context to extract relations.
    DSPy will optimize the instructions and examples for relation extraction.
    """

    def __init__(self) -> None:
        self.source_text: str = ""
        self.entities: list[str] = []
        self.relations: list[dict[str, str]] = []

    @staticmethod
    def get_input_fields() -> list[str]:
        """Return list of input field names."""
        return ["source_text", "entities"]

    @staticmethod
    def get_output_fields() -> list[str]:
        """Return list of output field names."""
        return ["relations"]

    @staticmethod
    def get_instructions() -> str:
        """Return default instructions for relation extraction."""
        return "Extract subject-predicate-object triples from the source text."


class DSPyOptimizer:
    """Optimizes extraction prompts using DSPy.

    This class provides methods for optimizing entity and relation extraction
    prompts using DSPy's BootstrapFewShot optimizer. It supports progress tracking
    and evaluation metrics.

    WARNING: DSPy integration requires dspy-ai package to be installed.
    This is NOT included in core dependencies to keep base installation lightweight.

    Install with: poetry add dspy-ai

    Attributes:
        llm_model: Ollama model name (default: qwen3:32b)
        lm: DSPy language model instance
    """

    # Type alias for progress callback - supports both sync and async
    ProgressCallback = Union[
        Callable[[str, float], None],
        Callable[[str, float], Awaitable[None]],
    ]

    def __init__(self, llm_model: str = "qwen3:32b") -> None:
        """Initialize DSPy optimizer with Ollama backend.

        Args:
            llm_model: Ollama model to use for optimization (default: qwen3:32b)

        Raises:
            ImportError: If dspy-ai is not installed
        """
        self.llm_model = llm_model
        self._dspy_available = False

        try:
            import dspy

            self._dspy = dspy
            self._dspy_available = True
            self._configure_dspy()
            logger.info("dspy_optimizer_initialized", llm_model=llm_model)
        except ImportError:
            logger.warning(
                "dspy_not_available",
                message=(
                    "DSPy not installed. Install with: poetry add dspy-ai. "
                    "Optimizer methods will return mock results."
                ),
            )

    def _configure_dspy(self) -> None:
        """Configure DSPy with Ollama backend.

        Note: We only create the LM here, actual configuration happens
        in _get_dspy_context() to be async-safe.
        """
        if not self._dspy_available:
            return

        # Create Ollama LLM (configuration done via context manager for async safety)
        self.lm = self._dspy.LM(
            model=f"ollama_chat/{self.llm_model}",
            api_base="http://localhost:11434",
            api_key="",  # Not needed for local Ollama
        )
        logger.info("dspy_lm_created", model=self.llm_model, backend="ollama")

    def _get_dspy_context(self) -> Any:
        """Get DSPy context manager for async-safe configuration.

        Returns:
            Context manager that configures DSPy LM for the current async task.
        """
        return self._dspy.context(lm=self.lm)

    async def _call_progress_callback(
        self,
        callback: "DSPyOptimizer.ProgressCallback | None",
        message: str,
        progress: float,
    ) -> None:
        """Safely call progress callback, handling both sync and async.

        Args:
            callback: Progress callback function (sync or async)
            message: Progress message
            progress: Progress percentage (0-100)
        """
        if callback is None:
            return

        if inspect.iscoroutinefunction(callback):
            await callback(message, progress)
        else:
            callback(message, progress)

    def set_event_stream(self, stream: Any, training_run_id: str) -> None:
        """Set the SSE event stream for detailed LLM interaction logging.

        Feature 45.13: Real-time Training Progress with SSE

        When set, the optimizer will emit detailed events for every LLM interaction:
        - LLM_REQUEST: Full prompt sent to the model (NOT truncated)
        - LLM_RESPONSE: Full response from the model (NOT truncated)
        - SAMPLE_PROCESSING: Current sample being processed
        - SAMPLE_RESULT: Evaluation result for sample

        Args:
            stream: TrainingEventStream instance
            training_run_id: Training run ID for emitting events
        """
        self._event_stream = stream
        self._training_run_id = training_run_id
        logger.info(
            "dspy_event_stream_configured",
            training_run_id=training_run_id,
        )

    def _emit_llm_event(
        self,
        event_type: str,
        phase: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Emit an LLM interaction event to the SSE stream.

        Args:
            event_type: Type of event (llm_request, llm_response, etc.)
            phase: Current training phase
            message: Human-readable message
            data: Additional event data (prompts, responses, scores)
        """
        if not hasattr(self, "_event_stream") or self._event_stream is None:
            return

        from src.components.domain_training.training_stream import EventType

        # Map string event types to EventType enum
        type_map = {
            "llm_request": EventType.LLM_REQUEST,
            "llm_response": EventType.LLM_RESPONSE,
            "sample_processing": EventType.SAMPLE_PROCESSING,
            "sample_result": EventType.SAMPLE_RESULT,
            "bootstrap_iteration": EventType.BOOTSTRAP_ITERATION,
            "demo_selected": EventType.DEMO_SELECTED,
        }

        evt_type = type_map.get(event_type, EventType.PROGRESS_UPDATE)

        self._event_stream.emit(
            training_run_id=self._training_run_id,
            event_type=evt_type,
            domain="",  # Will be filled by training_runner
            progress_percent=0.0,  # Progress managed by runner
            phase=phase,
            message=message,
            data=data or {},
        )

    async def optimize_entity_extraction(
        self,
        training_data: list[dict[str, Any]],
        progress_callback: "DSPyOptimizer.ProgressCallback | None" = None,
    ) -> dict[str, Any]:
        """Optimize entity extraction prompt using training data.

        Args:
            training_data: List of training examples with format:
                [{"text": str, "entities": list[str]}, ...]
            progress_callback: Optional callback for progress updates.
                Called with (step_description: str, progress_percent: float)

        Returns:
            Dictionary with optimized prompt configuration:
            {
                "instructions": str,  # Optimized instructions
                "demos": list[dict],  # Few-shot examples
                "metrics": dict       # Evaluation metrics (precision, recall, F1)
            }

        Raises:
            ValueError: If training_data is empty or invalid
        """
        if not training_data:
            raise ValueError("Training data cannot be empty")

        if not self._dspy_available:
            logger.warning("dspy_not_available", fallback="mock_results")
            return self._mock_entity_optimization_result(training_data)

        logger.info(
            "optimizing_entity_extraction",
            num_samples=len(training_data),
            model=self.llm_model,
        )

        await self._call_progress_callback(progress_callback, "Preparing training data", 10.0)

        # Convert to DSPy format
        dspy_examples = []
        for item in training_data:
            if "text" not in item or "entities" not in item:
                logger.warning("invalid_training_sample", sample=item)
                continue

            example = self._dspy.Example(
                source_text=item["text"],
                entities=item["entities"],
            ).with_inputs("source_text")
            dspy_examples.append(example)

        if not dspy_examples:
            raise ValueError("No valid training examples found")

        # Split train/validation (80/20)
        split_idx = int(len(dspy_examples) * 0.8)
        trainset = dspy_examples[:split_idx]
        valset = dspy_examples[split_idx:]

        logger.info(
            "training_data_prepared",
            train_size=len(trainset),
            val_size=len(valset),
        )

        await self._call_progress_callback(progress_callback, "Building DSPy module", 30.0)

        # Store reference to dspy module and self for inner class
        dspy_module = self._dspy
        optimizer_self = self  # Capture self for event emission in nested functions
        sample_counter = [0]  # Mutable counter for tracking sample index

        # Create entity extraction module (using closure for dspy reference)
        class EntityExtractor(dspy_module.Module):  # type: ignore[name-defined,misc]
            def __init__(self, signature: type) -> None:
                super().__init__()
                self.predictor = dspy_module.ChainOfThought(signature)

            def forward(self, source_text: str) -> Any:
                # Emit LLM request event (full prompt, NOT truncated)
                optimizer_self._emit_llm_event(
                    event_type="llm_request",
                    phase="entity_optimization",
                    message=f"Processing sample #{sample_counter[0] + 1}",
                    data={
                        "sample_index": sample_counter[0],
                        "prompt": source_text,  # FULL source text
                        "model": optimizer_self.llm_model,
                    },
                )

                result = self.predictor(source_text=source_text)

                # Emit LLM response event (full response, NOT truncated)
                entities = result.entities if hasattr(result, "entities") else []
                optimizer_self._emit_llm_event(
                    event_type="llm_response",
                    phase="entity_optimization",
                    message=f"Extracted {len(entities)} entities",
                    data={
                        "sample_index": sample_counter[0],
                        "entities": entities,  # FULL entity list
                        "reasoning": getattr(result, "reasoning", ""),  # FULL reasoning
                    },
                )

                sample_counter[0] += 1
                return result

        # Get semantic matcher for embedding-based comparison (Feature 45.17)
        semantic_matcher = get_semantic_matcher(threshold=0.75)

        # Define metric function with event emission and semantic matching
        def entity_extraction_metric(example: Any, pred: Any, trace: Any = None) -> float:
            """Calculate F1 score for entity extraction using semantic matching."""
            gold_entities = set(example.entities)
            pred_entities = set(pred.entities) if hasattr(pred, "entities") else set()

            if not gold_entities:
                return 1.0 if not pred_entities else 0.0

            # Use semantic matching instead of exact set intersection (Feature 45.17)
            metrics = semantic_matcher.compute_entity_metrics(gold_entities, pred_entities)
            precision = metrics["precision"]
            recall = metrics["recall"]
            f1 = metrics["f1"]

            # Calculate matched counts for logging
            tp = int(recall * len(gold_entities)) if gold_entities else 0
            fp = len(pred_entities) - tp
            fn = len(gold_entities) - tp

            # Emit sample result event
            optimizer_self._emit_llm_event(
                event_type="sample_result",
                phase="entity_optimization",
                message=f"Sample evaluated - F1: {f1:.3f} (semantic)",
                data={
                    "gold_entities": list(gold_entities),
                    "predicted_entities": list(pred_entities),
                    "true_positives": tp,
                    "false_positives": fp,
                    "false_negatives": fn,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "matching_mode": "semantic",
                },
            )

            return f1

        await self._call_progress_callback(
            progress_callback, "Running BootstrapFewShot optimization", 50.0
        )

        # Optimize with BootstrapFewShot using async-safe context
        try:
            with self._get_dspy_context():
                optimizer = dspy_module.BootstrapFewShot(
                    metric=entity_extraction_metric,
                    max_bootstrapped_demos=5,
                    max_labeled_demos=3,
                )

                # Create proper DSPy Signature class
                class EntityExtractionSig(dspy_module.Signature):
                    """Extract a THOROUGH list of key entities from the source text."""

                    source_text: str = dspy_module.InputField()
                    entities: list[str] = dspy_module.OutputField(
                        desc="THOROUGH list of key entities"
                    )

                optimized_module = optimizer.compile(
                    EntityExtractor(EntityExtractionSig),
                    trainset=trainset,
                )

                await self._call_progress_callback(
                    progress_callback, "Evaluating on validation set", 80.0
                )

                # Evaluate on validation set
                eval_score = await self._evaluate_async(
                    optimized_module, valset, entity_extraction_metric
                )

            logger.info("entity_extraction_optimized", val_f1=eval_score)

            await self._call_progress_callback(
                progress_callback, "Extracting optimized prompt", 95.0
            )

            # Extract prompt components
            result = {
                "instructions": EntityExtractionSignature.get_instructions(),
                "demos": self._extract_demos(optimized_module),
                "metrics": {
                    "val_f1": eval_score,
                    "val_samples": len(valset),
                    "train_samples": len(trainset),
                },
            }

            await self._call_progress_callback(
                progress_callback, "Optimization complete", 100.0
            )

            return result

        except Exception as e:
            logger.error("entity_extraction_optimization_failed", error=str(e))
            raise

    async def optimize_relation_extraction(
        self,
        training_data: list[dict[str, Any]],
        progress_callback: "DSPyOptimizer.ProgressCallback | None" = None,
    ) -> dict[str, Any]:
        """Optimize relation extraction prompt using training data.

        Args:
            training_data: List of training examples with format:
                [{
                    "text": str,
                    "entities": list[str],
                    "relations": list[dict]  # [{"subject": str, "predicate": str, "object": str}]
                }, ...]
            progress_callback: Optional callback for progress updates.
                Called with (step_description: str, progress_percent: float)

        Returns:
            Dictionary with optimized prompt configuration:
            {
                "instructions": str,  # Optimized instructions
                "demos": list[dict],  # Few-shot examples
                "metrics": dict       # Evaluation metrics (precision, recall, F1)
            }

        Raises:
            ValueError: If training_data is empty or invalid
        """
        if not training_data:
            raise ValueError("Training data cannot be empty")

        if not self._dspy_available:
            logger.warning("dspy_not_available", fallback="mock_results")
            return self._mock_relation_optimization_result(training_data)

        logger.info(
            "optimizing_relation_extraction",
            num_samples=len(training_data),
            model=self.llm_model,
        )

        await self._call_progress_callback(progress_callback, "Preparing training data", 10.0)

        # Convert to DSPy format
        dspy_examples = []
        for item in training_data:
            if "text" not in item or "entities" not in item or "relations" not in item:
                logger.warning("invalid_training_sample", sample=item)
                continue

            example = self._dspy.Example(
                source_text=item["text"],
                entities=item["entities"],
                relations=item["relations"],
            ).with_inputs("source_text", "entities")
            dspy_examples.append(example)

        if not dspy_examples:
            raise ValueError("No valid training examples found")

        # Split train/validation (80/20)
        split_idx = int(len(dspy_examples) * 0.8)
        trainset = dspy_examples[:split_idx]
        valset = dspy_examples[split_idx:]

        logger.info(
            "training_data_prepared",
            train_size=len(trainset),
            val_size=len(valset),
        )

        await self._call_progress_callback(progress_callback, "Building DSPy module", 30.0)

        # Store reference to dspy module and self for inner class
        dspy_module = self._dspy
        optimizer_self = self  # Capture self for event emission in nested functions
        sample_counter = [0]  # Mutable counter for tracking sample index

        # Create relation extraction module (using closure for dspy reference)
        class RelationExtractor(dspy_module.Module):  # type: ignore[name-defined,misc]
            def __init__(self, signature: type) -> None:
                super().__init__()
                self.predictor = dspy_module.ChainOfThought(signature)

            def forward(self, source_text: str, entities: list[str]) -> Any:
                # Emit LLM request event (full prompt, NOT truncated)
                optimizer_self._emit_llm_event(
                    event_type="llm_request",
                    phase="relation_optimization",
                    message=f"Processing sample #{sample_counter[0] + 1}",
                    data={
                        "sample_index": sample_counter[0],
                        "prompt": source_text,  # FULL source text
                        "entities": entities,  # FULL entity list
                        "model": optimizer_self.llm_model,
                    },
                )

                result = self.predictor(source_text=source_text, entities=entities)

                # Emit LLM response event (full response, NOT truncated)
                relations = result.relations if hasattr(result, "relations") else []
                optimizer_self._emit_llm_event(
                    event_type="llm_response",
                    phase="relation_optimization",
                    message=f"Extracted {len(relations)} relations",
                    data={
                        "sample_index": sample_counter[0],
                        "relations": relations,  # FULL relation list
                        "reasoning": getattr(result, "reasoning", ""),  # FULL reasoning
                    },
                )

                sample_counter[0] += 1
                return result

        # Get semantic matcher for embedding-based comparison (Feature 45.17)
        semantic_matcher = get_semantic_matcher(threshold=0.70, predicate_weight=0.4)

        # Define metric function with event emission and semantic matching
        def relation_extraction_metric(example: Any, pred: Any, trace: Any = None) -> float:
            """Calculate F1 score for relation extraction using semantic matching."""
            gold_relations = [
                {"subject": r["subject"], "predicate": r["predicate"], "object": r["object"]}
                for r in example.relations
                if isinstance(r, dict) and all(k in r for k in ["subject", "predicate", "object"])
            ]
            pred_relations = [
                {"subject": r["subject"], "predicate": r["predicate"], "object": r["object"]}
                for r in (pred.relations if hasattr(pred, "relations") else [])
                if isinstance(r, dict) and all(k in r for k in ["subject", "predicate", "object"])
            ]

            if not gold_relations:
                return 1.0 if not pred_relations else 0.0

            # Use semantic matching instead of exact tuple comparison (Feature 45.17)
            metrics = semantic_matcher.compute_relation_metrics(gold_relations, pred_relations)
            precision = metrics["precision"]
            recall = metrics["recall"]
            f1 = metrics["f1"]

            # Calculate matched counts for logging
            tp = int(recall * len(gold_relations)) if gold_relations else 0
            fp = len(pred_relations) - tp
            fn = len(gold_relations) - tp

            # Emit sample result event
            optimizer_self._emit_llm_event(
                event_type="sample_result",
                phase="relation_optimization",
                message=f"Sample evaluated - F1: {f1:.3f} (semantic)",
                data={
                    "gold_relations": gold_relations,
                    "predicted_relations": pred_relations,
                    "true_positives": tp,
                    "false_positives": fp,
                    "false_negatives": fn,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                    "matching_mode": "semantic",
                },
            )

            return f1

        await self._call_progress_callback(
            progress_callback, "Running BootstrapFewShot optimization", 50.0
        )

        # Optimize with BootstrapFewShot using async-safe context
        try:
            with self._get_dspy_context():
                optimizer = dspy_module.BootstrapFewShot(
                    metric=relation_extraction_metric,
                    max_bootstrapped_demos=5,
                    max_labeled_demos=3,
                )

                # Create proper DSPy Signature class
                class RelationExtractionSig(dspy_module.Signature):
                    """Extract subject-predicate-object triples from the source text."""

                    source_text: str = dspy_module.InputField()
                    entities: list[str] = dspy_module.InputField()
                    relations: list[dict[str, str]] = dspy_module.OutputField(
                        desc="List of {subject, predicate, object} tuples"
                    )

                optimized_module = optimizer.compile(
                    RelationExtractor(RelationExtractionSig),
                    trainset=trainset,
                )

                await self._call_progress_callback(
                    progress_callback, "Evaluating on validation set", 80.0
                )

                # Evaluate on validation set
                eval_score = await self._evaluate_async(
                    optimized_module, valset, relation_extraction_metric
                )

            logger.info("relation_extraction_optimized", val_f1=eval_score)

            await self._call_progress_callback(
                progress_callback, "Extracting optimized prompt", 95.0
            )

            # Extract prompt components
            result = {
                "instructions": RelationExtractionSignature.get_instructions(),
                "demos": self._extract_demos(optimized_module),
                "metrics": {
                    "val_f1": eval_score,
                    "val_samples": len(valset),
                    "train_samples": len(trainset),
                },
            }

            await self._call_progress_callback(
                progress_callback, "Optimization complete", 100.0
            )

            return result

        except Exception as e:
            logger.error("relation_extraction_optimization_failed", error=str(e))
            raise

    async def _evaluate_async(
        self, module: Any, testset: list[Any], metric: Callable[[Any, Any, Any], float]
    ) -> float:
        """Evaluate optimized module on test set asynchronously.

        Args:
            module: Optimized DSPy module
            testset: List of test examples
            metric: Metric function to evaluate predictions

        Returns:
            Average metric score across test set
        """
        # Capture LM reference for thread-safe access
        lm = self.lm
        dspy_module = self._dspy

        def _evaluate_sync() -> float:
            """Synchronous evaluation helper."""
            # Re-configure DSPy in worker thread (context is thread-local)
            with dspy_module.context(lm=lm):
                total_score = 0.0
                for example in testset:
                    try:
                        pred = module(**example.inputs())
                        score = metric(example, pred, None)
                        total_score += score
                    except Exception as e:
                        logger.warning("evaluation_example_failed", error=str(e))
                        continue

                return total_score / len(testset) if testset else 0.0

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _evaluate_sync)

    def _extract_demos(self, module: Any) -> list[dict[str, Any]]:
        """Extract few-shot demonstrations from optimized module.

        Args:
            module: Optimized DSPy module

        Returns:
            List of demonstration examples with inputs and outputs
        """
        demos = []
        try:
            if hasattr(module, "predictors"):
                for predictor in module.predictors():
                    if hasattr(predictor, "demos"):
                        for demo in predictor.demos:
                            demos.append(
                                {
                                    "input": demo.inputs() if hasattr(demo, "inputs") else {},
                                    "output": demo.labels() if hasattr(demo, "labels") else {},
                                }
                            )
        except Exception as e:
            logger.warning("demo_extraction_failed", error=str(e))

        return demos

    def _mock_entity_optimization_result(
        self, training_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate mock optimization result when DSPy is not available.

        Args:
            training_data: Training data used for mock result

        Returns:
            Mock optimization result dictionary
        """
        return {
            "instructions": EntityExtractionSignature.get_instructions(),
            "demos": [
                {
                    "input": {"source_text": item["text"]},
                    "output": {"entities": item["entities"]},
                }
                for item in training_data[:3]  # Use first 3 as mock demos
            ],
            "metrics": {
                "val_f1": 0.85,  # Mock F1 score
                "val_samples": len(training_data) // 5,
                "train_samples": len(training_data) - len(training_data) // 5,
            },
        }

    def _mock_relation_optimization_result(
        self, training_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate mock optimization result when DSPy is not available.

        Args:
            training_data: Training data used for mock result

        Returns:
            Mock optimization result dictionary
        """
        return {
            "instructions": RelationExtractionSignature.get_instructions(),
            "demos": [
                {
                    "input": {
                        "source_text": item["text"],
                        "entities": item.get("entities", []),
                    },
                    "output": {"relations": item.get("relations", [])},
                }
                for item in training_data[:3]  # Use first 3 as mock demos
            ],
            "metrics": {
                "val_f1": 0.80,  # Mock F1 score
                "val_samples": len(training_data) // 5,
                "train_samples": len(training_data) - len(training_data) // 5,
            },
        }
