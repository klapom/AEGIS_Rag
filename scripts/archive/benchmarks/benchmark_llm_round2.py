#!/usr/bin/env python3
"""
LLM Extraction Benchmark Round 2
Tests multiple models against qwen3:32b baseline using the same RAGAS sample.
"""
import json
import sys
import time
from datetime import datetime

import requests

# Same RAGAS sample as Round 1 (833 chars from 3 HotPotQA samples)
TEST_SAMPLES = [
    "Arthur's Magazine (1844–1846) was an American literary periodical published in Philadelphia in the 19th century. First for Women is a woman's magazine published by Bauer Media Group in the USA. The Oberoi family is an Indian family that is famous for its involvement in hotels, namely through The Oberoi Group.",
    "The Oberoi Group is a hotel company with its head office in Delhi. Allison Beth \"Allie\" Goertz (born March 2, 1991) is an American musician. She's known for her satirical songs based on various pop culture topics.",
    "\"Cossbysweater\" by Goertz is a satirical song about comedian Bill Cosby that appeared on YouTube and became viral. Richard Nixon's second vice president was Gerald Ford. The Simpsons is an animated TV series created by Matt Groening."
]

CHUNK_SIZE = 500

# Entity extraction prompt (same as production)
ENTITY_PROMPT = """Extract all named entities from the following text. Return ONLY a valid JSON array.

Each entity should have:
- "name": The entity name as it appears in the text
- "type": One of: PERSON, ORGANIZATION, LOCATION, PRODUCT, EVENT, CONCEPT, TECHNOLOGY
- "description": Brief description (1 sentence)

Text:
{text}

Return ONLY a JSON array like:
[
  {{"name": "Example", "type": "PERSON", "description": "A person mentioned"}}
]

JSON Output:"""

# Relationship extraction prompt
RELATION_PROMPT = """Extract relationships between entities from the text. Return ONLY a valid JSON array.

Each relationship should have:
- "source": Source entity name
- "target": Target entity name
- "type": Relationship type (e.g., LOCATED_IN, WORKS_FOR, PART_OF, CREATED_BY)
- "description": Brief description

Text:
{text}

Entities found: {entities}

Return ONLY a JSON array like:
[
  {{"source": "Entity1", "target": "Entity2", "type": "WORKS_FOR", "description": "Entity1 works for Entity2"}}
]

JSON Output:"""


def chunk_text(text: str, chunk_size: int) -> list:
    """Simple character-based chunking."""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks


def parse_json_array(text: str) -> list | None:
    """Try to extract a JSON array from text."""
    import re
    text = text.strip()

    # Direct parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except:
        pass

    # Find JSON array
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except:
            pass

    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except:
            pass

    return None


def extract_with_model(model: str, text: str, timeout: int = 180) -> dict:
    """Extract entities and relationships using a specific model."""
    result = {
        "model": model,
        "chunks": [],
        "total_entities": 0,
        "total_relations": 0,
        "total_time": 0,
        "total_tokens_output": 0,
        "status": "success",
        "error": None,
    }

    chunks = chunk_text(text, CHUNK_SIZE)
    print(f"\n{'='*60}")
    print(f"Model: {model}")
    print(f"{'='*60}")
    print(f"  Text: {len(text)} chars -> {len(chunks)} chunks")

    all_entities = []
    all_relations = []

    for i, chunk in enumerate(chunks):
        chunk_start = time.time()
        chunk_result = {
            "chunk_id": i,
            "chunk_length": len(chunk),
            "entities": [],
            "relations": [],
            "entity_time": 0,
            "relation_time": 0,
            "tokens_output": 0,
        }

        # Entity extraction
        try:
            entity_start = time.time()
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": ENTITY_PROMPT.format(text=chunk),
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 4096,
                    }
                },
                timeout=timeout
            )

            if response.status_code != 200:
                chunk_result["error"] = f"HTTP {response.status_code}"
                result["status"] = "partial"
                result["chunks"].append(chunk_result)
                continue

            data = response.json()
            raw_response = data.get("response", "")
            tokens = data.get("eval_count", 0)
            chunk_result["entity_time"] = time.time() - entity_start
            chunk_result["tokens_output"] += tokens

            entities = parse_json_array(raw_response)
            if entities:
                chunk_result["entities"] = entities
                all_entities.extend(entities)

            print(f"  Chunk {i}: {len(entities or [])} entities in {chunk_result['entity_time']:.1f}s ({tokens} tokens)")

        except requests.exceptions.Timeout:
            chunk_result["error"] = f"Timeout after {timeout}s"
            result["status"] = "partial"
            print(f"  Chunk {i}: TIMEOUT on entities")
            result["chunks"].append(chunk_result)
            continue
        except Exception as e:
            chunk_result["error"] = str(e)
            result["status"] = "partial"
            print(f"  Chunk {i}: ERROR - {e}")
            result["chunks"].append(chunk_result)
            continue

        # Relationship extraction
        try:
            rel_start = time.time()
            entity_names = [e.get("name", "") for e in (entities or [])]
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": RELATION_PROMPT.format(
                        text=chunk,
                        entities=", ".join(entity_names)
                    ),
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 4096,
                    }
                },
                timeout=timeout
            )

            if response.status_code == 200:
                data = response.json()
                raw_response = data.get("response", "")
                tokens = data.get("eval_count", 0)
                chunk_result["relation_time"] = time.time() - rel_start
                chunk_result["tokens_output"] += tokens

                relations = parse_json_array(raw_response)
                if relations:
                    chunk_result["relations"] = relations
                    all_relations.extend(relations)

                print(f"          + {len(relations or [])} relations in {chunk_result['relation_time']:.1f}s")

        except:
            pass  # Relations are optional

        result["chunks"].append(chunk_result)
        result["total_tokens_output"] += chunk_result["tokens_output"]

    result["total_entities"] = len(all_entities)
    result["total_relations"] = len(all_relations)
    result["total_time"] = sum(c.get("entity_time", 0) + c.get("relation_time", 0) for c in result["chunks"])
    result["all_entities"] = all_entities
    result["all_relations"] = all_relations

    return result


def main():
    # Models to benchmark (working models from sanity test)
    MODELS_TO_TEST = [
        "qwen3:32b",           # BASELINE
        "gemma3:4b",           # TOP performer in sanity test
        "qwen2.5:7b",          # Good quality
        "phi4-mini:latest",    # Function calling support
        "mistral:7b",          # Versatile
        "qwen2.5:3b",          # Fast
        "nuextract:3.8b",      # Specialized extraction
    ]

    # Allow specific models via command line
    if len(sys.argv) > 1:
        MODELS_TO_TEST = sys.argv[1:]

    # Combine test samples
    full_text = " ".join(TEST_SAMPLES)

    print("="*60)
    print("LLM EXTRACTION BENCHMARK - ROUND 2")
    print("="*60)
    print(f"Test text: {len(full_text)} characters")
    print(f"Chunk size: {CHUNK_SIZE} characters")
    print(f"Models to test: {len(MODELS_TO_TEST)}")
    print("Baseline: qwen3:32b")

    results = []

    for model in MODELS_TO_TEST:
        try:
            result = extract_with_model(model, full_text)
            results.append(result)
        except Exception as e:
            print(f"\nERROR with {model}: {e}")
            results.append({
                "model": model,
                "status": "error",
                "error": str(e),
            })

    # Summary
    print("\n" + "="*80)
    print("COMPLETE BENCHMARK SUMMARY")
    print("="*80)

    # Find baseline
    baseline = next((r for r in results if r["model"] == "qwen3:32b"), None)
    baseline_time = baseline.get("total_time", 1) if baseline else 1

    print(f"\n{'Model':<25} {'Entities':<10} {'Relations':<10} {'Time (s)':<12} {'Speed':<15} {'Status'}")
    print("-"*90)

    for r in results:
        if r.get("status") == "error":
            print(f"{r['model']:<25} {'N/A':<10} {'N/A':<10} {'N/A':<12} {'ERROR':<15}")
            continue

        time_taken = r.get("total_time", 0)
        speed_factor = time_taken / baseline_time if baseline_time > 0 else 0

        if r["model"] == "qwen3:32b":
            speed_str = "1.0x (baseline)"
        elif speed_factor < 1:
            speed_str = f"{1/speed_factor:.1f}x FASTER"
        else:
            speed_str = f"{speed_factor:.1f}x slower"

        status = "✅" if r.get("status") == "success" else "⚠️"
        print(f"{r['model']:<25} {r.get('total_entities', 0):<10} {r.get('total_relations', 0):<10} {time_taken:<12.1f} {speed_str:<15} {status}")

    print("-"*90)

    # Save results
    output_file = f"reports/llm_extraction_benchmark_round2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "test_text_length": len(full_text),
            "chunk_size": CHUNK_SIZE,
            "models_tested": MODELS_TO_TEST,
            "baseline_model": "qwen3:32b",
            "results": results,
        }, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    # Print entity comparison for top models
    print("\n" + "="*80)
    print("ENTITY COMPARISON (showing unique entities)")
    print("="*80)

    for r in results[:4]:  # Top 4 models
        if r.get("all_entities"):
            entities = r.get("all_entities", [])
            print(f"\n{r['model']}:")
            for e in entities[:10]:  # First 10
                name = e.get("name", "?")
                etype = e.get("type", "?")
                print(f"  [{etype}] {name}")
            if len(entities) > 10:
                print(f"  ... and {len(entities) - 10} more")


if __name__ == "__main__":
    main()
