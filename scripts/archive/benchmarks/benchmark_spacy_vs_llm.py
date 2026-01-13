#!/usr/bin/env python3
"""Benchmark: SpaCy-First vs LLM-Only Entity Extraction.

Sprint 85: Compare extraction approaches for token efficiency.

Approaches:
A) LLM-Only (current): LLM extracts all entities directly
B) SpaCy-First + LLM-Additional: SpaCy NER first, LLM finds additional entities

Metrics:
- Entities found (SpaCy vs LLM vs Combined)
- Relations found
- Token usage (input + output)
- Duration (ms)
- ER Ratio

Usage:
    poetry run python scripts/benchmark_spacy_vs_llm.py
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import spacy

# Load SpaCy models
try:
    nlp_en = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading en_core_web_sm...")
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp_en = spacy.load("en_core_web_sm")

API_BASE = "http://localhost:8000"
BASE_PATH = Path("/home/admin/projects/aegisrag/AEGIS_Rag")

# Test files (5 from each dataset)
TEST_FILES = [
    # Re-DocRED (best ER ratio)
    BASE_PATH / "data/hf_relation_datasets/redocred/redocred_0002.txt",
    BASE_PATH / "data/hf_relation_datasets/redocred/redocred_0003.txt",
    # CNN/DailyMail
    BASE_PATH / "data/hf_relation_datasets/docred/cnn_0003.txt",
    BASE_PATH / "data/hf_relation_datasets/docred/cnn_0024.txt",
    # SQuAD
    BASE_PATH / "data/hf_relation_datasets/tacred/squad_0006.txt",
    BASE_PATH / "data/hf_relation_datasets/tacred/squad_0015.txt",
]


@dataclass
class ExtractionResult:
    """Result of entity/relation extraction."""
    file: str
    approach: str  # "llm_only" or "spacy_first"

    # Entities
    spacy_entities: int = 0
    llm_entities: int = 0
    total_entities: int = 0

    # Relations
    relations: int = 0
    er_ratio: float = 0.0

    # Token usage
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    # Timing
    spacy_duration_ms: float = 0.0
    llm_entity_duration_ms: float = 0.0
    llm_relation_duration_ms: float = 0.0
    total_duration_ms: float = 0.0

    # Raw data
    entity_names: list = field(default_factory=list)
    relation_types: list = field(default_factory=list)


def extract_with_spacy(text: str) -> tuple[list[dict], float]:
    """Extract entities using SpaCy NER.

    Returns:
        Tuple of (entities, duration_ms)
    """
    start = time.perf_counter()
    doc = nlp_en(text)

    entities = []
    seen = set()
    for ent in doc.ents:
        if ent.text.lower() not in seen:
            entities.append({
                "name": ent.text,
                "type": ent.label_,
                "description": f"{ent.label_} entity",
            })
            seen.add(ent.text.lower())

    duration_ms = (time.perf_counter() - start) * 1000
    return entities, duration_ms


async def call_ollama_direct(
    prompt: str,
    model: str = "nemotron-3-nano:latest",
    timeout: float = 120.0,
) -> tuple[str, int, int, float]:
    """Call Ollama API directly for benchmarking.

    Returns:
        Tuple of (response_text, input_tokens, output_tokens, duration_ms)
    """
    start = time.perf_counter()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 2048,
                },
            },
            timeout=timeout,
        )

    duration_ms = (time.perf_counter() - start) * 1000

    if response.status_code == 200:
        data = response.json()
        return (
            data.get("response", ""),
            data.get("prompt_eval_count", 0),
            data.get("eval_count", 0),
            duration_ms,
        )
    else:
        return "", 0, 0, duration_ms


def parse_json_response(response: str) -> list[dict]:
    """Parse JSON array from LLM response with multiple strategies."""
    response = response.strip()

    # Strategy 1: Find JSON array boundaries
    start_idx = response.find("[")
    end_idx = response.rfind("]")

    if start_idx != -1 and end_idx != -1:
        json_str = response[start_idx:end_idx + 1]
        try:
            result = json.loads(json_str)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 2: Try to fix common issues
    # Remove markdown code fences
    response = response.replace("```json", "").replace("```", "")

    # Try again after cleanup
    start_idx = response.find("[")
    end_idx = response.rfind("]")

    if start_idx != -1 and end_idx != -1:
        json_str = response[start_idx:end_idx + 1]
        # Fix trailing commas
        json_str = json_str.replace(",]", "]").replace(",\n]", "]")
        try:
            result = json.loads(json_str)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: Extract individual JSON objects
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


async def benchmark_llm_only(text: str, file_name: str) -> ExtractionResult:
    """Benchmark: LLM-Only entity extraction (current approach)."""
    result = ExtractionResult(file=file_name, approach="llm_only")

    start_total = time.perf_counter()

    # Step 1: LLM Entity Extraction
    entity_prompt = f"""Extract all entities from the following text. For each entity, identify:
1. Entity name (exact string from text)
2. Entity type (PERSON, ORGANIZATION, LOCATION, CONCEPT, TECHNOLOGY, PRODUCT, EVENT, or other)
3. Short description (1 sentence)

Text:
{text}

Return ONLY a valid JSON array:
[{{"name": "Entity Name", "type": "ENTITY_TYPE", "description": "Description"}}]

Output (JSON array only):"""

    response, input_tok, output_tok, duration = await call_ollama_direct(entity_prompt)
    entities = parse_json_response(response)

    result.llm_entities = len(entities)
    result.total_entities = len(entities)
    result.input_tokens = input_tok
    result.output_tokens = output_tok
    result.llm_entity_duration_ms = duration
    result.entity_names = [e.get("name", "") for e in entities]

    # Step 2: LLM Relation Extraction
    if entities:
        entity_list = ", ".join([e.get("name", "") for e in entities])
        relation_prompt = f"""Extract ALL relationships between these entities:

Entities: {entity_list}

Text:
{text}

For each relationship, provide source, target, type, and description.
Return ONLY a valid JSON array:
[{{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "Why related"}}]

Output (JSON array only):"""

        response, input_tok2, output_tok2, duration2 = await call_ollama_direct(relation_prompt)
        relations = parse_json_response(response)

        result.relations = len(relations)
        result.input_tokens += input_tok2
        result.output_tokens += output_tok2
        result.llm_relation_duration_ms = duration2
        result.relation_types = [r.get("type", "") for r in relations]

    result.total_tokens = result.input_tokens + result.output_tokens
    result.total_duration_ms = (time.perf_counter() - start_total) * 1000
    result.er_ratio = result.relations / result.total_entities if result.total_entities > 0 else 0

    return result


async def benchmark_spacy_first(text: str, file_name: str) -> ExtractionResult:
    """Benchmark: SpaCy-First + LLM-Additional (proposed approach)."""
    result = ExtractionResult(file=file_name, approach="spacy_first")

    start_total = time.perf_counter()

    # Step 1: SpaCy NER (FREE)
    spacy_entities, spacy_duration = extract_with_spacy(text)
    result.spacy_entities = len(spacy_entities)
    result.spacy_duration_ms = spacy_duration

    spacy_entity_names = [e["name"] for e in spacy_entities]
    spacy_entity_list = ", ".join(spacy_entity_names) if spacy_entity_names else "None found"

    # Step 2: LLM Additional Entities (ALWAYS)
    additional_prompt = f"""I already found these entities using NER: [{spacy_entity_list}]

Find ADDITIONAL entities that I MISSED in the text below.
Focus on: CONCEPT, TECHNOLOGY, PRODUCT, EVENT, ORGANIZATION not captured above.
Do NOT repeat entities I already found.

Text:
{text}

Return ONLY a valid JSON array of ADDITIONAL entities (not already in my list):
[{{"name": "Entity Name", "type": "ENTITY_TYPE", "description": "Description"}}]

Output (JSON array only):"""

    response, input_tok, output_tok, duration = await call_ollama_direct(additional_prompt)
    additional_entities = parse_json_response(response)

    result.llm_entities = len(additional_entities)
    result.input_tokens = input_tok
    result.output_tokens = output_tok
    result.llm_entity_duration_ms = duration

    # Combine entities (deduplicate)
    all_entity_names = set(spacy_entity_names)
    combined_entities = list(spacy_entities)
    for e in additional_entities:
        name = e.get("name", "")
        if name.lower() not in {n.lower() for n in all_entity_names}:
            combined_entities.append(e)
            all_entity_names.add(name)

    result.total_entities = len(combined_entities)
    result.entity_names = list(all_entity_names)

    # Step 3: LLM Relation Extraction
    if combined_entities:
        entity_list = ", ".join(list(all_entity_names)[:30])  # Limit for prompt size
        relation_prompt = f"""Extract ALL relationships between these entities:

Entities: {entity_list}

Text:
{text}

For each relationship, provide source, target, type, and description.
Return ONLY a valid JSON array:
[{{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "Why related"}}]

Output (JSON array only):"""

        response, input_tok2, output_tok2, duration2 = await call_ollama_direct(relation_prompt)
        relations = parse_json_response(response)

        result.relations = len(relations)
        result.input_tokens += input_tok2
        result.output_tokens += output_tok2
        result.llm_relation_duration_ms = duration2
        result.relation_types = [r.get("type", "") for r in relations]

    result.total_tokens = result.input_tokens + result.output_tokens
    result.total_duration_ms = (time.perf_counter() - start_total) * 1000
    result.er_ratio = result.relations / result.total_entities if result.total_entities > 0 else 0

    return result


async def run_benchmark():
    """Run full benchmark comparison."""
    print("=" * 80)
    print("BENCHMARK: SpaCy-First vs LLM-Only Entity Extraction")
    print("=" * 80)

    results_llm = []
    results_spacy = []

    for file_path in TEST_FILES:
        if not file_path.exists():
            print(f"SKIP: {file_path.name} not found")
            continue

        text = file_path.read_text()
        # Skip header comments
        lines = text.split("\n")
        text_lines = [l for l in lines if not l.startswith("#")]
        text = "\n".join(text_lines).strip()

        if len(text) < 100:
            print(f"SKIP: {file_path.name} too short")
            continue

        print(f"\n{'='*60}")
        print(f"File: {file_path.name} ({len(text)} chars)")
        print("=" * 60)

        # Run LLM-Only
        print("\n[A] LLM-Only approach...")
        result_llm = await benchmark_llm_only(text, file_path.name)
        results_llm.append(result_llm)
        print(f"    Entities: {result_llm.total_entities}")
        print(f"    Relations: {result_llm.relations}")
        print(f"    ER Ratio: {result_llm.er_ratio:.2f}")
        print(f"    Tokens: {result_llm.total_tokens} (in:{result_llm.input_tokens}, out:{result_llm.output_tokens})")
        print(f"    Duration: {result_llm.total_duration_ms:.0f}ms")

        # Run SpaCy-First
        print("\n[B] SpaCy-First approach...")
        result_spacy = await benchmark_spacy_first(text, file_path.name)
        results_spacy.append(result_spacy)
        print(f"    SpaCy Entities: {result_spacy.spacy_entities}")
        print(f"    LLM Additional: {result_spacy.llm_entities}")
        print(f"    Total Entities: {result_spacy.total_entities}")
        print(f"    Relations: {result_spacy.relations}")
        print(f"    ER Ratio: {result_spacy.er_ratio:.2f}")
        print(f"    Tokens: {result_spacy.total_tokens} (in:{result_spacy.input_tokens}, out:{result_spacy.output_tokens})")
        print(f"    Duration: {result_spacy.total_duration_ms:.0f}ms (SpaCy: {result_spacy.spacy_duration_ms:.0f}ms)")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY COMPARISON")
    print("=" * 80)

    if not results_llm or not results_spacy:
        print("No results to compare")
        return

    # Aggregate metrics
    llm_entities = sum(r.total_entities for r in results_llm)
    llm_relations = sum(r.relations for r in results_llm)
    llm_tokens = sum(r.total_tokens for r in results_llm)
    llm_duration = sum(r.total_duration_ms for r in results_llm)

    spacy_base = sum(r.spacy_entities for r in results_spacy)
    spacy_additional = sum(r.llm_entities for r in results_spacy)
    spacy_entities = sum(r.total_entities for r in results_spacy)
    spacy_relations = sum(r.relations for r in results_spacy)
    spacy_tokens = sum(r.total_tokens for r in results_spacy)
    spacy_duration = sum(r.total_duration_ms for r in results_spacy)

    print(f"\n{'Metric':<25} {'LLM-Only':>15} {'SpaCy-First':>15} {'Diff':>15}")
    print("-" * 70)
    print(f"{'Entities (SpaCy)':<25} {'-':>15} {spacy_base:>15}")
    print(f"{'Entities (LLM)':<25} {llm_entities:>15} {spacy_additional:>15}")
    print(f"{'Entities (Total)':<25} {llm_entities:>15} {spacy_entities:>15} {spacy_entities - llm_entities:>+15}")
    print(f"{'Relations':<25} {llm_relations:>15} {spacy_relations:>15} {spacy_relations - llm_relations:>+15}")
    print(f"{'ER Ratio':<25} {llm_relations/max(llm_entities,1):>15.2f} {spacy_relations/max(spacy_entities,1):>15.2f}")
    print("-" * 70)
    print(f"{'Input Tokens':<25} {sum(r.input_tokens for r in results_llm):>15} {sum(r.input_tokens for r in results_spacy):>15}")
    print(f"{'Output Tokens':<25} {sum(r.output_tokens for r in results_llm):>15} {sum(r.output_tokens for r in results_spacy):>15}")
    print(f"{'Total Tokens':<25} {llm_tokens:>15} {spacy_tokens:>15} {spacy_tokens - llm_tokens:>+15}")
    print(f"{'Token Savings':<25} {'-':>15} {(1 - spacy_tokens/max(llm_tokens,1))*100:>14.1f}%")
    print("-" * 70)
    print(f"{'Total Duration (ms)':<25} {llm_duration:>15.0f} {spacy_duration:>15.0f} {spacy_duration - llm_duration:>+15.0f}")
    print(f"{'Speedup':<25} {'-':>15} {llm_duration/max(spacy_duration,1):>14.1f}x")
    print("=" * 80)

    # Per-file comparison
    print("\n" + "=" * 80)
    print("PER-FILE COMPARISON")
    print("=" * 80)
    print(f"{'File':<20} {'LLM E/R':>10} {'SpaCy E/R':>12} {'LLM Tok':>10} {'SpaCy Tok':>10} {'Saved':>8}")
    print("-" * 70)

    for r_llm, r_spacy in zip(results_llm, results_spacy):
        saved = (1 - r_spacy.total_tokens / max(r_llm.total_tokens, 1)) * 100
        print(f"{r_llm.file[:20]:<20} {r_llm.total_entities:>4}/{r_llm.relations:<5} "
              f"{r_spacy.total_entities:>4}/{r_spacy.relations:<7} "
              f"{r_llm.total_tokens:>10} {r_spacy.total_tokens:>10} {saved:>7.1f}%")

    print("=" * 80)

    # Return results for documentation
    return {
        "llm_only": {
            "entities": llm_entities,
            "relations": llm_relations,
            "tokens": llm_tokens,
            "duration_ms": llm_duration,
            "er_ratio": llm_relations / max(llm_entities, 1),
        },
        "spacy_first": {
            "spacy_entities": spacy_base,
            "llm_additional": spacy_additional,
            "total_entities": spacy_entities,
            "relations": spacy_relations,
            "tokens": spacy_tokens,
            "duration_ms": spacy_duration,
            "er_ratio": spacy_relations / max(spacy_entities, 1),
        },
        "comparison": {
            "token_savings_pct": (1 - spacy_tokens / max(llm_tokens, 1)) * 100,
            "entity_diff": spacy_entities - llm_entities,
            "relation_diff": spacy_relations - llm_relations,
            "speedup": llm_duration / max(spacy_duration, 1),
        },
    }


if __name__ == "__main__":
    asyncio.run(run_benchmark())
