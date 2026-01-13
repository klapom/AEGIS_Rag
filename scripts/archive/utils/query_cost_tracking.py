"""Query cost tracking database for Sprint 23 analysis."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "cost_tracking.db"

if not db_path.exists():
    print(f"Cost tracking database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("=" * 80)
print("COST TRACKING SUMMARY (Sprint 23)")
print("=" * 80)
print()

# Total by provider
cursor.execute(
    """
    SELECT
        provider,
        COUNT(*) as total_requests,
        ROUND(SUM(cost_usd), 6) as total_cost,
        ROUND(AVG(latency_ms), 2) as avg_latency_ms
    FROM llm_requests
    GROUP BY provider
    ORDER BY total_cost DESC
"""
)

print("By Provider:")
print("-" * 80)
for row in cursor.fetchall():
    provider, requests, cost, latency = row
    print(
        f"  {provider:20s} | Requests: {requests:4d} | Cost: ${cost:8.6f} | Avg Latency: {latency:6.2f}ms"
    )

print()

# Total by task type
cursor.execute(
    """
    SELECT
        task_type,
        COUNT(*) as total_requests,
        ROUND(SUM(cost_usd), 6) as total_cost
    FROM llm_requests
    GROUP BY task_type
    ORDER BY total_cost DESC
"""
)

print("By Task Type:")
print("-" * 80)
for row in cursor.fetchall():
    task_type, requests, cost = row
    print(f"  {task_type:20s} | Requests: {requests:4d} | Cost: ${cost:8.6f}")

print()

# Overall totals
cursor.execute(
    """
    SELECT
        COUNT(*) as total_requests,
        ROUND(SUM(cost_usd), 6) as total_cost,
        ROUND(SUM(tokens_input), 0) as total_tokens_input,
        ROUND(SUM(tokens_output), 0) as total_tokens_output
    FROM llm_requests
"""
)

row = cursor.fetchone()
total_requests, total_cost, tokens_in, tokens_out = row
print("Overall Totals:")
print("-" * 80)
print(f"  Total Requests:  {total_requests}")
print(f"  Total Cost:      ${total_cost:.6f}")
print(f"  Tokens Input:    {int(tokens_in):,}")
print(f"  Tokens Output:   {int(tokens_out):,}")
print(f"  Tokens Total:    {int(tokens_in + tokens_out):,}")
print()

# Recent requests
cursor.execute(
    """
    SELECT
        timestamp,
        provider,
        model,
        task_type,
        cost_usd,
        latency_ms
    FROM llm_requests
    ORDER BY timestamp DESC
    LIMIT 10
"""
)

print("Recent Requests (Last 10):")
print("-" * 80)
for row in cursor.fetchall():
    timestamp, provider, model, task_type, cost, latency = row
    print(f"  {timestamp} | {provider:15s} | {task_type:15s} | ${cost:.6f} | {latency:.2f}ms")

conn.close()

print()
print("=" * 80)
print(f"Database Location: {db_path}")
print("=" * 80)
