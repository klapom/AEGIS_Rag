"""Unit tests for CostTracker - LLM request cost tracking and analysis.

Tests cover:
- Database initialization and schema
- Request tracking with accurate cost calculation
- Monthly/period spending aggregation
- Provider-based filtering
- Export functionality
- Edge cases and error handling
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.domains.llm_integration.cost.cost_tracker import CostTracker, get_cost_tracker


class TestCostTrackerInitialization:
    """Test CostTracker initialization and database setup."""

    def test_init_with_custom_db_path(self, temp_db_path: Path) -> None:
        """Test CostTracker initialization with custom database path."""
        tracker = CostTracker(db_path=temp_db_path)

        assert tracker.db_path == temp_db_path
        assert temp_db_path.exists()

    def test_init_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test CostTracker creates parent directories if needed."""
        nested_path = tmp_path / "data" / "nested" / "cost_tracking.db"
        CostTracker(db_path=nested_path)

        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_database_schema_created(self, cost_tracker: CostTracker) -> None:
        """Test that database schema is properly initialized."""
        with sqlite3.connect(cost_tracker.db_path) as conn:
            cursor = conn.cursor()

            # Check llm_requests table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_requests'"
            )
            assert cursor.fetchone() is not None

            # Check monthly_summary table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='monthly_summary'"
            )
            assert cursor.fetchone() is not None

    def test_indexes_created(self, cost_tracker: CostTracker) -> None:
        """Test that database indexes are created for performance."""
        with sqlite3.connect(cost_tracker.db_path) as conn:
            cursor = conn.cursor()

            # Check indexes
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_provider_timestamp'"
            )
            assert cursor.fetchone() is not None

            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_task_type'"
            )
            assert cursor.fetchone() is not None

    def test_init_default_db_path(self) -> None:
        """Test CostTracker initialization with default database path."""
        tracker = CostTracker(db_path=None)
        # Default path should be: data/cost_tracking.db relative to project root
        assert tracker.db_path.name == "cost_tracking.db"
        assert "data" in str(tracker.db_path)


class TestTrackRequest:
    """Test request tracking functionality."""

    def test_track_request_basic(self, cost_tracker: CostTracker) -> None:
        """Test basic request tracking."""
        row_id = cost_tracker.track_request(
            provider="local_ollama",
            model="gemma-3-4b-it-Q8_0",
            task_type="extraction",
            tokens_input=100,
            tokens_output=50,
            cost_usd=0.0,
        )

        assert row_id > 0

        # Verify in database
        with sqlite3.connect(cost_tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM llm_requests WHERE id = ?", (row_id,))
            row = cursor.fetchone()

            assert row is not None
            # Schema: id, timestamp, provider, model, task_type, task_id, tokens_input, tokens_output, tokens_total, cost_usd, latency_ms, routing_reason, fallback_used, created_at
            assert row[2] == "local_ollama"  # provider
            assert row[3] == "gemma-3-4b-it-Q8_0"  # model
            assert row[4] == "extraction"  # task_type
            assert row[6] == 100  # tokens_input
            assert row[7] == 50  # tokens_output
            assert row[8] == 150  # tokens_total

    def test_track_request_with_all_fields(self, cost_tracker: CostTracker) -> None:
        """Test request tracking with all optional fields."""
        row_id = cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
            latency_ms=250.5,
            routing_reason="high_quality_high_complexity",
            fallback_used=False,
            task_id="task-12345",
        )

        assert row_id > 0

        with sqlite3.connect(cost_tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM llm_requests WHERE id = ?", (row_id,))
            row = cursor.fetchone()

            assert row is not None
            # Schema: id(0), timestamp(1), provider(2), model(3), task_type(4), task_id(5), tokens_input(6), tokens_output(7), tokens_total(8), cost_usd(9), latency_ms(10), routing_reason(11), fallback_used(12), created_at(13)
            assert row[3] == "qwen-turbo"
            assert row[9] == 0.035  # cost_usd
            assert row[10] == 250.5  # latency_ms
            assert row[11] == "high_quality_high_complexity"  # routing_reason
            assert not row[12]  # fallback_used
            assert row[5] == "task-12345"  # task_id

    def test_track_request_fallback_used(self, cost_tracker: CostTracker) -> None:
        """Test tracking request with fallback flag."""
        row_id = cost_tracker.track_request(
            provider="openai",
            model="gpt-4o",
            task_type="generation",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0375,
            fallback_used=True,
        )

        with sqlite3.connect(cost_tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT fallback_used FROM llm_requests WHERE id = ?", (row_id,))
            row = cursor.fetchone()

            assert row[0] == 1  # SQLite stores True as 1

    def test_track_multiple_requests(self, cost_tracker: CostTracker) -> None:
        """Test tracking multiple requests sequentially."""
        row_ids = []
        for i in range(5):
            row_id = cost_tracker.track_request(
                provider="local_ollama",
                model="gemma-3-4b-it-Q8_0",
                task_type="extraction",
                tokens_input=100 * i,
                tokens_output=50 * i,
                cost_usd=0.0,
            )
            row_ids.append(row_id)

        # Verify all rows exist
        with sqlite3.connect(cost_tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM llm_requests")
            count = cursor.fetchone()[0]

            assert count == 5
            assert len(set(row_ids)) == 5  # All IDs unique

    def test_track_request_tokens_total_calculated(self, cost_tracker: CostTracker) -> None:
        """Test that tokens_total is correctly calculated."""
        cost_tracker.track_request(
            provider="local_ollama",
            model="gemma-3-4b-it-Q8_0",
            task_type="extraction",
            tokens_input=300,
            tokens_output=150,
            cost_usd=0.0,
        )

        with sqlite3.connect(cost_tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tokens_total FROM llm_requests")
            tokens_total = cursor.fetchone()[0]

            assert tokens_total == 450  # 300 + 150


class TestGetMonthlySpending:
    """Test monthly spending aggregation."""

    def test_monthly_spending_empty_database(self, cost_tracker: CostTracker) -> None:
        """Test monthly spending on empty database returns empty dict."""
        spending = cost_tracker.get_monthly_spending()

        assert spending == {}

    def test_monthly_spending_single_provider(self, cost_tracker: CostTracker) -> None:
        """Test monthly spending for single provider."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )

        spending = cost_tracker.get_monthly_spending()

        assert "alibaba_cloud" in spending
        assert spending["alibaba_cloud"] == 0.070

    def test_monthly_spending_multiple_providers(self, cost_tracker: CostTracker) -> None:
        """Test monthly spending aggregated by provider."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )
        cost_tracker.track_request(
            provider="openai",
            model="gpt-4o",
            task_type="generation",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0375,
        )

        spending = cost_tracker.get_monthly_spending()

        assert spending["alibaba_cloud"] == 0.035
        assert spending["openai"] == 0.0375

    def test_monthly_spending_filters_by_provider(self, cost_tracker: CostTracker) -> None:
        """Test monthly spending can filter by specific provider."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )
        cost_tracker.track_request(
            provider="openai",
            model="gpt-4o",
            task_type="generation",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0375,
        )

        spending = cost_tracker.get_monthly_spending(provider="alibaba_cloud")

        assert len(spending) == 1
        assert spending["alibaba_cloud"] == 0.035


class TestGetTotalSpending:
    """Test total spending calculation with date filtering."""

    def test_total_spending_empty_database(self, cost_tracker: CostTracker) -> None:
        """Test total spending on empty database returns 0."""
        total = cost_tracker.get_total_spending()

        assert total == 0.0

    def test_total_spending_all_requests(self, cost_tracker: CostTracker) -> None:
        """Test total spending sums all requests."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )
        cost_tracker.track_request(
            provider="openai",
            model="gpt-4o",
            task_type="generation",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0375,
        )

        total = cost_tracker.get_total_spending()

        assert total == pytest.approx(0.0725, rel=1e-3)

    def test_total_spending_with_date_range(self, cost_tracker: CostTracker) -> None:
        """Test total spending with date range filtering."""
        # Track request
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )

        # Query with date range covering today
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now() + timedelta(days=1)

        total = cost_tracker.get_total_spending(start_date=start_date, end_date=end_date)

        assert total == 0.035

    def test_total_spending_with_provider_filter(self, cost_tracker: CostTracker) -> None:
        """Test total spending filters by provider."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )
        cost_tracker.track_request(
            provider="openai",
            model="gpt-4o",
            task_type="generation",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0375,
        )

        total = cost_tracker.get_total_spending(provider="alibaba_cloud")

        assert total == 0.035

    def test_total_spending_excludes_old_dates(self, cost_tracker: CostTracker) -> None:
        """Test total spending excludes requests outside date range."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )

        # Query with date range in future
        start_date = datetime.now() + timedelta(days=1)
        end_date = datetime.now() + timedelta(days=2)

        total = cost_tracker.get_total_spending(start_date=start_date, end_date=end_date)

        assert total == 0.0


class TestGetRequestStats:
    """Test request statistics aggregation."""

    def test_request_stats_empty_database(self, cost_tracker: CostTracker) -> None:
        """Test request stats on empty database."""
        stats = cost_tracker.get_request_stats()

        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0
        assert stats["total_cost_usd"] == 0.0
        assert stats["fallback_count"] == 0

    def test_request_stats_all_fields(self, cost_tracker: CostTracker) -> None:
        """Test request stats includes all required fields."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
            latency_ms=250.5,
        )

        stats = cost_tracker.get_request_stats()

        assert "total_requests" in stats
        assert "total_tokens" in stats
        assert "total_cost_usd" in stats
        assert "avg_cost_per_request_usd" in stats
        assert "avg_latency_ms" in stats
        assert "fallback_count" in stats
        assert "provider_breakdown" in stats
        assert "task_breakdown" in stats

    def test_request_stats_provider_breakdown(self, cost_tracker: CostTracker) -> None:
        """Test provider breakdown in request stats."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )
        cost_tracker.track_request(
            provider="openai",
            model="gpt-4o",
            task_type="generation",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0375,
        )

        stats = cost_tracker.get_request_stats()

        assert len(stats["provider_breakdown"]) == 2
        alibaba_entry = next(
            (p for p in stats["provider_breakdown"] if p["provider"] == "alibaba_cloud"),
            None,
        )
        assert alibaba_entry is not None
        assert alibaba_entry["requests"] == 2
        assert alibaba_entry["cost_usd"] == 0.070

    def test_request_stats_task_breakdown(self, cost_tracker: CostTracker) -> None:
        """Test task type breakdown in request stats."""
        cost_tracker.track_request(
            provider="local_ollama",
            model="gemma-3-4b-it-Q8_0",
            task_type="extraction",
            tokens_input=100,
            tokens_output=50,
            cost_usd=0.0,
            latency_ms=50.0,
        )
        cost_tracker.track_request(
            provider="local_ollama",
            model="gemma-3-4b-it-Q8_0",
            task_type="generation",
            tokens_input=200,
            tokens_output=100,
            cost_usd=0.0,
            latency_ms=100.0,
        )

        stats = cost_tracker.get_request_stats()

        assert len(stats["task_breakdown"]) == 2
        extraction_entry = next(
            (t for t in stats["task_breakdown"] if t["task_type"] == "extraction"), None
        )
        assert extraction_entry is not None
        assert extraction_entry["requests"] == 1
        assert extraction_entry["avg_latency_ms"] == 50.0

    def test_request_stats_fallback_count(self, cost_tracker: CostTracker) -> None:
        """Test fallback count in request stats."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
            fallback_used=True,
        )
        cost_tracker.track_request(
            provider="local_ollama",
            model="gemma-3-4b-it-Q8_0",
            task_type="extraction",
            tokens_input=100,
            tokens_output=50,
            cost_usd=0.0,
            fallback_used=False,
        )

        stats = cost_tracker.get_request_stats()

        assert stats["fallback_count"] == 1

    def test_request_stats_with_days_filter(self, cost_tracker: CostTracker) -> None:
        """Test request stats with days parameter."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )

        stats = cost_tracker.get_request_stats(days=30)

        assert stats["period_days"] == 30
        assert stats["total_requests"] == 1

    def test_request_stats_with_provider_filter(self, cost_tracker: CostTracker) -> None:
        """Test request stats filtered by provider."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )
        cost_tracker.track_request(
            provider="openai",
            model="gpt-4o",
            task_type="generation",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.0375,
        )

        stats = cost_tracker.get_request_stats(provider="alibaba_cloud")

        assert stats["total_requests"] == 1
        assert stats["total_cost_usd"] == 0.035


class TestExportToCsv:
    """Test CSV export functionality."""

    def test_export_to_csv_basic(self, cost_tracker: CostTracker, tmp_path: Path) -> None:
        """Test exporting cost data to CSV."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )

        output_path = tmp_path / "costs.csv"
        cost_tracker.export_to_csv(output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "alibaba_cloud" in content
        assert "qwen-turbo" in content

    def test_export_to_csv_with_days_filter(
        self, cost_tracker: CostTracker, tmp_path: Path
    ) -> None:
        """Test CSV export with days filter."""
        cost_tracker.track_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_input=500,
            tokens_output=200,
            cost_usd=0.035,
        )

        output_path = tmp_path / "costs.csv"
        cost_tracker.export_to_csv(output_path, days=30)

        assert output_path.exists()

    def test_export_to_csv_empty_database(self, cost_tracker: CostTracker, tmp_path: Path) -> None:
        """Test CSV export on empty database."""
        output_path = tmp_path / "costs.csv"
        cost_tracker.export_to_csv(output_path)

        assert output_path.exists()
        content = output_path.read_text()
        # Should have headers but no data rows
        lines = content.strip().split("\n")
        assert len(lines) >= 1  # At least header


class TestGetCostTrackerSingleton:
    """Test singleton pattern for cost tracker."""

    def test_get_cost_tracker_returns_instance(self) -> None:
        """Test get_cost_tracker returns CostTracker instance."""
        # Note: This test uses the actual singleton, which may be initialized
        # by other tests. For isolation, consider mocking.
        tracker = get_cost_tracker()

        assert isinstance(tracker, CostTracker)

    @patch("src.domains.llm_integration.cost.cost_tracker._cost_tracker_instance", None)
    def test_get_cost_tracker_singleton_creation(self) -> None:
        """Test get_cost_tracker creates singleton on first call."""
        with patch("src.domains.llm_integration.cost.cost_tracker.CostTracker") as mock_class:
            mock_instance = MagicMock(spec=CostTracker)
            mock_instance.db_path = Path("/tmp/test.db")
            mock_class.return_value = mock_instance

            tracker = get_cost_tracker()

            assert tracker == mock_instance
            mock_class.assert_called_once()

    @patch("src.domains.llm_integration.cost.cost_tracker._cost_tracker_instance", MagicMock())
    def test_get_cost_tracker_returns_existing_instance(self) -> None:
        """Test get_cost_tracker returns existing singleton."""
        existing_instance = MagicMock(spec=CostTracker)

        with patch(
            "src.domains.llm_integration.cost.cost_tracker._cost_tracker_instance",
            existing_instance,
        ):
            tracker = get_cost_tracker()

            assert tracker == existing_instance


class TestCostTrackerEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_cost_request(self, cost_tracker: CostTracker) -> None:
        """Test tracking request with zero cost (local provider)."""
        row_id = cost_tracker.track_request(
            provider="local_ollama",
            model="gemma-3-4b-it-Q8_0",
            task_type="extraction",
            tokens_input=100,
            tokens_output=50,
            cost_usd=0.0,
        )

        assert row_id > 0

        with sqlite3.connect(cost_tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cost_usd FROM llm_requests WHERE id = ?", (row_id,))
            cost = cursor.fetchone()[0]

            assert cost == 0.0

    def test_very_large_token_count(self, cost_tracker: CostTracker) -> None:
        """Test tracking request with very large token counts."""
        row_id = cost_tracker.track_request(
            provider="openai",
            model="gpt-4o",
            task_type="generation",
            tokens_input=100000,
            tokens_output=50000,
            cost_usd=1500.0,
        )

        assert row_id > 0

        with sqlite3.connect(cost_tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tokens_total FROM llm_requests WHERE id = ?", (row_id,))
            tokens_total = cursor.fetchone()[0]

            assert tokens_total == 150000

    def test_null_optional_fields(self, cost_tracker: CostTracker) -> None:
        """Test tracking request without optional fields."""
        row_id = cost_tracker.track_request(
            provider="local_ollama",
            model="gemma-3-4b-it-Q8_0",
            task_type="extraction",
            tokens_input=100,
            tokens_output=50,
            cost_usd=0.0,
            latency_ms=None,
            routing_reason=None,
            task_id=None,
        )

        with sqlite3.connect(cost_tracker.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT latency_ms, routing_reason, task_id FROM llm_requests WHERE id = ?",
                (row_id,),
            )
            row = cursor.fetchone()

            assert row[0] is None
            assert row[1] is None
            assert row[2] is None

    def test_spending_precision(self, cost_tracker: CostTracker) -> None:
        """Test spending calculation maintains precision."""
        # Track several requests with fractional costs
        for _i in range(10):
            cost_tracker.track_request(
                provider="alibaba_cloud",
                model="qwen-turbo",
                task_type="extraction",
                tokens_input=100,
                tokens_output=50,
                cost_usd=0.0123,
            )

        spending = cost_tracker.get_monthly_spending()

        # Sum should be approximately 0.123 (10 * 0.0123)
        assert spending["alibaba_cloud"] == pytest.approx(0.123, rel=1e-4)
