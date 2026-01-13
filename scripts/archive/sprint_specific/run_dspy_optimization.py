#!/usr/bin/env python3
"""DSPy MIPROv2 Optimization Runner.

Sprint 86 Feature 86.1: DSPy MIPROv2 Training Pipeline.

This script runs automated prompt optimization for entity and relation extraction
using DSPy's MIPROv2 optimizer.

Usage:
    poetry run python scripts/run_dspy_optimization.py --help
    poetry run python scripts/run_dspy_optimization.py --quick-test
    poetry run python scripts/run_dspy_optimization.py \
        --training-data data/dspy_training/train.jsonl \
        --model nemotron-3-nano:latest \
        --num-candidates 15
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import dspy
    from dspy import MIPROv2  # DSPy 3.0+ API

    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False
    print("WARNING: DSPy not installed. Run: pip install dspy-ai")


# ============================================================================
# DSPy Signatures
# ============================================================================


class EntityExtractionSignature(dspy.Signature):
    """Extract named entities from document text."""

    text: str = dspy.InputField(desc="Document text to extract entities from")
    domain: str = dspy.InputField(
        desc="Document domain: technical, organizational, or scientific"
    )
    entities: list = dspy.OutputField(
        desc="JSON array of {name, type, description} objects for each entity"
    )


class RelationExtractionSignature(dspy.Signature):
    """Extract relationships between entities."""

    text: str = dspy.InputField(desc="Source document text")
    entities: list = dspy.InputField(desc="List of extracted entities")
    relations: list = dspy.OutputField(
        desc="JSON array of {source, target, type, strength} objects"
    )


# ============================================================================
# Pipeline Module (Entity → Relation)
# ============================================================================


class EntityRelationPipeline(dspy.Module):
    """
    Two-stage extraction pipeline: Entities first, then Relations.

    This solves the problem where RelationExtractionSignature expects
    entities as input but they aren't available during standalone optimization.

    Architecture:
        text + domain → EntityExtractor → entities
        text + entities → RelationExtractor → relations
    """

    def __init__(self):
        super().__init__()
        self.entity_extractor = dspy.ChainOfThought(EntityExtractionSignature)
        self.relation_extractor = dspy.ChainOfThought(RelationExtractionSignature)

    def forward(self, text: str, domain: str = "technical"):
        """
        Extract entities and relations in a two-stage pipeline.

        Args:
            text: Document text to process
            domain: Document domain (technical, organizational, scientific)

        Returns:
            dspy.Prediction with entities and relations
        """
        # Stage 1: Extract entities from text
        entity_result = self.entity_extractor(text=text, domain=domain)

        # Parse entities if they're a string
        entities = entity_result.entities
        if isinstance(entities, str):
            try:
                entities = json.loads(entities)
            except json.JSONDecodeError:
                entities = []

        # Stage 2: Extract relations using the extracted entities
        relation_result = self.relation_extractor(
            text=text,
            entities=entities  # Pass extracted entities as input
        )

        return dspy.Prediction(
            entities=entity_result.entities,
            relations=relation_result.relations
        )


# ============================================================================
# Objective Functions
# ============================================================================


def compute_f1(predicted: list, gold: list) -> float:
    """Compute F1 score between predicted and gold entities/relations."""
    if not predicted or not gold:
        return 0.0

    # Normalize for comparison
    pred_set = set()
    gold_set = set()

    for item in predicted:
        if isinstance(item, dict):
            key = item.get("name", item.get("source", "")).lower()
            pred_set.add(key)
        else:
            pred_set.add(str(item).lower())

    for item in gold:
        if isinstance(item, dict):
            key = item.get("name", item.get("source", "")).lower()
            gold_set.add(key)
        else:
            gold_set.add(str(item).lower())

    if not pred_set or not gold_set:
        return 0.0

    true_positives = len(pred_set & gold_set)
    precision = true_positives / len(pred_set) if pred_set else 0.0
    recall = true_positives / len(gold_set) if gold_set else 0.0

    if precision + recall == 0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)


def entity_extraction_objective(example, prediction, trace=None) -> float:
    """
    Multi-objective score for entity extraction optimization.

    Components:
    - F1 Score (60% weight): Accuracy of entity extraction
    - Type Coverage (30% weight): % of entities with specific types
    - Description Quality (10% weight): % of entities with descriptions
    """
    try:
        # Parse prediction if string
        if isinstance(prediction.entities, str):
            entities = json.loads(prediction.entities)
        else:
            entities = prediction.entities or []

        # Parse gold
        if isinstance(example.entities, str):
            gold = json.loads(example.entities)
        else:
            gold = example.entities or []

        # F1 Score (60%)
        f1 = compute_f1(entities, gold)

        # Type Coverage (30%)
        if entities:
            typed = sum(1 for e in entities if e.get("type") and e["type"] != "UNKNOWN")
            type_coverage = typed / len(entities)
        else:
            type_coverage = 0.0

        # Description Quality (10%)
        if entities:
            with_desc = sum(1 for e in entities if e.get("description", "").strip())
            desc_quality = with_desc / len(entities)
        else:
            desc_quality = 0.0

        # Weighted composite
        score = 0.6 * f1 + 0.3 * type_coverage + 0.1 * desc_quality

        return max(0.0, min(1.0, score))

    except Exception as e:
        print(f"Objective function error: {e}")
        return 0.0


def relation_extraction_objective(example, prediction, trace=None) -> float:
    """
    Multi-objective score for relation extraction optimization.

    Components:
    - F1 Score (50% weight): Accuracy of relation extraction
    - Typed Coverage (30% weight): % with specific types (not RELATES_TO)
    - Deduplication (20% penalty): Penalize duplicate extractions
    """
    try:
        # Parse prediction
        if isinstance(prediction.relations, str):
            relations = json.loads(prediction.relations)
        else:
            relations = prediction.relations or []

        # Parse gold
        if isinstance(example.relations, str):
            gold = json.loads(example.relations)
        else:
            gold = example.relations or []

        # F1 Score (50%)
        f1 = compute_f1(relations, gold)

        # Typed Coverage (30%)
        if relations:
            typed = [r for r in relations if r.get("type", "RELATES_TO") != "RELATES_TO"]
            coverage = len(typed) / len(relations)
        else:
            coverage = 0.0

        # Duplication Rate (20% penalty)
        if relations:
            unique = set()
            for r in relations:
                key = (
                    r.get("source", "").lower(),
                    r.get("type", "").upper(),
                    r.get("target", "").lower(),
                )
                unique.add(key)
            dup_rate = 1 - (len(unique) / len(relations))
        else:
            dup_rate = 0.0

        # Weighted composite
        score = 0.5 * f1 + 0.3 * coverage - 0.2 * dup_rate

        return max(0.0, min(1.0, score))

    except Exception as e:
        print(f"Objective function error: {e}")
        return 0.0


def pipeline_extraction_objective(example, prediction, trace=None) -> float:
    """
    Combined objective for Entity→Relation Pipeline optimization.

    Weights both entity and relation quality:
    - Entity Score (40%): Quality of entity extraction
    - Relation Score (40%): Quality of relation extraction
    - E/R Ratio Bonus (20%): Reward balanced extraction (target: 1.0-2.0)
    """
    try:
        # Parse entities
        if isinstance(prediction.entities, str):
            entities = json.loads(prediction.entities)
        else:
            entities = prediction.entities or []

        if isinstance(example.entities, str):
            gold_entities = json.loads(example.entities)
        else:
            gold_entities = example.entities or []

        # Parse relations
        if isinstance(prediction.relations, str):
            relations = json.loads(prediction.relations)
        else:
            relations = prediction.relations or []

        if isinstance(example.relations, str):
            gold_relations = json.loads(example.relations)
        else:
            gold_relations = example.relations or []

        # Entity F1 (40%)
        entity_f1 = compute_f1(entities, gold_entities)

        # Relation F1 (40%)
        relation_f1 = compute_f1(relations, gold_relations)

        # E/R Ratio Bonus (20%) - reward ratios between 1.0 and 2.0
        if entities and relations:
            er_ratio = len(entities) / len(relations)
            # Perfect score at ratio 1.5, decreasing towards 0.5 and 3.0
            if 1.0 <= er_ratio <= 2.0:
                er_bonus = 1.0
            elif 0.5 <= er_ratio < 1.0:
                er_bonus = 0.5 + (er_ratio - 0.5)
            elif 2.0 < er_ratio <= 3.0:
                er_bonus = 1.0 - (er_ratio - 2.0) * 0.5
            else:
                er_bonus = 0.2
        else:
            er_bonus = 0.0

        # Weighted composite
        score = 0.4 * entity_f1 + 0.4 * relation_f1 + 0.2 * er_bonus

        return max(0.0, min(1.0, score))

    except Exception as e:
        print(f"Pipeline objective error: {e}")
        return 0.0


# ============================================================================
# Data Loading
# ============================================================================


def load_training_data(path: str) -> list[dspy.Example]:
    """Load training data from JSONL file."""
    examples = []
    path = Path(path)

    if not path.exists():
        print(f"Training data not found: {path}")
        return examples

    with open(path) as f:
        for line in f:
            data = json.loads(line)
            example = dspy.Example(
                text=data.get("text", ""),
                domain=data.get("domain", "technical"),
                entities=json.dumps(data.get("entities", [])),
                relations=json.dumps(data.get("relations", [])),
            ).with_inputs("text", "domain")
            examples.append(example)

    return examples


def create_sample_data() -> tuple[list[dspy.Example], list[dspy.Example]]:
    """Create sample training/validation data for quick testing."""
    samples = [
        {
            "text": "Microsoft was founded by Bill Gates and Paul Allen in 1975. The company is headquartered in Redmond, Washington. Microsoft acquired GitHub in 2018.",
            "domain": "organizational",
            "entities": [
                {"name": "Microsoft", "type": "ORGANIZATION", "description": "Technology company"},
                {"name": "Bill Gates", "type": "PERSON", "description": "Co-founder"},
                {"name": "Paul Allen", "type": "PERSON", "description": "Co-founder"},
                {"name": "Redmond", "type": "LOCATION", "description": "City in Washington"},
                {"name": "GitHub", "type": "ORGANIZATION", "description": "Code hosting platform"},
            ],
            "relations": [
                {"source": "Bill Gates", "target": "Microsoft", "type": "FOUNDED", "strength": 10},
                {"source": "Paul Allen", "target": "Microsoft", "type": "FOUNDED", "strength": 10},
                {"source": "Microsoft", "target": "Redmond", "type": "HEADQUARTERED_IN", "strength": 9},
                {"source": "Microsoft", "target": "GitHub", "type": "ACQUIRED", "strength": 10},
            ],
        },
        {
            "text": "TensorFlow is an open-source machine learning framework developed by Google. It supports Python and C++ programming languages. PyTorch is a competing framework by Facebook.",
            "domain": "technical",
            "entities": [
                {"name": "TensorFlow", "type": "SOFTWARE", "description": "ML framework"},
                {"name": "Google", "type": "ORGANIZATION", "description": "Tech company"},
                {"name": "Python", "type": "LANGUAGE", "description": "Programming language"},
                {"name": "C++", "type": "LANGUAGE", "description": "Programming language"},
                {"name": "PyTorch", "type": "SOFTWARE", "description": "ML framework"},
                {"name": "Facebook", "type": "ORGANIZATION", "description": "Tech company"},
            ],
            "relations": [
                {"source": "Google", "target": "TensorFlow", "type": "DEVELOPED", "strength": 10},
                {"source": "TensorFlow", "target": "Python", "type": "SUPPORTS", "strength": 9},
                {"source": "TensorFlow", "target": "C++", "type": "SUPPORTS", "strength": 8},
                {"source": "Facebook", "target": "PyTorch", "type": "DEVELOPED", "strength": 10},
            ],
        },
        {
            "text": "The BERT model was introduced by Google researchers in 2018. It achieved state-of-the-art results on the GLUE benchmark. GPT-3 by OpenAI later surpassed BERT on many tasks.",
            "domain": "scientific",
            "entities": [
                {"name": "BERT", "type": "MODEL", "description": "Language model"},
                {"name": "Google", "type": "ORGANIZATION", "description": "Research org"},
                {"name": "GLUE", "type": "DATASET", "description": "NLP benchmark"},
                {"name": "GPT-3", "type": "MODEL", "description": "Large language model"},
                {"name": "OpenAI", "type": "ORGANIZATION", "description": "AI research company"},
            ],
            "relations": [
                {"source": "Google", "target": "BERT", "type": "INTRODUCED", "strength": 10},
                {"source": "BERT", "target": "GLUE", "type": "EVALUATED_ON", "strength": 9},
                {"source": "OpenAI", "target": "GPT-3", "type": "CREATED", "strength": 10},
                {"source": "GPT-3", "target": "BERT", "type": "SURPASSED", "strength": 8},
            ],
        },
    ]

    # Hard negatives (no relations)
    hard_negatives = [
        {
            "text": "Python and Java are popular programming languages. Both are used in enterprise development.",
            "domain": "technical",
            "entities": [
                {"name": "Python", "type": "LANGUAGE", "description": "Programming language"},
                {"name": "Java", "type": "LANGUAGE", "description": "Programming language"},
            ],
            "relations": [],  # No relation - just enumeration
        },
        {
            "text": "The meeting is scheduled for Monday. TensorFlow will be discussed during the session.",
            "domain": "organizational",
            "entities": [
                {"name": "Monday", "type": "DATE", "description": "Day of week"},
                {"name": "TensorFlow", "type": "SOFTWARE", "description": "ML framework"},
            ],
            "relations": [],  # No semantic relationship
        },
    ]

    all_samples = samples + hard_negatives

    # Convert to DSPy examples
    examples = []
    for data in all_samples:
        example = dspy.Example(
            text=data["text"],
            domain=data["domain"],
            entities=json.dumps(data["entities"]),
            relations=json.dumps(data["relations"]),
        ).with_inputs("text", "domain")
        examples.append(example)

    # Split 80/20
    split_idx = int(len(examples) * 0.8)
    return examples[:split_idx], examples[split_idx:]


# ============================================================================
# Optimization Runner
# ============================================================================


class DSPyOptimizer:
    """DSPy MIPROv2 optimizer for extraction prompts."""

    def __init__(
        self,
        model: str = "nemotron-3-nano:latest",
        ollama_base: str = "http://localhost:11434",
    ):
        self.model = model
        self.ollama_base = ollama_base
        self._configure_dspy()

    def _configure_dspy(self):
        """Configure DSPy with Ollama backend (DSPy 3.0+ API)."""
        # DSPy 3.0 uses dspy.LM with provider/model format
        lm = dspy.LM(
            f"ollama_chat/{self.model}",
            api_base=self.ollama_base,
            temperature=0.1,
            max_tokens=2048,
        )
        dspy.configure(lm=lm)
        print(f"DSPy configured with model: {self.model}")

    def optimize_entity_extraction(
        self,
        trainset: list[dspy.Example],
        valset: list[dspy.Example],
        num_candidates: int = 10,
        num_trials: int | None = None,
        max_bootstrapped_demos: int = 4,
        max_labeled_demos: int = 4,
    ) -> dspy.Module:
        """Optimize entity extraction prompts using MIPROv2."""
        print("\n" + "=" * 60)
        print("ENTITY EXTRACTION OPTIMIZATION")
        print("=" * 60)
        print(f"Training samples: {len(trainset)}")
        print(f"Validation samples: {len(valset)}")
        # Calculate recommended num_trials if not provided (DSPy recommendation: ~2x num_candidates)
        if num_trials is None:
            num_trials = num_candidates * 2 - 1

        print(f"Candidates: {num_candidates}, Trials: {num_trials}")

        # Create base module
        base_module = dspy.ChainOfThought(EntityExtractionSignature)

        # Configure optimizer
        # DSPy 3.0+: Must set auto=None when specifying num_candidates (num_trials goes to compile())
        optimizer = MIPROv2(
            metric=entity_extraction_objective,
            auto=None,  # Disable auto mode to use explicit num_candidates
            num_candidates=num_candidates,
            max_bootstrapped_demos=max_bootstrapped_demos,
            max_labeled_demos=max_labeled_demos,
        )

        # Run optimization
        print("\nRunning MIPROv2 optimization...")
        # minibatch_size must be <= len(valset), disable minibatch for small datasets
        optimized = optimizer.compile(
            base_module,
            trainset=trainset,
            valset=valset,
            num_trials=num_trials,  # DSPy 3.0: num_trials goes to compile()
            minibatch=len(valset) >= 10,  # Only use minibatch for larger datasets
            minibatch_size=min(10, len(valset)) if len(valset) >= 10 else len(valset),
        )

        print("Optimization complete!")
        return optimized

    def optimize_relation_extraction(
        self,
        trainset: list[dspy.Example],
        valset: list[dspy.Example],
        num_candidates: int = 10,
        num_trials: int | None = None,
        max_bootstrapped_demos: int = 4,
        max_labeled_demos: int = 4,
    ) -> dspy.Module:
        """Optimize relation extraction prompts using MIPROv2."""
        print("\n" + "=" * 60)
        print("RELATION EXTRACTION OPTIMIZATION")
        print("=" * 60)
        print(f"Training samples: {len(trainset)}")
        # Calculate recommended num_trials if not provided
        if num_trials is None:
            num_trials = num_candidates * 2 - 1

        print(f"Candidates: {num_candidates}, Trials: {num_trials}")

        # Create base module
        base_module = dspy.ChainOfThought(RelationExtractionSignature)

        # Configure optimizer
        # DSPy 3.0+: Must set auto=None when specifying num_candidates (num_trials goes to compile())
        optimizer = MIPROv2(
            metric=relation_extraction_objective,
            auto=None,  # Disable auto mode to use explicit num_candidates
            num_candidates=num_candidates,
            max_bootstrapped_demos=max_bootstrapped_demos,
            max_labeled_demos=max_labeled_demos,
        )

        # Run optimization
        print("\nRunning MIPROv2 optimization...")
        # minibatch_size must be <= len(valset), disable minibatch for small datasets
        optimized = optimizer.compile(
            base_module,
            trainset=trainset,
            valset=valset,
            num_trials=num_trials,  # DSPy 3.0: num_trials goes to compile()
            minibatch=len(valset) >= 10,  # Only use minibatch for larger datasets
            minibatch_size=min(10, len(valset)) if len(valset) >= 10 else len(valset),
        )

        print("Optimization complete!")
        return optimized

    def optimize_pipeline(
        self,
        trainset: list[dspy.Example],
        valset: list[dspy.Example],
        num_candidates: int = 10,
        num_trials: int | None = None,
        max_bootstrapped_demos: int = 4,
        max_labeled_demos: int = 4,
    ) -> dspy.Module:
        """
        Optimize Entity→Relation Pipeline using MIPROv2.

        This optimizes the full pipeline where:
        1. EntityExtractor extracts entities from text
        2. RelationExtractor uses those entities to find relations

        The combined objective weights both entity and relation quality.
        """
        print("\n" + "=" * 60)
        print("PIPELINE OPTIMIZATION (Entity → Relation)")
        print("=" * 60)
        print(f"Training samples: {len(trainset)}")
        print(f"Validation samples: {len(valset)}")

        # Calculate recommended num_trials if not provided
        if num_trials is None:
            num_trials = num_candidates * 2 - 1

        print(f"Candidates: {num_candidates}, Trials: {num_trials}")

        # Create pipeline module
        base_module = EntityRelationPipeline()

        # Configure optimizer with combined objective
        optimizer = MIPROv2(
            metric=pipeline_extraction_objective,
            auto=None,
            num_candidates=num_candidates,
            max_bootstrapped_demos=max_bootstrapped_demos,
            max_labeled_demos=max_labeled_demos,
        )

        # Run optimization
        print("\nRunning MIPROv2 pipeline optimization...")
        print("Note: This optimizes BOTH entity and relation extraction together.")
        optimized = optimizer.compile(
            base_module,
            trainset=trainset,
            valset=valset,
            num_trials=num_trials,
            minibatch=len(valset) >= 10,
            minibatch_size=min(10, len(valset)) if len(valset) >= 10 else len(valset),
        )

        print("Pipeline optimization complete!")
        return optimized

    def save_optimized_module(self, module: dspy.Module, path: str, name: str):
        """Save optimized module to file."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        output_file = path / f"{name}.json"

        # Save module state
        state = module.dump_state()

        config = {
            "name": name,
            "model": self.model,
            "optimized_at": datetime.now().isoformat(),
            "state": state,
        }

        with open(output_file, "w") as f:
            json.dump(config, f, indent=2)

        print(f"Saved optimized module to: {output_file}")

    def evaluate(
        self,
        module: dspy.Module,
        testset: list[dspy.Example],
        objective_fn: callable,
    ) -> dict[str, float]:
        """Evaluate module on test set."""
        scores = []

        for example in testset:
            try:
                prediction = module(text=example.text, domain=example.domain)
                score = objective_fn(example, prediction)
                scores.append(score)
            except Exception as e:
                print(f"Evaluation error: {e}")
                scores.append(0.0)

        avg_score = sum(scores) / len(scores) if scores else 0.0

        return {
            "avg_score": avg_score,
            "min_score": min(scores) if scores else 0.0,
            "max_score": max(scores) if scores else 0.0,
            "num_samples": len(scores),
        }


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="DSPy MIPROv2 Optimization for Extraction Prompts"
    )
    parser.add_argument(
        "--training-data",
        type=str,
        help="Path to training data JSONL file",
    )
    parser.add_argument(
        "--validation-data",
        type=str,
        help="Path to validation data JSONL file",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="nemotron-3-nano:latest",
        help="Ollama model to use",
    )
    parser.add_argument(
        "--ollama-base",
        type=str,
        default="http://localhost:11434",
        help="Ollama API base URL",
    )
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=10,
        help="Number of prompt candidates to generate",
    )
    parser.add_argument(
        "--max-bootstrapped-demos",
        type=int,
        default=4,
        help="Max bootstrapped few-shot examples",
    )
    parser.add_argument(
        "--max-labeled-demos",
        type=int,
        default=4,
        help="Max labeled few-shot examples",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/dspy_prompts",
        help="Output directory for optimized prompts",
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Run quick test with sample data",
    )
    parser.add_argument(
        "--entity-only",
        action="store_true",
        help="Only optimize entity extraction",
    )
    parser.add_argument(
        "--relation-only",
        action="store_true",
        help="Only optimize relation extraction",
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="Optimize Entity→Relation Pipeline (recommended for relation extraction)",
    )

    args = parser.parse_args()

    if not DSPY_AVAILABLE:
        print("ERROR: DSPy not installed. Run: pip install dspy-ai")
        sys.exit(1)

    print("=" * 60)
    print("DSPy MIPROv2 OPTIMIZATION")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    # Load or create data
    if args.quick_test:
        print("\nRunning quick test with sample data...")
        trainset, valset = create_sample_data()
    elif args.training_data:
        print(f"\nLoading training data from: {args.training_data}")
        trainset = load_training_data(args.training_data)
        if args.validation_data:
            valset = load_training_data(args.validation_data)
        else:
            # Split training data
            split_idx = int(len(trainset) * 0.8)
            valset = trainset[split_idx:]
            trainset = trainset[:split_idx]
    else:
        print("ERROR: Provide --training-data or use --quick-test")
        sys.exit(1)

    print(f"Training samples: {len(trainset)}")
    print(f"Validation samples: {len(valset)}")

    # Initialize optimizer
    optimizer = DSPyOptimizer(model=args.model, ollama_base=args.ollama_base)

    # Run optimization based on mode
    if args.pipeline:
        # Pipeline mode: Optimize Entity→Relation together
        print("\n🔗 PIPELINE MODE: Optimizing Entity→Relation together")
        pipeline_module = optimizer.optimize_pipeline(
            trainset=trainset,
            valset=valset,
            num_candidates=args.num_candidates,
            max_bootstrapped_demos=args.max_bootstrapped_demos,
            max_labeled_demos=args.max_labeled_demos,
        )

        # Evaluate
        pipeline_results = optimizer.evaluate(
            pipeline_module, valset, pipeline_extraction_objective
        )
        print(f"\nPipeline Extraction Results:")
        print(f"  Average Score: {pipeline_results['avg_score']:.3f}")
        print(f"  Min Score: {pipeline_results['min_score']:.3f}")
        print(f"  Max Score: {pipeline_results['max_score']:.3f}")

        # Save
        optimizer.save_optimized_module(
            pipeline_module,
            args.output,
            f"pipeline_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )

    else:
        # Separate mode: Optimize entity and/or relation separately
        if not args.relation_only:
            entity_module = optimizer.optimize_entity_extraction(
                trainset=trainset,
                valset=valset,
                num_candidates=args.num_candidates,
                max_bootstrapped_demos=args.max_bootstrapped_demos,
                max_labeled_demos=args.max_labeled_demos,
            )

            # Evaluate
            entity_results = optimizer.evaluate(
                entity_module, valset, entity_extraction_objective
            )
            print(f"\nEntity Extraction Results:")
            print(f"  Average Score: {entity_results['avg_score']:.3f}")
            print(f"  Min Score: {entity_results['min_score']:.3f}")
            print(f"  Max Score: {entity_results['max_score']:.3f}")

            # Save
            optimizer.save_optimized_module(
                entity_module,
                args.output,
                f"entity_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            )

        if not args.entity_only:
            print("\n⚠️  WARNING: Standalone relation extraction may underperform.")
            print("   Consider using --pipeline for better results.")
            relation_module = optimizer.optimize_relation_extraction(
                trainset=trainset,
                valset=valset,
                num_candidates=args.num_candidates,
                max_bootstrapped_demos=args.max_bootstrapped_demos,
                max_labeled_demos=args.max_labeled_demos,
            )

            # Evaluate
            relation_results = optimizer.evaluate(
                relation_module, valset, relation_extraction_objective
            )
            print(f"\nRelation Extraction Results:")
            print(f"  Average Score: {relation_results['avg_score']:.3f}")
            print(f"  Min Score: {relation_results['min_score']:.3f}")
            print(f"  Max Score: {relation_results['max_score']:.3f}")

            # Save
            optimizer.save_optimized_module(
                relation_module,
                args.output,
                f"relation_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            )

    print("\n" + "=" * 60)
    print("OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(f"Output directory: {args.output}")
    print("\nNext steps:")
    print("1. Review optimized prompts in the output directory")
    print("2. Run A/B test against baseline: scripts/evaluate_dspy_prompts.py")
    print("3. Update docs/dspy/OPTIMIZATION_LOG.md with results")


if __name__ == "__main__":
    main()
