"""Analyze DOCX JSON structure to understand heading representation.

Sprint 33 - TD-044: DOCX documents don't have 'title' labels!
We need to understand how Docling represents headings in DOCX files.
"""

import json
from collections import Counter
from pathlib import Path

# Load the DOCX JSON
json_path = Path(__file__).parent / "results" / "multi_format_test" / "docx_DE-D-AdvancedAdministration_0368_raw.json"

print(f"Loading: {json_path}")
print(f"File size: {json_path.stat().st_size / 1024:.1f} KB")
print()

with open(json_path, encoding="utf-8") as f:
    data = json.load(f)

# 1. Analyze all labels in texts array
print("=" * 70)
print("1. ALL LABELS IN TEXTS ARRAY")
print("=" * 70)
texts = data.get("texts", [])
labels = Counter(t.get("label", "NONE") for t in texts)
for label, count in labels.most_common():
    print(f"  {label}: {count}x")

# 2. Check if there are any heading-like labels we might have missed
print("\n" + "=" * 70)
print("2. SEARCH FOR HEADING-LIKE PATTERNS")
print("=" * 70)

heading_keywords = ["title", "heading", "section", "chapter", "header", "subtitle"]
for t in texts[:100]:
    label = t.get("label", "").lower()
    for keyword in heading_keywords:
        if keyword in label:
            print(f"  Found: label='{t.get('label')}' text='{t.get('text', '')[:50]}'")

# 3. Look at groups - maybe headings are in groups?
print("\n" + "=" * 70)
print("3. GROUP LABELS")
print("=" * 70)
groups = data.get("groups", [])
group_labels = Counter(g.get("label", "NONE") for g in groups)
for label, count in group_labels.most_common():
    print(f"  {label}: {count}x")

# 4. Check group structure - do groups have 'name' that indicates section?
print("\n" + "=" * 70)
print("4. FIRST 20 GROUPS WITH NAME AND LABEL")
print("=" * 70)
for i, g in enumerate(groups[:20]):
    label = g.get("label", "?")
    name = g.get("name", "?")
    children_count = len(g.get("children", []))
    print(f"  [{i:3d}] label={label:20s} name={name[:30]:30s} children={children_count}")

# 5. Check if any groups have heading-related labels
print("\n" + "=" * 70)
print("5. GROUPS WITH HEADING/SECTION LABELS")
print("=" * 70)
heading_groups = [g for g in groups if any(k in g.get("label", "").lower() for k in heading_keywords)]
print(f"  Found {len(heading_groups)} groups with heading-like labels")
for g in heading_groups[:10]:
    print(f"    label={g.get('label')} name={g.get('name')}")

# 6. Look at 'furniture' - header/footer content
print("\n" + "=" * 70)
print("6. FURNITURE (HEADERS/FOOTERS)")
print("=" * 70)
furniture = data.get("furniture", {})
print(f"  Furniture keys: {list(furniture.keys()) if furniture else 'None'}")

# 7. Check body children structure
print("\n" + "=" * 70)
print("7. BODY CHILDREN (FIRST 20)")
print("=" * 70)
body = data.get("body", {})
children = body.get("children", [])
print(f"  Total body children: {len(children)}")
for i, c in enumerate(children[:20]):
    if isinstance(c, dict):
        if "$ref" in c:
            ref = c["$ref"]
            # Try to resolve the reference
            if ref.startswith("#/groups/"):
                idx = int(ref.split("/")[-1])
                if idx < len(groups):
                    g = groups[idx]
                    print(f"  [{i:3d}] $ref={ref} -> label={g.get('label')} name={g.get('name', '')[:30]}")
                else:
                    print(f"  [{i:3d}] $ref={ref} -> INDEX OUT OF RANGE")
            else:
                print(f"  [{i:3d}] $ref={ref}")
        else:
            print(f"  [{i:3d}] dict keys: {list(c.keys())}")
    else:
        print(f"  [{i:3d}] type={type(c).__name__}")

# 8. Look at texts with specific patterns (e.g., short text that looks like heading)
print("\n" + "=" * 70)
print("8. POTENTIAL HEADINGS (SHORT PARAGRAPHS < 100 CHARS)")
print("=" * 70)
potential_headings = []
for i, t in enumerate(texts):
    text = t.get("text", "")
    label = t.get("label", "")
    # Short text, not a list item, could be a heading
    if label == "paragraph" and 5 < len(text) < 100 and not text.startswith("-"):
        # Check if it looks like a heading (starts with capital, no period at end)
        if text[0].isupper() and not text.rstrip().endswith("."):
            potential_headings.append((i, text[:60]))

print(f"  Found {len(potential_headings)} potential headings")
for idx, text in potential_headings[:20]:
    print(f"    [{idx:4d}] '{text}'")

# 9. Check if there's a 'style' or 'formatting' field that indicates headings
print("\n" + "=" * 70)
print("9. CHECK FOR STYLE/FORMATTING INFO IN FIRST TEXT ITEM")
print("=" * 70)
if texts:
    first_text = texts[0]
    print(f"  Keys in first text: {list(first_text.keys())}")
    for key, value in first_text.items():
        if key not in ["text", "prov"]:
            val_str = str(value)[:100]
            print(f"    {key}: {val_str}")

# 10. Check for 'section_header' or similar in schema
print("\n" + "=" * 70)
print("10. SCHEMA AND VERSION INFO")
print("=" * 70)
print(f"  schema_name: {data.get('schema_name')}")
print(f"  version: {data.get('version')}")
print(f"  name: {data.get('name')}")

# 11. Summary and recommendation
print("\n" + "=" * 70)
print("11. SUMMARY AND RECOMMENDATIONS")
print("=" * 70)
print(f"""
FINDINGS:
- DOCX has {len(texts)} text items but NO 'title' or 'subtitle-level-*' labels
- Labels found: {dict(labels)}
- This is different from PPTX which has 'title' labels

POSSIBLE CAUSES:
1. Docling uses different label names for DOCX headings
2. The DOCX document has no proper heading styles applied
3. Docling doesn't extract heading styles from DOCX

RECOMMENDATIONS:
1. Check if the source DOCX uses Word heading styles (Heading 1, Heading 2, etc.)
2. Look for 'section_header' or similar labels in the Docling schema
3. Consider using heuristics to detect headings (short paragraphs, formatting)
4. Check Docling documentation for DOCX-specific label mappings
""")
