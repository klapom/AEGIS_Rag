"""Cost Tracker for LLM Requests.

Sprint 23 - Feature 23.4: Multi-Cloud LLM Execution
Related ADR: ADR-033

This module provides persistent cost tracking for all LLM requests
using SQLite for local storage and aggregation.

Features:
- Per-request tracking (timestamp, provider, model, tokens, cost)
- Daily/monthly aggregations
- Budget alerts
- Export to CSV/JSON for analysis
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class CostTracker:
    """Persistent cost tracking for LLM requests."""

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize cost tracker.

        Args:
            db_path: Path to SQLite database (default: data/cost_tracking.db)
        """
        if db_path is None:
            # Default to project data directory
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "cost_tracking.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        logger.info("CostTracker initialized", db_path=str(self.db_path))

    def _init_db(self) -> None:
        """Create database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main requests table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    task_id TEXT,
                    tokens_input INTEGER NOT NULL,
                    tokens_output INTEGER NOT NULL,
                    tokens_total INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    latency_ms REAL,
                    routing_reason TEXT,
                    fallback_used BOOLEAN DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Index for fast queries
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_provider_timestamp
                ON llm_requests(provider, timestamp)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_task_type
                ON llm_requests(task_type)
            """
            )

            # Monthly summary table (pre-aggregated for performance)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS monthly_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year_month TEXT NOT NULL UNIQUE,
                    provider TEXT NOT NULL,
                    total_requests INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    total_cost_usd REAL NOT NULL,
                    avg_latency_ms REAL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.commit()

        logger.info(
            "Cost tracking database initialized", tables=["llm_requests", "monthly_summary"]
        )

    def track_request(
        self,
        provider: str,
        model: str,
        task_type: str,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float,
        latency_ms: float | None = None,
        routing_reason: str | None = None,
        fallback_used: bool = False,
        task_id: str | None = None,
    ) -> int:
        """Track a single LLM request.

        Args:
            provider: Provider name (local_ollama, alibaba_cloud, openai)
            model: Model name
            task_type: Task type (extraction, generation, vision, etc.)
            tokens_input: Input tokens
            tokens_output: Output tokens
            cost_usd: Cost in USD
            latency_ms: Request latency in milliseconds
            routing_reason: Reason for provider selection
            fallback_used: Whether fallback was used
            task_id: Unique task ID

        Returns:
            Database row ID
        """
        timestamp = datetime.now().isoformat()
        tokens_total = tokens_input + tokens_output

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO llm_requests (
                    timestamp, provider, model, task_type, task_id,
                    tokens_input, tokens_output, tokens_total,
                    cost_usd, latency_ms, routing_reason, fallback_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    timestamp,
                    provider,
                    model,
                    task_type,
                    task_id,
                    tokens_input,
                    tokens_output,
                    tokens_total,
                    cost_usd,
                    latency_ms,
                    routing_reason,
                    fallback_used,
                ),
            )

            row_id = cursor.lastrowid
            conn.commit()

        logger.debug(
            "Request tracked",
            row_id=row_id,
            provider=provider,
            model=model,
            cost_usd=cost_usd,
            tokens_total=tokens_total,
        )

        return row_id

    def get_monthly_spending(self, provider: str | None = None) -> dict[str, float]:
        """Get current month spending by provider.

        Args:
            provider: Filter by provider (None = all providers)

        Returns:
            Dict mapping provider -> spending in USD
        """
        current_month = datetime.now().strftime("%Y-%m")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if provider:
                cursor.execute(
                    """
                    SELECT provider, SUM(cost_usd)
                    FROM llm_requests
                    WHERE strftime('%Y-%m', timestamp) = ?
                      AND provider = ?
                    GROUP BY provider
                """,
                    (current_month, provider),
                )
            else:
                cursor.execute(
                    """
                    SELECT provider, SUM(cost_usd)
                    FROM llm_requests
                    WHERE strftime('%Y-%m', timestamp) = ?
                    GROUP BY provider
                """,
                    (current_month,),
                )

            results = cursor.fetchall()

        spending = {row[0]: row[1] for row in results}

        logger.debug("Monthly spending retrieved", month=current_month, spending=spending)

        return spending

    def get_total_spending(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        provider: str | None = None,
    ) -> float:
        """Get total spending in date range.

        Args:
            start_date: Start date (default: beginning of time)
            end_date: End date (default: now)
            provider: Filter by provider

        Returns:
            Total spending in USD
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            conditions = []
            params = []

            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date.isoformat())

            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date.isoformat())

            if provider:
                conditions.append("provider = ?")
                params.append(provider)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            cursor.execute(
                f"""
                SELECT SUM(cost_usd)
                FROM llm_requests
                WHERE {where_clause}
            """,
                tuple(params),
            )

            result = cursor.fetchone()

        total = result[0] if result and result[0] else 0.0

        logger.debug(
            "Total spending retrieved",
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            total_usd=total,
        )

        return total

    def get_request_stats(
        self,
        days: int = 30,
        provider: str | None = None,
    ) -> dict[str, any]:
        """Get aggregated statistics for recent requests.

        Args:
            days: Number of days to look back
            provider: Filter by provider

        Returns:
            Statistics dict with totals, averages, and breakdowns
        """
        start_date = datetime.now() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Overall stats
            conditions = ["timestamp >= ?"]
            params = [start_date.isoformat()]

            if provider:
                conditions.append("provider = ?")
                params.append(provider)

            where_clause = " AND ".join(conditions)

            cursor.execute(
                f"""
                SELECT
                    COUNT(*) as total_requests,
                    SUM(tokens_total) as total_tokens,
                    SUM(cost_usd) as total_cost,
                    AVG(cost_usd) as avg_cost_per_request,
                    AVG(latency_ms) as avg_latency_ms,
                    SUM(CASE WHEN fallback_used = 1 THEN 1 ELSE 0 END) as fallback_count
                FROM llm_requests
                WHERE {where_clause}
            """,
                tuple(params),
            )

            row = cursor.fetchone()

            # Per-provider breakdown
            cursor.execute(
                f"""
                SELECT
                    provider,
                    COUNT(*) as requests,
                    SUM(tokens_total) as tokens,
                    SUM(cost_usd) as cost
                FROM llm_requests
                WHERE {where_clause}
                GROUP BY provider
            """,
                tuple(params),
            )

            provider_breakdown = [
                {
                    "provider": row[0],
                    "requests": row[1],
                    "tokens": row[2],
                    "cost_usd": row[3],
                }
                for row in cursor.fetchall()
            ]

            # Per-task-type breakdown
            cursor.execute(
                f"""
                SELECT
                    task_type,
                    COUNT(*) as requests,
                    SUM(tokens_total) as tokens,
                    SUM(cost_usd) as cost,
                    AVG(latency_ms) as avg_latency
                FROM llm_requests
                WHERE {where_clause}
                GROUP BY task_type
            """,
                tuple(params),
            )

            task_breakdown = [
                {
                    "task_type": row[0],
                    "requests": row[1],
                    "tokens": row[2],
                    "cost_usd": row[3],
                    "avg_latency_ms": row[4],
                }
                for row in cursor.fetchall()
            ]

        stats = {
            "period_days": days,
            "total_requests": row[0] or 0,
            "total_tokens": row[1] or 0,
            "total_cost_usd": row[2] or 0.0,
            "avg_cost_per_request_usd": row[3] or 0.0,
            "avg_latency_ms": row[4] or 0.0,
            "fallback_count": row[5] or 0,
            "provider_breakdown": provider_breakdown,
            "task_breakdown": task_breakdown,
        }

        logger.info("Request statistics retrieved", days=days, provider=provider, stats=stats)

        return stats

    def export_to_csv(self, output_path: Path, days: int | None = None) -> None:
        """Export cost data to CSV.

        Args:
            output_path: Output CSV file path
            days: Number of days to export (None = all)
        """
        import csv

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if days:
                start_date = datetime.now() - timedelta(days=days)
                cursor.execute(
                    """
                    SELECT * FROM llm_requests
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                """,
                    (start_date.isoformat(),),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM llm_requests
                    ORDER BY timestamp DESC
                """
                )

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        logger.info("Cost data exported to CSV", output_path=str(output_path), rows=len(rows))
