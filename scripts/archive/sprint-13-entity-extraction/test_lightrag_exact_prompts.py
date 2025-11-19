#!/usr/bin/env python3
"""Test models with EXACT LightRAG prompts from lightrag/prompt.py.

Sprint 13 TD-31: Verify models can follow LightRAG's delimiter-separated format.
"""

import json
import re
import time
from pathlib import Path
from datetime import datetime
from ollama import Client

# ============================================================================
# EXACT DELIMITERS from lightrag/prompt.py
# ============================================================================
TUPLE_DELIMITER = "<|#|>"
COMPLETION_DELIMITER = "<|COMPLETE|>"

# ============================================================================
# EXACT SYSTEM PROMPT from lightrag/prompt.py (entity_extraction_system_prompt)
# ============================================================================
SYSTEM_PROMPT = f"""---Role---
You are a Knowledge Graph Specialist responsible for extracting entities and relationships from the input text.

---Instructions---
1.  **Entity Extraction & Output:**
    *   **Identification:** Identify clearly defined and meaningful entities in the input text.
    *   **Entity Details:** For each identified entity, extract the following information:
        *   `entity_name`: The name of the entity.
        *   `entity_type`: Categorize the entity (PERSON, ORGANIZATION, LOCATION, TECHNOLOGY, CONCEPT, EVENT, OTHER).
        *   `entity_description`: Provide a concise yet comprehensive description of the entity.
    *   **Output Format - Entities:** Output a total of 4 fields for each entity, delimited by `{TUPLE_DELIMITER}`, on a single line. The first field *must* be the literal string `entity`.
        *   Format: `entity{TUPLE_DELIMITER}entity_name{TUPLE_DELIMITER}entity_type{TUPLE_DELIMITER}entity_description`

2.  **Relationship Extraction & Output:**
    *   **Identification:** Identify direct, clearly stated, and meaningful relationships between previously extracted entities.
    *   **Relationship Details:** For each binary relationship, extract the following fields:
        *   `source_entity`: The name of the source entity.
        *   `target_entity`: The name of the target entity.
        *   `relationship_keywords`: One or more high-level keywords summarizing the relationship (comma-separated).
        *   `relationship_description`: A concise explanation of the nature of the relationship.
    *   **Output Format - Relationships:** Output a total of 5 fields for each relationship, delimited by `{TUPLE_DELIMITER}`, on a single line. The first field *must* be the literal string `relation`.
        *   Format: `relation{TUPLE_DELIMITER}source_entity{TUPLE_DELIMITER}target_entity{TUPLE_DELIMITER}relationship_keywords{TUPLE_DELIMITER}relationship_description`

---Output Requirements---
1. Output ONLY entities and relations in the specified format
2. End with `{COMPLETION_DELIMITER}` on the final line
3. No markdown, no explanations, no additional text"""

# ============================================================================
# EXACT USER PROMPT from lightrag/prompt.py (entity_extraction_user_prompt)
# ============================================================================
USER_PROMPT_TEMPLATE = f"""---Task---
Extract entities and relationships from the input text.

---Input Text---
{{text}}

---Output Format---
entity{TUPLE_DELIMITER}entity_name{TUPLE_DELIMITER}entity_type{TUPLE_DELIMITER}entity_description
relation{TUPLE_DELIMITER}source_entity{TUPLE_DELIMITER}target_entity{TUPLE_DELIMITER}relationship_keywords{TUPLE_DELIMITER}relationship_description
{COMPLETION_DELIMITER}"""

# ============================================================================
# TEST CASES - Using LightRAG's Example Texts
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


def append_to_log(
    log_path: Path,
    test_case: dict,
    system_prompt: str,
    user_prompt: str,
    response: str,
    validation: dict,
    start_time: datetime,
    end_time: datetime,
    duration: float,
):
    """Append test execution to model's log file."""
    # Format test content
    log_content = f"""
{'='*80}
TEST CASE {test_case['id']}: {test_case['name']}
{'='*80}

Start Time: {start_time.isoformat()}
End Time: {end_time.isoformat()}
Duration: {duration:.2f}s

Expected: {test_case['expected_entities']} entities, {test_case['expected_relations']} relations

--------------------------------------------------------------------------------
SYSTEM PROMPT:
--------------------------------------------------------------------------------

{system_prompt}

--------------------------------------------------------------------------------
USER PROMPT:
--------------------------------------------------------------------------------

{user_prompt}

--------------------------------------------------------------------------------
RESPONSE FROM LLM:
--------------------------------------------------------------------------------

{response}

--------------------------------------------------------------------------------
VALIDATION RESULTS:
--------------------------------------------------------------------------------

Valid Format: {validation['valid']}
Has Completion Delimiter: {validation['has_completion']}
Entities Found: {validation['entity_count']}
Relations Found: {validation['relation_count']}

"""

    # Add entities
    if validation["entities"]:
        log_content += "\n--- EXTRACTED ENTITIES ---\n\n"
        for i, entity in enumerate(validation["entities"], 1):
            log_content += f"{i}. {entity['name']} ({entity['type']})\n"
            log_content += f"   Description: {entity['description']}\n\n"

    # Add relations
    if validation["relations"]:
        log_content += "\n--- EXTRACTED RELATIONS ---\n\n"
        for i, relation in enumerate(validation["relations"], 1):
            log_content += f"{i}. {relation['source']} -> {relation['target']}\n"
            log_content += f"   Keywords: {relation['keywords']}\n"
            log_content += f"   Description: {relation['description']}\n\n"

    # Add errors
    if validation["errors"]:
        log_content += "\n--- FORMAT ERRORS ---\n\n"
        for error in validation["errors"]:
            log_content += f"  - {error}\n"

    log_content += "\n"

    # Append to log file
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_content)


def validate_format(response: str) -> dict:
    """Validate if response follows EXACT LightRAG format."""
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


def test_model(
    model: str, test_case: dict, client: Client, log_path: Path, use_think_false: bool = False
) -> dict:
    """Test a model with a test case using EXACT LightRAG prompts."""
    mode = "think=False" if use_think_false else "default"

    # Prepare prompts
    user_prompt = USER_PROMPT_TEMPLATE.format(text=test_case["text"])

    # Record start time
    start_time = datetime.now()
    start = time.perf_counter()

    try:
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": 0.1, "num_predict": 2000, "num_ctx": 8192},
        }

        if use_think_false:
            kwargs["think"] = False

        response = client.chat(**kwargs)
        elapsed = time.perf_counter() - start
        end_time = datetime.now()

        content = response["message"]["content"]
        validation = validate_format(content)

        # Append to log file
        append_to_log(
            log_path=log_path,
            test_case=test_case,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response=content,
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
            "log_file": str(log_path),
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
     LightRAG EXACT PROMPT TEST - From lightrag/prompt.py
================================================================================

Testing models with EXACT prompts from LightRAG source code:
- System Prompt: entity_extraction_system_prompt
- User Prompt: entity_extraction_user_prompt
- Examples: All 3 original examples from prompt.py

Expected format:
- entity<|#|>name<|#|>type<|#|>description
- relation<|#|>source<|#|>target<|#|>keywords<|#|>description
- <|COMPLETE|> at the end
    """
    )

    client = Client()

    # Models to test
    models_to_test = [
        # NuExtract Q6_K - Higher quantization for comparison
        ("hf.co/mradermacher/NuExtract-2.0-4B-i1-GGUF:Q6_K", True),
        # Previous baseline models (commented out for this run)
        # ("hf.co/mradermacher/NuExtract-2.0-4B-i1-GGUF:Q4_K_M", True),
        # ("hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0", True),
        # ("hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M", True),
        # ("llama3.2:3b", True),
        # ("qwen3:4b", True),
    ]

    results = []

    log_dir = Path("logs/lightrag_exact_prompts")
    log_dir.mkdir(parents=True, exist_ok=True)

    for model, supports_think in models_to_test:
        model_short = model.split("/")[-1] if "/" in model else model

        print(f"\n{'='*80}")
        print(f"MODEL: {model_short}")
        print(f"{'='*80}")

        # Test default mode
        mode = "default"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{timestamp}_{model_short.replace(':', '_')}_{mode}.log"
        log_path = log_dir / log_filename

        # Write log header
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(
                f"""{'='*80}
LightRAG EXACT PROMPTS TEST LOG
{'='*80}

Model: {model}
Mode: {mode}
Test Suite: All 3 LightRAG Original Examples
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

            status = "OK" if result["success"] else "FAIL"
            format_ok = "FORMAT_OK" if result["valid_format"] else "FORMAT_ERROR"
            print(
                f"{result['entity_count']}E/{result['relation_count']}R in {result['time']:.1f}s [{status}] [{format_ok}]"
            )

            if result.get("errors"):
                for err in result["errors"][:2]:  # Show first 2 errors
                    print(f"    ERROR: {err}")

        # Write log footer
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\nEND OF LOG - {datetime.now().isoformat()}\n{'='*80}\n")

        # Test think=False if supported
        if supports_think:
            time.sleep(0.2)
            mode = "think=False"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = (
                f"{timestamp}_{model_short.replace(':', '_')}_{mode.replace('=', '')}.log"
            )
            log_path = log_dir / log_filename

            # Write log header
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(
                    f"""{'='*80}
LightRAG EXACT PROMPTS TEST LOG
{'='*80}

Model: {model}
Mode: {mode}
Test Suite: All 3 LightRAG Original Examples
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

                status = "OK" if result["success"] else "FAIL"
                format_ok = "FORMAT_OK" if result["valid_format"] else "FORMAT_ERROR"
                print(
                    f"{result['entity_count']}E/{result['relation_count']}R in {result['time']:.1f}s [{status}] [{format_ok}]"
                )

                if result.get("errors"):
                    for err in result["errors"][:2]:
                        print(f"    ERROR: {err}")

            # Write log footer
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*80}\nEND OF LOG - {datetime.now().isoformat()}\n{'='*80}\n")

    # SUMMARY
    print(f"\n{'='*80}")
    print("SUMMARY: FORMAT COMPLIANCE")
    print(f"{'='*80}\n")

    print(
        f"{'Model':<35} {'Mode':<15} {'Test':<30} {'Format':<12} {'Entities':<12} {'Relations':<12} {'Status'}"
    )
    print(f"{'-'*35} {'-'*15} {'-'*30} {'-'*12} {'-'*12} {'-'*12} {'-'*8}")

    for r in results:
        if "error" in r and not r.get("entity_count"):
            continue

        model_short = r["model"].split("/")[-1] if "/" in r["model"] else r["model"]
        format_status = "VALID" if r["valid_format"] else "INVALID"
        status = "OK" if r["success"] else "FAIL"

        print(
            f"{model_short:<35} {r['mode']:<15} {r['test_name']:<30} {format_status:<12} "
            f"{r['entity_count']}/{r['expected_entities']:<10} {r['relation_count']}/{r['expected_relations']:<10} {status}"
        )

    # ACCURACY ANALYSIS
    print(f"\n{'='*80}")
    print("ACCURACY ANALYSIS (vs Expected Counts)")
    print(f"{'='*80}\n")

    successful = [r for r in results if r.get("success")]
    if successful:
        for test_case in TEST_CASES:
            print(f"\nTest: {test_case['name']}")
            print(
                f"  Expected: {test_case['expected_entities']}E / {test_case['expected_relations']}R"
            )

            test_results = [r for r in successful if r["test_id"] == test_case["id"]]
            if test_results:
                for r in test_results:
                    model_short = r["model"].split("/")[-1] if "/" in r["model"] else r["model"]
                    entity_accuracy = (
                        (r["entity_count"] / test_case["expected_entities"] * 100)
                        if test_case["expected_entities"] > 0
                        else 0
                    )
                    relation_accuracy = (
                        (r["relation_count"] / test_case["expected_relations"] * 100)
                        if test_case["expected_relations"] > 0
                        else 0
                    )
                    print(
                        f"  {model_short} [{r['mode']}]: {r['entity_count']}E ({entity_accuracy:.0f}%) / {r['relation_count']}R ({relation_accuracy:.0f}%) in {r['time']:.1f}s"
                    )

    # BEST PERFORMERS
    print(f"\n{'='*80}")
    print("BEST PERFORMERS")
    print(f"{'='*80}\n")

    if successful:
        # Best by total extraction (entities + relations)
        best = max(successful, key=lambda r: r["entity_count"] + r["relation_count"])
        print(f"Most Comprehensive Extraction:")
        print(f"  Model: {best['model'].split('/')[-1] if '/' in best['model'] else best['model']}")
        print(f"  Mode: {best['mode']}")
        print(f"  Test: {best['test_name']}")
        print(f"  Extracted: {best['entity_count']} entities, {best['relation_count']} relations")
        print(f"  Time: {best['time']:.2f}s")

        # Fastest valid
        fastest = min(successful, key=lambda r: r["time"])
        print(f"\nFastest Valid Extraction:")
        print(
            f"  Model: {fastest['model'].split('/')[-1] if '/' in fastest['model'] else fastest['model']}"
        )
        print(f"  Mode: {fastest['mode']}")
        print(f"  Time: {fastest['time']:.2f}s")
        print(
            f"  Extracted: {fastest['entity_count']} entities, {fastest['relation_count']} relations"
        )

        # Best balance (entities+relations per second)
        balanced = max(
            successful,
            key=lambda r: (
                (r["entity_count"] + r["relation_count"]) / r["time"] if r["time"] > 0 else 0
            ),
        )
        score = (balanced["entity_count"] + balanced["relation_count"]) / balanced["time"]
        print(f"\nBest Balance (throughput):")
        print(
            f"  Model: {balanced['model'].split('/')[-1] if '/' in balanced['model'] else balanced['model']}"
        )
        print(f"  Mode: {balanced['mode']}")
        print(f"  Score: {score:.2f} items/sec")
        print(f"  Time: {balanced['time']:.2f}s")

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

    if error_types:
        for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f"  {error_type}: {count} occurrences")
    else:
        print("  No format errors detected!")

    # RECOMMENDATION
    print(f"\n{'='*80}")
    print("RECOMMENDATION FOR PRODUCTION")
    print(f"{'='*80}\n")

    if successful:
        # Group by model
        model_stats = {}
        for r in successful:
            model = r["model"]
            if model not in model_stats:
                model_stats[model] = {
                    "total_entities": 0,
                    "total_relations": 0,
                    "total_time": 0,
                    "count": 0,
                    "modes": {},
                }
            model_stats[model]["total_entities"] += r["entity_count"]
            model_stats[model]["total_relations"] += r["relation_count"]
            model_stats[model]["total_time"] += r["time"]
            model_stats[model]["count"] += 1

            if r["mode"] not in model_stats[model]["modes"]:
                model_stats[model]["modes"][r["mode"]] = {"time": 0, "count": 0}
            model_stats[model]["modes"][r["mode"]]["time"] += r["time"]
            model_stats[model]["modes"][r["mode"]]["count"] += 1

        for model, stats in model_stats.items():
            model_short = model.split("/")[-1] if "/" in model else model
            avg_entities = stats["total_entities"] / stats["count"]
            avg_relations = stats["total_relations"] / stats["count"]
            avg_time = stats["total_time"] / stats["count"]

            print(f"\n{model_short}:")
            print(f"  Avg per test: {avg_entities:.1f} entities, {avg_relations:.1f} relations")
            print(f"  Avg time: {avg_time:.1f}s")

            for mode, mode_stats in stats["modes"].items():
                mode_avg_time = mode_stats["time"] / mode_stats["count"]
                print(f"    [{mode}]: {mode_avg_time:.1f}s avg")

    # Save results
    output_file = "lightrag_exact_prompts_test.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Detailed results saved to: {output_file}")
    print(f"[OK] Detailed logs saved to: logs/lightrag_exact_prompts/")


if __name__ == "__main__":
    main()
