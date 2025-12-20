#!/usr/bin/env python3
"""Test NuExtract models with JSON output format, then convert to LightRAG format.

Sprint 13 TD-31: Test NuExtract models with their native JSON format,
then convert to LightRAG's delimiter-separated format.
"""

import json
import time
from datetime import datetime
from pathlib import Path

from ollama import Client

# ============================================================================
# LIGHTRAG DELIMITERS (for conversion)
# ============================================================================
TUPLE_DELIMITER = "<|#|>"
COMPLETION_DELIMITER = "<|COMPLETE|>"

# ============================================================================
# JSON-BASED SYSTEM PROMPT for NuExtract
# ============================================================================
SYSTEM_PROMPT_JSON = """---Role---
You are a Knowledge Graph Specialist responsible for extracting entities and relationships from the input text.

---Instructions---
1. **Entity Extraction:** Identify clearly defined and meaningful entities in the input text.
   - For each entity, extract:
     - `name`: The name of the entity
     - `type`: Category (PERSON, ORGANIZATION, LOCATION, TECHNOLOGY, CONCEPT, EVENT, OTHER)
     - `description`: Concise yet comprehensive description

2. **Relationship Extraction:** Identify direct, clearly stated relationships between extracted entities.
   - For each relationship, extract:
     - `source`: Name of the source entity
     - `target`: Name of the target entity
     - `keywords`: High-level keywords summarizing the relationship (comma-separated)
     - `description`: Concise explanation of the relationship

---Output Requirements---
Output valid JSON with two arrays: "entities" and "relations".
No markdown formatting, no code blocks, just pure JSON."""

# ============================================================================
# JSON USER PROMPT TEMPLATE
# ============================================================================
USER_PROMPT_TEMPLATE_JSON = """---Task---
Extract entities and relationships from the input text and output as JSON.

---Input Text---
{text}

---Output Format---
{{
  "entities": [
    {{"name": "EntityName", "type": "CATEGORY", "description": "Entity description"}},
    ...
  ],
  "relations": [
    {{"source": "SourceEntity", "target": "TargetEntity", "keywords": "keyword1, keyword2", "description": "Relationship description"}},
    ...
  ]
}}

Output only valid JSON, no markdown, no code blocks."""

# ============================================================================
# TEST CASES - Same as original LightRAG examples
# ============================================================================

# Example 1 from lightrag/prompt.py (Fiction narrative)
FICTION_TEXT = """Alex is a powerful person, but Jordan is smarter and more talented. They worked at TechCorp together. Jordan left to found DevStart, a startup focused on AI research. Alex later joined DevStart as Chief Technology Officer. The company is developing a new framework called NeuralGraph, which they plan to present at the AI Summit in San Francisco. Taylor is working with Jordan on this project, while Cruz is managing partnerships with OpenResearch. The Device they're building uses quantum computing."""

# Example 2 from lightrag/prompt.py (Financial news)
FINANCIAL_TEXT = """Stock markets faced a sharp downturn today as tech giants saw significant declines. The Global Tech Index fell 3.4%, with Nexon Technologies dropping 7.8% after disappointing quarterly results. Analysts at MarketWatch attribute the selloff to concerns over rising interest rates and slowing consumer demand. Meanwhile, energy stocks showed resilience, with GreenPower Corp gaining 2.1% on strong earnings."""

# Example 3 from lightrag/prompt.py (Sports news)
SPORTS_TEXT = """At the World Athletics Championship in Tokyo, Noah Carter broke the 100-meter sprint record with a time of 9.58 seconds. The 24-year-old American athlete, training under Coach Maria Santos at the Elite Performance Center in California, attributed his success to innovative training methods and cutting-edge carbon-fiber spikes developed by SpeedTech. Carter's achievement surpassed the previous record held by Marcus Johnson since 2015."""

TEST_CASES = [
    {
        "id": 1,
        "name": "Fiction (LightRAG Example 1)",
        "text": FICTION_TEXT,
        "expected_entities": 11,
        "expected_relations": 11,
    },
    {
        "id": 2,
        "name": "Financial (LightRAG Example 2)",
        "text": FINANCIAL_TEXT,
        "expected_entities": 4,
        "expected_relations": 4,
    },
    {
        "id": 3,
        "name": "Sports (LightRAG Example 3)",
        "text": SPORTS_TEXT,
        "expected_entities": 10,
        "expected_relations": 8,
    },
]


def convert_json_to_lightrag(json_data: dict) -> str:
    """Convert JSON format to LightRAG delimiter-separated format.

    Args:
        json_data: Dictionary with 'entities' and 'relations' arrays

    Returns:
        LightRAG formatted string
    """
    lines = []

    # Convert entities
    for entity in json_data.get("entities", []):
        name = entity.get("name", "").strip()
        etype = entity.get("type", "OTHER").strip().upper()
        desc = entity.get("description", "").strip()

        if name:  # Only add if we have a name
            line = f"entity{TUPLE_DELIMITER}{name}{TUPLE_DELIMITER}{etype}{TUPLE_DELIMITER}{desc}"
            lines.append(line)

    # Convert relations
    for relation in json_data.get("relations", []):
        source = relation.get("source", "").strip()
        target = relation.get("target", "").strip()
        keywords = relation.get("keywords", "").strip()
        desc = relation.get("description", "").strip()

        if source and target:  # Only add if we have source and target
            line = f"relation{TUPLE_DELIMITER}{source}{TUPLE_DELIMITER}{target}{TUPLE_DELIMITER}{keywords}{TUPLE_DELIMITER}{desc}"
            lines.append(line)

    # Add completion marker
    lines.append(COMPLETION_DELIMITER)

    return "\n".join(lines)


def validate_json_and_convert(response: str) -> dict:
    """Validate JSON response and convert to LightRAG format.

    Returns:
        Dictionary with validation results and converted format
    """
    result = {
        "json_valid": False,
        "json_data": None,
        "lightrag_format": "",
        "entity_count": 0,
        "relation_count": 0,
        "errors": [],
    }

    # Try to parse JSON
    try:
        # Remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Extract JSON from code block
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        json_data = json.loads(cleaned)
        result["json_valid"] = True
        result["json_data"] = json_data

        # Count entities and relations
        result["entity_count"] = len(json_data.get("entities", []))
        result["relation_count"] = len(json_data.get("relations", []))

        # Convert to LightRAG format
        result["lightrag_format"] = convert_json_to_lightrag(json_data)

    except json.JSONDecodeError as e:
        result["errors"].append(f"JSON parsing error: {e}")
    except Exception as e:
        result["errors"].append(f"Conversion error: {e}")

    return result


def append_to_log(
    log_path: Path,
    test_case: dict,
    system_prompt: str,
    user_prompt: str,
    raw_response: str,
    validation: dict,
    start_time: datetime,
    end_time: datetime,
    duration: float,
):
    """Append test execution to model's log file."""
    log_content = f"""
{'='*80}
TEST CASE {test_case['id']}: {test_case['name']}
{'='*80}

Start Time: {start_time.isoformat()}
End Time: {end_time.isoformat()}
Duration: {duration:.2f}s
Expected: {test_case['expected_entities']} entities, {test_case['expected_relations']} relations

{'='*80}
SYSTEM PROMPT:
{'='*80}
{system_prompt}

{'='*80}
USER PROMPT:
{'='*80}
{user_prompt}

{'='*80}
RAW JSON RESPONSE FROM LLM:
{'='*80}
{raw_response}

{'='*80}
VALIDATION RESULTS:
{'='*80}
JSON Valid: {validation['json_valid']}
Entities Found: {validation['entity_count']}
Relations Found: {validation['relation_count']}
Errors: {validation['errors']}

{'='*80}
CONVERTED LIGHTRAG FORMAT:
{'='*80}
{validation['lightrag_format']}

"""

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_content)


def test_model(
    model: str, test_case: dict, client: Client, log_path: Path, use_think_false: bool = False
) -> dict:
    """Test a model with JSON format and convert to LightRAG."""
    mode = "think=False" if use_think_false else "default"

    # Prepare prompts
    user_prompt = USER_PROMPT_TEMPLATE_JSON.format(text=test_case["text"])

    # Record start time
    start_time = datetime.now()
    start = time.perf_counter()

    try:
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_JSON},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": 0.1,
                "num_predict": 2000,
                "num_ctx": 16384,  # LightRAG's context window size
            },
            "format": "json",  # Request JSON format from Ollama
        }

        if use_think_false:
            kwargs["think"] = False

        response = client.chat(**kwargs)
        elapsed = time.perf_counter() - start
        end_time = datetime.now()

        content = response["message"]["content"]
        validation = validate_json_and_convert(content)

        # Append to log file
        append_to_log(
            log_path=log_path,
            test_case=test_case,
            system_prompt=SYSTEM_PROMPT_JSON,
            user_prompt=user_prompt,
            raw_response=content,
            validation=validation,
            start_time=start_time,
            end_time=end_time,
            duration=elapsed,
        )

        return {
            "model": model,
            "mode": mode,
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "time": elapsed,
            "json_valid": validation["json_valid"],
            "entities_found": validation["entity_count"],
            "relations_found": validation["relation_count"],
            "entities_expected": test_case["expected_entities"],
            "relations_expected": test_case["expected_relations"],
            "errors": validation["errors"],
            "status": (
                "PASS" if validation["json_valid"] and validation["entity_count"] > 0 else "FAIL"
            ),
        }

    except Exception as e:
        elapsed = time.perf_counter() - start
        end_time = datetime.now()

        error_msg = f"Exception during test: {e}"

        # Log the error
        append_to_log(
            log_path=log_path,
            test_case=test_case,
            system_prompt=SYSTEM_PROMPT_JSON,
            user_prompt=user_prompt,
            raw_response=f"ERROR: {error_msg}",
            validation={
                "json_valid": False,
                "entity_count": 0,
                "relation_count": 0,
                "errors": [error_msg],
                "lightrag_format": "",
            },
            start_time=start_time,
            end_time=end_time,
            duration=elapsed,
        )

        return {
            "model": model,
            "mode": mode,
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "time": elapsed,
            "json_valid": False,
            "entities_found": 0,
            "relations_found": 0,
            "entities_expected": test_case["expected_entities"],
            "relations_expected": test_case["expected_relations"],
            "errors": [error_msg],
            "status": "ERROR",
        }


def main():
    """Main test execution."""
    print(
        f"""{'='*80}
     NuExtract JSON Format Test - Convert to LightRAG
{'='*80}

Testing NuExtract models with JSON output format:
- System Prompt: Requests JSON with entities and relations arrays
- Conversion: JSON -> LightRAG delimiter-separated format
- Context Window: 16384 (LightRAG default)

Expected JSON format:
{{"entities": [{{"name": "X", "type": "Y", "description": "Z"}}], "relations": [...]}}

Converts to LightRAG format:
entity<|#|>X<|#|>Y<|#|>Z
    """
    )

    client = Client()

    # Models to test - NuExtract variants only
    models_to_test = [
        ("hf.co/mradermacher/NuExtract-2.0-4B-i1-GGUF:Q4_K_M", True),
        ("hf.co/mradermacher/NuExtract-2.0-4B-i1-GGUF:Q6_K", True),
    ]

    results = []

    log_dir = Path("logs/nuextract_json_format")
    log_dir.mkdir(parents=True, exist_ok=True)

    for model, supports_think in models_to_test:
        model_short = model.split("/")[-1] if "/" in model else model

        print(f"\n{'='*80}")
        print(f"MODEL: {model_short}")
        print(f"{'='*80}")

        # ====================================================================
        # WARMUP: Load model before first measured test
        # ====================================================================
        print("\n  [WARMUP] Loading model (not measured)...", end=" ", flush=True)
        try:
            client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello"},
                ],
                options={"num_ctx": 16384},
            )
            print("OK")
        except Exception as e:
            print(f"WARNING: {e}")

        # Test default mode
        mode = "default"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{timestamp}_{model_short.replace(':', '_')}_{mode}.log"
        log_path = log_dir / log_filename

        # Write log header
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(
                f"""{'='*80}
NuExtract JSON FORMAT TEST LOG
{'='*80}

Model: {model}
Mode: {mode}
Test Suite: All 3 LightRAG Original Examples
Context Window: 16384
Start Time: {datetime.now().isoformat()}

{'='*80}

"""
            )

        for test_case in TEST_CASES:
            print(
                f"\n  [{test_case['id']}/3] {test_case['name']} [default]...", end=" ", flush=True
            )
            result = test_model(model, test_case, client, log_path, use_think_false=False)
            results.append(result)

            status = "OK" if result["status"] == "PASS" else "FAIL"
            print(
                f"{result['entities_found']}E/{result['relations_found']}R in {result['time']:.1f}s [{status}]"
            )
            if result["errors"]:
                for error in result["errors"][:2]:  # Show first 2 errors
                    print(f"    ERROR: {error}")

        # Test with think=False if supported
        if supports_think:
            mode = "think=False"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{timestamp}_{model_short.replace(':', '_')}_thinkFalse.log"
            log_path = log_dir / log_filename

            # Write log header
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(
                    f"""{'='*80}
NuExtract JSON FORMAT TEST LOG
{'='*80}

Model: {model}
Mode: {mode}
Test Suite: All 3 LightRAG Original Examples
Context Window: 16384
Start Time: {datetime.now().isoformat()}

{'='*80}

"""
                )

            for test_case in TEST_CASES:
                print(
                    f"  [{test_case['id']}/3] {test_case['name']} [think=False]...",
                    end=" ",
                    flush=True,
                )
                result = test_model(model, test_case, client, log_path, use_think_false=True)
                results.append(result)

                status = "OK" if result["status"] == "PASS" else "FAIL"
                print(
                    f"{result['entities_found']}E/{result['relations_found']}R in {result['time']:.1f}s [{status}]"
                )
                if result["errors"]:
                    for error in result["errors"][:2]:
                        print(f"    ERROR: {error}")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print(f"\n{'='*80}")
    print("SUMMARY: JSON VALIDATION & CONVERSION")
    print(f"{'='*80}\n")

    # Summary table
    print(
        f"{'Model':<35} {'Mode':<15} {'Test':<30} {'JSON':<8} {'Entities':<12} {'Relations':<12} {'Status':<8}"
    )
    print(f"{'-'*35} {'-'*15} {'-'*30} {'-'*8} {'-'*12} {'-'*12} {'-'*8}")

    for r in results:
        model_short = r["model"].split("/")[-1] if "/" in r["model"] else r["model"]
        json_status = "VALID" if r["json_valid"] else "INVALID"
        entity_str = f"{r['entities_found']}/{r['entities_expected']}"
        relation_str = f"{r['relations_found']}/{r['relations_expected']}"

        print(
            f"{model_short:<35} {r['mode']:<15} {r['test_name']:<30} {json_status:<8} {entity_str:<12} {relation_str:<12} {r['status']:<8}"
        )

    # Save results
    output_file = Path("nuextract_json_format_test.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*80}")
    print(f"[OK] Detailed results saved to: {output_file}")
    print(f"[OK] Detailed logs saved to: {log_dir}/")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
