"""Unit tests for OllamaReranker.

Sprint 48 Feature 48.8: TD-059 Ollama Reranker Implementation

Tests cover:
- Initialization and configuration
- Document scoring via Ollama API
- Score parsing from model responses
- Reranking logic (sorting by relevance)
- Error handling and fallback behavior
- Edge cases (empty documents, invalid responses)
"""

from unittest.mock import patch

import pytest

from src.components.retrieval.ollama_reranker import OllamaReranker, get_ollama_reranker


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("src.components.retrieval.ollama_reranker.settings") as mock:
        mock.ollama_base_url = "http://localhost:11434"
        mock.reranker_ollama_model = "bge-reranker-v2-m3"  # Fixed: use correct attribute name
        yield mock


@pytest.fixture
def reranker(mock_settings):
    """Create OllamaReranker instance for testing."""
    return OllamaReranker(model="bge-reranker-v2-m3", top_k=10)


class TestOllamaRerankerInitialization:
    """Test OllamaReranker initialization."""

    def test_init_with_defaults(self, mock_settings):
        """Test initialization with default parameters."""
        reranker = OllamaReranker()

        assert reranker.model == "bge-reranker-v2-m3"
        assert reranker.top_k == 10
        assert reranker.ollama_url == "http://localhost:11434/api/generate"

    def test_init_with_custom_params(self, mock_settings):
        """Test initialization with custom parameters."""
        reranker = OllamaReranker(model="custom-reranker", top_k=5)

        assert reranker.model == "custom-reranker"
        assert reranker.top_k == 5

    def test_get_model_info(self, reranker):
        """Test get_model_info returns correct information."""
        info = reranker.get_model_info()

        assert info["model"] == "bge-reranker-v2-m3"
        assert info["top_k"] == 10
        assert info["ollama_url"] == "http://localhost:11434/api/generate"
        assert info["backend"] == "ollama"


class TestOllamaRerankerScoreDocument:
    """Test document scoring functionality.

    Note: These tests mock at the _score_document level rather than
    mocking aiohttp directly, as aiohttp AsyncMock behavior is complex.
    Integration tests verify the actual HTTP behavior.
    """

    @pytest.mark.asyncio
    async def test_score_document_via_rerank(self, reranker):
        """Test document scoring indirectly via rerank method."""
        # Mock _score_document to return a specific score
        with patch.object(reranker, "_score_document", return_value=0.8):
            ranked = await reranker.rerank("query", ["document"], top_k=1)

            assert len(ranked) == 1
            assert ranked[0][1] == 0.8  # Score is 0.8

    @pytest.mark.asyncio
    async def test_score_document_error_handling(self, reranker):
        """Test that scoring errors are handled gracefully."""
        # Mock _score_document to raise an exception
        with patch.object(reranker, "_score_document", side_effect=Exception("API Error")):
            ranked = await reranker.rerank("query", ["document"], top_k=1)

            # Should still return result with fallback score of 0.0
            assert len(ranked) == 1
            assert ranked[0][1] == 0.0  # Fallback score


class TestOllamaRerankerRerank:
    """Test full reranking functionality."""

    @pytest.mark.asyncio
    async def test_rerank_success(self, reranker):
        """Test successful reranking of documents."""
        query = "What is vector search?"
        documents = [
            "Vector search uses embeddings for similarity matching",
            "BM25 is a probabilistic keyword search algorithm",
            "Hybrid search combines vector and keyword approaches",
        ]

        # Mock _score_document to return different scores
        with patch.object(reranker, "_score_document", side_effect=[0.9, 0.3, 0.7]) as mock_score:
            ranked = await reranker.rerank(query, documents, top_k=3)

            # Check that all documents were scored
            assert mock_score.call_count == 3

            # Results should be sorted by score (descending)
            assert len(ranked) == 3
            assert ranked[0] == (0, 0.9)  # Doc 0 has highest score
            assert ranked[1] == (2, 0.7)  # Doc 2 has second highest
            assert ranked[2] == (1, 0.3)  # Doc 1 has lowest score

    @pytest.mark.asyncio
    async def test_rerank_with_top_k(self, reranker):
        """Test reranking with top_k limit."""
        query = "test query"
        documents = ["doc1", "doc2", "doc3", "doc4", "doc5"]

        with patch.object(reranker, "_score_document", side_effect=[0.9, 0.8, 0.7, 0.6, 0.5]):
            ranked = await reranker.rerank(query, documents, top_k=3)

            # Should only return top 3
            assert len(ranked) == 3
            assert ranked[0] == (0, 0.9)
            assert ranked[1] == (1, 0.8)
            assert ranked[2] == (2, 0.7)

    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self, reranker):
        """Test reranking with empty document list."""
        ranked = await reranker.rerank("query", [])

        assert ranked == []

    @pytest.mark.asyncio
    async def test_rerank_with_scoring_failures(self, reranker):
        """Test reranking handles individual document scoring failures."""
        query = "test query"
        documents = ["doc1", "doc2", "doc3"]

        # Mock _score_document: first succeeds, second fails, third succeeds
        async def mock_score(q, d):
            if d == "doc2":
                raise Exception("Scoring failed")
            return 0.8 if d == "doc1" else 0.6

        with patch.object(reranker, "_score_document", side_effect=mock_score):
            ranked = await reranker.rerank(query, documents)

            # Should return 3 results, with failed doc having score 0.0
            assert len(ranked) == 3
            assert ranked[0][0] == 0  # doc1 with score 0.8
            assert ranked[1][0] == 2  # doc3 with score 0.6
            assert ranked[2][0] == 1  # doc2 with score 0.0 (failed)


class TestOllamaRerankerPromptBuilding:
    """Test prompt construction for reranking."""

    def test_build_rerank_prompt(self, reranker):
        """Test prompt building with normal inputs."""
        query = "What is vector search?"
        document = "Vector search uses embeddings for similarity matching."

        prompt = reranker._build_rerank_prompt(query, document)

        assert "Query: What is vector search?" in prompt
        assert "Document: Vector search uses embeddings" in prompt
        assert "Relevance Score:" in prompt
        assert "0 to 10" in prompt

    def test_build_rerank_prompt_truncates_long_document(self, reranker):
        """Test that long documents are truncated."""
        query = "test"
        document = "x" * 1000  # Very long document

        prompt = reranker._build_rerank_prompt(query, document)

        # Should be truncated to ~500 chars + "..."
        assert len(prompt) < 1000
        assert "..." in prompt


class TestOllamaRerankerScoreParsing:
    """Test score parsing from model responses."""

    def test_parse_score_single_digit(self, reranker):
        """Test parsing a single digit score."""
        score = reranker._parse_score("8")
        assert score == 0.8

    def test_parse_score_decimal(self, reranker):
        """Test parsing a decimal score."""
        score = reranker._parse_score("7.5")
        assert score == 0.75

    def test_parse_score_with_text(self, reranker):
        """Test parsing score from text response."""
        score = reranker._parse_score("The relevance score is 9 out of 10")
        assert score == 0.9

    def test_parse_score_zero(self, reranker):
        """Test parsing zero score."""
        score = reranker._parse_score("0")
        assert score == 0.0

    def test_parse_score_max(self, reranker):
        """Test parsing maximum score."""
        score = reranker._parse_score("10")
        assert score == 1.0

    def test_parse_score_out_of_range_high(self, reranker):
        """Test parsing score above 10 (should clamp to 1.0)."""
        score = reranker._parse_score("15")
        assert score == 1.0

    def test_parse_score_out_of_range_low(self, reranker):
        """Test parsing negative score (should clamp to 0.0)."""
        score = reranker._parse_score("-5")
        assert score == 0.0

    def test_parse_score_invalid_no_number(self, reranker):
        """Test parsing invalid response with no numbers."""
        score = reranker._parse_score("No score available")
        assert score == 0.5  # Default fallback

    def test_parse_score_empty(self, reranker):
        """Test parsing empty response."""
        score = reranker._parse_score("")
        assert score == 0.5  # Default fallback

    def test_parse_score_malformed(self, reranker):
        """Test parsing malformed response."""
        score = reranker._parse_score("abc xyz")
        assert score == 0.5  # Default fallback


class TestOllamaRerankerFallback:
    """Test fallback behavior."""

    def test_fallback_ranking(self, reranker):
        """Test fallback ranking returns original order."""
        ranked = reranker._fallback_ranking(num_docs=5, top_k=3)

        assert len(ranked) == 3
        assert ranked[0] == (0, 1.0)  # First doc, highest score
        assert ranked[1] == (1, 0.5)  # Second doc
        assert ranked[2] == (2, 1 / 3)  # Third doc

    def test_fallback_ranking_limited_docs(self, reranker):
        """Test fallback with fewer docs than top_k."""
        ranked = reranker._fallback_ranking(num_docs=2, top_k=5)

        assert len(ranked) == 2
        assert ranked[0] == (0, 1.0)
        assert ranked[1] == (1, 0.5)


class TestOllamaRerankerSingleton:
    """Test singleton pattern."""

    def test_get_ollama_reranker_singleton(self, mock_settings):
        """Test that get_ollama_reranker returns singleton instance."""
        reranker1 = get_ollama_reranker()
        reranker2 = get_ollama_reranker()

        assert reranker1 is reranker2


class TestOllamaRerankerIntegration:
    """Integration tests with mocked Ollama API."""

    @pytest.mark.asyncio
    async def test_full_reranking_workflow(self, reranker):
        """Test complete reranking workflow with mocked API."""
        query = "How does hybrid search work?"
        documents = [
            "Hybrid search combines vector and keyword approaches for better results",
            "BM25 is a traditional keyword-based search algorithm",
            "Vector embeddings capture semantic meaning of text",
        ]

        # Mock _score_document to return specific scores
        with patch.object(reranker, "_score_document", side_effect=[0.9, 0.4, 0.7]) as mock_score:
            ranked = await reranker.rerank(query, documents, top_k=3)

            # Verify all documents were scored
            assert mock_score.call_count == 3

            # Verify results are sorted by relevance
            assert len(ranked) == 3
            assert ranked[0][0] == 0  # Doc 0 (score 0.9)
            assert ranked[1][0] == 2  # Doc 2 (score 0.7)
            assert ranked[2][0] == 1  # Doc 1 (score 0.4)

            # Verify scores are correct
            assert ranked[0][1] == 0.9
            assert ranked[1][1] == 0.7
            assert ranked[2][1] == 0.4
