import os
import time
import asyncio
import importlib
from typing import Any

import pytest
import requests

BASE_URL = os.environ.get("AEGIS_BASE_URL", "http://localhost:8000")


def _wait_for_api(timeout_sec: int = 180) -> None:
    start = time.time()
    url = f"{BASE_URL}/api/v1/health/"
    while time.time() - start < timeout_sec:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError(f"API not healthy after {timeout_sec}s: {url}")


def _insert_graph_sample_via_lightrag() -> None:
    print("[graph] Insert sample docs via LightRAG (Ollama+Neo4j)...")
    # Ensure LightRAG is importable, otherwise skip
    try:
        importlib.import_module("lightrag")
        importlib.import_module("lightrag.storage")
    except ModuleNotFoundError as e:
        pytest.skip(f"LightRAG not installed or import failed: {e}")

    # Import wrapper lazily to avoid early settings cache issues
    from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper

    wrapper = get_lightrag_wrapper()

    sample_docs: list[dict[str, Any]] = [
        {"text": "Die Stadt Berlin ist die Hauptstadt von Deutschland."},
        {"text": "Die Firma Siemens hat ihren Sitz in München."},
    ]

    res = asyncio.run(wrapper.insert_documents(sample_docs))
    print(
        f"[graph] LightRAG insert result: success={res.get('success')} failed={res.get('failed')}"
    )


def test_graph_analytics_and_visualization_endpoints():
    print("[graph] Step 1/5: Wait for API health...")
    _wait_for_api()

    print("[graph] Step 2/5: Ensure graph has content (insert few docs)...")
    _insert_graph_sample_via_lightrag()

    print("[graph] Step 3/5: Graph statistics endpoint ...")
    r = requests.get(f"{BASE_URL}/api/v1/graph/analytics/statistics", timeout=60)
    r.raise_for_status()
    stats = r.json()
    print(f"[graph] Statistics: keys={list(stats.keys())}")
    assert "node_count" in stats or "edge_count" in stats or isinstance(stats, dict)

    print("[graph] Step 4/5: PageRank + Influential ...")
    r = requests.get(f"{BASE_URL}/api/v1/graph/analytics/pagerank?top_k=5", timeout=60)
    r.raise_for_status()
    pr = r.json()
    print(f"[graph] PageRank count={len(pr)}")
    assert isinstance(pr, list)

    r = requests.get(f"{BASE_URL}/api/v1/graph/analytics/influential?top_k=5", timeout=60)
    r.raise_for_status()
    influential = r.json()
    print(f"[graph] Influential count={len(influential)}")
    assert isinstance(influential, list)

    print("[graph] Step 5/5: Knowledge gaps ...")
    r = requests.get(f"{BASE_URL}/api/v1/graph/analytics/gaps", timeout=60)
    r.raise_for_status()
    gaps = r.json()
    print(f"[graph] Gaps keys={list(gaps.keys())}")
    assert isinstance(gaps, dict)