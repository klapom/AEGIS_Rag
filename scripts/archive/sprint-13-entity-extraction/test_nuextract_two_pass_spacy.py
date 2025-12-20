#!/usr/bin/env python3
"""Test NuExtract with 2-pass extraction strategy combining NuExtract + spaCy NER.

Sprint 13 TD-31: Implement 2-pass strategy:
  Phase 1a: Entity extraction with NuExtract (JSON)
  Phase 1b: Entity extraction with spaCy Transformer NER (JSON)
  Phase 2:  Entity Fusion (merge both outputs)
  Phase 3:  Relation extraction with unified entity list (JSON)
  Phase 4:  Post-process to LightRAG format
"""

import json
import time
from datetime import datetime
from pathlib import Path

from ollama import Client

# Try to import spaCy
try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("WARNING: spaCy not available. Install with: pip install spacy")
    print("WARNING: Download model with: python -m spacy download en_core_web_trf")

# ============================================================================
# LIGHTRAG DELIMITERS (for conversion)
# ============================================================================
TUPLE_DELIMITER = "<|#|>"
COMPLETION_DELIMITER = "<|COMPLETE|>"

# ============================================================================
# PHASE 1 - ENTITY EXTRACTION PROMPT (NuExtract)
# ============================================================================
SYSTEM_PROMPT_ENTITY = """---Role---
You are an intelligent assistant that identifies entities in a text document.

---Goal---
Given a text document, identify all entities present in the text.

---Steps---
1. Identify all entities. For each identified entity, extract the following information:
   - name: Name of the entity, capitalized
   - type: One of the following types: ORGANIZATION, PERSON, LOCATION, TECHNOLOGY, CONCEPT, EVENT, DATE, PRODUCT, OTHER
   - description: Comprehensive description of the entity's attributes and activities

2. Return output as valid JSON with array: "entities".

---Output Requirements---
Output valid JSON only. No markdown formatting, no code blocks, just pure JSON.
Format: {"entities": [...]}"""

USER_PROMPT_TEMPLATE_ENTITY = """---Task---
Extract all entities from the input text following the steps above.

######################
-Examples-
######################
Example 1:
Input: "Alex is a powerful person, but Jordan is smarter. They worked at TechCorp together."
Output:
{{
  "entities": [
    {{"name": "Alex", "type": "PERSON", "description": "Alex is described as a powerful person."}},
    {{"name": "Jordan", "type": "PERSON", "description": "Jordan is described as smarter and more talented."}},
    {{"name": "TechCorp", "type": "ORGANIZATION", "description": "TechCorp is a company where Alex and Jordan worked together."}}
  ]
}}

Example 2:
Input: "At the World Athletics Championship in Tokyo, Noah Carter broke the 100m sprint record."
Output:
{{
  "entities": [
    {{"name": "World Athletics Championship", "type": "EVENT", "description": "A global sports competition."}},
    {{"name": "Tokyo", "type": "LOCATION", "description": "Tokyo is the host city."}},
    {{"name": "Noah Carter", "type": "PERSON", "description": "Noah Carter is a sprinter who broke the record."}},
    {{"name": "100m Sprint Record", "type": "CONCEPT", "description": "A benchmark in athletics."}}
  ]
}}

######################
-Real Data-
######################
Input text:
{text}

######################
Output (valid JSON only):
"""

# ============================================================================
# PHASE 3 - RELATION EXTRACTION PROMPT (with entity context)
# ============================================================================
SYSTEM_PROMPT_RELATION = """---Role---
You are an intelligent assistant that identifies relationships between entities in a text document.

---Goal---
Given a text document and a list of entities found in that text, identify all relationships among the entities.

---Steps---
1. Review the provided entity list.
2. From the entities in the list, identify all pairs of (source, target) that are *clearly related* to each other in the text.
3. For each pair of related entities, extract the following information:
   - source: name of the source entity (must match an entity from the provided list)
   - target: name of the target entity (must match an entity from the provided list)
   - description: Explanation as to why the source entity and target entity are related
   - strength: A numeric score (1-10) indicating strength of the relationship

4. Return output as valid JSON with array: "relations".

---Output Requirements---
Output valid JSON only. No markdown formatting, no code blocks, just pure JSON.
Format: {"relations": [...]}"""

USER_PROMPT_TEMPLATE_RELATION = """---Task---
Extract relationships between the provided entities based on the input text.

######################
-Entity List-
######################
{entity_list}

######################
-Input Text-
######################
{text}

######################
-Example-
######################
If entity list contains ["Alex", "Jordan", "TechCorp"] and text says "Alex and Jordan worked at TechCorp together", output:
{{
  "relations": [
    {{"source": "Alex", "target": "TechCorp", "description": "Alex worked at TechCorp.", "strength": 8}},
    {{"source": "Jordan", "target": "TechCorp", "description": "Jordan worked at TechCorp.", "strength": 8}},
    {{"source": "Alex", "target": "Jordan", "description": "Alex and Jordan worked together.", "strength": 7}}
  ]
}}

######################
Output (valid JSON only):
"""

# ============================================================================
# TEST CASES
# ============================================================================
FICTION_TEXT = """Alex is a powerful person, but Jordan is smarter and more talented. They worked at TechCorp together. Jordan left to found DevStart, a startup focused on AI research. Alex later joined DevStart as Chief Technology Officer. The company is developing a new framework called NeuralGraph, which they plan to present at the AI Summit in San Francisco. Taylor is working with Jordan on this project, while Cruz is managing partnerships with OpenResearch. The Device they're building uses quantum computing."""

FINANCIAL_TEXT = """Stock markets faced a sharp downturn today as tech giants saw significant declines. The Global Tech Index fell 3.4%, with Nexon Technologies dropping 7.8% after disappointing quarterly results. Analysts at MarketWatch attribute the selloff to concerns over rising interest rates and slowing consumer demand. Meanwhile, energy stocks showed resilience, with GreenPower Corp gaining 2.1% on strong earnings."""

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

# ============================================================================
# SPACY NER TYPE MAPPING
# ============================================================================
SPACY_TO_LIGHTRAG_TYPE = {
    "PERSON": "PERSON",
    "ORG": "ORGANIZATION",
    "GPE": "LOCATION",  # Geopolitical entity
    "LOC": "LOCATION",
    "DATE": "DATE",
    "TIME": "DATE",
    "MONEY": "CONCEPT",
    "PERCENT": "CONCEPT",
    "PRODUCT": "PRODUCT",
    "EVENT": "EVENT",
    "WORK_OF_ART": "PRODUCT",
    "LAW": "CONCEPT",
    "LANGUAGE": "CONCEPT",
    "NORP": "CONCEPT",  # Nationalities, religious/political groups
    "FAC": "LOCATION",  # Facilities
    "CARDINAL": "CONCEPT",
    "ORDINAL": "CONCEPT",
    "QUANTITY": "CONCEPT",
}


def extract_entities_spacy(text: str, nlp) -> list[dict[str, str]]:
    """Extract entities using spaCy NER.

    Args:
        text: Input text
        nlp: spaCy model

    Returns:
        List of entity dictionaries with name, type, description
    """
    doc = nlp(text)
    entities = []

    for ent in doc.ents:
        # Map spaCy type to LightRAG type
        lightrag_type = SPACY_TO_LIGHTRAG_TYPE.get(ent.label_, "OTHER")

        entities.append(
            {
                "name": ent.text,
                "type": lightrag_type,
                "description": f"{ent.text} is a {ent.label_} extracted by spaCy NER.",
                "source": "spacy",
            }
        )

    return entities


def fuse_entities(
    nuextract_entities: list[dict[str, str]], spacy_entities: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Fuse NuExtract and spaCy entities with conflict resolution.

    Resolution strategy:
    - If entity name matches (case-insensitive), keep NuExtract version
    - If types differ, note in description
    - Add all unique entities from both sources

    Args:
        nuextract_entities: Entities from NuExtract
        spacy_entities: Entities from spaCy

    Returns:
        Unified entity list
    """
    fused = []
    nuextract_names = set()

    # Add all NuExtract entities first (higher quality)
    for entity in nuextract_entities:
        fused.append(entity)
        nuextract_names.add(entity["name"].lower())

    # Add spaCy entities that don't conflict
    for spacy_entity in spacy_entities:
        spacy_name_lower = spacy_entity["name"].lower()

        # Check for name match
        if spacy_name_lower not in nuextract_names:
            # Unique entity from spaCy, add it
            fused.append(
                {
                    "name": spacy_entity["name"],
                    "type": spacy_entity["type"],
                    "description": f"{spacy_entity['name']} identified by spaCy NER as {spacy_entity['type']}.",
                }
            )
        else:
            # Name conflict - check if types differ
            nuextract_entity = next(
                (e for e in nuextract_entities if e["name"].lower() == spacy_name_lower), None
            )
            if nuextract_entity and nuextract_entity["type"] != spacy_entity["type"]:
                # Note type difference in description
                nuextract_entity[
                    "description"
                ] += f" (spaCy also identified as {spacy_entity['type']})"

    return fused


def convert_json_to_lightrag(
    entities: list[dict[str, str]], relations: list[dict[str, str]]
) -> str:
    """Convert entity and relation lists to LightRAG delimiter-separated format."""
    lines = []

    # Convert entities
    for entity in entities:
        name = str(entity.get("name", "")).strip() if entity.get("name") is not None else ""
        etype = (
            str(entity.get("type", "OTHER")).strip().upper()
            if entity.get("type") is not None
            else "OTHER"
        )
        desc = (
            str(entity.get("description", "")).strip()
            if entity.get("description") is not None
            else ""
        )

        if name:
            line = f"entity{TUPLE_DELIMITER}{name}{TUPLE_DELIMITER}{etype}{TUPLE_DELIMITER}{desc}"
            lines.append(line)

    # Convert relations
    for relation in relations:
        source = (
            str(relation.get("source", "")).strip() if relation.get("source") is not None else ""
        )
        target = (
            str(relation.get("target", "")).strip() if relation.get("target") is not None else ""
        )
        desc = (
            str(relation.get("description", "")).strip()
            if relation.get("description") is not None
            else ""
        )
        strength = (
            str(relation.get("strength", "5")).strip()
            if relation.get("strength") is not None
            else "5"
        )

        if source and target:
            line = f"relation{TUPLE_DELIMITER}{source}{TUPLE_DELIMITER}{target}{TUPLE_DELIMITER}{desc}{TUPLE_DELIMITER}{strength}"
            lines.append(line)

    lines.append(COMPLETION_DELIMITER)
    return "\n".join(lines)


def parse_json_response(response: str) -> dict:
    """Parse JSON response, handling markdown code blocks and malformed JSON."""
    import re

    cleaned = response.strip()

    # Remove markdown code blocks
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    # Try direct parsing first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        # Look for {...} pattern
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # If all else fails, return empty structure
        return {"entities": [], "relations": []}


def test_two_pass(model: str, test_case: dict, client: Client, nlp, log_path: Path) -> dict:
    """Test 2-pass extraction strategy with spaCy NER fusion."""

    results = {
        "model": model,
        "test_id": test_case["id"],
        "test_name": test_case["name"],
        "pass1a_time": 0,
        "pass1b_time": 0,
        "pass2_time": 0,
        "total_time": 0,
        "nuextract_entities": 0,
        "spacy_entities": 0,
        "fused_entities": 0,
        "relations_found": 0,
        "entities_expected": test_case["expected_entities"],
        "relations_expected": test_case["expected_relations"],
        "entity_accuracy": 0,
        "relation_accuracy": 0,
        "status": "FAIL",
        "errors": [],
    }

    total_start = time.perf_counter()

    try:
        # ====================================================================
        # PHASE 1a: NuExtract Entity Extraction
        # ====================================================================
        start = time.perf_counter()
        user_prompt_entity = USER_PROMPT_TEMPLATE_ENTITY.format(text=test_case["text"])

        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_ENTITY},
                {"role": "user", "content": user_prompt_entity},
            ],
            options={"temperature": 0.1, "num_predict": 2000, "num_ctx": 16384},
            format="json",
        )

        results["pass1a_time"] = time.perf_counter() - start

        nuextract_data = parse_json_response(response["message"]["content"])
        nuextract_entities = nuextract_data.get("entities", [])
        results["nuextract_entities"] = len(nuextract_entities)

        # ====================================================================
        # PHASE 1b: spaCy NER Extraction
        # ====================================================================
        start = time.perf_counter()
        spacy_entities = []
        if nlp is not None:
            spacy_entities = extract_entities_spacy(test_case["text"], nlp)
        results["pass1b_time"] = time.perf_counter() - start
        results["spacy_entities"] = len(spacy_entities)

        # ====================================================================
        # PHASE 2: Entity Fusion
        # ====================================================================
        fused_entities = fuse_entities(nuextract_entities, spacy_entities)
        results["fused_entities"] = len(fused_entities)

        # ====================================================================
        # PHASE 3: Relation Extraction with Entity Context
        # ====================================================================
        start = time.perf_counter()

        # Format entity list for prompt
        entity_names = [e["name"] for e in fused_entities]
        entity_list_str = ", ".join(entity_names)

        user_prompt_relation = USER_PROMPT_TEMPLATE_RELATION.format(
            entity_list=entity_list_str, text=test_case["text"]
        )

        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_RELATION},
                {"role": "user", "content": user_prompt_relation},
            ],
            options={"temperature": 0.1, "num_predict": 2000, "num_ctx": 16384},
            format="json",
        )

        results["pass2_time"] = time.perf_counter() - start

        relation_data = parse_json_response(response["message"]["content"])
        relations = relation_data.get("relations", [])
        results["relations_found"] = len(relations)

        # ====================================================================
        # PHASE 4: Post-process to LightRAG format
        # ====================================================================
        lightrag_format = convert_json_to_lightrag(fused_entities, relations)

        results["total_time"] = time.perf_counter() - total_start
        results["entity_accuracy"] = (
            100 * results["fused_entities"] / test_case["expected_entities"]
            if test_case["expected_entities"] > 0
            else 0
        )
        results["relation_accuracy"] = (
            100 * results["relations_found"] / test_case["expected_relations"]
            if test_case["expected_relations"] > 0
            else 0
        )
        results["status"] = (
            "PASS"
            if results["fused_entities"] > 0 and results["relations_found"] > 0
            else "PARTIAL"
        )

        # ====================================================================
        # Log Results
        # ====================================================================
        log_content = f"""
{'='*80}
TEST CASE {test_case['id']}: {test_case['name']} [TWO-PASS + spaCy]
{'='*80}

Expected: {test_case['expected_entities']} entities, {test_case['expected_relations']} relations
Found: {results['fused_entities']} entities, {results['relations_found']} relations

Phase 1a (NuExtract Entities): {results['pass1a_time']:.2f}s → {results['nuextract_entities']} entities
Phase 1b (spaCy NER):           {results['pass1b_time']:.2f}s → {results['spacy_entities']} entities
Phase 2  (Entity Fusion):       → {results['fused_entities']} entities (unified)
Phase 3  (Relations):           {results['pass2_time']:.2f}s → {results['relations_found']} relations
Total Time:                     {results['total_time']:.2f}s

Accuracy: {results['entity_accuracy']:.1f}% entities, {results['relation_accuracy']:.1f}% relations

{'='*80}
PHASE 1a - NuExtract ENTITIES:
{'='*80}
{json.dumps(nuextract_entities, indent=2)}

{'='*80}
PHASE 1b - spaCy ENTITIES:
{'='*80}
{json.dumps(spacy_entities, indent=2)}

{'='*80}
PHASE 2 - FUSED ENTITIES:
{'='*80}
{json.dumps(fused_entities, indent=2)}

{'='*80}
PHASE 3 - RELATIONS:
{'='*80}
{json.dumps(relations, indent=2)}

{'='*80}
PHASE 4 - LIGHTRAG FORMAT:
{'='*80}
{lightrag_format}

"""
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_content)

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()

        results["errors"].append(str(e))
        results["status"] = "ERROR"
        results["total_time"] = time.perf_counter() - total_start

        # Log error with full traceback
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(
                f"""
{'='*80}
TEST CASE {test_case['id']}: {test_case['name']} [ERROR]
{'='*80}
Error: {e}

Full Traceback:
{error_details}
{'='*80}
"""
            )

    return results


def main():
    """Main test execution."""
    print(
        f"""{'='*80}
     NuExtract Two-Pass Strategy with spaCy NER Fusion
{'='*80}

Architecture:
  Phase 1a: Entity Extraction -> NuExtract 4B -> Entities (JSON)
  Phase 1b: Entity Extraction -> spaCy Transformer -> Entities (JSON)
  Phase 2:  Entity Fusion -> Merge NuExtract + spaCy -> Unified List
  Phase 3:  Relation Extraction -> NuExtract 4B + Entity Context -> Relations (JSON)
  Phase 4:  Post-Process -> LightRAG delimiter-separated format

Expected Improvements:
  - Entity Recall: +10-15% (especially LOCATION, DATE, ORG)
  - Total Time: +1-2s (spaCy NER overhead)

Baseline (single-pass DETAILED):
  - Entity Accuracy: 70.9%
  - Relation Accuracy: 45.5%
  - Average Time: 8.9s
    """
    )

    # Load spaCy model
    nlp = None
    if SPACY_AVAILABLE:
        try:
            print(
                "\n[INFO] Loading spaCy transformer model (en_core_web_trf)...", end=" ", flush=True
            )
            nlp = spacy.load("en_core_web_trf")
            print("OK")
        except OSError:
            print("\n[WARNING] spaCy model 'en_core_web_trf' not found.")
            print("[WARNING] Download with: python -m spacy download en_core_web_trf")
            print("[WARNING] Continuing without spaCy NER (Phase 1b will be skipped).")
    else:
        print("\n[WARNING] spaCy not available. Phase 1b will be skipped.")

    client = Client()

    # Test NuExtract Q4_K_M (best performer from previous benchmarks)
    model = "hf.co/mradermacher/NuExtract-2.0-4B-i1-GGUF:Q4_K_M"
    model_short = model.split("/")[-1] if "/" in model else model

    print(f"\n{'='*80}")
    print(f"MODEL: {model_short}")
    print(f"{'='*80}")

    # Warmup
    print("\n[WARMUP] Loading model (not measured)...", end=" ", flush=True)
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

    # Create log directory
    log_dir = Path("logs/nuextract_two_pass_spacy")
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{timestamp}_{model_short.replace(':', '_')}_two_pass.log"
    log_path = log_dir / log_filename

    # Write log header
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(
            f"""{'='*80}
NuExtract TWO-PASS + spaCy NER TEST LOG
{'='*80}

Model: {model}
Strategy: Two-Pass with spaCy NER Fusion
Test Suite: All 3 LightRAG Original Examples
Context Window: 16384
Start Time: {datetime.now().isoformat()}

{'='*80}

"""
        )

    results = []

    for test_case in TEST_CASES:
        print(f"\n[{test_case['id']}/3] {test_case['name']}...", end=" ", flush=True)
        result = test_two_pass(model, test_case, client, nlp, log_path)
        results.append(result)

        print(f"\n  Phase 1a: {result['nuextract_entities']}E in {result['pass1a_time']:.1f}s")
        print(f"  Phase 1b: {result['spacy_entities']}E in {result['pass1b_time']:.1f}s")
        print(f"  Phase 2:  {result['fused_entities']}E (fused)")
        print(f"  Phase 3:  {result['relations_found']}R in {result['pass2_time']:.1f}s")
        print(
            f"  Total:    {result['total_time']:.1f}s | "
            f"{result['entity_accuracy']:.0f}% entities, {result['relation_accuracy']:.0f}% relations | "
            f"[{result['status']}]"
        )

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print(f"\n{'='*80}")
    print("SUMMARY: TWO-PASS vs BASELINE COMPARISON")
    print(f"{'='*80}\n")

    print(f"{'Test':<30} {'Total Time':<12} {'Entities':<15} {'Relations':<15} {'Status':<8}")
    print(f"{'-'*30} {'-'*12} {'-'*15} {'-'*15} {'-'*8}")

    for r in results:
        entity_str = f"{r['fused_entities']}/{r['entities_expected']} ({r['entity_accuracy']:.0f}%)"
        relation_str = (
            f"{r['relations_found']}/{r['relations_expected']} ({r['relation_accuracy']:.0f}%)"
        )
        time_str = f"{r['total_time']:.1f}s"

        print(
            f"{r['test_name']:<30} {time_str:<12} {entity_str:<15} {relation_str:<15} {r['status']:<8}"
        )

    # Calculate averages
    print(f"\n{'='*80}")
    print("AVERAGE PERFORMANCE")
    print(f"{'='*80}\n")

    avg_time = sum(r["total_time"] for r in results) / len(results)
    avg_entity_acc = sum(r["entity_accuracy"] for r in results) / len(results)
    avg_relation_acc = sum(r["relation_accuracy"] for r in results) / len(results)
    success_rate = (
        100 * sum(1 for r in results if r["status"] in ["PASS", "PARTIAL"]) / len(results)
    )

    print("TWO-PASS + spaCy:")
    print(f"  Average Time: {avg_time:.1f}s")
    print(f"  Average Entity Accuracy: {avg_entity_acc:.1f}%")
    print(f"  Average Relation Accuracy: {avg_relation_acc:.1f}%")
    print(f"  Success Rate: {success_rate:.0f}%")
    print()

    print("BASELINE (single-pass DETAILED):")
    print("  Average Time: 8.9s")
    print("  Average Entity Accuracy: 70.9%")
    print("  Average Relation Accuracy: 45.5%")
    print("  Success Rate: 100%")
    print()

    print("DELTA (Two-Pass vs Baseline):")
    print(f"  Time: {avg_time - 8.9:+.1f}s ({100*(avg_time - 8.9)/8.9:+.1f}%)")
    print(
        f"  Entity Accuracy: {avg_entity_acc - 70.9:+.1f}% ({100*(avg_entity_acc - 70.9)/70.9:+.1f}%)"
    )
    print(
        f"  Relation Accuracy: {avg_relation_acc - 45.5:+.1f}% ({100*(avg_relation_acc - 45.5)/45.5:+.1f}%)"
    )
    print()

    # Save results
    output_file = Path("nuextract_two_pass_spacy_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"{'='*80}")
    print(f"[OK] Detailed results saved to: {output_file}")
    print(f"[OK] Detailed logs saved to: {log_dir}/")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
