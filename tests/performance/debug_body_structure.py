"""Debug script to analyze Docling JSON body structure."""

import asyncio
import json

# Import directly to avoid pipeline overhead
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.components.ingestion.docling_client import DoclingContainerClient


async def analyze_body_structure():
    """Analyze the body structure of a parsed document."""
    # Use a sample document
    sample_dir = Path(
        r"C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\data\sample_documents"
    )
    pptx_file = sample_dir / "99_pptx_text" / "PerformanceTuning_textonly.pptx"

    if not pptx_file.exists():
        print(f"ERROR: File not found: {pptx_file}")
        return

    print(f"Parsing: {pptx_file}")
    print("=" * 80)

    client = DoclingContainerClient()
    try:
        parsed = await client.parse_document(pptx_file)

        print("\nDoclingParsedDocument attributes:")
        print(f"  - has .body: {hasattr(parsed, 'body')}")
        print(f"  - has .document: {hasattr(parsed, 'document')}")
        print(f"  - .body is None: {parsed.body is None}")
        print(f"  - type of .body: {type(parsed.body)}")

        body = parsed.body
        if body is None:
            print("\nERROR: body is None!")
            return

        print("\n\nBody structure (top-level keys):")
        if isinstance(body, dict):
            for key in body:
                print(f"  - {key}: {type(body[key])}")

        # Recursively analyze the body
        def analyze_node(node, depth=0, path="root"):
            """Recursively analyze node structure."""
            indent = "  " * depth

            if isinstance(node, dict):
                # Get label if present
                label = node.get("label", "<no label>")
                text_preview = node.get("text", "")[:50] if node.get("text") else ""
                children_count = len(node.get("children", []))

                print(
                    f"{indent}{path}: label='{label}', text='{text_preview}...', children={children_count}"
                )

                # Recurse into children
                for i, child in enumerate(node.get("children", [])):
                    analyze_node(child, depth + 1, f"child[{i}]")
            else:
                print(f"{indent}{path}: type={type(node)}, value={str(node)[:50]}...")

        print("\n\nBody tree structure (first 50 nodes):")
        print("-" * 80)

        nodes_printed = [0]  # Use list to allow mutation in nested function
        max_nodes = 50

        def limited_analyze(node, depth=0, path="root"):
            if nodes_printed[0] >= max_nodes:
                return
            nodes_printed[0] += 1

            indent = "  " * depth

            if isinstance(node, dict):
                label = node.get("label", "<no label>")
                text = node.get("text", "")
                text_preview = text[:40].replace("\n", "\\n") if text else ""
                children_count = len(node.get("children", []))
                has_prov = "prov" in node

                print(
                    f"{indent}{path}: label='{label}', text='{text_preview}', children={children_count}, prov={has_prov}"
                )

                for i, child in enumerate(node.get("children", [])):
                    limited_analyze(child, depth + 1, f"[{i}]")
            else:
                print(f"{indent}{path}: {type(node).__name__} = {str(node)[:40]}...")

        limited_analyze(body)

        # Also dump first child for detailed inspection
        if isinstance(body, dict) and body.get("children"):
            print("\n\nFirst child detailed structure:")
            print("-" * 80)
            first_child = body["children"][0] if body["children"] else None
            if first_child:
                print(json.dumps(first_child, indent=2, default=str)[:2000])

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(analyze_body_structure())
