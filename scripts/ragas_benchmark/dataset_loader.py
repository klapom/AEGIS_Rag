"""
Dataset loader for RAGAS benchmark.

Loads and normalizes HuggingFace datasets using appropriate adapters.

Sprint 82: Phase 1 - Text-Only Benchmark
"""

from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

from datasets import load_dataset, Dataset

from .models import NormalizedSample, SamplingStats
from .adapters import (
    DatasetAdapter,
    HotpotQAAdapter,
    RAGBenchAdapter,
    LogQAAdapter,
)
from .config import DATASET_CONFIGS

logger = logging.getLogger(__name__)


class DatasetLoader:
    """
    Load and normalize HuggingFace datasets for RAGAS evaluation.

    Supports:
    - HotpotQA (multi-hop QA)
    - RAGBench (comprehensive RAG benchmark)
    - LogQA (log-based QA)

    Usage:
        loader = DatasetLoader()
        samples = loader.load_dataset("hotpot_qa", max_samples=1000)
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize DatasetLoader.

        Args:
            cache_dir: Directory for caching downloaded datasets
        """
        self.cache_dir = cache_dir
        self.adapters = self._register_adapters()
        self.stats = SamplingStats()

    def _register_adapters(self) -> Dict[str, DatasetAdapter]:
        """Register all available dataset adapters."""
        return {
            "hotpot_qa": HotpotQAAdapter(),
            "ragbench": RAGBenchAdapter(),
            "ragbench_covidqa": RAGBenchAdapter(),
            "ragbench_techqa": RAGBenchAdapter(),
            "ragbench_msmarco": RAGBenchAdapter(),
            "ragbench_emanual": LogQAAdapter(),  # Use LogQA adapter for log_ticket
            "logqa": LogQAAdapter(),
        }

    def get_available_datasets(self) -> List[str]:
        """Return list of available dataset names."""
        return list(self.adapters.keys())

    def load_dataset(
        self,
        name: str,
        subset: Optional[str] = None,
        split: str = "train",
        max_samples: int = -1,
        progress_callback: Optional[callable] = None
    ) -> List[NormalizedSample]:
        """
        Load dataset and normalize with appropriate adapter.

        Args:
            name: Dataset name (hotpot_qa, ragbench, logqa)
            subset: Dataset subset/configuration
            split: Dataset split (train, validation, test)
            max_samples: Maximum samples to load (-1 for all)
            progress_callback: Optional callback for progress updates

        Returns:
            List of NormalizedSample objects
        """
        # Get adapter
        adapter = self._get_adapter(name)
        if not adapter:
            raise ValueError(f"No adapter found for dataset: {name}")

        # Get config
        config = DATASET_CONFIGS.get(name, {})
        hf_name = config.get("hf_name", name)
        subset = subset or config.get("subset")
        split = split or config.get("split", "train")

        # Apply max_samples from config if not specified
        if max_samples == -1:
            max_samples = config.get("max_samples", -1)

        logger.info(f"Loading dataset: {hf_name} (subset={subset}, split={split})")

        try:
            # Load from HuggingFace
            dataset = self._load_hf_dataset(hf_name, subset, split)

            if dataset is None or len(dataset) == 0:
                logger.warning(f"Empty dataset: {hf_name}")
                return []

            # Limit samples
            if max_samples > 0 and len(dataset) > max_samples:
                dataset = dataset.select(range(max_samples))
                logger.info(f"Limited to {max_samples} samples")

            # Normalize with adapter
            samples = self._normalize_dataset(dataset, adapter, progress_callback)

            logger.info(
                f"Loaded {len(samples)} samples from {hf_name} "
                f"(dropped: {adapter.drop_count})"
            )

            return samples

        except Exception as e:
            logger.error(f"Failed to load dataset {hf_name}: {e}")
            raise

    def load_all_phase1(
        self,
        max_per_dataset: Optional[Dict[str, int]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, List[NormalizedSample]]:
        """
        Load all Phase 1 datasets.

        Args:
            max_per_dataset: Optional dict of max samples per dataset
            progress_callback: Optional callback for progress updates

        Returns:
            Dict mapping dataset name to list of samples
        """
        if max_per_dataset is None:
            max_per_dataset = {
                "hotpot_qa": 5000,
                "ragbench": 3000,
                "logqa": 2000,
            }

        results = {}

        for name in ["hotpot_qa", "ragbench", "logqa"]:
            max_samples = max_per_dataset.get(name, -1)
            try:
                samples = self.load_dataset(
                    name,
                    max_samples=max_samples,
                    progress_callback=progress_callback
                )
                results[name] = samples
            except Exception as e:
                logger.error(f"Failed to load {name}: {e}")
                results[name] = []

        return results

    def _get_adapter(self, name: str) -> Optional[DatasetAdapter]:
        """Get adapter for dataset name."""
        # Direct match
        if name in self.adapters:
            return self.adapters[name]

        # Try partial match (e.g., "rungalileo/ragbench" → "ragbench")
        for key, adapter in self.adapters.items():
            if key in name.lower():
                return adapter

        return None

    def _load_hf_dataset(
        self,
        name: str,
        subset: Optional[str],
        split: str
    ) -> Optional[Dataset]:
        """
        Load dataset from HuggingFace Hub.

        Args:
            name: HuggingFace dataset name
            subset: Dataset configuration/subset
            split: Data split

        Returns:
            HuggingFace Dataset object
        """
        try:
            kwargs = {
                "path": name,
                "split": split,
            }

            if subset:
                kwargs["name"] = subset

            if self.cache_dir:
                kwargs["cache_dir"] = self.cache_dir

            logger.debug(f"Loading HF dataset with kwargs: {kwargs}")
            dataset = load_dataset(**kwargs)

            return dataset

        except Exception as e:
            logger.error(f"HuggingFace load error for {name}: {e}")
            raise

    def _normalize_dataset(
        self,
        dataset: Dataset,
        adapter: DatasetAdapter,
        progress_callback: Optional[callable] = None
    ) -> List[NormalizedSample]:
        """
        Normalize dataset using adapter.

        Args:
            dataset: HuggingFace Dataset
            adapter: Dataset adapter
            progress_callback: Optional callback for progress

        Returns:
            List of NormalizedSample objects
        """
        samples = []
        total = len(dataset)

        for idx, record in enumerate(dataset):
            # Progress update
            if progress_callback and idx % 100 == 0:
                progress_callback(idx, total)

            # Adapt record
            sample = adapter.adapt(record, record_idx=idx)
            if sample:
                samples.append(sample)

        # Log drop stats
        drop_stats = adapter.get_drop_stats()
        if drop_stats["total_dropped"] > 0:
            logger.info(f"Drop stats: {drop_stats}")

        return samples

    def get_stats(self) -> SamplingStats:
        """Get current sampling statistics."""
        return self.stats

    def reset_stats(self):
        """Reset sampling statistics."""
        self.stats = SamplingStats()
        for adapter in self.adapters.values():
            adapter.reset_stats()
