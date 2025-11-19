"""
Comprehensive test script to evaluate all available Ollama models for LightRAG compatibility.
Tests each model with the correct LightRAG delimiter format (<|#|>).
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import ollama


# Test document from E2E test
TEST_TEXT = """
Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.
Steve Jobs served as CEO and led product development. The company's headquarters
is located in Cupertino, California. Apple is known for products like the iPhone,
iPad, and Mac computers.
"""

# LightRAG-style prompt with correct delimiter <|#|>
LIGHTRAG_PROMPT_TEMPLATE = """---Role---
You are a Knowledge Graph Specialist responsible for extracting entities and relationships from the input text.

---Instructions---
1.  **Entity Extraction & Output:**
    *   **Identification:** Identify clearly defined and meaningful entities in the input text.
    *   **Entity Details:** For each identified entity, extract the following information:
        *   `entity_name`: The name of the entity. Capitalize the first letter of each significant word (title case).
        *   `entity_type`: Categorize the entity using one of the following types: [organization, person, location, product, event, date]. If none apply, classify it as `Other`.
        *   `entity_description`: Provide a concise yet comprehensive description of the entity's attributes and activities.
    *   **Output Format - Entities:** Output a total of 4 fields for each entity, delimited by `<|#|>`, on a single line. The first field *must* be the literal string `entity`.
        *   Format: `entity<|#|>entity_name<|#|>entity_type<|#|>entity_description`

2.  **Relationship Extraction & Output:**
    *   **Identification:** Identify direct, clearly stated, and meaningful relationships between previously extracted entities.
    *   **Relationship Details:** For each binary relationship, extract the following fields:
        *   `source_entity`: The name of the source entity. Use consistent naming with entity extraction.
        *   `target_entity`: The name of the target entity. Use consistent naming with entity extraction.
        *   `relationship_keywords`: One or more high-level keywords summarizing the relationship (comma-separated).
        *   `relationship_description`: A concise explanation of the nature of the relationship.
    *   **Output Format - Relationships:** Output a total of 5 fields for each relationship, delimited by `<|#|>`, on a single line. The first field *must* be the literal string `relation`.
        *   Format: `relation<|#|>source_entity<|#|>target_entity<|#|>relationship_keywords<|#|>relationship_description`

3.  **Output Order:** Output all extracted entities first, followed by all extracted relationships.

4.  **Completion Signal:** Output the literal string `<|COMPLETE|>` only after all entities and relationships have been completely extracted.

---Example---
Input: "Alex works at Control, coordinating with Taylor."
Output:
entity<|#|>Alex<|#|>person<|#|>Alex is a coordinator.
entity<|#|>Control<|#|>organization<|#|>Control is the central authority.
entity<|#|>Taylor<|#|>person<|#|>Taylor is a team member.
relation<|#|>Alex<|#|>Control<|#|>employment<|#|>Alex works at Control.
relation<|#|>Alex<|#|>Taylor<|#|>collaboration<|#|>Alex coordinates with Taylor.
<|COMPLETE|>

---Task---
Extract entities and relationships from the following text:

{text}

---Output---
"""


async def test_model(model_name: str, client: ollama.AsyncClient) -> Dict[str, Any]:
    """Test a single model with LightRAG-style extraction."""
    result = {
        "model": model_name,
        "success": False,
        "entities_found": 0,
        "relationships_found": 0,
        "uses_correct_delimiter": False,
        "has_completion_marker": False,
        "generation_time_seconds": 0,
        "error": None,
        "output_preview": "",
    }

    prompt = LIGHTRAG_PROMPT_TEMPLATE.format(text=TEST_TEXT.strip())

    try:
        start_time = time.time()

        response = await client.generate(
            model=model_name,
            prompt=prompt,
            options={
                "temperature": 0.0,
                "num_predict": 2000,
                "num_ctx": 32768,
            },
        )

        result["generation_time_seconds"] = round(time.time() - start_time, 2)
        output = response["response"]
        result["output_preview"] = output[:500] + "..." if len(output) > 500 else output

        # Check for correct delimiter
        if "<|#|>" in output:
            result["uses_correct_delimiter"] = True

        # Count entities
        result["entities_found"] = output.count("entity<|#|>")

        # Count relationships
        result["relationships_found"] = output.count("relation<|#|>")

        # Check for completion marker
        if "<|COMPLETE|>" in output:
            result["has_completion_marker"] = True

        # Success if we found entities with correct delimiter
        if result["entities_found"] > 0 and result["uses_correct_delimiter"]:
            result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


async def main():
    """Test all available Ollama models."""
    client = ollama.AsyncClient()

    # Get list of available models
    models_response = await client.list()
    available_models = [
        m.get("name", m.get("model", "unknown")) for m in models_response.get("models", [])
    ]

    # Filter to LLM models (exclude embedding models)
    llm_models = [m for m in available_models if "embed" not in m.lower()]

    print("=" * 100)
    print("LIGHTRAG MODEL COMPATIBILITY TEST")
    print("=" * 100)
    print(f"\nTesting {len(llm_models)} models with LightRAG delimiter format (<|#|>)")
    print(f"Test document: Apple Inc. founding story (4 expected entities, 3+ relationships)\n")

    results = []

    for i, model in enumerate(llm_models, 1):
        print(f"[{i}/{len(llm_models)}] Testing {model}...", end=" ", flush=True)
        result = await test_model(model, client)
        results.append(result)

        if result["success"]:
            print(
                f"[OK] SUCCESS ({result['entities_found']} entities, {result['relationships_found']} relations, {result['generation_time_seconds']}s)"
            )
        elif result["error"]:
            print(f"[ERROR]: {result['error'][:80]}")
        else:
            print(
                f"[FAIL] (delimiter: {result['uses_correct_delimiter']}, entities: {result['entities_found']})"
            )

    # Print summary table
    print("\n" + "=" * 100)
    print("RESULTS SUMMARY")
    print("=" * 100)
    print(
        f"{'Model':<40} {'Status':<10} {'Entities':<10} {'Relations':<10} {'Delimiter':<12} {'Time (s)':<10}"
    )
    print("-" * 100)

    for r in results:
        status = "[OK]" if r["success"] else ("[ERROR]" if r["error"] else "[FAIL]")
        delimiter = "[OK] <|#|>" if r["uses_correct_delimiter"] else "[X] Wrong"

        print(
            f"{r['model']:<40} {status:<10} {r['entities_found']:<10} {r['relationships_found']:<10} {delimiter:<12} {r['generation_time_seconds']:<10}"
        )

    # Find best candidates
    successful_models = [r for r in results if r["success"]]

    if successful_models:
        print("\n" + "=" * 100)
        print("RECOMMENDED MODELS FOR LIGHTRAG")
        print("=" * 100)

        # Sort by number of entities found (descending) and generation time (ascending)
        successful_models.sort(key=lambda x: (-x["entities_found"], x["generation_time_seconds"]))

        for i, r in enumerate(successful_models[:5], 1):
            print(f"\n{i}. {r['model']}")
            print(
                f"   - Entities: {r['entities_found']}, Relationships: {r['relationships_found']}"
            )
            print(f"   - Generation time: {r['generation_time_seconds']}s")
            print(f"   - Completion marker: {'[OK]' if r['has_completion_marker'] else '[X]'}")
            print(f"   - Output preview:")
            print(f"     {r['output_preview'][:200]}...")
    else:
        print("\n" + "=" * 100)
        print("⚠ NO COMPATIBLE MODELS FOUND")
        print("=" * 100)
        print(
            "\nNone of the tested models successfully produced entities with the correct <|#|> delimiter."
        )
        print(
            "This suggests that LightRAG may require specific prompt engineering or model selection."
        )

    # Print detailed failure analysis
    failed_models = [r for r in results if not r["success"] and not r["error"]]

    if failed_models:
        print("\n" + "=" * 100)
        print("FAILURE ANALYSIS")
        print("=" * 100)

        for r in failed_models[:3]:  # Show first 3 failures
            print(f"\n{r['model']}:")
            print(f"  - Uses <|#|> delimiter: {r['uses_correct_delimiter']}")
            print(f"  - Entities found: {r['entities_found']}")
            print(f"  - Output preview:\n    {r['output_preview'][:300]}")


if __name__ == "__main__":
    asyncio.run(main())
