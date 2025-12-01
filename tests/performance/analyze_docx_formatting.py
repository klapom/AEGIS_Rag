"""Analyze DOCX formatting to find potential headings.

Sprint 33 - TD-044: DOCX has no title labels.
Check if formatting (bold, etc.) can be used to detect headings.
"""

import json
from pathlib import Path
from collections import Counter

json_path = Path(__file__).parent / "results" / "multi_format_test" / "docx_DE-D-AdvancedAdministration_0368_raw.json"

print(f"Loading: {json_path}")
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

texts = data.get("texts", [])
print(f"Total texts: {len(texts)}")

# 1. Analyze formatting patterns
print("\n" + "=" * 70)
print("1. FORMATTING PATTERNS")
print("=" * 70)

formatting_patterns = Counter()
bold_texts = []
bold_short = []

for i, t in enumerate(texts):
    fmt = t.get("formatting")
    if fmt:
        pattern = f"bold={fmt.get('bold')}, italic={fmt.get('italic')}"
        formatting_patterns[pattern] += 1

        if fmt.get("bold"):
            text = t.get("text", "")
            bold_texts.append((i, text[:80], len(text)))
            if len(text) < 100:
                bold_short.append((i, text[:60]))

for pattern, count in formatting_patterns.most_common():
    print(f"  {pattern}: {count}x")

# 2. Bold texts analysis
print("\n" + "=" * 70)
print(f"2. BOLD TEXTS ({len(bold_texts)} total)")
print("=" * 70)

print(f"  Total bold texts: {len(bold_texts)}")
print(f"  Short bold texts (<100 chars): {len(bold_short)}")

print("\n  First 30 short bold texts (potential headings):")
for idx, text in bold_short[:30]:
    print(f"    [{idx:4d}] '{text}'")

# 3. Check first texts for title pattern
print("\n" + "=" * 70)
print("3. FIRST 20 TEXTS WITH FORMATTING")
print("=" * 70)

for i, t in enumerate(texts[:20]):
    text = t.get("text", "")[:50]
    label = t.get("label", "?")
    fmt = t.get("formatting", {})
    bold = fmt.get("bold", "?") if fmt else "?"
    print(f"  [{i:3d}] label={label:12s} bold={str(bold):5s} text='{text}'")

# 4. Check for texts with specific formatting that could be headings
print("\n" + "=" * 70)
print("4. POTENTIAL HEADING PATTERNS")
print("=" * 70)

# Pattern: Bold, short, no period at end
potential_headings = []
for i, t in enumerate(texts):
    text = t.get("text", "")
    fmt = t.get("formatting", {})
    label = t.get("label", "")

    is_bold = fmt.get("bold", False) if fmt else False
    is_short = 5 < len(text) < 150
    no_period = not text.rstrip().endswith(".")
    starts_upper = text[0].isupper() if text else False
    is_paragraph = label == "paragraph"

    # Pattern 1: Bold + short + no period
    if is_bold and is_short and no_period and is_paragraph:
        potential_headings.append((i, text[:70], "bold+short"))
    # Pattern 2: Short paragraph, starts uppercase, no period, no bullet
    elif is_paragraph and is_short and starts_upper and no_period and not text.startswith(("-", "*", "•")):
        # Only add if not already in list
        if not any(p[0] == i for p in potential_headings):
            # Additional heuristic: looks like a section name
            if len(text) < 60 or text.isupper() or any(kw in text.lower() for kw in ["kapitel", "abschnitt", "teil", "section", "chapter"]):
                potential_headings.append((i, text[:70], "heuristic"))

print(f"  Bold+Short pattern: {sum(1 for p in potential_headings if p[2] == 'bold+short')}")
print(f"  Heuristic pattern: {sum(1 for p in potential_headings if p[2] == 'heuristic')}")
print(f"  Total potential headings: {len(potential_headings)}")

print("\n  First 50 potential headings:")
for idx, text, pattern in potential_headings[:50]:
    print(f"    [{idx:4d}] ({pattern:10s}) '{text}'")

# 5. Recommendation
print("\n" + "=" * 70)
print("5. RECOMMENDATIONS")
print("=" * 70)
print(f"""
FINDINGS:
- DOCX texts have {sum(1 for t in texts if t.get('formatting', {}).get('bold'))} bold texts
- {len(bold_short)} are short (<100 chars) - likely headings
- Formatting is available but NOT used to set label='title'

DOCX HEADING DETECTION STRATEGY:
1. Use 'formatting.bold' as primary indicator
2. Add length constraint (<150 chars)
3. Add 'no period at end' constraint
4. Fall back to heuristics for non-bold headings

This would allow extracting ~{len(potential_headings)} sections from the DOCX!
""")
