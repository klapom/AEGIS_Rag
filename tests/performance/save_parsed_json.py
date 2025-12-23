"""Save parsed Docling JSON to file for inspection."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.components.ingestion.docling_client import DoclingContainerClient


async def save_json():
    """Parse document and save full JSON to file."""
    sample_dir = Path(
        r"C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag\data\sample_documents"
    )
    pptx_file = sample_dir / "99_pptx_text" / "PerformanceTuning_textonly.pptx"

    print(f"Parsing: {pptx_file}")

    client = DoclingContainerClient()
    parsed = await client.parse_document(pptx_file)

    output_path = Path(__file__).parent / "results" / "docling_parsed_sample.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed.json_content, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n{'=' * 60}")
    print(f"JSON saved to: {output_path.absolute()}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(save_json())
