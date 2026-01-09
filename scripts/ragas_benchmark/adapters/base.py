"""
Base adapter class for dataset normalization.

Sprint 82: Phase 1 - Text-Only Benchmark
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

from ..models import NormalizedSample
from ..config import (
    QUESTION_TYPE_KEYWORDS,
    DEFAULT_QUESTION_TYPE,
    DIFFICULTY_DISTRIBUTION,
    MIN_CONTEXT_LENGTH,
    MIN_QUESTION_LENGTH,
)

logger = logging.getLogger(__name__)


class DatasetAdapter(ABC):
    """
    Abstract adapter for dataset normalization.

    Each dataset adapter transforms raw records from a specific
    HuggingFace dataset into the NormalizedSample format.

    Subclasses must implement:
    - adapt(): Transform a single record
    - get_doc_type(): Return the doc_type for this dataset
    """

    def __init__(self):
        self.drop_count = 0
        self.drop_reasons: Dict[str, int] = {}

    @abstractmethod
    def adapt(self, record: Dict[str, Any], record_idx: int = 0) -> Optional[NormalizedSample]:
        """
        Transform raw record to normalized format.

        Args:
            record: Raw record from HuggingFace dataset
            record_idx: Index of the record (for ID generation)

        Returns:
            NormalizedSample or None if record should be dropped
        """
        pass

    @abstractmethod
    def get_doc_type(self) -> str:
        """Return doc_type for this dataset."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return source dataset name (e.g., 'hotpot_qa')."""
        pass

    def get_fields_mapping(self) -> Dict[str, str]:
        """
        Return field name mapping for this dataset.

        Override in subclasses to document field mappings.

        Returns:
            Dict mapping canonical field names to dataset-specific names
        """
        return {}

    def classify_question_type(self, question: str) -> str:
        """
        Classify question type based on keywords.

        Args:
            question: The question text

        Returns:
            Question type string (lookup, definition, howto, etc.)
        """
        question_lower = question.lower()

        for qtype, keywords in QUESTION_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in question_lower:
                    return qtype

        return DEFAULT_QUESTION_TYPE

    def assign_difficulty(self, question_type: str, context_length: int) -> str:
        """
        Assign difficulty based on question type and context.

        Heuristics:
        - Short contexts + lookup → D1
        - Multihop/comparison → D2-D3
        - Policy/complex inference → D3

        Args:
            question_type: The classified question type
            context_length: Total length of contexts

        Returns:
            Difficulty level (D1, D2, or D3)
        """
        # Hard questions
        if question_type in ["multihop", "policy"]:
            return "D3" if context_length > 2000 else "D2"

        # Medium questions
        if question_type in ["comparison", "howto"]:
            return "D2"

        # Easy questions
        if question_type in ["lookup", "entity", "numeric"]:
            return "D1" if context_length < 1000 else "D2"

        # Default based on context length
        if context_length < 500:
            return "D1"
        elif context_length < 2000:
            return "D2"
        else:
            return "D3"

    def validate_sample(
        self,
        question: str,
        answer: str,
        contexts: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate sample meets minimum requirements.

        Args:
            question: Question text
            answer: Ground truth answer
            contexts: List of context strings

        Returns:
            Tuple of (is_valid, drop_reason)
        """
        # Check question
        if not question or len(question.strip()) < MIN_QUESTION_LENGTH:
            return False, "question_too_short"

        # Check answer
        if not answer or len(answer.strip()) == 0:
            return False, "empty_answer"

        # Check contexts
        if not contexts:
            return False, "no_contexts"

        total_context_len = sum(len(c) for c in contexts if c)
        if total_context_len < MIN_CONTEXT_LENGTH:
            return False, "context_too_short"

        return True, None

    def record_drop(self, reason: str):
        """Record a dropped sample with reason."""
        self.drop_count += 1
        self.drop_reasons[reason] = self.drop_reasons.get(reason, 0) + 1
        logger.debug(f"Dropped sample: {reason}")

    def get_drop_stats(self) -> Dict[str, Any]:
        """Get drop statistics."""
        return {
            "total_dropped": self.drop_count,
            "reasons": self.drop_reasons.copy(),
        }

    def reset_stats(self):
        """Reset drop statistics."""
        self.drop_count = 0
        self.drop_reasons = {}

    def generate_id(self, source: str, original_id: str, idx: int) -> str:
        """
        Generate a unique ID for the sample.

        Format: ragas_phase1_{idx:04d}_{source}_{original_id[:8]}

        Args:
            source: Source dataset name
            original_id: Original ID from dataset
            idx: Sequential index

        Returns:
            Unique sample ID
        """
        # Clean original_id (remove special chars, truncate)
        clean_id = "".join(c for c in str(original_id) if c.isalnum())[:8]
        return f"ragas_phase1_{idx:04d}_{source}_{clean_id}"
