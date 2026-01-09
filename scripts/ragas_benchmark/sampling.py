"""
Stratified sampling engine for RAGAS benchmark.

Implements quota-based sampling across:
- doc_type (clean_text, log_ticket, etc.)
- question_type (lookup, multihop, comparison, etc.)
- difficulty (D1, D2, D3)

Sprint 82: Phase 1 - Text-Only Benchmark
"""

import random
from typing import Dict, List, Optional, Set
from collections import defaultdict
import logging

from .models import NormalizedSample, SamplingStats
from .config import (
    DOC_TYPE_QUOTAS_PHASE1,
    QUESTION_TYPE_QUOTAS_PHASE1,
    DIFFICULTY_DISTRIBUTION,
    QUESTION_TYPE_KEYWORDS,
    DEFAULT_QUESTION_TYPE,
)

logger = logging.getLogger(__name__)


def stratified_sample(
    pool: List[NormalizedSample],
    doc_type_quotas: Dict[str, int],
    qtype_quotas: Dict[str, Dict[str, int]],
    seed: int = 42
) -> List[NormalizedSample]:
    """
    Sample from pool respecting quotas.

    Multi-level stratification:
    1. First by doc_type
    2. Then by question_type within each doc_type
    3. Difficulty is assigned based on heuristics

    Args:
        pool: List of all available samples
        doc_type_quotas: Target count per doc_type
        qtype_quotas: Target count per question_type within each doc_type
        seed: Random seed for reproducibility

    Returns:
        List of samples matching quotas (sum of doc_type_quotas)
    """
    rng = random.Random(seed)

    # Group pool by doc_type and question_type
    grouped = _group_samples(pool)

    # Sample according to quotas
    selected: List[NormalizedSample] = []
    stats = SamplingStats()

    for doc_type, doc_quota in doc_type_quotas.items():
        if doc_type not in grouped:
            logger.warning(f"No samples found for doc_type: {doc_type}")
            continue

        # Get question type quotas for this doc_type
        qtypes = qtype_quotas.get(doc_type, {})

        # Sample each question type
        doc_samples = []
        for qtype, qtype_quota in qtypes.items():
            available = grouped.get(doc_type, {}).get(qtype, [])

            if len(available) < qtype_quota:
                logger.warning(
                    f"Underfill: {doc_type}/{qtype} has {len(available)} "
                    f"samples, need {qtype_quota}"
                )
                # Take all available and record shortfall
                sampled = available.copy()
                stats.record_drop(f"underfill_{doc_type}_{qtype}")
            else:
                # Random sample
                sampled = rng.sample(available, qtype_quota)

            doc_samples.extend(sampled)

        # Handle overall doc_type quota fulfillment
        if len(doc_samples) < doc_quota:
            # Try to fill from "lookup" or any remaining samples
            shortfall = doc_quota - len(doc_samples)
            logger.info(f"Filling {shortfall} samples for {doc_type} from fallback")

            # Get all remaining samples for this doc_type
            remaining = _get_remaining_samples(
                grouped.get(doc_type, {}),
                set(s.id for s in doc_samples)
            )

            if remaining:
                fill_count = min(shortfall, len(remaining))
                fill_samples = rng.sample(remaining, fill_count)
                doc_samples.extend(fill_samples)

        selected.extend(doc_samples)

    # Deduplicate (shouldn't happen, but safety check)
    seen_ids: Set[str] = set()
    unique_samples = []
    for sample in selected:
        if sample.id not in seen_ids:
            seen_ids.add(sample.id)
            unique_samples.append(sample)
            stats.add_sample(sample)

    logger.info(f"Stratified sampling complete: {len(unique_samples)} samples")
    logger.info(f"Stats:\n{stats.to_report()}")

    return unique_samples


def _group_samples(
    pool: List[NormalizedSample]
) -> Dict[str, Dict[str, List[NormalizedSample]]]:
    """
    Group samples by doc_type and question_type.

    Returns:
        Nested dict: {doc_type: {question_type: [samples]}}
    """
    grouped: Dict[str, Dict[str, List[NormalizedSample]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for sample in pool:
        grouped[sample.doc_type][sample.question_type].append(sample)

    return grouped


def _get_remaining_samples(
    doc_groups: Dict[str, List[NormalizedSample]],
    excluded_ids: Set[str]
) -> List[NormalizedSample]:
    """
    Get all samples not in excluded set.

    Args:
        doc_groups: Groups by question_type
        excluded_ids: Set of already selected IDs

    Returns:
        List of remaining samples
    """
    remaining = []
    for samples in doc_groups.values():
        for sample in samples:
            if sample.id not in excluded_ids:
                remaining.append(sample)
    return remaining


def classify_question_type(question: str, doc_type: str = "clean_text") -> str:
    """
    Classify question type based on keywords.

    Args:
        question: The question text
        doc_type: Document type for context-aware classification

    Returns:
        Question type string
    """
    question_lower = question.lower()

    # Check each question type's keywords
    for qtype, keywords in QUESTION_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in question_lower:
                return qtype

    return DEFAULT_QUESTION_TYPE


def assign_difficulty(
    doc_type: str,
    question_type: str,
    rng: Optional[random.Random] = None
) -> str:
    """
    Assign difficulty based on doc_type, question_type, and randomness.

    Combines heuristics with target distribution:
    - Certain question types skew harder (multihop, policy)
    - Certain doc_types are inherently harder (log_ticket)
    - Random variation maintains overall distribution

    Args:
        doc_type: Document type
        question_type: Question type
        rng: Random number generator (for reproducibility)

    Returns:
        Difficulty level (D1, D2, D3)
    """
    if rng is None:
        rng = random.Random()

    # Heuristic-based baseline
    if question_type in ["multihop", "policy"]:
        # Hard questions: mostly D2-D3
        weights = [0.1, 0.4, 0.5]  # D1, D2, D3
    elif question_type in ["comparison", "howto"]:
        # Medium questions: mostly D2
        weights = [0.2, 0.5, 0.3]
    elif question_type in ["lookup", "entity", "definition"]:
        # Easy questions: mostly D1-D2
        weights = [0.5, 0.35, 0.15]
    elif question_type in ["numeric"]:
        # Numeric can vary
        weights = [0.4, 0.4, 0.2]
    else:
        # Default: follow global distribution
        weights = [
            DIFFICULTY_DISTRIBUTION["D1"],
            DIFFICULTY_DISTRIBUTION["D2"],
            DIFFICULTY_DISTRIBUTION["D3"],
        ]

    # Adjust for doc_type
    if doc_type == "log_ticket":
        # Log questions are generally harder
        weights = [w * 0.8 if i == 0 else w * 1.1 for i, w in enumerate(weights)]

    # Normalize weights
    total = sum(weights)
    weights = [w / total for w in weights]

    # Random selection
    choices = ["D1", "D2", "D3"]
    return rng.choices(choices, weights=weights)[0]


def rebalance_difficulty(
    samples: List[NormalizedSample],
    target_distribution: Dict[str, float],
    seed: int = 42
) -> List[NormalizedSample]:
    """
    Rebalance difficulty distribution of samples.

    Reassigns difficulty to match target distribution while
    respecting question type constraints.

    Args:
        samples: List of samples to rebalance
        target_distribution: Target percentage for each difficulty
        seed: Random seed

    Returns:
        Samples with rebalanced difficulty
    """
    rng = random.Random(seed)

    # Calculate target counts
    total = len(samples)
    target_counts = {
        diff: int(total * pct)
        for diff, pct in target_distribution.items()
    }

    # Adjust for rounding
    assigned = sum(target_counts.values())
    if assigned < total:
        target_counts["D2"] += total - assigned

    # Group by current difficulty
    by_difficulty: Dict[str, List[int]] = defaultdict(list)
    for idx, sample in enumerate(samples):
        by_difficulty[sample.difficulty].append(idx)

    # Shuffle within groups
    for diff in by_difficulty:
        rng.shuffle(by_difficulty[diff])

    # Reassign difficulties
    result = list(samples)
    all_indices = list(range(total))
    rng.shuffle(all_indices)

    idx_ptr = 0
    for diff, count in target_counts.items():
        for _ in range(count):
            if idx_ptr < len(all_indices):
                result[all_indices[idx_ptr]].difficulty = diff
                idx_ptr += 1

    return result


def validate_distribution(
    samples: List[NormalizedSample],
    doc_type_quotas: Dict[str, int],
    qtype_quotas: Dict[str, Dict[str, int]],
    tolerance_pct: float = 5.0
) -> tuple[bool, str]:
    """
    Validate sample distribution matches quotas.

    Args:
        samples: List of samples to validate
        doc_type_quotas: Target doc_type quotas
        qtype_quotas: Target question_type quotas
        tolerance_pct: Allowed deviation percentage

    Returns:
        Tuple of (is_valid, message)
    """
    stats = SamplingStats()
    for sample in samples:
        stats.add_sample(sample)

    messages = []
    is_valid = True

    # Check doc_type quotas
    for doc_type, target in doc_type_quotas.items():
        actual = stats.doc_type_counts.get(doc_type, 0)
        deviation = abs(actual - target) / target * 100 if target > 0 else 0

        if deviation > tolerance_pct:
            is_valid = False
            messages.append(
                f"Doc type '{doc_type}': {actual} (target: {target}, "
                f"deviation: {deviation:.1f}%)"
            )

    # Check question_type quotas
    for doc_type, qtypes in qtype_quotas.items():
        for qtype, target in qtypes.items():
            actual = stats.question_type_counts.get(doc_type, {}).get(qtype, 0)
            deviation = abs(actual - target) / target * 100 if target > 0 else 0

            if deviation > tolerance_pct:
                is_valid = False
                messages.append(
                    f"Question type '{doc_type}/{qtype}': {actual} "
                    f"(target: {target}, deviation: {deviation:.1f}%)"
                )

    # Check difficulty distribution
    total = len(samples)
    for diff, target_pct in DIFFICULTY_DISTRIBUTION.items():
        actual_count = stats.difficulty_counts.get(diff, 0)
        actual_pct = actual_count / total * 100 if total > 0 else 0
        target_pct_100 = target_pct * 100
        deviation = abs(actual_pct - target_pct_100)

        if deviation > tolerance_pct:
            is_valid = False
            messages.append(
                f"Difficulty '{diff}': {actual_pct:.1f}% "
                f"(target: {target_pct_100:.1f}%, deviation: {deviation:.1f}%)"
            )

    if is_valid:
        return True, "Distribution validation passed"
    else:
        return False, "Distribution validation failed:\n" + "\n".join(messages)
