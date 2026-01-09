"""
Unanswerable question generator for RAGAS benchmark.

Generates variants of answerable questions that cannot be
answered from the given contexts, for anti-hallucination testing.

Generation Methods:
1. temporal_shift: Add future/past context that doesn't exist
2. entity_swap: Replace key entity with non-existent one
3. negation: Ask about something explicitly NOT in corpus
4. cross_domain: Ask about unrelated domain

Sprint 82: Phase 1 - Text-Only Benchmark
"""

import random
import re
from typing import Dict, List, Optional
from dataclasses import replace
import logging

from .models import NormalizedSample
from .config import (
    UNANSWERABLE_METHOD_DISTRIBUTION,
    TEMPORAL_SHIFT_PREFIXES,
    FAKE_ENTITIES,
    CROSS_DOMAIN_TEMPLATES,
)

logger = logging.getLogger(__name__)


class UnanswerableGenerator:
    """
    Generate unanswerable variants of answerable questions.

    These variants test a RAG system's ability to recognize
    when it cannot answer a question and avoid hallucination.
    """

    def __init__(self, seed: int = 42):
        """
        Initialize generator.

        Args:
            seed: Random seed for reproducibility
        """
        self.rng = random.Random(seed)
        self.generated_count = 0
        self.method_counts: Dict[str, int] = {
            "temporal_shift": 0,
            "entity_swap": 0,
            "negation": 0,
            "cross_domain": 0,
        }

    def temporal_shift(self, sample: NormalizedSample) -> NormalizedSample:
        """
        Add future/past context that doesn't exist.

        Modifies the question to reference a non-existent version,
        date, or context that the documents don't contain.

        Example:
            Original: "What year was X founded?"
            Modified: "In the 2030 update, what year was X founded?"

        Args:
            sample: Original answerable sample

        Returns:
            New unanswerable sample
        """
        prefix = self.rng.choice(TEMPORAL_SHIFT_PREFIXES)

        # Lowercase first character of original question
        question = sample.question
        if question and question[0].isupper():
            question = question[0].lower() + question[1:]

        new_question = prefix + question

        return self._create_unanswerable(
            sample,
            new_question,
            method="temporal_shift"
        )

    def entity_swap(self, sample: NormalizedSample) -> NormalizedSample:
        """
        Replace key entity with non-existent one.

        Identifies the main entity in the question and replaces
        it with a clearly fictional entity.

        Example:
            Original: "When was Apple founded?"
            Modified: "When was Zephyrix Corp founded?"

        Args:
            sample: Original answerable sample

        Returns:
            New unanswerable sample
        """
        fake_entity = self.rng.choice(FAKE_ENTITIES)

        # Try to identify and replace the main entity
        new_question = self._replace_entity(sample.question, fake_entity)

        return self._create_unanswerable(
            sample,
            new_question,
            method="entity_swap"
        )

    def negation(self, sample: NormalizedSample) -> NormalizedSample:
        """
        Ask about something explicitly NOT in corpus.

        Transforms the question to ask for information that
        explicitly contradicts or is absent from the context.

        Example:
            Original: "What is X known for?"
            Modified: "What aspects of X are NOT mentioned in the documents?"

        Args:
            sample: Original answerable sample

        Returns:
            New unanswerable sample
        """
        # Extract key subject from question
        subject = self._extract_subject(sample.question)

        negation_templates = [
            f"What information about {subject} is NOT mentioned in these documents?",
            f"What aspects of {subject} are absent from this context?",
            f"What details about {subject} cannot be found in the given passages?",
            f"What is explicitly NOT stated about {subject}?",
            f"What related topics to {subject} are missing from this text?",
        ]

        new_question = self.rng.choice(negation_templates)

        return self._create_unanswerable(
            sample,
            new_question,
            method="negation"
        )

    def cross_domain(self, sample: NormalizedSample) -> NormalizedSample:
        """
        Ask about unrelated domain.

        Extracts an entity from the original question and asks
        about it in a completely different domain context.

        Example:
            Original: (HotpotQA about history)
            Modified: "What is the chemical formula for X?"

        Args:
            sample: Original answerable sample

        Returns:
            New unanswerable sample
        """
        # Extract entity for template
        entity = self._extract_subject(sample.question)

        # Select template
        template = self.rng.choice(CROSS_DOMAIN_TEMPLATES)
        new_question = template.format(entity=entity)

        return self._create_unanswerable(
            sample,
            new_question,
            method="cross_domain"
        )

    def generate_batch(
        self,
        samples: List[NormalizedSample],
        target_count: int = 50,
        method_distribution: Optional[Dict[str, float]] = None
    ) -> List[NormalizedSample]:
        """
        Generate target_count unanswerables from pool.

        Distributes generation across methods according to
        the specified distribution.

        Args:
            samples: Pool of answerable samples to transform
            target_count: Number of unanswerables to generate
            method_distribution: Optional method weights

        Returns:
            List of unanswerable samples
        """
        if method_distribution is None:
            method_distribution = UNANSWERABLE_METHOD_DISTRIBUTION

        # Calculate per-method counts
        method_counts = {}
        remaining = target_count
        methods = list(method_distribution.keys())

        for i, method in enumerate(methods):
            if i == len(methods) - 1:
                # Last method gets remainder
                method_counts[method] = remaining
            else:
                count = int(target_count * method_distribution[method])
                method_counts[method] = count
                remaining -= count

        logger.info(f"Generating {target_count} unanswerables: {method_counts}")

        # Select source samples
        if len(samples) < target_count:
            logger.warning(
                f"Not enough samples ({len(samples)}) for {target_count} "
                "unanswerables. Some may be duplicated."
            )
            # Allow reuse
            source_samples = self.rng.choices(samples, k=target_count)
        else:
            source_samples = self.rng.sample(samples, target_count)

        # Generate unanswerables
        unanswerables = []
        sample_idx = 0

        method_funcs = {
            "temporal_shift": self.temporal_shift,
            "entity_swap": self.entity_swap,
            "negation": self.negation,
            "cross_domain": self.cross_domain,
        }

        for method, count in method_counts.items():
            func = method_funcs[method]

            for _ in range(count):
                if sample_idx >= len(source_samples):
                    break

                source = source_samples[sample_idx]
                unanswerable = func(source)
                unanswerables.append(unanswerable)

                sample_idx += 1
                self.generated_count += 1
                self.method_counts[method] += 1

        logger.info(
            f"Generated {len(unanswerables)} unanswerables "
            f"(distribution: {self.method_counts})"
        )

        return unanswerables

    def _create_unanswerable(
        self,
        original: NormalizedSample,
        new_question: str,
        method: str
    ) -> NormalizedSample:
        """
        Create unanswerable variant with proper metadata.

        Args:
            original: Original answerable sample
            new_question: Modified unanswerable question
            method: Generation method used

        Returns:
            New NormalizedSample marked as unanswerable
        """
        # Create new ID
        new_id = f"unanswerable_{self.generated_count:04d}_{original.id}"

        # Build metadata
        metadata = {
            **original.metadata,
            "unanswerable_method": method,
            "original_question": original.question,
            "original_answer": original.ground_truth,
            "original_id": original.id,
        }

        return NormalizedSample(
            id=new_id,
            question=new_question,
            ground_truth="",  # Empty = unanswerable
            contexts=original.contexts,  # Keep original contexts
            doc_type=original.doc_type,
            question_type=original.question_type,
            difficulty="D3",  # Unanswerables are hard
            answerable=False,
            source_dataset=original.source_dataset,
            metadata=metadata,
        )

    def _replace_entity(self, question: str, fake_entity: str) -> str:
        """
        Replace main entity in question with fake entity.

        Uses heuristics to identify proper nouns and entities.
        """
        # Find capitalized words/phrases (potential entities)
        # Pattern: sequence of capitalized words
        entity_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        matches = re.findall(entity_pattern, question)

        if matches:
            # Replace the longest match (likely main entity)
            main_entity = max(matches, key=len)
            return question.replace(main_entity, fake_entity, 1)

        # Fallback: look for quoted strings
        quoted_pattern = r'"([^"]+)"'
        quoted_matches = re.findall(quoted_pattern, question)
        if quoted_matches:
            return question.replace(quoted_matches[0], fake_entity, 1)

        # Last resort: prepend context about fake entity
        return f"Regarding {fake_entity}, {question.lower()}"

    def _extract_subject(self, question: str) -> str:
        """
        Extract main subject from question.

        Uses heuristics to identify what the question is about.
        """
        # Remove question words
        cleaned = re.sub(
            r'^(what|when|where|who|which|how|why|is|are|was|were|do|does|did)\s+',
            '',
            question.lower(),
            flags=re.IGNORECASE
        )

        # Try to find capitalized entity
        entity_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        matches = re.findall(entity_pattern, question)
        if matches:
            return max(matches, key=len)

        # Fallback: use first few words after cleaning
        words = cleaned.split()
        if len(words) >= 3:
            return " ".join(words[:3])
        elif words:
            return " ".join(words)

        return "this topic"

    def get_stats(self) -> Dict[str, int]:
        """Get generation statistics."""
        return {
            "total_generated": self.generated_count,
            "by_method": self.method_counts.copy(),
        }

    def reset_stats(self):
        """Reset generation statistics."""
        self.generated_count = 0
        self.method_counts = {
            "temporal_shift": 0,
            "entity_swap": 0,
            "negation": 0,
            "cross_domain": 0,
        }
