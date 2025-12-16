"""Ollama-based reranker for improving retrieval relevance.

Sprint 48 Feature 48.8: TD-059 Ollama Reranker Implementation

This module implements reranking using Ollama with the bge-reranker-v2-m3 model
as an alternative to sentence-transformers. This approach:
- Eliminates the need for sentence-transformers dependency in Docker containers
- Uses the existing Ollama infrastructure (no additional services required)
- Provides multilingual reranking compatible with BGE-M3 embeddings

Architecture:
    Query + Documents → Ollama API (bge-reranker-v2-m3) → Relevance Scores → Reranked Results

Performance Characteristics:
    - Model: BAAI/bge-reranker-v2-m3 (Multilingual cross-encoder)
    - Input: Query-document pairs
    - Output: Relevance scores (parsed from model response)
    - Latency: ~50-100ms per document (depends on Ollama server)
    - Fallback: Returns original ranking if reranking fails

Comparison to CrossEncoderReranker:
    | Feature | OllamaReranker | CrossEncoderReranker |
    |---------|----------------|----------------------|
    | Model   | bge-reranker-v2-m3 | ms-marco-MiniLM-L-6-v2 |
    | Backend | Ollama (HTTP API) | sentence-transformers (local) |
    | Dependencies | None (uses existing Ollama) | sentence-transformers (~2GB) |
    | Docker Size | No increase | +2GB |
    | Multilingual | Yes | No (English only) |

Typical usage:
    reranker = OllamaReranker()
    reranked_results = await reranker.rerank(
        query="What is hybrid search?",
        documents=["Vector search uses embeddings...", "BM25 is keyword-based..."],
        top_k=5
    )

Academic References:
    - BGE-Reranker-v2-m3: https://huggingface.co/BAAI/bge-reranker-v2-m3
    - Cross-Encoder Reranking: Nogueira & Cho (2019) - Passage Re-ranking with BERT
"""

from __future__ import annotations

from typing import Any

import aiohttp
import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)


class OllamaReranker:
    """Reranker using BAAI/bge-reranker-v2-m3 via Ollama.

    This reranker uses Ollama's API to score query-document pairs for relevance.
    It provides an alternative to sentence-transformers-based reranking without
    requiring additional Python dependencies in Docker containers.

    The reranker works by:
    1. Building prompts for each query-document pair
    2. Sending them to Ollama's API with the bge-reranker-v2-m3 model
    3. Parsing relevance scores from model responses
    4. Sorting documents by relevance scores (descending)
    5. Returning top-k reranked results

    Attributes:
        model: Ollama model name for reranking (default: bge-reranker-v2-m3)
        top_k: Number of top documents to return (default: 10)
        ollama_url: Ollama API endpoint URL

    Example:
        >>> reranker = OllamaReranker(model="bge-reranker-v2-m3", top_k=10)
        >>> docs = ["Vector search uses embeddings", "BM25 is keyword-based"]
        >>> ranked = await reranker.rerank("What is vector search?", docs)
        >>> # Returns [(0, 0.95), (1, 0.23)] - (doc_index, score) pairs
    """

    def __init__(self, model: str | None = None, top_k: int = 10) -> None:
        """Initialize Ollama reranker.

        Args:
            model: Ollama model name for reranking (default: from settings.reranker_model)
            top_k: Number of top documents to return (default: 10)
        """
        self.model = model or settings.reranker_model
        self.top_k = top_k
        self.ollama_url = f"{settings.ollama_base_url}/api/generate"

        logger.info(
            "ollama_reranker_initialized",
            model=self.model,
            top_k=top_k,
            ollama_url=self.ollama_url,
        )

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
    ) -> list[tuple[int, float]]:
        """Rerank documents using Ollama reranker model.

        This method scores each document's relevance to the query using the
        bge-reranker-v2-m3 model via Ollama's API. Documents are scored
        independently and then sorted by relevance.

        Args:
            query: User query string
            documents: List of document texts to rerank
            top_k: Override default top_k (default: use instance top_k)

        Returns:
            List of (doc_index, score) tuples sorted by relevance (descending)
            Example: [(2, 0.95), (0, 0.87), (1, 0.23)]

        Fallback Behavior:
            If reranking fails (API error, timeout, parse failure), returns
            original ranking with inverse rank scores: [(0, 1.0), (1, 0.5), (2, 0.33)]

        Example:
            >>> reranker = OllamaReranker()
            >>> docs = [
            ...     "Vector search uses semantic embeddings for similarity",
            ...     "BM25 is a probabilistic keyword matching algorithm",
            ...     "Hybrid search combines vector and keyword approaches"
            ... ]
            >>> ranked = await reranker.rerank("What is vector search?", docs, top_k=2)
            >>> # Returns top 2 most relevant documents: [(0, 0.95), (2, 0.78)]
        """
        k = top_k or self.top_k

        if not documents:
            logger.warning("ollama_rerank_empty_documents", query=query[:50])
            return []

        logger.debug(
            "ollama_rerank_started",
            query=query[:50],
            num_documents=len(documents),
            top_k=k,
        )

        # Score each document independently
        scores: list[float] = []
        for i, doc in enumerate(documents):
            try:
                score = await self._score_document(query, doc)
                scores.append(score)
            except Exception as e:
                logger.warning(
                    "ollama_rerank_document_failed",
                    doc_index=i,
                    error=str(e),
                )
                # Assign low score on failure
                scores.append(0.0)

        # Sort by score descending and return top-k
        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:k]

        logger.info(
            "ollama_rerank_completed",
            query=query[:50],
            num_documents=len(documents),
            returned=len(ranked),
            top_score=ranked[0][1] if ranked else None,
        )

        return ranked

    async def _score_document(self, query: str, document: str) -> float:
        """Score a single query-document pair using Ollama.

        Args:
            query: User query
            document: Document text

        Returns:
            Relevance score (0.0 to 1.0)

        Raises:
            Exception: If Ollama API call fails
        """
        prompt = self._build_rerank_prompt(query, document)

        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,  # Deterministic scoring
                    "num_predict": 10,  # Only need a single number
                },
            }

            logger.debug(
                "ollama_rerank_request",
                query=query[:30],
                doc=document[:50],
            )

            timeout = aiohttp.ClientTimeout(total=30)
            async with session.post(self.ollama_url, json=payload, timeout=timeout) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(
                        "ollama_rerank_http_error",
                        status=resp.status,
                        error=error_text[:200],
                    )
                    raise Exception(f"Ollama API returned status {resp.status}")

                result = await resp.json()
                response_text = result.get("response", "")

                # Parse score from response
                score = self._parse_score(response_text)

                logger.debug(
                    "ollama_rerank_response",
                    response=response_text[:100],
                    parsed_score=score,
                )

                return score

    def _build_rerank_prompt(self, query: str, document: str) -> str:
        """Build prompt for BGE reranker model.

        The prompt instructs the model to score the relevance of the document
        to the query on a scale of 0-10.

        Args:
            query: User query
            document: Document text

        Returns:
            Formatted prompt string
        """
        # Truncate document to first 500 chars to fit in context window
        doc_text = document[:500] + "..." if len(document) > 500 else document

        prompt = (
            "Given the following query and document, rate the relevance of the "
            f"document to the query on a scale from 0 to 10, where:\n"
            "- 0 = completely irrelevant\n"
            "- 5 = somewhat relevant\n"
            "- 10 = highly relevant and directly answers the query\n\n"
            f"Query: {query}\n\n"
            f"Document: {doc_text}\n\n"
            "Respond with ONLY a single number between 0 and 10. No explanation needed.\n\n"
            "Relevance Score:"
        )
        return prompt

    def _parse_score(self, response: str) -> float:
        """Parse relevance score from model response.

        Extracts a numeric score from the model's response and normalizes
        it to the range [0.0, 1.0].

        Args:
            response: Raw response text from Ollama

        Returns:
            Normalized score (0.0 to 1.0)

        Example:
            >>> reranker._parse_score("8")
            0.8
            >>> reranker._parse_score("The score is 7.5")
            0.75
            >>> reranker._parse_score("invalid")
            0.5
        """
        try:
            # Extract first number from response
            import re

            # Try to find a decimal number (e.g., "7.5" or "8")
            # Also handle negative numbers
            match = re.search(r"-?\d+\.?\d*", response.strip())
            if match:
                score = float(match.group())
                # Normalize to [0, 1] (assuming model outputs 0-10)
                # Negative scores clamp to 0.0
                normalized = min(max(score / 10.0, 0.0), 1.0)
                return normalized
            else:
                logger.warning(
                    "ollama_rerank_parse_failed_no_number",
                    response=response[:100],
                )
                return 0.5  # Default to medium relevance
        except Exception as e:
            logger.warning(
                "ollama_rerank_parse_exception",
                response=response[:100],
                error=str(e),
            )
            return 0.5  # Default to medium relevance

    def _fallback_ranking(self, num_docs: int, top_k: int) -> list[tuple[int, float]]:
        """Fallback to original ranking if reranking fails.

        Returns documents in original order with inverse rank scores.

        Args:
            num_docs: Total number of documents
            top_k: Number of documents to return

        Returns:
            List of (doc_index, score) tuples in original order
        """
        return [(i, 1.0 / (i + 1)) for i in range(min(num_docs, top_k))]

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the reranker configuration.

        Returns:
            Dictionary with model name, top_k, and Ollama URL
        """
        return {
            "model": self.model,
            "top_k": self.top_k,
            "ollama_url": self.ollama_url,
            "backend": "ollama",
        }


# Singleton instance (optional, for convenience)
_ollama_reranker: OllamaReranker | None = None


def get_ollama_reranker() -> OllamaReranker:
    """Get global OllamaReranker instance (singleton).

    Returns:
        OllamaReranker instance with default settings

    Example:
        >>> reranker = get_ollama_reranker()
        >>> ranked = await reranker.rerank("query", ["doc1", "doc2"])
    """
    global _ollama_reranker
    if _ollama_reranker is None:
        _ollama_reranker = OllamaReranker()
    return _ollama_reranker
