"""Debug script to analyze full Docling JSON structure."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.components.ingestion.docling_client import DoclingContainerClient


async def analyze_json_structure():
    """Analyze the full JSON structure of a parsed document."""
    sample_dir = Path(r"C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\data\sample_documents")
    pptx_file = sample_dir / "99_pptx_text" / "PerformanceTuning_textonly.pptx"

    print(f"Parsing: {pptx_file}")
    print("=" * 80)

    client = DoclingContainerClient()
    parsed = await client.parse_document(pptx_file)

    json_content = parsed.json_content

    print("\nTop-level keys in json_content:")
    for key in sorted(json_content.keys()):
        value = json_content[key]
        if isinstance(value, list):
            print(f"  - {key}: list[{len(value)}]")
        elif isinstance(value, dict):
            print(f"  - {key}: dict[{len(value)} keys]")
        else:
            print(f"  - {key}: {type(value).__name__} = {str(value)[:50]}")

    # Check 'groups' - this is likely where the actual content is
    if "groups" in json_content:
        groups = json_content["groups"]
        print(f"\n\n'groups' structure ({len(groups)} items):")
        print("-" * 80)
        for i, group in enumerate(groups[:10]):  # First 10
            label = group.get("label", "<no label>")
            text = group.get("text", "")[:50].replace("\n", "\\n") if group.get("text") else ""
            name = group.get("name", "")
            children_count = len(group.get("children", []))
            print(f"  [{i}]: label='{label}', name='{name}', text='{text}', children={children_count}")

    # Check 'texts' - might have the actual text content
    if "texts" in json_content:
        texts = json_content["texts"]
        print(f"\n\n'texts' structure ({len(texts)} items):")
        print("-" * 80)
        for i, text_item in enumerate(texts[:10]):  # First 10
            label = text_item.get("label", "<no label>")
            text = text_item.get("text", "")[:50].replace("\n", "\\n") if text_item.get("text") else ""
            parent = text_item.get("parent", {})
            if isinstance(parent, dict):
                parent_ref = parent.get("$ref", str(parent))
            else:
                parent_ref = str(parent)
            print(f"  [{i}]: label='{label}', text='{text}', parent='{parent_ref}'")

    # Check 'pictures' and 'tables'
    for key in ["pictures", "tables", "key_value_items", "form_items", "list_items"]:
        if key in json_content:
            items = json_content[key]
            print(f"\n'{key}': {len(items)} items")

    # Dump a sample group for detailed inspection
    if "groups" in json_content and json_content["groups"]:
        print("\n\nFirst group detailed structure:")
        print("-" * 80)
        print(json.dumps(json_content["groups"][0], indent=2, default=str)[:2000])

    # Dump a sample text for detailed inspection
    if "texts" in json_content and json_content["texts"]:
        print("\n\nFirst text detailed structure:")
        print("-" * 80)
        print(json.dumps(json_content["texts"][0], indent=2, default=str)[:2000])


if __name__ == "__main__":
    asyncio.run(analyze_json_structure())
