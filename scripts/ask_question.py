import os
import sys
from typing import Any

import httpx


BASE_URL = os.environ.get("AEGIS_BASE_URL", "http://localhost:8000")
ADMIN_PASSWORD = os.environ.get("AEGIS_ADMIN_PASSWORD", "admin123")


def get_token() -> str:
    url = f"{BASE_URL}/api/v1/retrieval/auth/token"
    payload = {"username": "admin", "password": ADMIN_PASSWORD}
    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()["access_token"]


def search(token: str, query: str, search_type: str = "hybrid", top_k: int = 5) -> dict[str, Any]:
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
            resp = search(token, query, search_type="hybrid", top_k=5)
            results = resp.get("results", [])
            print(f"\nAntwort-Vorschläge (top {len(results)}):")
            for i, item in enumerate(results, start=1):
                text = item.get("text", "")
                preview = text[:220].replace("\n", " ") + ("…" if len(text) > 220 else "")
                src = item.get("source") or item.get("document_id") or "?"
                score = item.get("score")
                print(f"{i}. score={score:.4f} src={src}\n   {preview}")
        except Exception as e:
            print(f"Fehler bei Suche: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

