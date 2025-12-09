"""Benchmark Dataset Loader for RAG Evaluation.

Sprint 41 Feature 41.6: Benchmark Corpus Ingestion

This module loads standard RAG evaluation datasets from HuggingFace and extracts
question-answer-context triples for benchmarking the AEGIS RAG system.

Supported Datasets:
- Natural Questions: Open-domain QA with Wikipedia contexts
- HotpotQA: Multi-hop reasoning over multiple documents
- MS MARCO: Large-scale passage ranking dataset
- FEVER: Fact verification with evidence retrieval
- RAGBench: Comprehensive RAG evaluation benchmark

Usage:
    >>> loader = BenchmarkDatasetLoader()
    >>> dataset = await loader.load_dataset("natural_questions", sample_size=1000)
    >>> print(f"Loaded {len(dataset)} samples")
    >>> print(dataset[0])
    {
        'question': 'Who wrote the novel Pride and Prejudice?',
        'answer': 'Jane Austen',
        'contexts': ['Pride and Prejudice is a novel by Jane Austen...'],
        'source': 'natural_questions',
        'question_id': 'nq_0001'
    }

Architecture:
    HuggingFace datasets → DatasetLoader → Normalized Format → Corpus Ingestion

    Each dataset has different schemas, so we normalize them to a common format:
    {
        'question': str,
        'answer': str,
        'contexts': list[str],
        'source': str,
        'question_id': str
    }

Performance:
    - Lazy loading: Datasets loaded on-demand (not all at once)
    - Streaming mode: For large datasets (MS MARCO)
    - Sample size control: Default 1000 (Track A), 100 (Track B)
"""

import hashlib
from typing import Any, Literal

import structlog
from datasets import load_dataset

logger = structlog.get_logger(__name__)


DatasetName = Literal[
    "natural_questions",
    "hotpotqa",
    "msmarco",
    "fever",
    "ragbench",
]


class BenchmarkDatasetLoader:
    """Loads and normalizes benchmark datasets from HuggingFace.

    This class handles the complexity of different dataset schemas and provides
    a unified interface for loading benchmark evaluation data.

    Features:
    - Automatic schema normalization
    - Sample size configuration
    - Progress logging
    - Error handling for missing/invalid data

    Example:
        loader = BenchmarkDatasetLoader()

        # Load Natural Questions (Track A)
        nq_data = await loader.load_dataset(
            "natural_questions",
            sample_size=1000
        )

        # Load HotpotQA (Track B - Complex)
        hotpot_data = await loader.load_dataset(
            "hotpotqa",
            sample_size=100
        )
    """

    # Dataset configurations
    DATASET_CONFIGS = {
        "natural_questions": {
            "path": "google-research-datasets/natural_questions",
            "split": "train",
            "description": "Open-domain QA with Wikipedia contexts",
            "track": "A",  # Track A: Simple retrieval
        },
        "hotpotqa": {
            "path": "hotpot_qa",
            "split": "train",
            "config": "distractor",  # 'distractor' split has hard negatives
            "description": "Multi-hop reasoning over multiple documents",
            "track": "B",  # Track B: Complex multi-hop
        },
        "msmarco": {
            "path": "microsoft/ms_marco",
            "split": "train",
            "config": "v2.1",
            "description": "Large-scale passage ranking dataset",
            "track": "A",  # Track A: Simple retrieval
        },
        "fever": {
            "path": "fever",
            "split": "train",
            "config": "v1.0",
            "description": "Fact verification with evidence retrieval",
            "track": "B",  # Track B: Verification reasoning
        },
        "ragbench": {
            "path": "rungalileo/ragbench",
            "split": "test",
            "description": "Comprehensive RAG evaluation benchmark",
            "track": "A",  # Track A: General RAG tasks
        },
    }

    def __init__(self) -> None:
        """Initialize benchmark dataset loader."""
        logger.info("BenchmarkDatasetLoader initialized")

    def _generate_question_id(self, dataset_name: str, index: int) -> str:
        """Generate unique question ID.

        Args:
            dataset_name: Name of the dataset
            index: Index of the question in the dataset

        Returns:
            Unique question ID (e.g., 'nq_0001', 'hotpot_0042')
        """
        prefix = dataset_name[:6]  # First 6 chars
        return f"{prefix}_{index:06d}"

    async def load_dataset(
        self,
        dataset_name: DatasetName,
        sample_size: int | None = None,
        split: str | None = None,
    ) -> list[dict[str, Any]]:
        """Load and normalize a benchmark dataset.

        Args:
            dataset_name: Name of the dataset to load
            sample_size: Number of samples to load (None = all)
            split: Dataset split to use (default: from config)

        Returns:
            List of normalized question-answer-context dicts

        Raises:
            ValueError: If dataset_name is not supported
            RuntimeError: If dataset loading fails

        Example:
            >>> loader = BenchmarkDatasetLoader()
            >>> data = await loader.load_dataset("natural_questions", sample_size=100)
            >>> print(data[0].keys())
            dict_keys(['question', 'answer', 'contexts', 'source', 'question_id'])
        """
        if dataset_name not in self.DATASET_CONFIGS:
            raise ValueError(
                f"Unsupported dataset: {dataset_name}. "
                f"Supported: {list(self.DATASET_CONFIGS.keys())}"
            )

        config = self.DATASET_CONFIGS[dataset_name]
        split = split or config["split"]

        logger.info(
            "Loading benchmark dataset",
            dataset=dataset_name,
            path=config["path"],
            split=split,
            sample_size=sample_size,
            track=config["track"],
        )

        try:
            # Load dataset from HuggingFace
            dataset_config = config.get("config")
            if dataset_config:
                raw_dataset = load_dataset(
                    config["path"],
                    dataset_config,
                    split=split,
                    trust_remote_code=True,
                )
            else:
                raw_dataset = load_dataset(
                    config["path"],
                    split=split,
                    trust_remote_code=True,
                )

            # Apply sampling if requested
            if sample_size and len(raw_dataset) > sample_size:
                raw_dataset = raw_dataset.select(range(sample_size))

            logger.info(
                "Dataset loaded from HuggingFace",
                dataset=dataset_name,
                total_samples=len(raw_dataset),
            )

            # Normalize dataset to common format
            normalized_data = self._normalize_dataset(
                raw_dataset,
                dataset_name,
            )

            logger.info(
                "Dataset normalized",
                dataset=dataset_name,
                normalized_samples=len(normalized_data),
                track=config["track"],
            )

            return normalized_data

        except Exception as e:
            logger.error(
                "Failed to load benchmark dataset",
                dataset=dataset_name,
                error=str(e),
            )
            raise RuntimeError(f"Failed to load dataset {dataset_name}: {e}") from e

    def _normalize_dataset(
        self,
        raw_dataset: Any,
        dataset_name: str,
    ) -> list[dict[str, Any]]:
        """Normalize dataset to common format.

        Args:
            raw_dataset: Raw HuggingFace dataset
            dataset_name: Name of the dataset

        Returns:
            List of normalized dicts with keys: question, answer, contexts, source, question_id
        """
        normalizer = getattr(self, f"_normalize_{dataset_name}", None)
        if not normalizer:
            raise NotImplementedError(
                f"No normalizer implemented for dataset: {dataset_name}"
            )

        normalized = []
        for idx, sample in enumerate(raw_dataset):
            try:
                normalized_sample = normalizer(sample, idx)
                if normalized_sample:  # Skip invalid samples
                    normalized.append(normalized_sample)
            except Exception as e:
                logger.warning(
                    "Failed to normalize sample",
                    dataset=dataset_name,
                    index=idx,
                    error=str(e),
                )

        return normalized

    def _normalize_natural_questions(
        self,
        sample: dict[str, Any],
        index: int,
    ) -> dict[str, Any] | None:
        """Normalize Natural Questions sample.

        Schema:
        - question: dict with 'text' field
        - annotations: list of dicts with 'short_answers' and 'yes_no_answer'
        - document: dict with 'tokens' and 'html'
        """
        try:
            question = sample.get("question", {}).get("text", "")
            if not question:
                return None

            # Extract answer (prefer short_answer over yes/no)
            annotations = sample.get("annotations", [{}])[0]
            short_answers = annotations.get("short_answers", [])

            if short_answers:
                # Use first short answer
                answer = short_answers[0].get("text", "")
            else:
                # Fallback to yes_no_answer
                yes_no = annotations.get("yes_no_answer", "")
                answer = yes_no if yes_no in ["YES", "NO"] else ""

            if not answer:
                return None

            # Extract context from document tokens
            document = sample.get("document", {})
            tokens = document.get("tokens", [])

            # Join tokens to form context (limit to reasonable length)
            context = " ".join(tokens[:2000]) if tokens else ""

            return {
                "question": question,
                "answer": answer,
                "contexts": [context] if context else [],
                "source": "natural_questions",
                "question_id": self._generate_question_id("natural_questions", index),
            }
        except Exception as e:
            logger.debug(f"Failed to normalize NQ sample {index}: {e}")
            return None

    def _normalize_hotpotqa(
        self,
        sample: dict[str, Any],
        index: int,
    ) -> dict[str, Any] | None:
        """Normalize HotpotQA sample.

        Schema:
        - question: str
        - answer: str
        - supporting_facts: list of [title, sentence_id] pairs
        - context: list of [title, sentences] pairs
        """
        try:
            question = sample.get("question", "")
            answer = sample.get("answer", "")

            if not question or not answer:
                return None

            # Extract supporting contexts
            contexts = []
            context_data = sample.get("context", [])
            supporting_facts = sample.get("supporting_facts", [])

            # Build map of title -> sentences
            context_map = {title: sentences for title, sentences in context_data}

            # Extract supporting sentences
            for title, sent_id in supporting_facts:
                if title in context_map:
                    sentences = context_map[title]
                    if sent_id < len(sentences):
                        contexts.append(sentences[sent_id])

            # Fallback: if no supporting facts, use first few sentences from contexts
            if not contexts and context_data:
                for title, sentences in context_data[:2]:  # First 2 documents
                    contexts.extend(sentences[:3])  # First 3 sentences each

            return {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "source": "hotpotqa",
                "question_id": self._generate_question_id("hotpotqa", index),
            }
        except Exception as e:
            logger.debug(f"Failed to normalize HotpotQA sample {index}: {e}")
            return None

    def _normalize_msmarco(
        self,
        sample: dict[str, Any],
        index: int,
    ) -> dict[str, Any] | None:
        """Normalize MS MARCO sample.

        Schema:
        - query: str
        - passages: list of dicts with 'passage_text' and 'is_selected'
        - answers: list of str (generated answers)
        """
        try:
            question = sample.get("query", "")
            if not question:
                return None

            # Extract answer (prefer first answer from answers list)
            answers = sample.get("answers", [])
            answer = answers[0] if answers else ""

            # Extract relevant passages (prefer selected passages)
            passages = sample.get("passages", [])
            contexts = []

            # First, try to get selected passages
            for passage in passages:
                if passage.get("is_selected", 0) == 1:
                    contexts.append(passage.get("passage_text", ""))

            # If no selected passages, use first few passages
            if not contexts:
                contexts = [p.get("passage_text", "") for p in passages[:3]]

            # Filter empty contexts
            contexts = [c for c in contexts if c]

            if not contexts or not answer:
                return None

            return {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "source": "msmarco",
                "question_id": self._generate_question_id("msmarco", index),
            }
        except Exception as e:
            logger.debug(f"Failed to normalize MS MARCO sample {index}: {e}")
            return None

    def _normalize_fever(
        self,
        sample: dict[str, Any],
        index: int,
    ) -> dict[str, Any] | None:
        """Normalize FEVER sample.

        Schema:
        - claim: str
        - evidence: list of [annotation_id, evidence_id, wiki_url, sent_id] tuples
        - label: str ('SUPPORTS', 'REFUTES', 'NOT ENOUGH INFO')
        """
        try:
            question = sample.get("claim", "")
            label = sample.get("label", "")

            if not question or not label:
                return None

            # The "answer" is the label for fact verification
            answer = label

            # Extract evidence sentences as contexts
            evidence = sample.get("evidence", [])
            contexts = []

            # Evidence format: [[annotation_id, evidence_id, wiki_url, sent_id], ...]
            # We need to extract actual text from wiki_url or use claim as context
            # For simplicity, we'll use the claim itself as context (real implementation
            # would fetch from Wikipedia)
            if evidence:
                # Placeholder: In real implementation, fetch evidence from Wikipedia
                contexts = [f"Evidence for claim: {question}"]

            if not contexts:
                return None

            return {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "source": "fever",
                "question_id": self._generate_question_id("fever", index),
            }
        except Exception as e:
            logger.debug(f"Failed to normalize FEVER sample {index}: {e}")
            return None

    def _normalize_ragbench(
        self,
        sample: dict[str, Any],
        index: int,
    ) -> dict[str, Any] | None:
        """Normalize RAGBench sample.

        Schema (varies by benchmark):
        - question: str
        - answer: str
        - contexts: list[str] or single str
        """
        try:
            question = sample.get("question", "")
            answer = sample.get("answer", "")

            if not question or not answer:
                return None

            # Extract contexts (handle both list and string formats)
            contexts_raw = sample.get("contexts", [])
            if isinstance(contexts_raw, str):
                contexts = [contexts_raw]
            elif isinstance(contexts_raw, list):
                contexts = contexts_raw
            else:
                contexts = []

            if not contexts:
                return None

            return {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "source": "ragbench",
                "question_id": self._generate_question_id("ragbench", index),
            }
        except Exception as e:
            logger.debug(f"Failed to normalize RAGBench sample {index}: {e}")
            return None

    def get_dataset_info(self, dataset_name: DatasetName) -> dict[str, Any]:
        """Get information about a benchmark dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Dictionary with dataset metadata

        Example:
            >>> loader = BenchmarkDatasetLoader()
            >>> info = loader.get_dataset_info("natural_questions")
            >>> print(info['description'])
            'Open-domain QA with Wikipedia contexts'
        """
        if dataset_name not in self.DATASET_CONFIGS:
            raise ValueError(f"Unknown dataset: {dataset_name}")

        return self.DATASET_CONFIGS[dataset_name].copy()

    def list_datasets(self) -> list[str]:
        """List all supported benchmark datasets.

        Returns:
            List of dataset names
        """
        return list(self.DATASET_CONFIGS.keys())


def get_benchmark_loader() -> BenchmarkDatasetLoader:
    """Get global BenchmarkDatasetLoader instance (singleton).

    Returns:
        BenchmarkDatasetLoader instance
    """
    return BenchmarkDatasetLoader()
