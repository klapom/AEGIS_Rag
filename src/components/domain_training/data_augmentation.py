"""Training Data Augmentation Component for DSPy Domain Training.

Sprint 45 - Feature 45.11: Training Data Augmentation

This module provides LLM-based generation of additional training samples from seed examples.
Uses Ollama LLM (qwen3:32b) to generate diverse, high-quality training data for domain-specific
entity and relation extraction.

Key Features:
- Generate N synthetic training samples from 5-10 seed examples
- Batch generation with configurable batch size
- JSON parsing and validation of generated samples
- Quality filtering (text length, entity count, relation validation)
- Progress logging and error recovery

Architecture:
    Seed Samples → LLM Prompt → Ollama API → JSON Parse → Validation → Augmented Dataset

    Process:
    1. Format seed examples into few-shot prompt
    2. Call Ollama LLM to generate batch of samples
    3. Parse JSON response and validate structure
    4. Filter by quality criteria (length, entity count)
    5. Return validated samples

Usage:
    >>> from src.components.domain_training import get_training_data_augmenter
    >>> augmenter = get_training_data_augmenter()
    >>>
    >>> seed_samples = [
    ...     {
    ...         "text": "FastAPI is a modern web framework...",
    ...         "entities": ["FastAPI", "web framework"],
    ...         "relations": [{"subject": "FastAPI", "predicate": "is_a", "object": "web framework"}]
    ...     },
    ...     ...  # 5-10 seed samples
    ... ]
    >>>
    >>> generated = await augmenter.augment(
    ...     seed_samples=seed_samples,
    ...     target_count=20,
    ...     batch_size=5
    ... )
    >>> print(f"Generated {len(generated)} samples")

Quality Criteria:
- Text length: 50-2000 characters
- Minimum entities: 2
- Valid JSON structure with text, entities, relations fields
- Non-empty text and entities list

Performance:
- Batch size 5: ~30s per batch (qwen3:32b)
- Target count 20: ~2 minutes total
- Temperature 0.8 for diversity
"""

import json
import re

import httpx
import structlog

from src.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


AUGMENTATION_PROMPT = """You are generating training data for an entity/relation extraction system.

Given these example documents with their extracted entities and relations:

{examples}

Generate {count} NEW, DIVERSE documents in the same domain/style with extracted entities.
The new documents should:
1. Cover different topics within the same domain
2. Have varying lengths (100-500 words)
3. Include realistic entities and relations
4. NOT copy or closely paraphrase the examples

Output as JSON array:
[
    {{
        "text": "The document text...",
        "entities": ["Entity1", "Entity2", ...],
        "relations": [
            {{"subject": "Entity1", "predicate": "relationship", "object": "Entity2"}}
        ]
    }},
    ...
]

Generate {count} unique samples:
"""


class TrainingDataAugmenter:
    """Generates additional training samples using LLM.

    This class uses Ollama LLM to generate synthetic training data for domain-specific
    entity and relation extraction. Given 5-10 seed samples, it can generate N additional
    samples in the same style and domain.

    Attributes:
        llm_model (str): Ollama model to use for generation (default: qwen3:32b)

    Example:
        >>> augmenter = TrainingDataAugmenter(llm_model="qwen3:32b")
        >>> generated = await augmenter.augment(
        ...     seed_samples=[...],
        ...     target_count=20,
        ...     batch_size=5
        ... )
    """

    def __init__(self, llm_model: str = "qwen3:32b"):
        """Initialize the training data augmenter.

        Args:
            llm_model: Ollama model name for generation (default: qwen3:32b)
        """
        self.llm_model = llm_model

    async def augment(
        self, seed_samples: list[dict], target_count: int = 20, batch_size: int = 5
    ) -> list[dict]:
        """Generate additional training samples from seed examples.

        Uses LLM to generate synthetic training data that matches the style and domain
        of the provided seed samples. Generation is done in batches to handle rate limits
        and improve reliability.

        Args:
            seed_samples: 5-10 seed samples with {text, entities, relations} format
            target_count: Number of samples to generate (default: 20)
            batch_size: Samples to generate per LLM call (default: 5)

        Returns:
            List of generated samples with same format as input:
            [
                {
                    "text": "Document text...",
                    "entities": ["Entity1", "Entity2", ...],
                    "relations": [
                        {"subject": "Entity1", "predicate": "rel", "object": "Entity2"}
                    ]
                },
                ...
            ]

        Raises:
            ValueError: If less than 5 seed samples provided
            httpx.HTTPError: If Ollama API call fails

        Example:
            >>> generated = await augmenter.augment(
            ...     seed_samples=[...],  # 5-10 seed samples
            ...     target_count=20,
            ...     batch_size=5
            ... )
            >>> print(f"Generated {len(generated)} samples")
        """
        if len(seed_samples) < 5:
            raise ValueError("At least 5 seed samples required")

        logger.info(
            "augmentation_start",
            seed_count=len(seed_samples),
            target_count=target_count,
            batch_size=batch_size,
            llm_model=self.llm_model,
        )

        generated = []
        remaining = target_count

        while remaining > 0:
            batch_count = min(batch_size, remaining)

            try:
                batch = await self._generate_batch(seed_samples, batch_count)
                generated.extend(batch)
                remaining -= len(batch)

                logger.info(
                    "augmentation_progress",
                    generated=len(generated),
                    remaining=remaining,
                    batch_count=len(batch),
                )
            except Exception as e:
                logger.error(
                    "augmentation_batch_failed",
                    error=str(e),
                    batch_count=batch_count,
                    exc_info=True,
                )
                # Continue with next batch instead of failing completely
                remaining -= batch_count

        # Validate and filter generated samples
        validated = self._validate_samples(generated)

        logger.info(
            "augmentation_complete",
            generated=len(generated),
            validated=len(validated),
            validation_rate=len(validated) / len(generated) if generated else 0,
        )

        return validated

    async def _generate_batch(self, seed_samples: list[dict], count: int) -> list[dict]:
        """Generate a batch of samples using LLM.

        Args:
            seed_samples: Seed samples for few-shot prompting
            count: Number of samples to generate in this batch

        Returns:
            List of generated samples (unvalidated)

        Raises:
            ValueError: If LLM response cannot be parsed
            httpx.HTTPError: If Ollama API call fails
        """
        # Format examples for prompt (use first 5 seed samples)
        examples_text = "\n\n".join(
            [
                f"Example {i+1}:\nText: {s['text'][:500]}...\n"
                f"Entities: {s['entities']}\n"
                f"Relations: {s.get('relations', [])}"
                for i, s in enumerate(seed_samples[:5])
            ]
        )

        prompt = AUGMENTATION_PROMPT.format(examples=examples_text, count=count)

        logger.debug(
            "generating_batch",
            count=count,
            prompt_length=len(prompt),
            model=self.llm_model,
        )

        response = await self._call_llm(prompt)
        samples = self._parse_response(response)

        logger.debug(
            "batch_generated",
            count=count,
            parsed_count=len(samples),
        )

        return samples

    async def _call_llm(self, prompt: str) -> str:
        """Call Ollama LLM with the given prompt.

        Args:
            prompt: Prompt text for generation

        Returns:
            LLM response text

        Raises:
            httpx.HTTPError: If Ollama API call fails
        """
        ollama_url = settings.ollama_base_url or "http://localhost:11434"

        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.8,  # Higher temperature for diversity
                        "num_predict": 4000,  # Max tokens for multiple samples
                    },
                },
            )
            response.raise_for_status()
            return response.json()["response"]

    def _parse_response(self, response: str) -> list[dict]:
        """Parse LLM response to extract JSON sample array.

        Args:
            response: Raw LLM response text

        Returns:
            List of parsed samples

        Raises:
            ValueError: If no valid JSON array found in response
        """
        # Find JSON array in response (handles surrounding text)
        json_match = re.search(r"\[[\s\S]*\]", response)
        if not json_match:
            logger.error(
                "json_parse_failed",
                response_preview=response[:500],
            )
            raise ValueError("Could not find JSON array in response")

        try:
            samples = json.loads(json_match.group())
            if not isinstance(samples, list):
                raise ValueError("Parsed JSON is not an array")
            return samples
        except json.JSONDecodeError as e:
            logger.error(
                "json_decode_failed",
                error=str(e),
                json_text=json_match.group()[:500],
            )
            raise ValueError(f"Invalid JSON in response: {e}") from e

    def _validate_samples(self, samples: list[dict]) -> list[dict]:
        """Validate and clean generated samples.

        Applies quality filters:
        - Must have text and entities fields
        - Text length: 50-2000 characters
        - Minimum 2 entities
        - Valid relations structure

        Args:
            samples: Raw generated samples

        Returns:
            List of validated samples that meet quality criteria
        """
        validated = []

        for sample in samples:
            # Must have text and entities
            if not sample.get("text") or not sample.get("entities"):
                logger.debug(
                    "sample_rejected_missing_fields",
                    has_text=bool(sample.get("text")),
                    has_entities=bool(sample.get("entities")),
                )
                continue

            # Text must have reasonable length
            text_length = len(sample["text"])
            if text_length < 50 or text_length > 2000:
                logger.debug(
                    "sample_rejected_length",
                    text_length=text_length,
                )
                continue

            # Must have at least 2 entities
            entity_count = len(sample["entities"])
            if entity_count < 2:
                logger.debug(
                    "sample_rejected_entity_count",
                    entity_count=entity_count,
                )
                continue

            # Clean up relations (ensure it's a list)
            if "relations" not in sample or not isinstance(sample["relations"], list):
                sample["relations"] = []

            validated.append(sample)

        logger.debug(
            "validation_complete",
            total=len(samples),
            validated=len(validated),
            rejected=len(samples) - len(validated),
        )

        return validated


# Singleton instance
_augmenter: TrainingDataAugmenter | None = None


def get_training_data_augmenter() -> TrainingDataAugmenter:
    """Get singleton instance of TrainingDataAugmenter.

    Returns:
        Shared TrainingDataAugmenter instance

    Example:
        >>> augmenter = get_training_data_augmenter()
        >>> augmenter.llm_model = "qwen3:32b"
        >>> generated = await augmenter.augment(seed_samples, target_count=20)
    """
    global _augmenter
    if _augmenter is None:
        _augmenter = TrainingDataAugmenter()
    return _augmenter
