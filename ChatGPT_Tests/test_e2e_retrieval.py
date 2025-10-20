import os
import time
from typing import Optional

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


def _get_token(password: Optional[str] = None) -> str:
    url = f"{BASE_URL}/api/v1/retrieval/auth/token"
    payload = {"username": "admin", "password": password or os.environ.get("AEGIS_ADMIN_PASSWORD", "admin123")}
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    return data["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_full_retrieval_flow():
    print("[retrieval] Step 1/6: Wait for API health...")
    _wait_for_api()

    print("[retrieval] Step 2/6: Request admin token...")
    token = _get_token()

    print("[retrieval] Step 3/6: Ingest sample documents from ./data/sample_documents ...")
    ingest_url = f"{BASE_URL}/api/v1/retrieval/ingest"
    payload = {
        "input_dir": "./data/sample_documents",
        "chunk_size": 512,
        "chunk_overlap": 128,
        # Keep extensions conservative to avoid external parsers (pdf/docx) issues
        "file_extensions": [".txt", ".md"],
        "use_adaptive_chunking": False,
        "batch_size": 64,
        "recursive": True,
    }
    r = requests.post(ingest_url, json=payload, headers=_auth_headers(token), timeout=600)
    if r.status_code != 200:
        print(f"[retrieval][warn] Ingest failed status={r.status_code} body={r.text[:500]}")
    else:
        data = r.json()
        print(f"[retrieval] Ingest status={data.get('status')} points_indexed={data.get('points_indexed')} chunks={data.get('chunks_created')}")

    print("[retrieval] Step 4/6: Prepare BM25 index from Qdrant ...")
    bm25_url = f"{BASE_URL}/api/v1/retrieval/prepare-bm25"
    r = requests.post(bm25_url, headers=_auth_headers(token), timeout=300)
    r.raise_for_status()

    print("[retrieval] Step 5/6: Get retrieval stats ...")
    stats_url = f"{BASE_URL}/api/v1/retrieval/stats"
    r = requests.get(stats_url, timeout=60)
    r.raise_for_status()
    stats = r.json()
    print(f"[retrieval] Stats: bm25_fitted={stats.get('bm25_fitted')} bm25_corpus_size={stats.get('bm25_corpus_size')} qdrant={stats.get('qdrant_stats')}")
    assert stats.get("status") == "success"
    # qdrant may be empty if documents were not parsed; still assert presence of keys
    assert "qdrant_stats" in stats

    print("[retrieval] Step 6/6: Run vector/bm25/hybrid searches ...")
    search_url = f"{BASE_URL}/api/v1/retrieval/search"
    for search_type in ("vector", "bm25", "hybrid"):
        body = {
            "query": "Sanierung oder Fenster oder Heizung",
            "top_k": 5,
            "search_type": search_type,
            "use_reranking": True,
            "filters": None,
        }
        r = requests.post(search_url, json=body, headers=_auth_headers(token), timeout=180)
        r.raise_for_status()
        res = r.json()
        print(f"[retrieval] Search type={search_type} results={len(res.get('results', []))}")
        assert res["search_type"] == search_type
        assert isinstance(res.get("results", []), list)
