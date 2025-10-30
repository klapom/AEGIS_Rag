#!/usr/bin/env python3
"""
Test models with LightRAG Original Format + Detailed Logging

Sprint 13 TD-31: Test all models with LightRAG's original prompt format
and log every detail (prompt, response, timestamps, validation).
"""

import json
import time
from datetime import datetime
from pathlib import Path
from ollama import Client

# ============================================================================
# CONFIGURATION
# ============================================================================

LOG_DIR = Path("logs/lightrag_format_tests")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# LIGHTRAG ORIGINAL PROMPT (from test_lightrag_prompts.py)
# ============================================================================

def create_lightrag_prompt(text: str, entity_types: list[str]) -> str:
    """Create the exact LightRAG prompt format."""
    return f"""
-Target activity-
You are an intelligent assistant that helps a human analyst to analyze claims against certain entities presented in a text document.

-Goal-
Given a text document that is potentially relevant to this activity, an entity type, and a list of entity categories, identify all entities of those types from the text and all relationships among the identified entities.

-Steps-
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity, capitalized
- entity_type: One of the following types: {entity_types}
- entity_description: Comprehensive description of the entity's attributes and activities
Format each entity as ("entity"<|#|><entity_name><|#|><entity_type><|#|><entity_description>)

2. From the entities identified in step 1, identify all pairs of (source_entity, target_entity) that are *clearly related* to each other.
For each pair of related entities, extract the following information:
- source_entity: name of the source entity, as identified in step 1
- target_entity: name of the target entity, as identified in step 1
- relationship_description: explanation as to why you think the source entity and the target entity are related to each other
- relationship_strength: a numeric score indicating strength of the relationship between the source entity and target entity
Format each relationship as ("relationship"<|#|><source_entity><|#|><target_entity><|#|><relationship_description><|#|><relationship_strength>)

3. Return output in English as a single list of all the entities and relationships identified in steps 1 and 2. Use **##** as the list delimiter.

4. When finished, output <|COMPLETE|>

######################
-Examples-
######################
Example 1:

entity_types: [person, technology, mission, organization, location]
text:
their voice slicing through the buzz of activity. "Control, this is Parker. We have a situation." The tension in their voice was palpable. "I'm routing you through now," Devi said, fingers flying across the keys with practiced ease.
------------------------
output:
("entity"<|#|>Parker<|#|>person<|#|>Parker is a communications specialist working at a central control station, coordinating responses during a critical incident. They are under significant stress and need to relay urgent information to decision-makers.)
("entity"<|#|>Control<|#|>organization<|#|>Control is the central authority managing and coordinating responses to the crisis. It serves as the decision-making hub for all operations.)
("entity"<|#|>Devi<|#|>person<|#|>Devi is a technical operator working under pressure to facilitate critical communications between field operatives and command structures.)
("relationship"<|#|>Parker<|#|>Control<|#|>Parker reports directly to Control, indicating a hierarchical relationship where Parker provides real-time updates.<|#|>8)
("relationship"<|#|>Devi<|#|>Parker<|#|>Devi assists Parker by routing communications, showing a supportive and collaborative relationship.<|#|>7)
<|COMPLETE|>

######################
-Real Data-
######################
entity_types: {entity_types}
text: {text.strip()}
######################
output:
"""

# ============================================================================
# TEST CASES
# ============================================================================

TEST_CASES = [
    {
        "id": 1,
        "complexity": "SIMPLE",
        "name": "Simple Person-Created Relationship",
        "text": "Python is a programming language created by Guido van Rossum in 1991.",
        "entity_types": ["person", "technology", "date", "event"],
        "expected": {
            "entities": ["Python", "Guido van Rossum", "1991"],
            "relations": [("Python", "Guido van Rossum")]
        }
    },
    {
        "id": 2,
        "complexity": "MEDIUM",
        "name": "Apple Company History (from test_lightrag_prompts.py)",
        "text": """Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.
Steve Jobs served as CEO and led product development. The company's headquarters
is located in Cupertino, California. Apple is known for products like the iPhone,
iPad, and Mac computers.""",
        "entity_types": ["organization", "person", "location", "product", "event", "date"],
        "expected": {
            "entities": ["Apple Inc.", "Steve Jobs", "Steve Wozniak", "Ronald Wayne", "Cupertino", "iPhone", "iPad", "Mac"],
            "relations": [
                ("Apple Inc.", "Steve Jobs"),
                ("Apple Inc.", "Steve Wozniak"),
                ("Apple Inc.", "Cupertino"),
                ("Steve Jobs", "iPhone")
            ]
        }
    },
    {
        "id": 3,
        "complexity": "COMPLEX",
        "name": "Multi-Company Acquisition Chain",
        "text": """In 2016, Microsoft acquired LinkedIn for $26.2 billion. LinkedIn was founded by Reid Hoffman
in 2002 and is headquartered in Sunnyvale, California. The acquisition was led by Microsoft CEO
Satya Nadella and LinkedIn CEO Jeff Weiner. Microsoft previously acquired GitHub in 2018 for $7.5 billion.
Both acquisitions were part of Microsoft's strategy to strengthen its cloud services and developer ecosystem.
The Federal Trade Commission reviewed the LinkedIn acquisition but approved it without conditions.""",
        "entity_types": ["organization", "person", "location", "product", "event", "date", "money"],
        "expected": {
            "entities": ["Microsoft", "LinkedIn", "GitHub", "Reid Hoffman", "Satya Nadella",
                        "Jeff Weiner", "Sunnyvale", "Federal Trade Commission", "2016", "2018"],
            "relations": [
                ("Microsoft", "LinkedIn"),
                ("Microsoft", "GitHub"),
                ("LinkedIn", "Reid Hoffman"),
                ("Microsoft", "Satya Nadella"),
                ("LinkedIn", "Jeff Weiner"),
                ("LinkedIn", "Sunnyvale"),
                ("Federal Trade Commission", "LinkedIn")
            ]
        }
    }
]

# ============================================================================
# VALIDATION
# ============================================================================

def validate_response(response: str) -> dict:
    """Validate LightRAG format compliance."""
    errors = []
    entities = []
    relations = []

    # Check for completion marker
    has_completion = "<|COMPLETE|>" in response

    # Check for delimiter ## or newlines
    has_delimiter = "##" in response

    # Parse entities
    import re
    entity_pattern = r'\("entity"<\|#\|>([^<]+)<\|#\|>([^<]+)<\|#\|>([^)]+)\)'
    entity_matches = re.findall(entity_pattern, response)

    for match in entity_matches:
        entities.append({
            "name": match[0].strip(),
            "type": match[1].strip(),
            "description": match[2].strip()
        })

    # Parse relationships
    relation_pattern = r'\("relationship"<\|#\|>([^<]+)<\|#\|>([^<]+)<\|#\|>([^<]+)<\|#\|>([^)]+)\)'
    relation_matches = re.findall(relation_pattern, response)

    for match in relation_matches:
        relations.append({
            "source": match[0].strip(),
            "target": match[1].strip(),
            "description": match[2].strip(),
            "strength": match[3].strip()
        })

    # Format validation
    if not has_completion:
        errors.append("Missing <|COMPLETE|> marker")

    if len(entities) == 0:
        errors.append("No entities found in expected format")

    # Check for wrong formats
    if response.strip().startswith('[') or response.strip().startswith('{'):
        errors.append("Response in JSON format instead of LightRAG format")

    if '```' in response:
        errors.append("Response contains markdown code blocks")

    return {
        "valid": len(errors) == 0 and len(entities) > 0,
        "entities": entities,
        "relations": relations,
        "entity_count": len(entities),
        "relation_count": len(relations),
        "has_completion": has_completion,
        "has_delimiter": has_delimiter,
        "errors": errors
    }

# ============================================================================
# LOGGING
# ============================================================================

def log_test_execution(log_data: dict, log_file: Path):
    """Write detailed log entry."""
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("\n" + "=" * 100 + "\n")
        f.write(f"TEST EXECUTION LOG\n")
        f.write("=" * 100 + "\n\n")

        f.write(f"Timestamp: {log_data['timestamp']}\n")
        f.write(f"Model: {log_data['model']}\n")
        f.write(f"Mode: {log_data['mode']}\n")
        f.write(f"Test Case: {log_data['test_case']['name']} (Complexity: {log_data['test_case']['complexity']})\n")
        f.write(f"Start Time: {log_data['start_time']}\n")
        f.write(f"End Time: {log_data['end_time']}\n")
        f.write(f"Duration: {log_data['duration']:.2f}s\n\n")

        f.write("-" * 100 + "\n")
        f.write("PROMPT SENT TO LLM:\n")
        f.write("-" * 100 + "\n")
        f.write(log_data['prompt'])
        f.write("\n\n")

        f.write("-" * 100 + "\n")
        f.write("RESPONSE FROM LLM:\n")
        f.write("-" * 100 + "\n")
        f.write(log_data['response'])
        f.write("\n\n")

        f.write("-" * 100 + "\n")
        f.write("VALIDATION RESULTS:\n")
        f.write("-" * 100 + "\n")
        validation = log_data['validation']
        f.write(f"Valid Format: {validation['valid']}\n")
        f.write(f"Entities Found: {validation['entity_count']}\n")
        f.write(f"Relations Found: {validation['relation_count']}\n")
        f.write(f"Has Completion Marker: {validation['has_completion']}\n")
        f.write(f"Has Delimiter (##): {validation['has_delimiter']}\n")

        if validation['errors']:
            f.write(f"\nErrors:\n")
            for error in validation['errors']:
                f.write(f"  - {error}\n")

        if validation['entities']:
            f.write(f"\nExtracted Entities:\n")
            for entity in validation['entities'][:5]:  # First 5
                f.write(f"  - {entity['name']} ({entity['type']})\n")

        if validation['relations']:
            f.write(f"\nExtracted Relations:\n")
            for relation in validation['relations'][:5]:  # First 5
                f.write(f"  - {relation['source']} -> {relation['target']}\n")

        f.write("\n" + "=" * 100 + "\n\n")

# ============================================================================
# TEST EXECUTION
# ============================================================================

def test_model(model: str, test_case: dict, client: Client, use_think_false: bool = False) -> dict:
    """Test a single model with a test case."""
    mode = "think=False" if use_think_false else "default"

    # Create prompt
    prompt = create_lightrag_prompt(test_case['text'], test_case['entity_types'])

    # Record start time
    start_time = datetime.now()
    start_timestamp = start_time.isoformat()
    start_perf = time.perf_counter()

    try:
        # Build kwargs
        kwargs = {
            "model": model,
            "prompt": prompt,
            "options": {
                "temperature": 0.0,
                "num_predict": 2000,
                "num_ctx": 32768
            }
        }

        if use_think_false:
            kwargs["think"] = False

        # Call model
        response = client.generate(**kwargs)

        # Record end time
        end_time = datetime.now()
        end_timestamp = end_time.isoformat()
        duration = time.perf_counter() - start_perf

        # Get response content
        content = response["response"]

        # Validate
        validation = validate_response(content)

        # Prepare log data
        log_data = {
            "timestamp": start_timestamp,
            "model": model,
            "mode": mode,
            "test_case": test_case,
            "prompt": prompt,
            "response": content,
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "duration": duration,
            "validation": validation
        }

        # Write to log file
        log_file = LOG_DIR / f"test_{test_case['id']}_{test_case['complexity']}_{''.join(c for c in model if c.isalnum())}.log"
        log_test_execution(log_data, log_file)

        return {
            "model": model,
            "mode": mode,
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "complexity": test_case["complexity"],
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "duration": duration,
            "valid_format": validation['valid'],
            "entity_count": validation['entity_count'],
            "relation_count": validation['relation_count'],
            "errors": validation['errors'],
            "success": validation['valid'],
            "log_file": str(log_file)
        }

    except Exception as e:
        end_time = datetime.now()
        end_timestamp = end_time.isoformat()
        duration = time.perf_counter() - start_perf

        error_msg = str(e)
        supports_think = "does not support thinking" not in error_msg

        # Log error
        log_data = {
            "timestamp": start_timestamp,
            "model": model,
            "mode": mode,
            "test_case": test_case,
            "prompt": prompt,
            "response": f"ERROR: {error_msg}",
            "start_time": start_timestamp,
            "end_time": end_timestamp,
            "duration": duration,
            "validation": {"valid": False, "errors": [error_msg], "entity_count": 0, "relation_count": 0}
        }

        log_file = LOG_DIR / f"test_{test_case['id']}_ERROR_{''.join(c for c in model if c.isalnum())}.log"
        log_test_execution(log_data, log_file)

        return {
            "model": model,
            "mode": mode,
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "complexity": test_case["complexity"],
            "duration": duration,
            "error": error_msg,
            "supports_think": supports_think,
            "success": False,
            "log_file": str(log_file)
        }

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("""
================================================================================
    LightRAG Format Test with Detailed Logging
================================================================================

Testing models with LightRAG's original format (from test_lightrag_prompts.py)
- 3 test cases: SIMPLE, MEDIUM (original), COMPLEX
- Detailed logging: Prompt, Response, Timestamps, Validation
- Format: ("entity"<|#|>name<|#|>type<|#|>description)
- Format: ("relationship"<|#|>source<|#|>target<|#|>description<|#|>strength)

Logs will be saved to: {LOG_DIR}
    """.format(LOG_DIR=LOG_DIR))

    client = Client()

    # Models to test
    models = [
        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0",
        "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M",
        "llama3.2:3b",
        "qwen3:4b"
    ]

    results = []

    for model in models:
        model_short = model.split('/')[-1] if '/' in model else model

        print(f"\n{'='*80}")
        print(f"MODEL: {model_short}")
        print(f"{'='*80}")

        for test_case in TEST_CASES:
            # Test default mode
            print(f"\n  Test {test_case['id']}: {test_case['name']} [{test_case['complexity']}]")
            print(f"    [default]...", end=" ", flush=True)

            result = test_model(model, test_case, client, use_think_false=False)
            results.append(result)

            status = "OK" if result['success'] else "FAIL"
            if 'error' in result:
                print(f"ERROR: {result['error'][:50]}")
            else:
                print(f"{result['entity_count']}E/{result['relation_count']}R in {result['duration']:.1f}s [{status}]")
                print(f"      Log: {result['log_file']}")

            # Test think=False
            time.sleep(0.5)
            print(f"    [think=False]...", end=" ", flush=True)

            result = test_model(model, test_case, client, use_think_false=True)
            results.append(result)

            status = "OK" if result['success'] else "FAIL"
            if 'error' in result:
                print(f"ERROR: {result['error'][:50]}")
            else:
                print(f"{result['entity_count']}E/{result['relation_count']}R in {result['duration']:.1f}s [{status}]")
                print(f"      Log: {result['log_file']}")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]

    print(f"Total Tests: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        print(f"\nBest Performance:")
        best = max(successful, key=lambda r: r['entity_count'] + r['relation_count'])
        print(f"  Model: {best['model'].split('/')[-1] if '/' in best['model'] else best['model']}")
        print(f"  Test: {best['test_name']}")
        print(f"  Entities: {best['entity_count']}, Relations: {best['relation_count']}")
        print(f"  Time: {best['duration']:.2f}s")

    # Save summary
    summary_file = LOG_DIR / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Summary saved to: {summary_file}")
    print(f"[OK] Detailed logs in: {LOG_DIR}")

if __name__ == "__main__":
    main()
