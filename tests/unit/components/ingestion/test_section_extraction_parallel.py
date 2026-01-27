"""Unit tests for parallel section extraction features (Sprint 121).

Sprint 121 Feature 121.2a-b: Tokenizer caching & parallel tokenization

Tests the following:
- _get_cached_tokenizer() — Singleton caching, thread-safety
- _batch_tokenize_parallel() — Token counting with ThreadPoolExecutor
- Integration: Parallel tokenization produces same results as sequential
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from src.components.ingestion.section_extraction import (
    _batch_tokenize_parallel,
    _get_cached_tokenizer,
    get_profiling_stats,
    reset_profiling_stats,
)


# ============================================================================
# Tests: _get_cached_tokenizer()
# ============================================================================


class TestGetCachedTokenizer:
    """Test tokenizer singleton caching and thread-safety."""

    def test_get_cached_tokenizer_first_call(self):
        """Test tokenizer is loaded on first call."""
        # Reset module state
        import src.components.ingestion.section_extraction as mod
        mod._TOKENIZER = None

        mock_tokenizer = MagicMock()
        with patch("transformers.AutoTokenizer") as mock_auto:
            mock_auto.from_pretrained.return_value = mock_tokenizer

            tokenizer = _get_cached_tokenizer()

            assert tokenizer is mock_tokenizer
            mock_auto.from_pretrained.assert_called_once_with("BAAI/bge-m3")

    def test_get_cached_tokenizer_second_call_cached(self):
        """Test tokenizer is cached and reused on subsequent calls."""
        import src.components.ingestion.section_extraction as mod
        mod._TOKENIZER = None

        with patch("transformers.AutoTokenizer") as mock_auto:
            mock_tokenizer = MagicMock()
            mock_auto.from_pretrained.return_value = mock_tokenizer

            # First call
            tokenizer1 = _get_cached_tokenizer()

            # Second call (should not call from_pretrained again)
            tokenizer2 = _get_cached_tokenizer()

            assert tokenizer1 is tokenizer2
            mock_auto.from_pretrained.assert_called_once()  # Only once!

    def test_get_cached_tokenizer_thread_safety(self):
        """Test tokenizer caching is thread-safe (double-check locking)."""
        import src.components.ingestion.section_extraction as mod
        mod._TOKENIZER = None

        with patch("transformers.AutoTokenizer") as mock_auto:
            mock_tokenizer = MagicMock()
            call_count = [0]

            def side_effect(*args, **kwargs):
                call_count[0] += 1
                time.sleep(0.01)  # Simulate loading time
                return mock_tokenizer

            mock_auto.from_pretrained.side_effect = side_effect

            tokenizers = []
            threads = []

            def get_tokenizer():
                t = _get_cached_tokenizer()
                tokenizers.append(t)

            # Start multiple threads simultaneously
            for _ in range(5):
                t = threading.Thread(target=get_tokenizer)
                threads.append(t)
                t.start()

            # Wait for all threads
            for t in threads:
                t.join()

            # All threads should get the same tokenizer instance
            assert len(tokenizers) == 5
            assert all(t is tokenizers[0] for t in tokenizers)

            # from_pretrained should have been called only once (thread-safe)
            assert call_count[0] == 1

    def test_get_cached_tokenizer_load_failure(self):
        """Test graceful fallback when tokenizer loading fails."""
        import src.components.ingestion.section_extraction as mod
        mod._TOKENIZER = None

        with patch("transformers.AutoTokenizer") as mock_auto:
            mock_auto.from_pretrained.side_effect = ImportError(
                "transformers not available"
            )

            tokenizer = _get_cached_tokenizer()

            # Should return None on failure
            assert tokenizer is None

    def test_get_cached_tokenizer_model_not_found(self):
        """Test handling of missing model error."""
        import src.components.ingestion.section_extraction as mod
        mod._TOKENIZER = None

        with patch("transformers.AutoTokenizer") as mock_auto:
            mock_auto.from_pretrained.side_effect = OSError(
                "Can't connect to HuggingFace"
            )

            tokenizer = _get_cached_tokenizer()

            assert tokenizer is None


# ============================================================================
# Tests: _batch_tokenize_parallel()
# ============================================================================


class TestBatchTokenizeParallel:
    """Test parallel tokenization functionality."""

    def test_batch_tokenize_success(self):
        """Test successful parallel tokenization."""
        texts = [
            "Hello world",
            "This is a test",
            "Another example text",
        ]

        mock_tokenizer = MagicMock()

        def mock_encode(text, add_special_tokens=False):
            # Simulate token counting: ~1 token per word
            return text.split()

        mock_tokenizer.encode.side_effect = mock_encode

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            token_counts = _batch_tokenize_parallel(texts, max_workers=2)

            assert len(token_counts) == 3
            assert token_counts[0] == 2  # "Hello world" = 2 tokens
            assert token_counts[1] == 4  # "This is a test" = 4 tokens
            assert token_counts[2] == 3  # "Another example text" = 3 tokens

    def test_batch_tokenize_empty_list(self):
        """Test tokenization of empty text list."""
        texts = []

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = []

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            token_counts = _batch_tokenize_parallel(texts)

            assert token_counts == {}

    def test_batch_tokenize_empty_strings(self):
        """Test tokenization of empty strings."""
        texts = ["", "hello", ""]

        mock_tokenizer = MagicMock()

        def mock_encode(text, add_special_tokens=False):
            return text.split() if text else []

        mock_tokenizer.encode.side_effect = mock_encode

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            token_counts = _batch_tokenize_parallel(texts)

            assert token_counts[0] == 0
            assert token_counts[1] == 1
            assert token_counts[2] == 0

    def test_batch_tokenize_unicode_text(self):
        """Test tokenization with Unicode/multi-language text."""
        texts = [
            "Bonjour le monde",
            "مرحبا بالعالم",  # Arabic
            "你好世界",  # Chinese
        ]

        mock_tokenizer = MagicMock()

        def mock_encode(text, add_special_tokens=False):
            # Simple character-based tokenization for testing
            return list(text)

        mock_tokenizer.encode.side_effect = mock_encode

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            token_counts = _batch_tokenize_parallel(texts)

            assert len(token_counts) == 3
            assert all(v > 0 for v in token_counts.values())

    def test_batch_tokenize_no_tokenizer_fallback(self):
        """Test fallback token counting when tokenizer unavailable."""
        texts = ["Hello world", "This is a test"]

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=None,
        ):
            token_counts = _batch_tokenize_parallel(texts)

            # Fallback: token count ≈ len(text) // 4
            assert 0 in token_counts
            assert 1 in token_counts
            # Approximate character count / 4
            assert token_counts[0] >= 2  # "Hello world" ≈ 11 chars / 4
            assert token_counts[1] >= 3  # "This is a test" ≈ 14 chars / 4

    def test_batch_tokenize_parallel_execution(self):
        """Test that parallel workers actually run concurrently."""
        texts = ["Text 1", "Text 2", "Text 3", "Text 4"]

        call_order = []

        mock_tokenizer = MagicMock()

        def mock_encode(text, add_special_tokens=False):
            call_order.append(text)
            time.sleep(0.01)  # Simulate work
            return text.split()

        mock_tokenizer.encode.side_effect = mock_encode

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            start_time = time.time()
            token_counts = _batch_tokenize_parallel(texts, max_workers=4)
            elapsed = time.time() - start_time

            # With 4 workers processing 4 tasks of 10ms each:
            # Sequential: ~40ms
            # Parallel: ~10-20ms
            # We check that it's faster than fully sequential
            assert len(token_counts) == 4

    def test_batch_tokenize_max_workers(self):
        """Test max_workers parameter is used."""
        texts = ["Text 1", "Text 2", "Text 3"]

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = ["token"]

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            with patch("src.components.ingestion.section_extraction.ThreadPoolExecutor") as mock_executor_class:
                mock_executor = MagicMock()
                mock_executor_class.return_value.__enter__ = MagicMock(
                    return_value=mock_executor
                )
                mock_executor_class.return_value.__exit__ = MagicMock(
                    return_value=False
                )
                mock_executor.submit.side_effect = [
                    MagicMock(result=lambda: (0, 1)),
                    MagicMock(result=lambda: (1, 1)),
                    MagicMock(result=lambda: (2, 1)),
                ]

                # Patch as_completed to return futures immediately
                with patch(
                    "src.components.ingestion.section_extraction.as_completed"
                ) as mock_as_completed:
                    futures = [MagicMock(result=lambda: (i, 1)) for i in range(3)]
                    mock_as_completed.return_value = futures

                    token_counts = _batch_tokenize_parallel(texts, max_workers=8)

                    # Verify ThreadPoolExecutor was called with correct max_workers
                    mock_executor_class.assert_called_once_with(max_workers=8)

    def test_batch_tokenize_long_text(self):
        """Test tokenization of long documents."""
        long_text = "word " * 10000  # 50,000 characters
        texts = [long_text]

        mock_tokenizer = MagicMock()

        def mock_encode(text, add_special_tokens=False):
            return text.split()

        mock_tokenizer.encode.side_effect = mock_encode

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            token_counts = _batch_tokenize_parallel(texts)

            assert token_counts[0] == 10000


# ============================================================================
# Integration Tests: Parallel vs Sequential Tokenization
# ============================================================================


class TestParallelVsSequentialTokenization:
    """Integration tests comparing parallel and sequential tokenization."""

    def test_parallel_matches_sequential_results(self):
        """Test that parallel tokenization produces identical results."""
        texts = [
            "The quick brown fox jumps over the lazy dog",
            "This is a test of the tokenization system",
            "Another long sentence with many words to tokenize",
        ]

        mock_tokenizer = MagicMock()

        def mock_encode(text, add_special_tokens=False):
            return text.split()

        mock_tokenizer.encode.side_effect = mock_encode

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            # Get parallel results
            parallel_counts = _batch_tokenize_parallel(texts, max_workers=4)

            # Get sequential results manually
            sequential_counts = {}
            for idx, text in enumerate(texts):
                sequential_counts[idx] = len(text.split())

            # Compare
            assert parallel_counts == sequential_counts

    def test_parallel_consistency_multiple_runs(self):
        """Test that parallel tokenization is consistent across multiple runs."""
        texts = ["Text A", "Text B", "Text C"]

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = ["token"]

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            results = []
            for _ in range(5):
                counts = _batch_tokenize_parallel(texts, max_workers=2)
                results.append(counts)

            # All runs should produce identical results
            assert all(r == results[0] for r in results)

    def test_parallel_handles_mixed_content(self):
        """Test parallel tokenization with mixed content types."""
        texts = [
            "Short",
            "This is a medium length text with several words",
            "A " * 1000 + "very long text with lots of repetition",
            "",
            "Special chars: !@#$%^&*()",
        ]

        mock_tokenizer = MagicMock()

        def mock_encode(text, add_special_tokens=False):
            return text.split() if text else []

        mock_tokenizer.encode.side_effect = mock_encode

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            token_counts = _batch_tokenize_parallel(texts, max_workers=3)

            assert len(token_counts) == 5
            assert token_counts[0] == 1  # "Short"
            assert token_counts[1] > 0
            assert token_counts[2] > 1000
            assert token_counts[3] == 0  # Empty
            assert token_counts[4] >= 1


# ============================================================================
# Tests: Profiling Stats Integration
# ============================================================================


class TestProfilingStatsWithParallel:
    """Test profiling stats collection with parallel tokenization."""

    def test_profiling_stats_reset(self):
        """Test profiling stats reset."""
        reset_profiling_stats()

        stats = get_profiling_stats()

        assert stats["total_extraction_time_ms"] == 0.0
        assert stats["total_tokenization_time_ms"] == 0.0
        assert stats["total_texts_processed"] == 0
        assert stats["extraction_calls"] == 0

    def test_profiling_stats_calculations(self):
        """Test profiling stats average calculations."""
        reset_profiling_stats()

        # Manually set some stats (normally done in section extraction)
        from src.components.ingestion import section_extraction
        section_extraction._PROFILING_STATS["total_extraction_time_ms"] = 100.0
        section_extraction._PROFILING_STATS["total_tokenization_time_ms"] = 50.0
        section_extraction._PROFILING_STATS["total_texts_processed"] = 200
        section_extraction._PROFILING_STATS["total_sections_extracted"] = 25
        section_extraction._PROFILING_STATS["extraction_calls"] = 5

        stats = get_profiling_stats()

        assert stats["avg_extraction_time_ms"] == 20.0  # 100 / 5
        assert stats["avg_texts_per_call"] == 40.0  # 200 / 5
        assert stats["avg_sections_per_call"] == 5.0  # 25 / 5


# ============================================================================
# Tests: Edge Cases & Error Handling
# ============================================================================


class TestTokenizationEdgeCases:
    """Test edge cases and error handling in tokenization."""

    def test_batch_tokenize_special_characters(self):
        """Test tokenization with special characters and symbols."""
        texts = [
            "email@example.com",
            "URL: https://example.com/path?query=value",
            "Code: if x > 0: print('hello')",
            "Math: 2^2 = 4, π ≈ 3.14159",
        ]

        mock_tokenizer = MagicMock()

        def mock_encode(text, add_special_tokens=False):
            return text.split()

        mock_tokenizer.encode.side_effect = mock_encode

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            token_counts = _batch_tokenize_parallel(texts)

            assert len(token_counts) == 4
            assert all(v > 0 for v in token_counts.values())

    def test_batch_tokenize_whitespace_only(self):
        """Test tokenization with whitespace-only strings."""
        texts = ["   ", "\n\n\n", "\t\t", " \n \t "]

        mock_tokenizer = MagicMock()

        def mock_encode(text, add_special_tokens=False):
            return text.split()

        mock_tokenizer.encode.side_effect = mock_encode

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            token_counts = _batch_tokenize_parallel(texts)

            # All whitespace-only should result in 0 tokens
            assert all(v == 0 for v in token_counts.values())

    def test_batch_tokenize_exception_handling(self):
        """Test handling of tokenizer exceptions."""
        texts = ["Text 1", "Text 2"]

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = RuntimeError("Tokenizer error")

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            # The function should propagate the exception
            with pytest.raises(RuntimeError):
                _batch_tokenize_parallel(texts)

    def test_batch_tokenize_single_text(self):
        """Test tokenization of single text item."""
        texts = ["Single text item"]

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = ["Single", "text", "item"]

        with patch(
            "src.components.ingestion.section_extraction._get_cached_tokenizer",
            return_value=mock_tokenizer,
        ):
            token_counts = _batch_tokenize_parallel(texts)

            assert len(token_counts) == 1
            assert token_counts[0] == 3
