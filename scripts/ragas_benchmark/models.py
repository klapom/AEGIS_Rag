"""
Data models for RAGAS benchmark samples.

Sprint 82: Phase 1 - Text-Only Benchmark
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


@dataclass
class NormalizedSample:
    """
    Normalized sample format for all datasets.

    This is the canonical format used across all dataset adapters,
    ensuring consistent structure for RAGAS evaluation.

    Attributes:
        id: Unique identifier for the sample
        question: The question to be answered
        ground_truth: The expected correct answer
        contexts: List of context passages (supporting documents)
        doc_type: Document type (clean_text, log_ticket, table, code_config, etc.)
        question_type: Question category (lookup, definition, howto, multihop, etc.)
        difficulty: D1 (easy), D2 (medium), D3 (hard)
        answerable: Whether the question is answerable from contexts
        source_dataset: Original dataset name (hotpot_qa, ragbench, logqa)
        metadata: Additional dataset-specific metadata
    """
    id: str
    question: str
    ground_truth: str
    contexts: List[str]
    doc_type: str
    question_type: str
    difficulty: str
    answerable: bool = True
    source_dataset: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "question": self.question,
            "ground_truth": self.ground_truth,
            "contexts": self.contexts,
            "answerable": self.answerable,
            "doc_type": self.doc_type,
            "question_type": self.question_type,
            "difficulty": self.difficulty,
            "source_dataset": self.source_dataset,
            "metadata": {
                **self.metadata,
                "generation_timestamp": datetime.utcnow().isoformat() + "Z",
                "generator_version": "1.0.0",
            }
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormalizedSample":
        """Create NormalizedSample from dictionary."""
        metadata = data.get("metadata", {})
        # Remove generation-time fields from metadata when reconstructing
        metadata.pop("generation_timestamp", None)
        metadata.pop("generator_version", None)

        return cls(
            id=data["id"],
            question=data["question"],
            ground_truth=data["ground_truth"],
            contexts=data["contexts"],
            doc_type=data["doc_type"],
            question_type=data["question_type"],
            difficulty=data["difficulty"],
            answerable=data.get("answerable", True),
            source_dataset=data.get("source_dataset", ""),
            metadata=metadata,
        )

    def __hash__(self):
        """Allow NormalizedSample to be used in sets."""
        return hash(self.id)

    def __eq__(self, other):
        """Equality based on id."""
        if isinstance(other, NormalizedSample):
            return self.id == other.id
        return False


@dataclass
class SamplingStats:
    """Statistics for stratified sampling validation."""
    total_samples: int = 0
    doc_type_counts: Dict[str, int] = field(default_factory=dict)
    question_type_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)
    difficulty_counts: Dict[str, int] = field(default_factory=dict)
    answerable_count: int = 0
    unanswerable_count: int = 0
    dropped_samples: int = 0
    drop_reasons: Dict[str, int] = field(default_factory=dict)

    def add_sample(self, sample: NormalizedSample):
        """Update stats with a new sample."""
        self.total_samples += 1

        # Doc type
        self.doc_type_counts[sample.doc_type] = \
            self.doc_type_counts.get(sample.doc_type, 0) + 1

        # Question type (nested by doc_type)
        if sample.doc_type not in self.question_type_counts:
            self.question_type_counts[sample.doc_type] = {}
        self.question_type_counts[sample.doc_type][sample.question_type] = \
            self.question_type_counts[sample.doc_type].get(sample.question_type, 0) + 1

        # Difficulty
        self.difficulty_counts[sample.difficulty] = \
            self.difficulty_counts.get(sample.difficulty, 0) + 1

        # Answerable
        if sample.answerable:
            self.answerable_count += 1
        else:
            self.unanswerable_count += 1

    def record_drop(self, reason: str):
        """Record a dropped sample with reason."""
        self.dropped_samples += 1
        self.drop_reasons[reason] = self.drop_reasons.get(reason, 0) + 1

    def to_report(self) -> str:
        """Generate human-readable report."""
        lines = [
            "=" * 60,
            "RAGAS Benchmark Sampling Statistics",
            "=" * 60,
            f"Total Samples: {self.total_samples}",
            f"  - Answerable: {self.answerable_count} ({self.answerable_count/max(1,self.total_samples)*100:.1f}%)",
            f"  - Unanswerable: {self.unanswerable_count} ({self.unanswerable_count/max(1,self.total_samples)*100:.1f}%)",
            "",
            "Doc Types:",
        ]
        for doc_type, count in sorted(self.doc_type_counts.items()):
            lines.append(f"  {doc_type}: {count}")

        lines.append("")
        lines.append("Question Types (by doc_type):")
        for doc_type, qtypes in sorted(self.question_type_counts.items()):
            lines.append(f"  [{doc_type}]")
            for qtype, count in sorted(qtypes.items()):
                lines.append(f"    {qtype}: {count}")

        lines.append("")
        lines.append("Difficulty Distribution:")
        for diff, count in sorted(self.difficulty_counts.items()):
            pct = count / max(1, self.total_samples) * 100
            lines.append(f"  {diff}: {count} ({pct:.1f}%)")

        if self.dropped_samples > 0:
            lines.append("")
            lines.append(f"Dropped Samples: {self.dropped_samples}")
            for reason, count in sorted(self.drop_reasons.items()):
                lines.append(f"  {reason}: {count}")

        lines.append("=" * 60)
        return "\n".join(lines)
