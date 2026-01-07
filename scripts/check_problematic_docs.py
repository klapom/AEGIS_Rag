"""Check for documents with problematic characters that might break JSON."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import AsyncQdrantClient


async def main():
    client = AsyncQdrantClient(host="localhost", port=6333, prefer_grpc=True)

    # Get first 5 documents from default namespace
    results = await client.scroll(
        collection_name="documents_v1",
        scroll_filter={
            "must": [
                {"key": "namespace_id", "match": {"value": "default"}}
            ]
        },
        limit=5,
        with_payload=True,
    )

    print("📄 Checking first 5 documents for problematic characters...\n")

    for i, point in enumerate(results[0], 1):
        text = point.payload.get("text", "")
        doc_id = point.payload.get("document_id", "unknown")

        # Check for problematic characters
        problems = []
        quote_count = text.count('"')
        if quote_count > 0:
            problems.append(f"Double quotes: {quote_count} found")
        single_quote_count = text.count("'")
        if single_quote_count > 0:
            problems.append(f"Single quotes: {single_quote_count} found")
        newline_count = text.count("\n")
        if newline_count > 0:
            problems.append(f"Newlines: {newline_count} found")
        if "{" in text or "}" in text:
            problems.append(f"Braces in text")

        print(f"Doc {i} ({doc_id[:30]}...):")
        print(f"  Length: {len(text)} chars")
        if problems:
            print(f"  ⚠️  Problems: {', '.join(problems)}")
        else:
            print(f"  ✅ No obvious problems")
        print(f"  Preview: {text[:150]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())
