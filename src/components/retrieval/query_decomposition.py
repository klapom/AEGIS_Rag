"""Query decomposition for handling complex multi-part questions.

This module uses LLM prompting (via Ollama) to classify and decompose
complex queries into simpler sub-queries that can be executed in parallel
or sequentially.

Query Types:
- SIMPLE: Single, direct question (e.g., "What is RAG?")
- COMPOUND: Multiple independent questions (e.g., "What is RAG and BM25?")
- MULTI_HOP: Sequential reasoning required (e.g., "Who created the tool used in X?")

Typical usage:
    decomposer = QueryDecomposer()
    result = await decomposer.decompose_and_search(
        query="What is vector search and how does BM25 compare?",
        search_fn=hybrid_search.hybrid_search
    )
"""

import asyncio
from enum import Enum

import structlog
from ollama import AsyncClient
from pydantic import BaseModel, Field

from src.core.config import settings

logger = structlog.get_logger(__name__)


class QueryType(str, Enum):
    """Query classification types."""

    SIMPLE = "SIMPLE"
    COMPOUND = "COMPOUND"
    MULTI_HOP = "MULTI_HOP"


class SubQuery(BaseModel):
    """A sub-query extracted from complex query."""

    query: str = Field(..., description="Sub-query text")
    index: int = Field(..., description="Execution order (0-indexed)")
    depends_on: list[int] = Field(
        default_factory=list, description="Indices of queries this depends on"
    )


class QueryClassification(BaseModel):
    """Query classification result."""

    query_type: QueryType = Field(..., description="Classified query type")
    confidence: float = Field(..., description="Classification confidence (0-1)")
    reasoning: str = Field(default="", description="Classification reasoning")


class DecompositionResult(BaseModel):
    """Query decomposition result."""

    original_query: str = Field(..., description="Original input query")
    classification: QueryClassification = Field(..., description="Query classification")
    sub_queries: list[SubQuery] = Field(
        default_factory=list, description="Extracted sub-queries"
    )
    execution_strategy: str = Field(
        ..., description="parallel or sequential execution"
    )


# Prompt templates
CLASSIFICATION_PROMPT = """Analyze this user query and classify it into ONE of these types:

Query: {query}

Classifications:
- SIMPLE: Single, direct question (e.g., "What is vector search?")
- COMPOUND: Multiple independent questions that can be answered separately (e.g., "What is vector search and how does BM25 work?")
- MULTI_HOP: Requires sequential reasoning where one answer depends on another (e.g., "Who developed the algorithm used in Qdrant?")

Respond ONLY with one word: SIMPLE, COMPOUND, or MULTI_HOP
"""

DECOMPOSITION_PROMPT = """Break down this complex query into simpler sub-queries.

Original Query: {query}
Query Type: {query_type}

Instructions:
- Extract {num_expected} or more sub-queries
- Each sub-query should be a complete, standalone question
- For COMPOUND: Split into independent questions
- For MULTI_HOP: Order questions based on dependency (first question's answer feeds into second)

Respond with one sub-query per line, numbered:
1. First sub-query
2. Second sub-query
...

Sub-queries:
"""


class QueryDecomposer:
    """Query decomposer using Ollama LLM.

    Uses prompt-based query classification and decomposition to handle
    complex questions by breaking them into simpler sub-queries.

    Attributes:
        ollama_client: Async Ollama client
        model_name: LLM model for decomposition (default: llama3.2)
        classification_threshold: Minimum confidence for complex queries
    """

    def __init__(
        self,
        ollama_base_url: str | None = None,
        model_name: str = "llama3.2",
        classification_threshold: float = 0.7,
    ):
        """Initialize query decomposer.

        Args:
            ollama_base_url: Ollama API base URL (default: from settings)
            model_name: Ollama model name (default: llama3.2)
            classification_threshold: Confidence threshold for complex queries
        """
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        self.ollama_client = AsyncClient(host=self.ollama_base_url)
        self.model_name = model_name
        self.classification_threshold = classification_threshold

        logger.info(
            "query_decomposer_initialized",
            model=self.model_name,
            threshold=self.classification_threshold,
        )

    async def classify_query(self, query: str) -> QueryClassification:
        """Classify query type using LLM.

        Args:
            query: User query to classify

        Returns:
            QueryClassification with type, confidence, and reasoning
        """
        prompt = CLASSIFICATION_PROMPT.format(query=query)

        try:
            response = await self.ollama_client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.1,  # Low temp for consistent classification
                    "top_p": 0.9,
                    "num_predict": 10,  # Only need 1 word
                },
            )

            classification_text = response["response"].strip().upper()

            # Parse response
            if "COMPOUND" in classification_text:
                query_type = QueryType.COMPOUND
                confidence = 0.9
            elif "MULTI_HOP" in classification_text or "MULTI-HOP" in classification_text:
                query_type = QueryType.MULTI_HOP
                confidence = 0.85
            else:
                query_type = QueryType.SIMPLE
                confidence = 0.95

            logger.info(
                "query_classified",
                query_type=query_type.value,
                confidence=confidence,
            )

            return QueryClassification(
                query_type=query_type,
                confidence=confidence,
                reasoning=classification_text,
            )

        except Exception as e:
            logger.warning("classification_failed_fallback_simple", error=str(e))
            # Fallback to SIMPLE on error
            return QueryClassification(
                query_type=QueryType.SIMPLE,
                confidence=0.5,
                reasoning=f"Fallback due to error: {e}",
            )

    async def decompose_query(
        self, query: str, query_type: QueryType
    ) -> list[SubQuery]:
        """Decompose complex query into sub-queries.

        Args:
            query: Original query
            query_type: Classified query type

        Returns:
            List of sub-queries with execution order
        """
        if query_type == QueryType.SIMPLE:
            # No decomposition needed
            return [SubQuery(query=query, index=0, depends_on=[])]

        # Determine expected number of sub-queries
        num_expected = 2 if query_type == QueryType.COMPOUND else 2

        prompt = DECOMPOSITION_PROMPT.format(
            query=query, query_type=query_type.value, num_expected=num_expected
        )

        try:
            response = await self.ollama_client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": 0.3,  # Moderate creativity
                    "top_p": 0.9,
                    "num_predict": 200,  # Enough for 2-3 sub-queries
                },
            )

            decomposition_text = response["response"].strip()

            # Parse sub-queries from numbered list
            sub_queries = []
            lines = [line.strip() for line in decomposition_text.split("\n") if line.strip()]

            for idx, line in enumerate(lines):
                # Remove numbering (1., 2., -, *, etc.)
                clean_line = line.lstrip("0123456789.-* ").strip()
                if clean_line and len(clean_line) > 5:  # Skip very short lines
                    depends_on = []
                    if query_type == QueryType.MULTI_HOP and idx > 0:
                        # Multi-hop: each query depends on previous
                        depends_on = [idx - 1]

                    sub_queries.append(
                        SubQuery(query=clean_line, index=idx, depends_on=depends_on)
                    )

            # Fallback if parsing failed
            if not sub_queries:
                logger.warning("decomposition_failed_fallback_original")
                return [SubQuery(query=query, index=0, depends_on=[])]

            logger.info(
                "query_decomposed",
                num_sub_queries=len(sub_queries),
                query_type=query_type.value,
            )

            return sub_queries

        except Exception as e:
            logger.error("decomposition_failed", error=str(e))
            # Fallback: return original query as single sub-query
            return [SubQuery(query=query, index=0, depends_on=[])]

    async def decompose(self, query: str) -> DecompositionResult:
        """Classify and decompose query.

        Args:
            query: User query

        Returns:
            DecompositionResult with classification and sub-queries
        """
        # Step 1: Classify query
        classification = await self.classify_query(query)

        # Step 2: Decompose if complex
        sub_queries = []
        execution_strategy = "direct"

        if (
            classification.query_type != QueryType.SIMPLE
            and classification.confidence >= self.classification_threshold
        ):
            sub_queries = await self.decompose_query(query, classification.query_type)

            # Determine execution strategy
            if classification.query_type == QueryType.COMPOUND:
                execution_strategy = "parallel"
            elif classification.query_type == QueryType.MULTI_HOP:
                execution_strategy = "sequential"
        else:
            # Simple query or low confidence - use original
            sub_queries = [SubQuery(query=query, index=0, depends_on=[])]
            execution_strategy = "direct"

        return DecompositionResult(
            original_query=query,
            classification=classification,
            sub_queries=sub_queries,
            execution_strategy=execution_strategy,
        )

    async def decompose_and_search(
        self,
        query: str,
        search_fn,
        merge_strategy: str = "rrf",
        **search_kwargs,
    ) -> dict:
        """Decompose query and execute sub-queries.

        Args:
            query: User query
            search_fn: Async search function to call for each sub-query
            merge_strategy: How to merge results ("rrf", "concat", "best")
            **search_kwargs: Additional kwargs for search_fn

        Returns:
            Combined search results with metadata
        """
        # Decompose query
        decomposition = await self.decompose(query)

        # Execute sub-queries based on strategy
        if decomposition.execution_strategy == "direct":
            # Simple query - direct search
            result = await search_fn(query=query, **search_kwargs)
            result["decomposition"] = {
                "applied": False,
                "query_type": decomposition.classification.query_type.value,
            }
            return result

        elif decomposition.execution_strategy == "parallel":
            # Compound query - parallel execution
            logger.info(
                "executing_parallel_sub_queries",
                num_queries=len(decomposition.sub_queries),
            )

            tasks = [
                search_fn(query=sq.query, **search_kwargs)
                for sq in decomposition.sub_queries
            ]
            sub_results = await asyncio.gather(*tasks)

            # Merge results
            merged_result = self._merge_results(
                sub_results, strategy=merge_strategy, query=query
            )
            merged_result["decomposition"] = {
                "applied": True,
                "query_type": decomposition.classification.query_type.value,
                "sub_queries": [sq.query for sq in decomposition.sub_queries],
                "execution_strategy": "parallel",
            }

            return merged_result

        else:  # sequential (MULTI_HOP)
            # Multi-hop query - sequential execution
            logger.info(
                "executing_sequential_sub_queries",
                num_queries=len(decomposition.sub_queries),
            )

            sub_results = []
            context = {}  # Store results for dependency resolution

            for sub_query in sorted(decomposition.sub_queries, key=lambda x: x.index):
                # TODO: For true multi-hop, inject context from previous results
                # For now, just execute sequentially
                result = await search_fn(query=sub_query.query, **search_kwargs)
                sub_results.append(result)
                context[sub_query.index] = result

            # Use last result as primary (most specific answer)
            merged_result = sub_results[-1] if sub_results else {"results": []}
            merged_result["decomposition"] = {
                "applied": True,
                "query_type": decomposition.classification.query_type.value,
                "sub_queries": [sq.query for sq in decomposition.sub_queries],
                "execution_strategy": "sequential",
            }

            return merged_result

    def _merge_results(
        self, results: list[dict], strategy: str, query: str
    ) -> dict:
        """Merge multiple search results.

        Args:
            results: List of search result dicts
            strategy: Merge strategy ("rrf", "concat", "best")
            query: Original query

        Returns:
            Merged result dict
        """
        if not results:
            return {"query": query, "results": [], "total_results": 0}

        if strategy == "concat":
            # Simple concatenation
            all_results = []
            for r in results:
                all_results.extend(r.get("results", []))

            return {
                "query": query,
                "results": all_results,
                "total_results": len(all_results),
                "search_metadata": {"merge_strategy": "concat"},
            }

        elif strategy == "best":
            # Return result set with most results
            best = max(results, key=lambda r: len(r.get("results", [])))
            best["search_metadata"] = {
                **best.get("search_metadata", {}),
                "merge_strategy": "best",
            }
            return best

        else:  # rrf (default)
            # Use RRF to merge (same as hybrid search)
            from src.utils.fusion import reciprocal_rank_fusion

            rankings = [r.get("results", []) for r in results]
            fused = reciprocal_rank_fusion(rankings, k=60, id_field="id")

            return {
                "query": query,
                "results": fused,
                "total_results": len(fused),
                "search_metadata": {"merge_strategy": "rrf"},
            }
