"""Domain Classification for Document-to-Domain Matching.

Sprint 45 - Feature 45.6: Domain Classifier

This module provides semantic classification of documents to registered domains
based on content similarity. It uses BGE-M3 embeddings for efficient domain matching
with configurable sampling strategies for long documents.

Key Features:
- Semantic domain matching using BGE-M3 (1024-dim)
- Smart text sampling (beginning, middle, end)
- Top-k domain ranking with similarity scores
- Singleton pattern for model reuse
- Async-ready with lazy loading

Architecture:
    DomainClassifier → BGE-M3 Embeddings → Cosine Similarity
    ├── Load domain descriptions from Neo4j
    ├── Compute domain embeddings (cached)
    └── Classify documents via similarity ranking

Usage:
    >>> from src.components.domain_training import get_domain_classifier
    >>> classifier = get_domain_classifier()
    >>> await classifier.load_domains()
    >>> results = classifier.classify_document(
    ...     text="This is a technical document about API design...",
    ...     top_k=3
    ... )
    >>> print(results[0])  # {"domain": "tech_docs", "score": 0.89}
"""

from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

# Constants
DEFAULT_SAMPLE_SIZE = 2000  # Characters to sample for classification
DEFAULT_TOP_K = 3  # Number of top domains to return
MIN_SIMILARITY_THRESHOLD = 0.3  # Minimum similarity to consider a match


class DomainClassifier:
    """Classifies documents to registered domains based on content similarity.

    This class uses BGE-M3 embeddings to compute semantic similarity between
    document content and domain descriptions. It supports smart text sampling
    for long documents and returns ranked domain matches.

    Attributes:
        embedding_model: SentenceTransformer model (BGE-M3)
        _domain_embeddings: Cache of domain name -> embedding mappings
        _domains_loaded: Flag indicating if domains have been loaded
    """

    def __init__(self) -> None:
        """Initialize domain classifier with BGE-M3 embeddings.

        Note: The embedding model is loaded lazily on first use to avoid
        unnecessary initialization overhead.
        """
        self.embedding_model: Any = None  # Loaded lazily
        self._domain_embeddings: dict[str, np.ndarray[Any, Any]] = {}
        self._domains_loaded: bool = False
        self._model_loaded: bool = False

        logger.info("domain_classifier_initialized", model="BAAI/bge-m3")

    def _load_embedding_model(self) -> None:
        """Load BGE-M3 embedding model lazily.

        Raises:
            ImportError: If sentence-transformers is not installed
        """
        if self._model_loaded:
            return

        try:
            from sentence_transformers import SentenceTransformer

            self.embedding_model = SentenceTransformer("BAAI/bge-m3")
            self._model_loaded = True
            logger.info("embedding_model_loaded", model="BAAI/bge-m3", dim=1024)

        except ImportError as e:
            logger.error(
                "sentence_transformers_not_available",
                error=str(e),
                message=(
                    "sentence-transformers not installed. "
                    "Install with: poetry install --with reranking"
                ),
            )
            raise

    async def load_domains(self) -> None:
        """Load domain descriptions and compute embeddings.

        This method fetches all registered domains from the DomainRepository
        and computes embeddings for their descriptions. The embeddings are cached
        for efficient classification.

        Raises:
            ImportError: If required dependencies are not installed
        """
        if self._domains_loaded:
            logger.info("domains_already_loaded", num_domains=len(self._domain_embeddings))
            return

        # Load embedding model
        self._load_embedding_model()

        # Load domains from repository
        from src.components.domain_training import get_domain_repository

        repo = get_domain_repository()

        try:
            domains = await repo.list_domains()
            logger.info("loading_domains", num_domains=len(domains))

            # Compute embeddings for each domain
            for domain in domains:
                domain_name = domain.get("name")
                description = domain.get("description")

                if not domain_name:
                    logger.warning("domain_missing_name", domain=domain)
                    continue

                if not description:
                    logger.warning(
                        "domain_missing_description",
                        domain_name=domain_name,
                        message="Skipping domain without description",
                    )
                    continue

                # Compute embedding
                embedding = self.embedding_model.encode(
                    description, normalize_embeddings=True  # Normalize for cosine similarity
                )

                self._domain_embeddings[domain_name] = np.array(embedding, dtype=np.float32)

                logger.info(
                    "domain_embedding_computed",
                    domain_name=domain_name,
                    description_length=len(description),
                    embedding_shape=embedding.shape,
                )

            self._domains_loaded = True
            logger.info("domains_loaded", num_domains=len(self._domain_embeddings))

        except Exception as e:
            logger.error("domain_loading_failed", error=str(e))
            raise

    def classify_document(
        self, text: str, top_k: int = DEFAULT_TOP_K, sample_size: int = DEFAULT_SAMPLE_SIZE
    ) -> list[dict[str, Any]]:
        """Classify document to best matching domain(s).

        This method samples text from the document, computes its embedding,
        and ranks domains by cosine similarity.

        Args:
            text: Document text to classify
            top_k: Number of top domains to return (default: 3)
            sample_size: Characters to sample for classification (default: 2000)

        Returns:
            List of domain matches sorted by score (descending):
            [
                {"domain": "tech_docs", "score": 0.89},
                {"domain": "finance", "score": 0.67},
                ...
            ]

        Raises:
            ValueError: If text is empty or domains not loaded
            ImportError: If required dependencies not installed
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if not self._domains_loaded:
            raise ValueError("Domains not loaded. Call load_domains() first before classifying.")

        if not self._domain_embeddings:
            logger.warning(
                "no_domains_available",
                message="No domains registered. Returning empty results.",
            )
            return []

        # Ensure model is loaded
        self._load_embedding_model()

        logger.info(
            "classifying_document",
            text_length=len(text),
            sample_size=sample_size,
            top_k=top_k,
        )

        # Sample text for classification
        sampled_text = self._sample_text(text, sample_size)

        # Compute document embedding
        doc_embedding = self.embedding_model.encode(
            sampled_text, normalize_embeddings=True  # Normalize for cosine similarity
        )
        doc_embedding = np.array(doc_embedding, dtype=np.float32)

        # Calculate cosine similarity with all domains
        scores = []
        for domain_name, domain_embedding in self._domain_embeddings.items():
            # Cosine similarity (already normalized)
            similarity = float(np.dot(doc_embedding, domain_embedding))

            # Only include domains above threshold
            if similarity >= MIN_SIMILARITY_THRESHOLD:
                scores.append({"domain": domain_name, "score": similarity})

        # Sort by score (descending)
        scores.sort(key=lambda x: float(x["score"]), reverse=True)  # type: ignore[arg-type]

        # Return top-k results
        results = scores[:top_k]

        logger.info(
            "document_classified",
            num_matches=len(scores),
            top_match=results[0] if results else None,
            top_k_returned=len(results),
        )

        return results

    def _sample_text(self, text: str, size: int) -> str:
        """Sample text from beginning, middle, and end.

        This method ensures comprehensive representation of document content
        by sampling from three key regions.

        Args:
            text: Full text to sample from
            size: Total number of characters to sample

        Returns:
            Sampled text string with "..." separators
        """
        if len(text) <= size:
            return text

        # Allocate thirds of sample size to each region
        third = size // 3

        beginning = text[:third]
        middle_start = len(text) // 2 - third // 2
        middle_end = len(text) // 2 + third // 2
        middle = text[middle_start:middle_end]
        end = text[-third:]

        sampled = f"{beginning} ... {middle} ... {end}"

        logger.debug(
            "text_sampled",
            original_length=len(text),
            sampled_length=len(sampled),
            sample_regions=["beginning", "middle", "end"],
        )

        return sampled

    def get_loaded_domains(self) -> list[str]:
        """Get list of currently loaded domain names.

        Returns:
            List of domain names with cached embeddings
        """
        return list(self._domain_embeddings.keys())

    def is_loaded(self) -> bool:
        """Check if domains have been loaded.

        Returns:
            True if domains are loaded and ready for classification
        """
        return self._domains_loaded and len(self._domain_embeddings) > 0

    async def reload_domains(self) -> None:
        """Reload domains from repository (useful after domain updates).

        This method clears the cached embeddings and reloads all domains
        from the DomainRepository.
        """
        logger.info("reloading_domains")
        self._domain_embeddings.clear()
        self._domains_loaded = False
        await self.load_domains()


# Singleton instance management
_classifier: DomainClassifier | None = None


def get_domain_classifier() -> DomainClassifier:
    """Get singleton instance of DomainClassifier.

    This function ensures only one instance of DomainClassifier exists,
    avoiding redundant model loading and memory usage.

    Returns:
        Singleton DomainClassifier instance

    Example:
        >>> classifier = get_domain_classifier()
        >>> await classifier.load_domains()
        >>> results = classifier.classify_document(text)
    """
    global _classifier
    if _classifier is None:
        _classifier = DomainClassifier()
        logger.info("domain_classifier_singleton_created")
    return _classifier


def reset_classifier() -> None:
    """Reset singleton classifier instance (useful for testing).

    This function clears the singleton instance, forcing a new
    instance to be created on next get_domain_classifier() call.
    """
    global _classifier
    _classifier = None
    logger.info("domain_classifier_singleton_reset")
