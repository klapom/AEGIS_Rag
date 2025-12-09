"""Analyze text labels in parsed JSON."""

import json
from collections import Counter
from pathlib import Path

json_path = Path(__file__).parent / "results" / "docling_parsed_sample.json"
with open(json_path, encoding="utf-8") as f:
    data = json.load(f)

print("=== Alle Text-Labels und deren Haeufigkeit ===")
labels = Counter(t.get("label", "NONE") for t in data["texts"])
for label, count in labels.most_common():
    print(f"  {label}: {count}x")

print("\n=== Erste 30 Texts mit Label und Text-Preview ===")
for i, t in enumerate(data["texts"][:30]):
    label = t.get("label", "?")
    text = t.get("text", "")[:60].replace("\n", " ")
    page = t.get("prov", [{}])[0].get("page_no", "?") if t.get("prov") else "?"
    print(f"[{i:3d}] page={page} label={label:12s} text=\"{text}\"")

print("\n=== Suche nach 'Theory' ===")
for i, t in enumerate(data["texts"]):
    if "Theory" in t.get("text", ""):
        print(f"[{i}] label={t.get('label')} text=\"{t.get('text')}\"")
        print(f"     parent={t.get('parent')}")
