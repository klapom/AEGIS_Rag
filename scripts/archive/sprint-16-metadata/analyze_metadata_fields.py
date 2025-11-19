"""Analyze which metadata fields are valuable for RAG and which can be removed."""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from llama_index.core import SimpleDirectoryReader


def analyze_field_value(field_name: str, field_value, indent: int = 0) -> dict:
    """Analyze a metadata field's characteristics."""
    prefix = "  " * indent

    if isinstance(field_value, str):
        return {
            "type": "string",
            "length": len(field_value),
            "preview": field_value[:100] if len(field_value) > 100 else field_value,
        }
    elif isinstance(field_value, list):
        total_size = len(json.dumps(field_value))
        return {
            "type": "list",
            "count": len(field_value),
            "total_size": total_size,
            "example": field_value[0] if field_value else None,
        }
    elif isinstance(field_value, dict):
        total_size = len(json.dumps(field_value))
        return {"type": "dict", "keys": list(field_value.keys()), "total_size": total_size}
    else:
        return {"type": type(field_value).__name__, "value": str(field_value)}


def main():
    """Analyze PPTX metadata fields."""

    pptx_file = Path("data/sample_documents/1. Basic Admin/Email Gateway/DE-D-EGW-Exercise.pptx")

    print("=" * 80)
    print("PPTX METADATA FIELD ANALYSIS")
    print("=" * 80)
    print()

    # Load document
    reader = SimpleDirectoryReader(input_files=[str(pptx_file.resolve())], recursive=False)
    documents = reader.load_data()

    # Analyze first document part
    doc = documents[0]
    metadata = doc.metadata

    print(f"Analyzing {len(documents)} document parts...")
    print(f"First part metadata has {len(metadata)} fields")
    print()

    print("=" * 80)
    print("FIELD-BY-FIELD ANALYSIS")
    print("=" * 80)
    print()

    total_metadata_size = len(json.dumps(metadata))

    for field_name, field_value in metadata.items():
        field_size = len(json.dumps({field_name: field_value}))
        percentage = (field_size / total_metadata_size) * 100

        print(f"Field: {field_name}")
        print(f"  Size: {field_size} bytes ({percentage:.1f}% of total)")

        analysis = analyze_field_value(field_name, field_value)

        if analysis["type"] == "string":
            print(f"  Type: String ({analysis['length']} chars)")
            print(f"  Preview: {analysis['preview']}")
        elif analysis["type"] == "list":
            print(f"  Type: List with {analysis['count']} items")
            print(f"  Total size: {analysis['total_size']} bytes")
            if analysis["example"]:
                print(
                    f"  Example item keys: {list(analysis['example'].keys()) if isinstance(analysis['example'], dict) else type(analysis['example']).__name__}"
                )
        elif analysis["type"] == "dict":
            print(f"  Type: Dict with keys: {analysis['keys']}")
            print(f"  Total size: {analysis['total_size']} bytes")
        else:
            print(f"  Type: {analysis['type']}")
            print(f"  Value: {analysis['value']}")

        print()

    print("=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print()

    recommendations = {"KEEP": [], "SIMPLIFY": [], "REMOVE": []}

    # Analyze each field
    for field_name, field_value in metadata.items():
        field_size = len(json.dumps({field_name: field_value}))

        # Essential identification fields
        if field_name in ["file_name", "file_path", "page_label", "title"]:
            recommendations["KEEP"].append(
                {
                    "field": field_name,
                    "reason": "Essential for document identification and citation",
                    "size": field_size,
                }
            )

        # File metadata - useful but could be simplified
        elif field_name in ["file_type", "file_size", "creation_date", "last_modified_date"]:
            recommendations["KEEP"].append(
                {
                    "field": field_name,
                    "reason": "Useful file metadata (small size)",
                    "size": field_size,
                }
            )

        # Structure fields - very large, formatting details
        elif field_name in ["text_sections", "extraction_errors", "extraction_warnings"]:
            if field_size > 1000:
                recommendations["REMOVE"].append(
                    {
                        "field": field_name,
                        "reason": f"Too large ({field_size} bytes), contains formatting details not needed for RAG",
                        "size": field_size,
                    }
                )
            else:
                recommendations["SIMPLIFY"].append(
                    {
                        "field": field_name,
                        "reason": "Could be useful but needs simplification",
                        "size": field_size,
                    }
                )

        # Content arrays - could be useful but check size
        elif field_name in ["tables", "charts", "images", "notes"]:
            if field_size > 500:
                recommendations["SIMPLIFY"].append(
                    {
                        "field": field_name,
                        "reason": "Potentially useful but large - extract only essential info",
                        "size": field_size,
                    }
                )
            else:
                recommendations["KEEP"].append(
                    {
                        "field": field_name,
                        "reason": "Small size, could contain useful context",
                        "size": field_size,
                    }
                )

    print("Fields to KEEP (essential + small):")
    for item in recommendations["KEEP"]:
        print(f"  - {item['field']}: {item['reason']} ({item['size']} bytes)")
    print()

    print("Fields to SIMPLIFY (useful but too detailed):")
    for item in recommendations["SIMPLIFY"]:
        print(f"  - {item['field']}: {item['reason']} ({item['size']} bytes)")
    print()

    print("Fields to REMOVE (too large, not useful for RAG):")
    for item in recommendations["REMOVE"]:
        print(f"  - {item['field']}: {item['reason']} ({item['size']} bytes)")
    print()

    # Calculate savings
    keep_size = sum(item["size"] for item in recommendations["KEEP"])
    remove_size = sum(item["size"] for item in recommendations["REMOVE"])

    print("=" * 80)
    print(f"Original metadata size: {total_metadata_size} bytes")
    print(f"After cleanup (estimated): {keep_size} bytes")
    print(f"Reduction: {remove_size} bytes ({(remove_size/total_metadata_size)*100:.1f}%)")
    print(f"Fits in 512 token chunk: {'YES' if keep_size < 400 else 'NO (still too large)'}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
