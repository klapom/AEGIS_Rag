#!/usr/bin/env python3
"""
Quick Model Sanity Test for Entity Extraction
Tests if a model can produce valid JSON entity extraction output.
"""
import json
import time
import requests
import sys
from typing import Optional

# Test sample (500 chars from RAGAS)
TEST_TEXT = """Arthur's Magazine (1844–1846) was an American literary periodical published in Philadelphia in the 19th century. First for Women is a woman's magazine published by Bauer Media Group in the USA. The Oberoi family is an Indian family that is famous for its involvement in hotels, namely through The Oberoi Group. The Oberoi Group is a hotel company with its head office in Delhi. Allison Beth "Allie" Goertz (born March 2, 1991) is an American musician."""

# Entity extraction prompt (simplified version of our production prompt)
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
- "type": Relationship type (e.g., LOCATED_IN, WORKS_FOR, PART_OF)
- "description": Brief description

Text:
{text}

Entities found: {entities}

Return ONLY a JSON array like:
[
  {{"source": "Entity1", "target": "Entity2", "type": "WORKS_FOR", "description": "Entity1 works for Entity2"}}
]

JSON Output:"""


def test_model(model_name: str, timeout: int = 120) -> dict:
    """Test a single model for entity extraction capability."""
    result = {
        "model": model_name,
        "status": "unknown",
        "entities_extracted": 0,
        "relations_extracted": 0,
        "entity_time_seconds": 0,
        "relation_time_seconds": 0,
        "total_time_seconds": 0,
        "error": None,
        "sample_entities": [],
        "sample_relations": [],
    }

    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"{'='*60}")

    # Test entity extraction
    print("  [1/2] Testing entity extraction...")
    start_time = time.time()

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": ENTITY_PROMPT.format(text=TEST_TEXT),
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 2048,
                }
            },
            timeout=timeout
        )

        if response.status_code != 200:
            result["status"] = "api_error"
            result["error"] = f"HTTP {response.status_code}"
            return result

        data = response.json()
        raw_response = data.get("response", "")
        entity_time = time.time() - start_time
        result["entity_time_seconds"] = round(entity_time, 2)

        # Try to parse JSON from response
        entities = parse_json_array(raw_response)

        if entities is None:
            result["status"] = "json_parse_failed"
            result["error"] = f"Could not parse JSON from: {raw_response[:200]}..."
            print(f"    FAILED: Could not parse JSON")
            print(f"    Response: {raw_response[:300]}...")
            return result

        result["entities_extracted"] = len(entities)
        result["sample_entities"] = entities[:3]  # First 3 for inspection
        print(f"    OK: {len(entities)} entities in {entity_time:.1f}s")

    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = f"Entity extraction timed out after {timeout}s"
        print(f"    TIMEOUT after {timeout}s")
        return result
    except Exception as e:
        result["status"] = "exception"
        result["error"] = str(e)
        print(f"    ERROR: {e}")
        return result

    # Test relationship extraction
    print("  [2/2] Testing relationship extraction...")
    start_time = time.time()

    try:
        entity_names = [e.get("name", "") for e in entities]
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": RELATION_PROMPT.format(
                    text=TEST_TEXT,
                    entities=", ".join(entity_names)
                ),
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 2048,
                }
            },
            timeout=timeout
        )

        if response.status_code != 200:
            result["status"] = "partial_success"
            result["error"] = f"Relation extraction HTTP {response.status_code}"
            return result

        data = response.json()
        raw_response = data.get("response", "")
        relation_time = time.time() - start_time
        result["relation_time_seconds"] = round(relation_time, 2)

        relations = parse_json_array(raw_response)

        if relations is None:
            result["status"] = "partial_success"
            result["error"] = "Relation JSON parse failed"
            print(f"    PARTIAL: Entities OK, relations failed")
        else:
            result["relations_extracted"] = len(relations)
            result["sample_relations"] = relations[:3]
            result["status"] = "success"
            print(f"    OK: {len(relations)} relations in {relation_time:.1f}s")

    except requests.exceptions.Timeout:
        result["status"] = "partial_success"
        result["error"] = f"Relation extraction timed out"
        print(f"    TIMEOUT on relations")
    except Exception as e:
        result["status"] = "partial_success"
        result["error"] = f"Relation error: {e}"

    result["total_time_seconds"] = round(
        result["entity_time_seconds"] + result["relation_time_seconds"], 2
    )

    return result


def parse_json_array(text: str) -> Optional[list]:
    """Try to extract a JSON array from text."""
    # Clean up common issues
    text = text.strip()

    # Try direct parse first
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except:
        pass

    # Try to find JSON array in text
    import re

    # Look for [...] pattern
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except:
            pass

    # Try to fix common issues
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # Try again after cleanup
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except:
            pass

    return None


def check_model_available(model_name: str) -> bool:
    """Check if model is available in Ollama."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            # Check both exact match and base name match
            return (model_name in model_names or
                    any(model_name in n or n.startswith(model_name.split(":")[0]) for n in model_names))
    except:
        pass
    return False


def main():
    # Models to test
    MODELS_TO_TEST = [
        "gemma3:4b",
        "gemma3:1b",
        "phi4-mini",
        "qwen2.5:7b",
        "qwen2.5:3b",
        "mistral:7b",
        "llama3.2:8b",
        "zeffmuks/universal-ner",
    ]

    # Allow specific model via command line
    if len(sys.argv) > 1:
        MODELS_TO_TEST = sys.argv[1:]

    print("="*60)
    print("QUICK MODEL SANITY TEST FOR ENTITY EXTRACTION")
    print("="*60)
    print(f"Test text: {len(TEST_TEXT)} characters")
    print(f"Models to test: {len(MODELS_TO_TEST)}")

    # Check which models are available
    print("\nChecking model availability...")
    available = []
    not_available = []

    for model in MODELS_TO_TEST:
        if check_model_available(model):
            available.append(model)
            print(f"  [OK] {model}")
        else:
            not_available.append(model)
            print(f"  [--] {model} (not downloaded yet)")

    if not available:
        print("\nNo models available yet. Please wait for downloads to complete.")
        return

    # Test available models
    results = []
    for model in available:
        result = test_model(model)
        results.append(result)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"{'Model':<30} {'Status':<15} {'Entities':<10} {'Relations':<10} {'Time':<10}")
    print("-"*75)

    working_models = []
    for r in results:
        status_emoji = "✅" if r["status"] == "success" else "⚠️" if "partial" in r["status"] else "❌"
        print(f"{r['model']:<30} {status_emoji} {r['status']:<12} {r['entities_extracted']:<10} {r['relations_extracted']:<10} {r['total_time_seconds']:<10.1f}s")

        if r["status"] in ["success", "partial_success"] and r["entities_extracted"] > 0:
            working_models.append(r["model"])

    print("-"*75)
    print(f"\nWorking models for full benchmark: {working_models}")

    if not_available:
        print(f"\nStill downloading: {not_available}")

    # Save results
    output_file = f"reports/model_sanity_test_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": time.strftime("%Y%m%d_%H%M%S"),
            "test_text_length": len(TEST_TEXT),
            "results": results,
            "working_models": working_models,
            "not_available": not_available,
        }, f, indent=2)
    print(f"\nResults saved to: {output_file}")

    return working_models


if __name__ == "__main__":
    main()
