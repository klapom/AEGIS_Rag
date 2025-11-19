#!/usr/bin/env python3
"""Test models with LightRAG's ORIGINAL prompts and format validation.

Sprint 13 TD-31: Test if models can follow LightRAG's delimiter-separated format.
"""

import json
import re
import time
from ollama import Client

# LightRAG Original Delimiters
TUPLE_DELIMITER = "<|#|>"
COMPLETION_DELIMITER = "<|COMPLETE|>"

# ============================================================================
# LightRAG ORIGINAL SYSTEM PROMPT (from prompt.py)
# ============================================================================

SYSTEM_PROMPT = """---Role---
You are a Knowledge Graph Specialist responsible for extracting entities and relationships from the input text.

---Instructions---
1.  **Entity Extraction & Output:**
    *   **Identification:** Identify clearly defined and meaningful entities in the input text.
    *   **Entity Details:** For each identified entity, extract the following information:
        *   `entity_name`: The name of the entity.
        *   `entity_type`: Categorize the entity (PERSON, ORGANIZATION, LOCATION, TECHNOLOGY, CONCEPT, EVENT, OTHER).
        *   `entity_description`: Provide a concise yet comprehensive description of the entity.
    *   **Output Format - Entities:** Output a total of 4 fields for each entity, delimited by `<|#|>`, on a single line. The first field *must* be the literal string `entity`.
        *   Format: `entity<|#|>entity_name<|#|>entity_type<|#|>entity_description`

2.  **Relationship Extraction & Output:**
    *   **Identification:** Identify direct, clearly stated, and meaningful relationships between previously extracted entities.
    *   **Relationship Details:** For each binary relationship, extract the following fields:
        *   `source_entity`: The name of the source entity.
        *   `target_entity`: The name of the target entity.
        *   `relationship_keywords`: One or more high-level keywords summarizing the relationship (comma-separated).
        *   `relationship_description`: A concise explanation of the nature of the relationship.
    *   **Output Format - Relationships:** Output a total of 5 fields for each relationship, delimited by `<|#|>`, on a single line. The first field *must* be the literal string `relation`.
        *   Format: `relation<|#|>source_entity<|#|>target_entity<|#|>relationship_keywords<|#|>relationship_description`

---Output Requirements---
1. Output ONLY entities and relations in the specified format
2. End with `<|COMPLETE|>` on the final line
3. No markdown, no explanations, no additional text"""

USER_PROMPT_TEMPLATE = """---Task---
Extract entities and relationships from the input text.

---Input Text---
{text}

---Output Format---
entity<|#|>entity_name<|#|>entity_type<|#|>entity_description
relation<|#|>source_entity<|#|>target_entity<|#|>relationship_keywords<|#|>relationship_description
<|COMPLETE|>"""

# ============================================================================
# TEST CASES (LightRAG Original Examples)
# ============================================================================

TEST_CASES = [
    {
        "id": 1,
        "name": "Simple Test",
        "text": "Python is a programming language created by Guido van Rossum. It was first released in 1991.",
        "expected_entities": 2,  # Python, Guido van Rossum
        "expected_relations": 1,  # Python created_by Guido
    },
    {
        "id": 2,
        "name": "Financial News",
        "text": "Stock markets faced a sharp downturn today as tech giants saw significant declines. The Global Tech Index fell 3.4%, with Nexon Technologies dropping 7.8%.",
        "expected_entities": 3,
        "expected_relations": 2,
    },
    {
        "id": 3,
        "name": "Sports News",
        "text": "At the World Athletics Championship in Tokyo, Noah Carter broke the 100m sprint record using cutting-edge carbon-fiber spikes.",
        "expected_entities": 5,
        "expected_relations": 3,
    },
]


def validate_format(response: str) -> dict:
    """Validate if response follows LightRAG format."""
    lines = response.strip().split("\n")

    entities = []
    relations = []
    has_completion = False
    errors = []

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        if line == COMPLETION_DELIMITER:
            has_completion = True
            continue

        parts = line.split(TUPLE_DELIMITER)

        if parts[0] == "entity":
            if len(parts) != 4:
                errors.append(f"Line {i}: Entity has {len(parts)} fields, expected 4")
            else:
                entities.append({"name": parts[1], "type": parts[2], "description": parts[3]})
        elif parts[0] == "relation":
            if len(parts) != 5:
                errors.append(f"Line {i}: Relation has {len(parts)} fields, expected 5")
            else:
                relations.append(
                    {
                        "source": parts[1],
                        "target": parts[2],
                        "keywords": parts[3],
                        "description": parts[4],
                    }
                )
        else:
            # Check if it's JSON or markdown
            if line.startswith("[") or line.startswith("{") or line.startswith("```"):
                errors.append(
                    f"Line {i}: Wrong format (JSON/markdown instead of delimiter-separated)"
                )
            else:
                errors.append(
                    f"Line {i}: Unknown line type '{parts[0]}' (expected 'entity' or 'relation')"
                )

    return {
        "valid": len(errors) == 0 and has_completion,
        "entities": entities,
        "relations": relations,
        "has_completion": has_completion,
        "errors": errors,
        "entity_count": len(entities),
        "relation_count": len(relations),
    }


def test_model(model: str, test_case: dict, client: Client, use_think_false: bool = False) -> dict:
    """Test a model with a test case."""
    mode = "think=False" if use_think_false else "default"

    start = time.perf_counter()
    try:
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=test_case["text"])},
            ],
            "options": {"temperature": 0.1, "num_predict": 1000, "num_ctx": 8192},
        }

        if use_think_false:
            kwargs["think"] = False

        response = client.chat(**kwargs)
        elapsed = time.perf_counter() - start

        content = response["message"]["content"]
        validation = validate_format(content)

        return {
            "model": model,
            "mode": mode,
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "time": elapsed,
            "valid_format": validation["valid"],
            "entity_count": validation["entity_count"],
            "relation_count": validation["relation_count"],
            "expected_entities": test_case["expected_entities"],
            "expected_relations": test_case["expected_relations"],
            "has_completion": validation["has_completion"],
            "errors": validation["errors"],
            "entities": validation["entities"],
            "relations": validation["relations"],
            "response": content,
            "success": validation["valid"] and validation["entity_count"] > 0,
        }

    except Exception as e:
        elapsed = time.perf_counter() - start
        error_msg = str(e)
        supports_think = "does not support thinking" not in error_msg

        return {
            "model": model,
            "mode": mode,
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "time": elapsed,
            "valid_format": False,
            "entity_count": 0,
            "relation_count": 0,
            "expected_entities": test_case["expected_entities"],
            "expected_relations": test_case["expected_relations"],
            "error": error_msg,
            "supports_think": supports_think,
            "success": False,
        }


def main():
    print(
        """
================================================================================
     LightRAG ORIGINAL FORMAT TEST - Delimiter-Separated Output
================================================================================

Testing models with LightRAG's original prompt format:
- Expected: entity<|#|>name<|#|>type<|#|>description
- Expected: relation<|#|>source<|#|>target<|#|>keywords<|#|>description
- Expected: <|COMPLETE|> at the end
    """
    )

    client = Client()

    # Models to test
    models_to_test = [
        ("hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0", True),
        ("hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M", True),
        ("llama3.2:3b", True),
        ("qwen3:4b", True),
    ]

    results = []

    for model, supports_think in models_to_test:
        model_short = model.split("/")[-1] if "/" in model else model

        print(f"\n{'='*80}")
        print(f"MODEL: {model_short}")
        print(f"{'='*80}")

        for test_case in TEST_CASES:
            # Test default mode
            print(
                f"\n  [{test_case['id']}/3] {test_case['name']} [default]...", end=" ", flush=True
            )
            result = test_model(model, test_case, client, use_think_false=False)
            results.append(result)

            status = "OK" if result["success"] else "FAIL"
            format_ok = "FORMAT_OK" if result["valid_format"] else "FORMAT_ERROR"
            print(
                f"{result['entity_count']}E/{result['relation_count']}R in {result['time']:.1f}s [{status}] [{format_ok}]"
            )

            if result.get("errors"):
                for err in result["errors"][:2]:  # Show first 2 errors
                    print(f"    ERROR: {err}")

            # Test think=False if supported
            if supports_think:
                time.sleep(0.2)
                print(
                    f"  [{test_case['id']}/3] {test_case['name']} [think=False]...",
                    end=" ",
                    flush=True,
                )
                result = test_model(model, test_case, client, use_think_false=True)
                results.append(result)

                status = "OK" if result["success"] else "FAIL"
                format_ok = "FORMAT_OK" if result["valid_format"] else "FORMAT_ERROR"
                print(
                    f"{result['entity_count']}E/{result['relation_count']}R in {result['time']:.1f}s [{status}] [{format_ok}]"
                )

                if result.get("errors"):
                    for err in result["errors"][:2]:
                        print(f"    ERROR: {err}")

    # SUMMARY
    print(f"\n{'='*80}")
    print("SUMMARY: FORMAT COMPLIANCE")
    print(f"{'='*80}\n")

    print(
        f"{'Model':<35} {'Mode':<15} {'Test':<20} {'Format':<12} {'Entities':<10} {'Relations':<10} {'Status'}"
    )
    print(f"{'-'*35} {'-'*15} {'-'*20} {'-'*12} {'-'*10} {'-'*10} {'-'*8}")

    for r in results:
        if "error" in r:
            continue

        model_short = r["model"].split("/")[-1] if "/" in r["model"] else r["model"]
        format_status = "VALID" if r["valid_format"] else "INVALID"
        status = "OK" if r["success"] else "FAIL"

        print(
            f"{model_short:<35} {r['mode']:<15} {r['test_name']:<20} {format_status:<12} "
            f"{r['entity_count']}/{r['expected_entities']:<8} {r['relation_count']}/{r['expected_relations']:<8} {status}"
        )

    # BEST PERFORMERS
    print(f"\n{'='*80}")
    print("BEST FORMAT COMPLIANCE")
    print(f"{'='*80}\n")

    successful = [r for r in results if r.get("success")]
    if successful:
        # Best by entities + relations
        best = max(successful, key=lambda r: r["entity_count"] + r["relation_count"])
        print(
            f"Best Extraction: {best['model'].split('/')[-1] if '/' in best['model'] else best['model']}"
        )
        print(f"  Mode: {best['mode']}")
        print(f"  Test: {best['test_name']}")
        print(f"  Entities: {best['entity_count']}, Relations: {best['relation_count']}")
        print(f"  Time: {best['time']:.2f}s")

        # Fastest valid
        fastest = min(successful, key=lambda r: r["time"])
        print(
            f"\nFastest Valid: {fastest['model'].split('/')[-1] if '/' in fastest['model'] else fastest['model']}"
        )
        print(f"  Mode: {fastest['mode']}")
        print(f"  Time: {fastest['time']:.2f}s")
        print(f"  Entities: {fastest['entity_count']}, Relations: {fastest['relation_count']}")

    # FORMAT ERRORS SUMMARY
    print(f"\n{'='*80}")
    print("COMMON FORMAT ERRORS")
    print(f"{'='*80}\n")

    error_types = {}
    for r in results:
        if r.get("errors"):
            for error in r["errors"]:
                # Categorize errors
                if "JSON" in error or "markdown" in error:
                    error_types["Wrong Format (JSON/Markdown)"] = (
                        error_types.get("Wrong Format (JSON/Markdown)", 0) + 1
                    )
                elif "fields" in error:
                    error_types["Wrong Field Count"] = error_types.get("Wrong Field Count", 0) + 1
                elif "Unknown line type" in error:
                    error_types["Unknown Line Type"] = error_types.get("Unknown Line Type", 0) + 1
                else:
                    error_types["Other"] = error_types.get("Other", 0) + 1

    for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
        print(f"  {error_type}: {count} occurrences")

    # Save results
    output_file = "lightrag_original_format_test.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Detailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
