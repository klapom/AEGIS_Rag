"""Debug script to inspect Docling image extraction.

Sprint 33 Fix: Debug why images aren't being extracted.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def debug_image_extraction():
    """Debug Docling image extraction."""
    print("=" * 70)
    print("SPRINT 33: DEBUG IMAGE EXTRACTION")
    print("=" * 70)

    # Test with a known image-containing document
    test_files = [
        Path(r"C:\Projekte\AEGISRAG\data\sample_documents\30. GAC\OMNITRACKER GDPR Anonymization Center GAC.pdf"),
        Path(r"C:\Projekte\AEGISRAG\data\sample_documents\1. Basic Admin\Web Gateway.pptx"),
    ]

    from src.components.ingestion.docling_client import DoclingClient

    client = DoclingClient()
    await client.start_container()

    for test_file in test_files:
        if not test_file.exists():
            print(f"[SKIP] File not found: {test_file}")
            continue

        print(f"\n[FILE] {test_file.name}")
        print("-" * 50)

        try:
            parsed = await client.parse_document(test_file)

            # Check md_content for base64 images
            md_content = parsed.md_content
            print(f"  md_content length: {len(md_content)} chars")

            # Look for base64 image patterns
            base64_pattern = r'!\[([^\]]*)\]\(data:image/([^;]+);base64,([^)]{0,100})'
            matches = list(re.finditer(base64_pattern, md_content))
            print(f"  Base64 images in MD: {len(matches)}")

            # Look for any image references
            img_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
            all_img_matches = list(re.finditer(img_pattern, md_content))
            print(f"  All image references: {len(all_img_matches)}")

            if all_img_matches[:5]:
                print("  First 5 image refs:")
                for m in all_img_matches[:5]:
                    alt = m.group(1)[:30]
                    src = m.group(2)[:80]
                    print(f"    - [{alt}]({src}...)")

            # Check json_content for pictures
            json_content = parsed.json_content
            json_pictures = json_content.get("pictures", [])
            print(f"  pictures in JSON: {len(json_pictures)}")

            # Check images list
            images_metadata = parsed.images
            print(f"  images metadata: {len(images_metadata)}")

            # Check pictures property (our fix)
            pictures = parsed.pictures
            print(f"  pictures property: {len(pictures)}")

            if pictures:
                print("  First 3 pictures:")
                for i, pic in enumerate(pictures[:3]):
                    img = pic.get_image()
                    print(f"    Picture {i}: {img.size} {img.mode}")
                    if pic.prov:
                        prov = pic.prov[0]
                        print(f"      page={prov.page_no}, bbox=({prov.bbox.l:.0f},{prov.bbox.t:.0f},{prov.bbox.r:.0f},{prov.bbox.b:.0f})")

            # Save a sample of md_content for inspection
            sample_file = Path(__file__).parent / "results" / f"debug_{test_file.stem}_md.txt"
            sample_file.parent.mkdir(exist_ok=True)
            with open(sample_file, "w", encoding="utf-8") as f:
                f.write(md_content[:50000])
            print(f"  MD sample saved to: {sample_file.name}")

            # Save json_content structure
            json_file = Path(__file__).parent / "results" / f"debug_{test_file.stem}_structure.json"
            structure = {
                "keys": list(json_content.keys()) if json_content else [],
                "pictures_count": len(json_pictures),
                "tables_count": len(json_content.get("tables", [])),
                "texts_count": len(json_content.get("texts", [])),
                "pages": json_content.get("pages", {}),
            }
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(structure, f, indent=2)
            print(f"  JSON structure saved to: {json_file.name}")

        except Exception as e:
            print(f"  [ERROR] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    await client.stop_container()
    print("\n[DONE] Debug complete")


if __name__ == "__main__":
    asyncio.run(debug_image_extraction())
