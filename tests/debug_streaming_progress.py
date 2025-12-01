"""Debug script to test streaming progress updates.

Run with: poetry run python tests/debug_streaming_progress.py
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def test_streaming_progress():
    """Test the run_ingestion_pipeline_streaming function directly."""
    from src.components.ingestion.langgraph_pipeline import run_ingestion_pipeline_streaming

    # Use a sample PDF file
    test_file = r"C:\Projekte\AEGISRAG\data\sample_documents\12. BPMN-Foundation\DE-D-BPMN-Handout-A4.pdf"

    if not os.path.exists(test_file):
        print(f"ERROR: Test file not found: {test_file}")
        # Try to find any PDF in sample_documents
        sample_dir = r"C:\Projekte\AEGISRAG\data\sample_documents"
        if os.path.exists(sample_dir):
            for root, dirs, files in os.walk(sample_dir):
                for f in files:
                    if f.endswith(".pdf"):
                        test_file = os.path.join(root, f)
                        print(f"Found alternative test file: {test_file}")
                        break
                if os.path.exists(test_file) and test_file.endswith(".pdf"):
                    break

    print(f"\n{'='*60}")
    print(f"Testing run_ingestion_pipeline_streaming()")
    print(f"File: {test_file}")
    print(f"{'='*60}\n")

    try:
        update_count = 0
        async for update in run_ingestion_pipeline_streaming(
            document_path=test_file,
            document_id="debug_test_001",
            batch_id="debug_batch_001",
            batch_index=0,
            total_documents=1,
        ):
            update_count += 1
            node = update.get("node", "unknown")
            progress = update.get("progress", 0.0)
            state = update.get("state", {})

            # Extract some state info
            errors = state.get("errors", [])
            chunks = len(state.get("chunks", []))
            entities = len(state.get("entities", []))

            print(f"[{update_count}] Node: {node:30} | Progress: {progress:6.1%} | Chunks: {chunks} | Entities: {entities}")

            if errors:
                print(f"    ERRORS: {errors}")

        print(f"\n{'='*60}")
        print(f"TOTAL UPDATES RECEIVED: {update_count}")
        print(f"{'='*60}\n")

        if update_count < 5:
            print("WARNING: Expected at least 5-6 updates (one per pipeline node)")
            print("The streaming function may not be yielding correctly!")
        else:
            print("SUCCESS: Multiple updates received, streaming is working!")

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_streaming_progress())
