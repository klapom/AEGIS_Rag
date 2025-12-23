"""Debug script to test Admin API streaming progress directly."""

import asyncio
import urllib.parse

import httpx


async def test_admin_api_stream():
    """Test the Admin API indexing/add streaming endpoint."""
    file_paths = [
        r"C:\Projekte\AEGISRAG\data\sample_documents\12. BPMN-Foundation\DE-D-BPMN-Handout-A4.pdf"
    ]

    print("\n" + "=" * 60)
    print("Testing Admin API /indexing/add streaming")
    print("=" * 60 + "\n")

    # Build URL with query params
    params = "&".join([f"file_paths={urllib.parse.quote(p)}" for p in file_paths])
    params += "&dry_run=false"
    url = f"http://localhost:8000/api/v1/admin/indexing/add?{params}"

    print(f"URL: {url[:100]}...")

    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", url) as response:
            print(f"Response status: {response.status_code}")
            if response.status_code != 200:
                content = await response.aread()
                print(f"Error: {content}")
                return

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    import json

                    try:
                        chunk = json.loads(data)
                        phase = chunk.get("phase", "?")
                        progress = chunk.get("progress_percent", 0)
                        message = chunk.get("message", "")[:80]
                        print(f"[{phase:15}] Progress: {progress:5.1f}% | {message}")
                    except:
                        print(f"RAW: {line[:100]}")


if __name__ == "__main__":
    asyncio.run(test_admin_api_stream())
