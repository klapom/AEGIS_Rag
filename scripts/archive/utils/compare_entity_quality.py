#!/usr/bin/env python3
"""Compare SpaCy vs LLM Entity Quality.

Sprint 85: Qualitative analysis of extracted entities.
"""

import asyncio
import json
from pathlib import Path

import httpx
import spacy

# Load SpaCy
nlp_en = spacy.load("en_core_web_sm")

BASE_PATH = Path("/home/admin/projects/aegisrag/AEGIS_Rag")

# Test files for quality comparison
TEST_FILES = [
    BASE_PATH / "data/hf_relation_datasets/redocred/redocred_0002.txt",
    BASE_PATH / "data/hf_relation_datasets/docred/cnn_0024.txt",
]


def extract_with_spacy(text: str) -> list[dict]:
    """Extract entities using SpaCy NER."""
    doc = nlp_en(text)
    entities = []
    seen = set()
    for ent in doc.ents:
        if ent.text.lower() not in seen:
            entities.append({
                "name": ent.text,
                "type": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            })
            seen.add(ent.text.lower())
    return entities


async def extract_with_llm(text: str) -> list[dict]:
    """Extract entities using LLM."""
    prompt = f"""Extract all named entities from the following text. For each entity, identify:
1. Entity name (exact string from text)
2. Entity type (PERSON, ORGANIZATION, LOCATION, DATE, EVENT, CONCEPT, TECHNOLOGY, or other)

Text:
{text}

Return ONLY a valid JSON array:
[{{"name": "Entity Name", "type": "ENTITY_TYPE"}}]

Output (JSON array only):"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "nemotron-3-nano:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 2048},
            },
            timeout=120.0,
        )

    if response.status_code == 200:
        data = response.json()
        response_text = data.get("response", "")
        return parse_json_response(response_text)
    return []


def parse_json_response(response: str) -> list[dict]:
    """Parse JSON array from LLM response."""
    response = response.strip()
    start_idx = response.find("[")
    end_idx = response.rfind("]")

    if start_idx != -1 and end_idx != -1:
        json_str = response[start_idx:end_idx + 1]
        json_str = json_str.replace(",]", "]").replace(",\n]", "]")
        try:
            result = json.loads(json_str)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Fallback: extract individual objects
    import re
    objects = re.findall(r'\{[^{}]+\}', response)
    results = []
    for obj_str in objects:
        try:
            obj = json.loads(obj_str)
            if isinstance(obj, dict):
                results.append(obj)
        except json.JSONDecodeError:
            continue
    return results


def categorize_entity_type(entity_type: str) -> str:
    """Map SpaCy labels to common categories."""
    mapping = {
        # SpaCy labels
        "PERSON": "PERSON",
        "PER": "PERSON",
        "ORG": "ORGANIZATION",
        "GPE": "LOCATION",  # Geopolitical entity
        "LOC": "LOCATION",
        "FAC": "LOCATION",  # Facility
        "DATE": "DATE",
        "TIME": "DATE",
        "CARDINAL": "NUMBER",
        "ORDINAL": "NUMBER",
        "MONEY": "NUMBER",
        "PERCENT": "NUMBER",
        "QUANTITY": "NUMBER",
        "EVENT": "EVENT",
        "WORK_OF_ART": "CONCEPT",
        "LAW": "CONCEPT",
        "LANGUAGE": "CONCEPT",
        "NORP": "CONCEPT",  # Nationalities, religious groups
        "PRODUCT": "PRODUCT",
    }
    return mapping.get(entity_type.upper(), entity_type.upper())


async def compare_file(file_path: Path):
    """Compare SpaCy vs LLM entities for a single file."""
    print(f"\n{'='*80}")
    print(f"File: {file_path.name}")
    print("=" * 80)

    text = file_path.read_text()
    # Remove header comments
    lines = text.split("\n")
    text_lines = [l for l in lines if not l.startswith("#")]
    text = "\n".join(text_lines).strip()

    print(f"Text length: {len(text)} chars")
    print(f"\nText preview: {text[:200]}...\n")

    # Extract with SpaCy
    spacy_entities = extract_with_spacy(text)

    # Extract with LLM
    llm_entities = await extract_with_llm(text)

    # Normalize types for comparison
    spacy_normalized = {
        (e["name"].lower(), categorize_entity_type(e["type"]))
        for e in spacy_entities
    }
    llm_normalized = {
        (e.get("name", "").lower(), categorize_entity_type(e.get("type", "")))
        for e in llm_entities
    }

    # Find overlaps and differences
    both = spacy_normalized & llm_normalized
    spacy_only = spacy_normalized - llm_normalized
    llm_only = llm_normalized - spacy_normalized

    # Also check name-only overlap (ignoring type)
    spacy_names = {e["name"].lower() for e in spacy_entities}
    llm_names = {e.get("name", "").lower() for e in llm_entities}
    names_both = spacy_names & llm_names
    names_spacy_only = spacy_names - llm_names
    names_llm_only = llm_names - spacy_names

    print("-" * 80)
    print("SPACY ENTITIES (sorted by type):")
    print("-" * 80)
    for e in sorted(spacy_entities, key=lambda x: x["type"]):
        normalized = categorize_entity_type(e["type"])
        in_llm = "✓" if e["name"].lower() in llm_names else "✗"
        print(f"  [{normalized:12}] {e['name']:<30} (LLM: {in_llm})")

    print(f"\n  Total: {len(spacy_entities)} entities")

    print("\n" + "-" * 80)
    print("LLM ENTITIES (sorted by type):")
    print("-" * 80)
    for e in sorted(llm_entities, key=lambda x: x.get("type", "")):
        entity_type = e.get("type", "UNKNOWN")
        name = e.get("name", "")
        in_spacy = "✓" if name.lower() in spacy_names else "✗"
        print(f"  [{entity_type:12}] {name:<30} (SpaCy: {in_spacy})")

    print(f"\n  Total: {len(llm_entities)} entities")

    print("\n" + "-" * 80)
    print("OVERLAP ANALYSIS:")
    print("-" * 80)
    print(f"  Names found by BOTH:       {len(names_both):3} ({', '.join(sorted(names_both)[:5])}...)")
    print(f"  Names ONLY in SpaCy:       {len(names_spacy_only):3} ({', '.join(sorted(names_spacy_only)[:5])}...)")
    print(f"  Names ONLY in LLM:         {len(names_llm_only):3} ({', '.join(sorted(names_llm_only)[:5])}...)")

    print("\n" + "-" * 80)
    print("TYPE DISTRIBUTION:")
    print("-" * 80)

    # SpaCy type distribution
    spacy_types = {}
    for e in spacy_entities:
        t = categorize_entity_type(e["type"])
        spacy_types[t] = spacy_types.get(t, 0) + 1

    # LLM type distribution
    llm_types = {}
    for e in llm_entities:
        t = categorize_entity_type(e.get("type", "UNKNOWN"))
        llm_types[t] = llm_types.get(t, 0) + 1

    all_types = sorted(set(spacy_types.keys()) | set(llm_types.keys()))
    print(f"  {'Type':<15} {'SpaCy':>8} {'LLM':>8}")
    print(f"  {'-'*31}")
    for t in all_types:
        print(f"  {t:<15} {spacy_types.get(t, 0):>8} {llm_types.get(t, 0):>8}")

    print("\n" + "-" * 80)
    print("QUALITY EXAMPLES:")
    print("-" * 80)

    print("\n  SpaCy-ONLY (LLM missed):")
    for name in sorted(names_spacy_only)[:10]:
        entity = next((e for e in spacy_entities if e["name"].lower() == name), None)
        if entity:
            print(f"    - {entity['name']} ({entity['type']})")

    print("\n  LLM-ONLY (SpaCy missed):")
    for name in sorted(names_llm_only)[:10]:
        entity = next((e for e in llm_entities if e.get("name", "").lower() == name), None)
        if entity:
            print(f"    - {entity.get('name')} ({entity.get('type')})")

    return {
        "file": file_path.name,
        "spacy_count": len(spacy_entities),
        "llm_count": len(llm_entities),
        "overlap_names": len(names_both),
        "spacy_only": len(names_spacy_only),
        "llm_only": len(names_llm_only),
        "spacy_entities": spacy_entities,
        "llm_entities": llm_entities,
    }


async def main():
    """Run quality comparison."""
    print("=" * 80)
    print("ENTITY QUALITY COMPARISON: SpaCy vs LLM")
    print("=" * 80)

    results = []
    for file_path in TEST_FILES:
        if file_path.exists():
            result = await compare_file(file_path)
            results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_spacy = sum(r["spacy_count"] for r in results)
    total_llm = sum(r["llm_count"] for r in results)
    total_overlap = sum(r["overlap_names"] for r in results)
    total_spacy_only = sum(r["spacy_only"] for r in results)
    total_llm_only = sum(r["llm_only"] for r in results)

    print(f"\n  {'Metric':<25} {'Value':>10}")
    print(f"  {'-'*35}")
    print(f"  {'SpaCy Total Entities':<25} {total_spacy:>10}")
    print(f"  {'LLM Total Entities':<25} {total_llm:>10}")
    print(f"  {'Overlap (same names)':<25} {total_overlap:>10}")
    print(f"  {'SpaCy-only':<25} {total_spacy_only:>10}")
    print(f"  {'LLM-only':<25} {total_llm_only:>10}")

    if total_spacy > 0:
        print(f"\n  SpaCy Precision (in LLM): {total_overlap / total_spacy * 100:.1f}%")
    if total_llm > 0:
        print(f"  LLM Precision (in SpaCy): {total_overlap / total_llm * 100:.1f}%")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("""
  SpaCy STRENGTHS:
    ✓ Named entities (PERSON, ORG, LOCATION, DATE)
    ✓ Fast and consistent
    ✓ No hallucination risk
    ✓ Exact text spans

  LLM STRENGTHS:
    ✓ Conceptual entities (CONCEPT, EVENT, TECHNOLOGY)
    ✓ Context-aware disambiguation
    ✓ Implicit entity recognition
    ✓ Domain-specific knowledge

  RECOMMENDATION:
    Use SpaCy for: PERSON, ORG, LOCATION, DATE (high confidence)
    Use LLM for: CONCEPT, EVENT, TECHNOLOGY, PRODUCT (reasoning needed)
""")


if __name__ == "__main__":
    asyncio.run(main())
