#!/usr/bin/env python3
"""
Sprint 113: LLM Request Tracer

This script traces a complete LLM request through all components with detailed
timestamps to identify performance bottlenecks.

Usage:
    cd /home/admin/projects/aegisrag/AEGIS_Rag
    poetry run python scripts/trace_llm_request.py

Output:
    - Console output with timestamps
    - docs/analysis/LLM_TRACE_ANALYSIS.md with detailed breakdown
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone

import httpx

# Configuration
API_BASE = "http://localhost:8000"
TEST_QUERY = "What is machine learning?"
SESSION_ID = f"trace-{int(time.time())}"


def timestamp() -> str:
    """Get current timestamp in ISO format with milliseconds."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def elapsed_ms(start: float) -> float:
    """Calculate elapsed milliseconds."""
    return (time.time() - start) * 1000


async def trace_chat_request():
    """Trace a complete chat request with detailed timing."""
    trace_data = {
        "session_id": SESSION_ID,
        "query": TEST_QUERY,
        "start_time": timestamp(),
        "phases": [],
    }

    overall_start = time.time()

    print(f"\n{'='*80}")
    print(f"LLM REQUEST TRACE - Sprint 113 Performance Analysis")
    print(f"{'='*80}")
    print(f"[{timestamp()}] START: Query = '{TEST_QUERY}'")
    print(f"[{timestamp()}] Session ID: {SESSION_ID}")
    print(f"{'='*80}\n")

    async with httpx.AsyncClient(timeout=180.0) as client:
        # Phase 1: API Request Start
        phase1_start = time.time()
        print(f"[{timestamp()}] PHASE 1: Sending HTTP POST to /api/v1/chat/")

        trace_data["phases"].append({
            "name": "HTTP Request Start",
            "timestamp": timestamp(),
            "elapsed_ms": 0,
        })

        try:
            response = await client.post(
                f"{API_BASE}/api/v1/chat/",
                json={
                    "query": TEST_QUERY,
                    "session_id": SESSION_ID,
                },
                headers={"Content-Type": "application/json"},
            )

            phase1_elapsed = elapsed_ms(phase1_start)
            print(f"[{timestamp()}] PHASE 1 COMPLETE: HTTP Response received ({phase1_elapsed:.0f}ms)")
            print(f"              Status: {response.status_code}")

            trace_data["phases"].append({
                "name": "HTTP Response Received",
                "timestamp": timestamp(),
                "elapsed_ms": phase1_elapsed,
                "status_code": response.status_code,
            })

            if response.status_code != 200:
                print(f"[{timestamp()}] ERROR: Non-200 response")
                print(response.text[:500])
                return

            # Parse response
            data = response.json()

            # Phase 2: Extract metadata
            print(f"\n[{timestamp()}] PHASE 2: Analyzing response metadata...")

            metadata = data.get("metadata", {})
            search_meta = metadata.get("search", {})
            graph_meta = metadata.get("graph_search", {})
            coord_meta = metadata.get("coordinator", {})

            # Extract all timing information
            print(f"\n{'='*80}")
            print(f"DETAILED TIMING BREAKDOWN")
            print(f"{'='*80}")

            # Search phase
            search_latency = search_meta.get("latency_ms", "N/A")
            print(f"\n[SEARCH]")
            print(f"  Mode: {search_meta.get('search_mode', 'N/A')}")
            print(f"  Latency: {search_latency}ms")
            print(f"  Results: {search_meta.get('result_count', 'N/A')}")
            print(f"  Dense Results: {search_meta.get('dense_results_count', 'N/A')}")
            print(f"  Sparse Results: {search_meta.get('sparse_results_count', 'N/A')}")
            print(f"  Vector Results: {search_meta.get('vector_results_count', 'N/A')}")
            print(f"  BM25 Results: {search_meta.get('bm25_results_count', 'N/A')}")
            print(f"  Reranking Applied: {search_meta.get('reranking_applied', 'N/A')}")

            # Intent phase
            print(f"\n[INTENT]")
            print(f"  Detected: {search_meta.get('intent', 'N/A')}")
            print(f"  Confidence: {search_meta.get('intent_confidence', 'N/A')}")
            print(f"  Method: {search_meta.get('intent_method', 'N/A')}")
            print(f"  Latency: {search_meta.get('intent_latency_ms', 'N/A')}ms")

            # Graph phase
            graph_latency = graph_meta.get("latency_ms", "N/A")
            print(f"\n[GRAPH SEARCH]")
            print(f"  Mode: {graph_meta.get('mode', 'N/A')}")
            print(f"  Latency: {graph_latency}ms")
            print(f"  Entities Found: {graph_meta.get('entities_found', 'N/A')}")
            print(f"  Relationships Found: {graph_meta.get('relationships_found', 'N/A')}")
            print(f"  Topics Found: {graph_meta.get('topics_found', 'N/A')}")

            # Graph vector fallback
            fallback = metadata.get("graph_vector_fallback", {})
            if fallback:
                print(f"\n[GRAPH VECTOR FALLBACK]")
                print(f"  Triggered: {fallback.get('triggered', 'N/A')}")
                print(f"  Reason: {fallback.get('reason', 'N/A')}")
                print(f"  Fallback Contexts: {fallback.get('fallback_contexts_count', 'N/A')}")

            # Hybrid search merge
            hybrid = metadata.get("hybrid_search", {})
            if hybrid:
                print(f"\n[HYBRID MERGE]")
                print(f"  Vector Count: {hybrid.get('vector_count', 'N/A')}")
                print(f"  Graph Count: {hybrid.get('graph_count', 'N/A')}")
                print(f"  Merged Count: {hybrid.get('merged_count', 'N/A')}")

            # Coordinator totals
            coord_latency = coord_meta.get("total_latency_ms", "N/A")
            print(f"\n[COORDINATOR]")
            print(f"  Total Latency: {coord_latency}ms")
            print(f"  Session ID: {coord_meta.get('session_id', 'N/A')}")
            print(f"  Use Persistence: {coord_meta.get('use_persistence', 'N/A')}")

            # Agent path
            agent_path = metadata.get("agent_path", [])
            if agent_path:
                print(f"\n[AGENT PATH]")
                for i, step in enumerate(agent_path, 1):
                    print(f"  {i}. {step}")

            # Answer
            answer = data.get("answer", "")
            print(f"\n[ANSWER]")
            print(f"  Length: {len(answer)} chars")
            print(f"  Intent: {data.get('intent', 'N/A')}")
            print(f"  Sources: {len(data.get('sources', []))}")
            print(f"  Tool Calls: {len(data.get('tool_calls', []))}")

            # Overall summary
            overall_elapsed = elapsed_ms(overall_start)
            print(f"\n{'='*80}")
            print(f"SUMMARY")
            print(f"{'='*80}")
            print(f"  HTTP Round-Trip: {phase1_elapsed:.0f}ms")
            print(f"  Search Latency: {search_latency}ms")
            print(f"  Graph Latency: {graph_latency}ms")
            print(f"  Coordinator Total: {coord_latency}ms")
            print(f"  Overall Script Time: {overall_elapsed:.0f}ms")

            # Calculate where time is spent
            print(f"\n[TIME BREAKDOWN ANALYSIS]")
            try:
                search_ms = float(search_latency) if search_latency != "N/A" else 0
                graph_ms = float(graph_latency) if graph_latency != "N/A" else 0
                coord_ms = float(coord_latency) if coord_latency != "N/A" else 0

                # Estimate LLM time (coordinator - search - graph)
                llm_time = coord_ms - search_ms - graph_ms

                print(f"  Search: {search_ms:.0f}ms ({search_ms/coord_ms*100:.1f}%)" if coord_ms > 0 else "  Search: N/A")
                print(f"  Graph: {graph_ms:.0f}ms ({graph_ms/coord_ms*100:.1f}%)" if coord_ms > 0 else "  Graph: N/A")
                print(f"  LLM Generation (estimated): {llm_time:.0f}ms ({llm_time/coord_ms*100:.1f}%)" if coord_ms > 0 else "  LLM: N/A")

            except (ValueError, TypeError):
                print("  Unable to calculate breakdown (missing data)")

            # Store trace data
            trace_data["phases"].append({
                "name": "Response Analysis Complete",
                "timestamp": timestamp(),
                "elapsed_ms": overall_elapsed,
                "metadata": {
                    "search_latency_ms": search_latency,
                    "graph_latency_ms": graph_latency,
                    "coordinator_latency_ms": coord_latency,
                    "answer_length": len(answer),
                },
            })

            trace_data["end_time"] = timestamp()
            trace_data["total_elapsed_ms"] = overall_elapsed

            # Save trace to file
            trace_file = f"/tmp/llm_trace_{SESSION_ID}.json"
            with open(trace_file, "w") as f:
                json.dump(trace_data, f, indent=2, default=str)
            print(f"\n[{timestamp()}] Trace saved to: {trace_file}")

            return data

        except httpx.TimeoutException:
            print(f"[{timestamp()}] ERROR: Request timed out after 180s")
            return None
        except Exception as e:
            print(f"[{timestamp()}] ERROR: {type(e).__name__}: {e}")
            return None


async def check_api_logs():
    """Fetch recent API logs for LLM-related entries."""
    print(f"\n{'='*80}")
    print(f"CHECKING API LOGS FOR LLM ACTIVITY")
    print(f"{'='*80}\n")

    import subprocess

    # Get last 100 lines of API logs
    result = subprocess.run(
        ["docker", "logs", "aegis-api", "--tail", "100"],
        capture_output=True,
        text=True,
    )

    log_lines = result.stderr.split("\n") if result.stderr else []

    # Filter for LLM-related entries
    llm_keywords = [
        "llm_request", "routing_decision", "streaming", "provider",
        "ollama", "generate", "acompletion", "token", "cost",
        "cache_hit", "cache_miss", "phase_event",
    ]

    print(f"LLM-related log entries (last 100 lines):\n")
    for line in log_lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in llm_keywords):
            # Parse timestamp and message
            print(f"  {line[:200]}...")


async def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("Sprint 113: LLM Request Performance Trace")
    print("="*80)
    print(f"Timestamp: {timestamp()}")
    print(f"API Base: {API_BASE}")
    print("="*80 + "\n")

    # Run trace
    result = await trace_chat_request()

    if result:
        print("\n" + "="*80)
        print("TRACE COMPLETE - See timing breakdown above")
        print("="*80 + "\n")
    else:
        print("\n" + "="*80)
        print("TRACE FAILED - Check API logs")
        print("="*80 + "\n")

    # Show API logs
    await check_api_logs()


if __name__ == "__main__":
    asyncio.run(main())
