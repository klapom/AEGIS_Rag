"""Inspect document metadata to understand the oversized metadata issue."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json

from llama_index.core import SimpleDirectoryReader


def main():
    """Inspect metadata of the problematic PPTX file."""

    # The file that caused the error
    pptx_file = Path("data/sample_documents/1. Basic Admin/Email Gateway/DE-D-EGW-Exercise.pptx")

    print("=" * 80)
    print("METADATA INSPECTION")
    print("=" * 80)
    print(f"File: {pptx_file}")
    print()

    if not pptx_file.exists():
        print(f"[ERROR] File not found: {pptx_file}")
        return 1

    print("[1/2] Loading document...")
    reader = SimpleDirectoryReader(input_files=[str(pptx_file.resolve())], recursive=False)
    documents = reader.load_data()
    print(f"  [OK] Loaded {len(documents)} document parts")
    print()

    print("[2/2] Analyzing metadata...")
    print()

    for i, doc in enumerate(documents[:5]):  # Show first 5 parts
        print(f"--- Document Part {i} ---")
        print(f"Document ID: {doc.doc_id}")
        print(f"Content Length: {len(doc.get_content())} chars")
        print()

        # Show metadata
        print(f"Metadata Keys: {list(doc.metadata.keys())}")
        print()

        # Calculate metadata size
        metadata_str = json.dumps(doc.metadata)
        metadata_size = len(metadata_str)
        print(f"Metadata Size: {metadata_size} bytes")
        print()

        # Show full metadata
        print("Full Metadata:")
        print(json.dumps(doc.metadata, indent=2, ensure_ascii=False))
        print()

        # Check if this would cause the error
        if metadata_size > 512:
            print(f"[WARNING] Metadata size ({metadata_size}) > chunk_size (512)")
            print("This document part would cause the 'Metadata length > chunk size' error!")
        print()
        print("=" * 80)
        print()

    if len(documents) > 5:
        print(f"... and {len(documents) - 5} more document parts (not shown)")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
