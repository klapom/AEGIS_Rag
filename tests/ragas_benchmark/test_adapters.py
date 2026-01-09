"""
Unit tests for RAGAS benchmark dataset adapters.

Sprint 82: Phase 1 - Text-Only Benchmark
"""

import pytest
from scripts.ragas_benchmark.adapters import (
    HotpotQAAdapter,
    RAGBenchAdapter,
    LogQAAdapter,
)
from scripts.ragas_benchmark.models import NormalizedSample


class TestHotpotQAAdapter:
    """Tests for HotpotQA adapter."""

    @pytest.fixture
    def adapter(self):
        return HotpotQAAdapter()

    def test_basic_adaptation(self, adapter):
        """Test HotpotQA adapter with sample record."""
        record = {
            "id": "test_001",
            "question": "Which magazine was started first?",
            "answer": "Arthur's Magazine",
            "type": "comparison",
            "level": "medium",
            "context": {
                "title": ["Arthur's Magazine", "First for Women"],
                "sentences": [
                    ["Arthur's Magazine (1844–1846) was an American literary periodical."],
                    ["First for Women is a woman's magazine published by Bauer Media Group."]
                ]
            },
            "supporting_facts": {
                "title": ["Arthur's Magazine"],
                "sent_id": [0]
            }
        }

        result = adapter.adapt(record, record_idx=0)

        assert result is not None
        assert result.question == "Which magazine was started first?"
        assert result.ground_truth == "Arthur's Magazine"
        assert result.doc_type == "clean_text"
        assert result.question_type == "comparison"
        assert result.difficulty == "D2"  # medium maps to D2
        assert result.answerable is True
        assert len(result.contexts) == 2

    def test_empty_answer_dropped(self, adapter):
        """Test that records with empty answers are dropped."""
        record = {
            "id": "test_002",
            "question": "What is something?",
            "answer": "",
            "context": {
                "title": ["Test"],
                "sentences": [["Some context."]]
            }
        }

        result = adapter.adapt(record, record_idx=0)
        assert result is None
        assert adapter.drop_count == 1

    def test_multihop_classification(self, adapter):
        """Test that bridge type maps to multihop."""
        record = {
            "id": "test_003",
            "question": "Who founded the company that made X?",
            "answer": "John Doe",
            "type": "bridge",
            "level": "hard",
            "context": {
                "title": ["Company A", "John Doe"],
                "sentences": [
                    ["Company A made X."],
                    ["John Doe founded Company A."]
                ]
            }
        }

        result = adapter.adapt(record, record_idx=0)

        assert result is not None
        assert result.question_type == "multihop"
        assert result.difficulty == "D3"  # hard maps to D3


class TestRAGBenchAdapter:
    """Tests for RAGBench adapter."""

    @pytest.fixture
    def adapter(self):
        return RAGBenchAdapter()

    def test_basic_adaptation(self, adapter):
        """Test RAGBench adapter with sample record."""
        record = {
            "question": "What is the capital of France?",
            "answer": "Paris",
            "context": ["France is a country in Europe. Its capital is Paris."],
        }

        result = adapter.adapt(record, record_idx=0)

        assert result is not None
        assert result.question == "What is the capital of France?"
        assert result.ground_truth == "Paris"
        assert result.doc_type == "clean_text"
        assert len(result.contexts) == 1

    def test_response_field_fallback(self, adapter):
        """Test that 'response' field is used when 'answer' missing."""
        record = {
            "question": "What is X and how does it work?",
            "response": "X is Y and it works by doing Z",
            "context": ["Some detailed context about X. X is a technology that was developed in 2020. It provides many benefits."],
        }

        result = adapter.adapt(record, record_idx=0)

        assert result is not None
        assert result.ground_truth == "X is Y and it works by doing Z"

    def test_documents_field_fallback(self, adapter):
        """Test that 'documents' field is used when 'context' missing."""
        record = {
            "question": "What is X and why is it important?",
            "answer": "Y is the answer to the question",
            "documents": ["Document 1 about X with detailed information and context.", "Document 2 about X with more details."],
        }

        result = adapter.adapt(record, record_idx=0)

        assert result is not None
        assert len(result.contexts) == 2


class TestLogQAAdapter:
    """Tests for LogQA adapter."""

    @pytest.fixture
    def adapter(self):
        return LogQAAdapter()

    def test_basic_adaptation(self, adapter):
        """Test LogQA adapter with sample record."""
        record = {
            "id": "logqa_001",
            "question": "What error occurred in the log?",
            "answer": "NullPointerException",
            "context": ["2024-01-01 10:30:45 ERROR: NullPointerException at line 42 in module UserService. The stack trace shows the error originated from the authentication handler."],
            "log_type": "application",
        }

        result = adapter.adapt(record, record_idx=0)

        assert result is not None
        assert result.question == "What error occurred in the log?"
        assert result.ground_truth == "NullPointerException"
        assert result.doc_type == "log_ticket"
        assert result.question_type == "lookup"  # "what error" → lookup

    def test_security_log_harder(self, adapter):
        """Test that security logs get higher difficulty."""
        record = {
            "id": "logqa_002",
            "question": "What security event occurred?",
            "answer": "Unauthorized access",
            "context": ["2024-01-01 12:00:00 SECURITY: Unauthorized access detected from IP 192.168.1.100. User attempted to access restricted resource /admin/users without proper credentials."],
            "log_type": "security",
        }

        result = adapter.adapt(record, record_idx=0)

        assert result is not None
        # Security logs should be at least D2
        assert result.difficulty in ["D2", "D3"]

    def test_howto_classification(self, adapter):
        """Test that troubleshooting questions are classified as howto."""
        record = {
            "id": "logqa_003",
            "question": "How to fix the connection error?",
            "answer": "Restart the service",
            "context": ["2024-01-01 15:00:00 ERROR: Connection refused to database server at localhost:5432. The service has been unable to establish a connection for the past 5 minutes."],
        }

        result = adapter.adapt(record, record_idx=0)

        assert result is not None
        assert result.question_type == "howto"


class TestAdapterDropHandling:
    """Tests for adapter drop handling."""

    def test_drop_stats_tracking(self):
        """Test that drop statistics are tracked correctly."""
        adapter = HotpotQAAdapter()

        # Create records that will be dropped
        invalid_records = [
            {"id": "1", "question": "", "answer": "x", "context": {}},  # empty question
            {"id": "2", "question": "What?", "answer": "", "context": {}},  # empty answer
        ]

        for i, record in enumerate(invalid_records):
            adapter.adapt(record, record_idx=i)

        stats = adapter.get_drop_stats()
        assert stats["total_dropped"] >= 2

    def test_reset_stats(self):
        """Test that stats can be reset."""
        adapter = HotpotQAAdapter()

        # Cause a drop
        adapter.adapt({"id": "1", "question": "", "answer": "", "context": {}}, 0)
        assert adapter.drop_count > 0

        # Reset
        adapter.reset_stats()
        assert adapter.drop_count == 0
        assert adapter.drop_reasons == {}
