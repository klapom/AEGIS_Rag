"""Test the metadata cleanup to see actual sizes."""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from llama_index.core import SimpleDirectoryReader

from src.components.vector_search.ingestion import DocumentIngestionPipeline


def main():
    """Test metadata cleanup."""

    # The file that caused the 618-byte metadata
    pptx_file = Path("data/sample_documents/1. Basic Admin/Email Gateway/DE-D-EGW.pptx")

    print("=" * 80)
    print("METADATA CLEANUP TEST")
    print("=" * 80)
    print(f"File: {pptx_file}")
    print()

    # Load document
    reader = SimpleDirectoryReader(input_files=[str(pptx_file.resolve())], recursive=False)
    documents = reader.load_data()

    # Find the problematic part (part 12)
    if len(documents) > 12:
        doc = documents[12]
    else:
        doc = documents[0]

    print(f"Testing document part: {doc.doc_id}")
    print(f"Content length: {len(doc.get_content())} chars")
    print()

    # Original metadata
    original_metadata = doc.metadata
    original_size = len(json.dumps(original_metadata))

    print("ORIGINAL METADATA:")
    print(f"  Size: {original_size} bytes")
    print(f"  Keys: {list(original_metadata.keys())}")
    print()

    # Test cleanup
    pipeline = DocumentIngestionPipeline()
    cleaned_metadata = pipeline._clean_metadata(original_metadata)
    cleaned_size = len(json.dumps(cleaned_metadata))

    print("CLEANED METADATA:")
    print(f"  Size: {cleaned_size} bytes")
    print(f"  Keys: {list(cleaned_metadata.keys())}")
    print()

    print("Full cleaned metadata:")
    print(json.dumps(cleaned_metadata, indent=2, ensure_ascii=False))
    print()

    print("=" * 80)
    print(
        f"Reduction: {original_size - cleaned_size} bytes ({(1 - cleaned_size/original_size)*100:.1f}%)"
    )
    print(f"Fits in 512-token chunk: {'YES' if cleaned_size < 400 else 'NO - still too large'}")

    if cleaned_size >= 400:
        print()
        print("Still too large! Let's see which fields are biggest:")
        for key, value in cleaned_metadata.items():
            field_size = len(json.dumps({key: value}))
            if field_size > 50:
                print(f"  - {key}: {field_size} bytes")
                if isinstance(value, str) and len(value) > 100:
                    print(f"    Preview: {value[:100]}...")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
