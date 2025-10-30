"""Script to trigger re-indexing via Admin API with SSE progress tracking."""

import requests
import sys
from pathlib import Path

def trigger_reindex(input_dir: str):
    """Trigger re-indexing and display progress."""
    url = "http://127.0.0.1:8000/api/v1/admin/reindex"
    params = {
        "input_dir": input_dir,
        "confirm": "true"
    }

    print(f"Starting re-indexing for directory: {input_dir}")
    print(f"URL: {url}")
    print("=" * 80)

    try:
        response = requests.post(
            url,
            params=params,
            headers={"Accept": "text/event-stream"},
            stream=True,
            timeout=600
        )

        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return False

        # Process SSE stream
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    print(data_str)

        print("=" * 80)
        print("Re-indexing completed!")
        return True

    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        print("Make sure the API server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "data/sample_documents/30. GAC"
    success = trigger_reindex(input_dir)
    sys.exit(0 if success else 1)
