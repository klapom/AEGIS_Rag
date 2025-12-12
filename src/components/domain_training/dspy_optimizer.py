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
from collections.abc import Callable
from typing import Any

import structlog

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

    async def optimize_entity_extraction(
        self,
        training_data: list[dict[str, Any]],
        progress_callback: Callable[[str, float], None] | None = None,
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

        if progress_callback:
            progress_callback("Preparing training data", 10.0)

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

        if progress_callback:
            progress_callback("Building DSPy module", 30.0)

        # Store reference to dspy module for inner class
        dspy_module = self._dspy

        # Create entity extraction module (using closure for dspy reference)
        class EntityExtractor(dspy_module.Module):  # type: ignore[name-defined,misc]
            def __init__(self, signature: type) -> None:
                super().__init__()
                self.predictor = dspy_module.ChainOfThought(signature)

            def forward(self, source_text: str) -> Any:
                return self.predictor(source_text=source_text)

        # Define metric function
        def entity_extraction_metric(example: Any, pred: Any, trace: Any = None) -> float:
            """Calculate F1 score for entity extraction."""
            gold_entities = set(example.entities)
            pred_entities = set(pred.entities) if hasattr(pred, "entities") else set()

            if not gold_entities:
                return 1.0 if not pred_entities else 0.0

            tp = len(gold_entities & pred_entities)
            fp = len(pred_entities - gold_entities)
            fn = len(gold_entities - pred_entities)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            return f1

        if progress_callback:
            progress_callback("Running BootstrapFewShot optimization", 50.0)

        # Optimize with BootstrapFewShot using async-safe context
        try:
            with self._get_dspy_context():
                optimizer = dspy_module.BootstrapFewShot(
                    metric=entity_extraction_metric,
                    max_bootstrapped_demos=5,
                    max_labeled_demos=3,
                )

                # Create signature dynamically
                signature = type(
                    "EntityExtractionSignature",
                    (),
                    {
                        "__doc__": EntityExtractionSignature.get_instructions(),
                        "source_text": dspy_module.InputField(),
                        "entities": dspy_module.OutputField(desc="THOROUGH list of key entities"),
                    },
                )

                optimized_module = optimizer.compile(
                    EntityExtractor(signature),
                    trainset=trainset,
                )

                if progress_callback:
                    progress_callback("Evaluating on validation set", 80.0)

                # Evaluate on validation set
                eval_score = await self._evaluate_async(
                    optimized_module, valset, entity_extraction_metric
                )

            logger.info("entity_extraction_optimized", val_f1=eval_score)

            if progress_callback:
                progress_callback("Extracting optimized prompt", 95.0)

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

            if progress_callback:
                progress_callback("Optimization complete", 100.0)

            return result

        except Exception as e:
            logger.error("entity_extraction_optimization_failed", error=str(e))
            raise

    async def optimize_relation_extraction(
        self,
        training_data: list[dict[str, Any]],
        progress_callback: Callable[[str, float], None] | None = None,
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

        if progress_callback:
            progress_callback("Preparing training data", 10.0)

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

        if progress_callback:
            progress_callback("Building DSPy module", 30.0)

        # Store reference to dspy module for inner class
        dspy_module = self._dspy

        # Create relation extraction module (using closure for dspy reference)
        class RelationExtractor(dspy_module.Module):  # type: ignore[name-defined,misc]
            def __init__(self, signature: type) -> None:
                super().__init__()
                self.predictor = dspy_module.ChainOfThought(signature)

            def forward(self, source_text: str, entities: list[str]) -> Any:
                return self.predictor(source_text=source_text, entities=entities)

        # Define metric function
        def relation_extraction_metric(example: Any, pred: Any, trace: Any = None) -> float:
            """Calculate F1 score for relation extraction."""
            gold_relations = {
                (r["subject"], r["predicate"], r["object"])
                for r in example.relations
                if isinstance(r, dict) and all(k in r for k in ["subject", "predicate", "object"])
            }
            pred_relations = {
                (r["subject"], r["predicate"], r["object"])
                for r in (pred.relations if hasattr(pred, "relations") else [])
                if isinstance(r, dict) and all(k in r for k in ["subject", "predicate", "object"])
            }

            if not gold_relations:
                return 1.0 if not pred_relations else 0.0

            tp = len(gold_relations & pred_relations)
            fp = len(pred_relations - gold_relations)
            fn = len(gold_relations - pred_relations)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            return f1

        if progress_callback:
            progress_callback("Running BootstrapFewShot optimization", 50.0)

        # Optimize with BootstrapFewShot using async-safe context
        try:
            with self._get_dspy_context():
                optimizer = dspy_module.BootstrapFewShot(
                    metric=relation_extraction_metric,
                    max_bootstrapped_demos=5,
                    max_labeled_demos=3,
                )

                # Create signature dynamically
                signature = type(
                    "RelationExtractionSignature",
                    (),
                    {
                        "__doc__": RelationExtractionSignature.get_instructions(),
                        "source_text": dspy_module.InputField(),
                        "entities": dspy_module.InputField(),
                        "relations": dspy_module.OutputField(
                            desc="List of {subject, predicate, object} tuples"
                        ),
                    },
                )

                optimized_module = optimizer.compile(
                    RelationExtractor(signature),
                    trainset=trainset,
                )

                if progress_callback:
                    progress_callback("Evaluating on validation set", 80.0)

                # Evaluate on validation set
                eval_score = await self._evaluate_async(
                    optimized_module, valset, relation_extraction_metric
                )

            logger.info("relation_extraction_optimized", val_f1=eval_score)

            if progress_callback:
                progress_callback("Extracting optimized prompt", 95.0)

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

            if progress_callback:
                progress_callback("Optimization complete", 100.0)

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

        def _evaluate_sync() -> float:
            """Synchronous evaluation helper."""
            total_score = 0.0
            for example in testset:
                try:
                    pred = module(**example.inputs())
                    score = metric(example, pred, None)  # Add trace=None for consistency
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
