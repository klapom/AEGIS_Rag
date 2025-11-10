"""
Interactive Q&A Client for AEGIS RAG System.

Sprint Context: Sprint 7-8 (2025-10-19) - Query & Testing Infrastructure

This script provides a command-line interface to query the AEGIS RAG system
via HTTP API. It authenticates using admin credentials and supports hybrid
search with reranking.

Usage:
    python scripts/ask_question.py

    # With custom base URL
    AEGIS_BASE_URL=http://production:8000 python scripts/ask_question.py

Environment Variables:
    AEGIS_BASE_URL: API base URL (default: http://localhost:8000)
    AEGIS_ADMIN_PASSWORD: Admin password (default: admin123)

Features:
    - Token-based authentication
    - Hybrid search (vector + BM25)
    - Cross-encoder reranking
    - Interactive loop (type 'exit', 'quit', or ':q' to quit)
    - Result previews with scores and sources

Exit Codes:
    0: Success (user exit)
    1: Authentication failure

Example Session:
    $ python scripts/ask_question.py
    AEGIS RAG QA Client (BASE_URL=http://localhost:8000)
    Authenticated as admin. Type 'exit' to quit.

    Frage> Was ist AEGIS RAG?
    Antwort-Vorschläge (top 5):
    1. score=0.8523 src=README.md
       AEGIS RAG ist ein hybrides Retrieval-Augmented Generation System...
"""
import os
import sys
from typing import Any

import httpx


BASE_URL = os.environ.get("AEGIS_BASE_URL", "http://localhost:8000")
ADMIN_PASSWORD = os.environ.get("AEGIS_ADMIN_PASSWORD", "admin123")


def get_token() -> str:
    """Authenticate with AEGIS API and retrieve access token.

    Returns:
        str: JWT access token for API authentication

    Raises:
        httpx.HTTPStatusError: If authentication fails
    """
    url = f"{BASE_URL}/api/v1/retrieval/auth/token"
    payload = {"username": "admin", "password": ADMIN_PASSWORD}
    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()["access_token"]


def search(token: str, query: str, search_type: str = "hybrid", top_k: int = 5) -> dict[str, Any]:
    """Execute search query against AEGIS RAG API.

    Args:
        token: JWT access token from get_token()
        query: Natural language query string
        search_type: Search mode ("hybrid", "vector", or "bm25")
        top_k: Number of results to return

    Returns:
        dict: Search response containing results with text, score, and source

    Raises:
        httpx.HTTPStatusError: If search request fails
    """
    url = f"{BASE_URL}/api/v1/retrieval/search"
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "query": query,
        "top_k": top_k,
        "search_type": search_type,
        "use_reranking": True,
        "filters": None,
    }
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=body, headers=headers)
        r.raise_for_status()
        return r.json()


def main() -> int:
    """Main interactive Q&A loop.

    Authenticates with the API and enters an interactive query loop.
    Prints search results with scores and source information.

    Returns:
        int: Exit code (0 for success, 1 for auth failure)
    """
    print(f"AEGIS RAG QA Client (BASE_URL={BASE_URL})")
    try:
        token = get_token()
        print("Authenticated as admin. Type 'exit' to quit.")
    except Exception as e:
        print(f"Failed to authenticate: {e}")
        return 1

    while True:
        try:
            query = input("\nFrage> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0
        if not query or query.lower() in {"exit", "quit", ":q"}:
            print("Bye.")
            return 0

        try:
            # Execute hybrid search with reranking
            resp = search(token, query, search_type="hybrid", top_k=5)
            results = resp.get("results", [])
            print(f"\nAntwort-Vorschläge (top {len(results)}):")
            for i, item in enumerate(results, start=1):
                text = item.get("text", "")
                # Show first 220 chars as preview
                preview = text[:220].replace("\n", " ") + ("…" if len(text) > 220 else "")
                src = item.get("source") or item.get("document_id") or "?"
                score = item.get("score")
                print(f"{i}. score={score:.4f} src={src}\n   {preview}")
        except Exception as e:
            print(f"Fehler bei Suche: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

