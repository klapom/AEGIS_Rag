#!/usr/bin/env python3
"""Benchmark Relation Extraction across multiple models.

Sprint 13 TD-31: Test relation extraction performance with fixed entity lists.
- NO entity extraction phase
- Entities are pre-defined for each test case
- Tests ALL downloaded Ollama models
- Warmup before each model
"""

import json
import time
from pathlib import Path
from datetime import datetime
from ollama import Client
from typing import List, Dict

# ============================================================================
# LIGHTRAG DELIMITERS
# ============================================================================
TUPLE_DELIMITER = "<|#|>"
COMPLETION_DELIMITER = "<|COMPLETE|>"

# ============================================================================
# RELATION EXTRACTION PROMPT (Enhanced with 4 examples)
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
Format: {{"relations": [...]}}"""

USER_PROMPT_TEMPLATE_RELATION = """---Task---
Extract relationships between the provided entities based on the input text.

######################
-Examples-
######################
Example 1 - Character Dynamics:
Entity List: ["Alex", "Taylor", "Jordan", "Cruz", "The Device"]
Text: "while Alex clenched his jaw, the buzz of frustration dull against the backdrop of Taylor's authoritarian certainty. It was this competitive undercurrent that kept him alert, the sense that his and Jordan's shared commitment to discovery was an unspoken rebellion against Cruz's narrowing vision of control and order. Then Taylor did something unexpected. They paused beside Jordan and, for a moment, observed the device with something akin to reverence."

Output:
{{{{
  "relations": [
    {{{{"source": "Alex", "target": "Taylor", "description": "Alex observes Taylor's authoritarian behavior and notes changes in Taylor's attitude toward the device.", "strength": 7}}}},
    {{{{"source": "Alex", "target": "Jordan", "description": "Alex and Jordan share a commitment to discovery, which contrasts with Cruz's vision.", "strength": 8}}}},
    {{{{"source": "Taylor", "target": "Jordan", "description": "Taylor and Jordan interact directly regarding the device, leading to a moment of mutual respect and an uneasy truce.", "strength": 6}}}},
    {{{{"source": "Jordan", "target": "Cruz", "description": "Jordan's commitment to discovery is in rebellion against Cruz's vision of control and order.", "strength": 7}}}},
    {{{{"source": "Taylor", "target": "The Device", "description": "Taylor shows reverence towards the device, indicating its importance and potential impact.", "strength": 8}}}}
  ]
}}}}

Example 2 - Financial Markets:
Entity List: ["Global Tech Index", "Nexon Technologies", "Market Selloff"]
Text: "Stock markets faced a sharp downturn today as tech giants saw significant declines, with the global tech index dropping by 3.4% in midday trading. Analysts attribute the selloff to investor concerns over rising interest rates and regulatory uncertainty. Among the hardest hit, Nexon Technologies saw its stock plummet by 7.8% after reporting lower-than-expected quarterly earnings."

Output:
{{{{
  "relations": [
    {{{{"source": "Global Tech Index", "target": "Market Selloff", "description": "The decline in the Global Tech Index is part of the broader market selloff driven by investor concerns.", "strength": 9}}}},
    {{{{"source": "Nexon Technologies", "target": "Global Tech Index", "description": "Nexon Technologies' stock decline contributed to the overall drop in the Global Tech Index.", "strength": 8}}}},
    {{{{"source": "Nexon Technologies", "target": "Market Selloff", "description": "Nexon Technologies was among the hardest hit in the market selloff with a 7.8% decline.", "strength": 9}}}}
  ]
}}}}

Example 3 - Sports Achievement:
Entity List: ["World Athletics Championship", "Tokyo", "Noah Carter", "100m Sprint Record", "Carbon-Fiber Spikes"]
Text: "At the World Athletics Championship in Tokyo, Noah Carter broke the 100m sprint record using cutting-edge carbon-fiber spikes."

Output:
{{{{
  "relations": [
    {{{{"source": "World Athletics Championship", "target": "Tokyo", "description": "The World Athletics Championship is being hosted in Tokyo.", "strength": 9}}}},
    {{{{"source": "Noah Carter", "target": "100m Sprint Record", "description": "Noah Carter set a new 100m sprint record at the championship.", "strength": 10}}}},
    {{{{"source": "Noah Carter", "target": "Carbon-Fiber Spikes", "description": "Noah Carter used carbon-fiber spikes to enhance performance during the race.", "strength": 7}}}},
    {{{{"source": "Noah Carter", "target": "World Athletics Championship", "description": "Noah Carter is competing at the World Athletics Championship.", "strength": 9}}}}
  ]
}}}}

Example 4 - Business Collaboration:
Entity List: ["Alex", "Jordan", "TechCorp", "DevStart", "NeuralGraph", "AI Summit", "San Francisco"]
Text: "Alex and Jordan worked at TechCorp together. Jordan left to found DevStart, a startup focused on AI research. Alex later joined DevStart as Chief Technology Officer. The company is developing a new framework called NeuralGraph, which they plan to present at the AI Summit in San Francisco."

Output:
{{{{
  "relations": [
    {{{{"source": "Alex", "target": "TechCorp", "description": "Alex previously worked at TechCorp.", "strength": 7}}}},
    {{{{"source": "Jordan", "target": "TechCorp", "description": "Jordan previously worked at TechCorp.", "strength": 7}}}},
    {{{{"source": "Alex", "target": "Jordan", "description": "Alex and Jordan worked together at TechCorp and now collaborate at DevStart.", "strength": 9}}}},
    {{{{"source": "Jordan", "target": "DevStart", "description": "Jordan founded DevStart, a startup focused on AI research.", "strength": 10}}}},
    {{{{"source": "Alex", "target": "DevStart", "description": "Alex joined DevStart as Chief Technology Officer.", "strength": 9}}}},
    {{{{"source": "DevStart", "target": "NeuralGraph", "description": "DevStart is developing the NeuralGraph framework.", "strength": 10}}}},
    {{{{"source": "NeuralGraph", "target": "AI Summit", "description": "NeuralGraph will be presented at the AI Summit.", "strength": 8}}}},
    {{{{"source": "AI Summit", "target": "San Francisco", "description": "The AI Summit is taking place in San Francisco.", "strength": 9}}}}
  ]
}}}}

######################
-Real Data-
######################
Entity List: {entity_list}

Input Text: {text}

######################
Output (valid JSON only):
"""

# ============================================================================
# TEST CASES with PRE-DEFINED ENTITIES
# ============================================================================
HEALTHCARE_TEXT = """Dr. Sarah Chen, chief cardiologist at Metropolitan Hospital in Boston, announced a breakthrough treatment for atrial fibrillation on Monday. The innovative procedure, developed in collaboration with BioTech Solutions and funded by the National Heart Foundation, uses advanced catheter ablation techniques combined with AI-powered imaging. Clinical trials conducted from January to September 2024 showed a 92% success rate among 150 patients. Dr. Chen's research team includes Dr. Marcus Williams from Stanford Medical Center and Dr. Priya Patel from Johns Hopkins University. The FDA is expected to approve the treatment by December 2024."""

CLIMATE_TEXT = """The International Climate Summit in Copenhagen concluded yesterday with representatives from 45 nations signing the Green Energy Accord. The agreement commits signatories to reduce carbon emissions by 40% before 2030. Climate scientist Professor Emma Rodriguez from MIT presented data showing Arctic ice loss has accelerated 15% since 2020. Major industrial nations including Germany, Japan, and Canada pledged $500 billion to renewable energy infrastructure. Environmental advocacy group EarthFirst praised the accord but noted concerns about enforcement mechanisms. The European Union will host the next summit in Paris in 2026."""

AUTOMOTIVE_TEXT = """Tesla Motors unveiled its latest electric vehicle, the Model Z sedan, at the Detroit Auto Show on Thursday. The vehicle features a revolutionary solid-state battery developed by partner company QuantumCell, offering 600 miles of range on a single charge. CEO Jennifer Park stated production will begin at the Gigafactory in Austin, Texas in March 2025. The Model Z competes directly with the Lucid Air and BMW i7 in the luxury EV segment. Automotive industry analyst Robert Kim from Morgan Stanley predicts the Model Z will capture 8% market share within two years. Pre-orders exceeded 50,000 units in the first week."""

TEST_CASES = [
    {
        "id": 1,
        "name": "Healthcare Innovation",
        "text": HEALTHCARE_TEXT,
        "entities": [
            "Dr. Sarah Chen", "Metropolitan Hospital", "Boston", "atrial fibrillation",
            "BioTech Solutions", "National Heart Foundation", "catheter ablation",
            "AI-powered imaging", "Clinical trials", "January to September 2024",
            "Dr. Marcus Williams", "Stanford Medical Center", "Dr. Priya Patel",
            "Johns Hopkins University", "FDA", "December 2024"
        ],
        "expected_relations": 14,
    },
    {
        "id": 2,
        "name": "Climate Policy",
        "text": CLIMATE_TEXT,
        "entities": [
            "International Climate Summit", "Copenhagen", "45 nations",
            "Green Energy Accord", "carbon emissions", "2030",
            "Professor Emma Rodriguez", "MIT", "Arctic ice loss", "2020",
            "Germany", "Japan", "Canada", "$500 billion",
            "renewable energy infrastructure", "EarthFirst", "European Union",
            "Paris", "2026"
        ],
        "expected_relations": 12,
    },
    {
        "id": 3,
        "name": "Automotive Industry",
        "text": AUTOMOTIVE_TEXT,
        "entities": [
            "Tesla Motors", "Model Z sedan", "Detroit Auto Show", "Thursday",
            "solid-state battery", "QuantumCell", "600 miles", "Jennifer Park",
            "Gigafactory", "Austin", "Texas", "March 2025",
            "Lucid Air", "BMW i7", "luxury EV segment",
            "Robert Kim", "Morgan Stanley", "8% market share",
            "50,000 units", "first week"
        ],
        "expected_relations": 15,
    }
]

# ============================================================================
# MODELS TO TEST
# ============================================================================
MODELS_TO_TEST = [
    "hf.co/mradermacher/NuExtract-2.0-4B-i1-GGUF:Q4_K_M",
    "hf.co/mradermacher/NuExtract-2.0-4B-i1-GGUF:Q6_K",
    "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M",
    "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0",
    "hf.co/MaziyarPanahi/Qwen3-4B-GGUF:Q6_K",
    "qwen3:4b",
    "llama3.2:3b",
]


def parse_json_response(response: str) -> dict:
    """Parse JSON response, handling markdown code blocks and malformed JSON."""
    import re

    cleaned = response.strip()

    # Remove markdown code blocks
    if cleaned.startswith('```'):
        lines = cleaned.split('\n')
        cleaned = '\n'.join(lines[1:-1]) if len(lines) > 2 else cleaned
        cleaned = cleaned.replace('```json', '').replace('```', '').strip()

    # Try direct parsing first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # If all else fails, return empty structure
        return {"relations": []}


def test_relation_extraction(model: str, test_case: dict, client: Client, log_path: Path) -> dict:
    """Test relation extraction with pre-defined entities."""

    results = {
        "model": model,
        "test_id": test_case["id"],
        "test_name": test_case["name"],
        "extraction_time": 0,
        "relations_found": 0,
        "relations_expected": test_case["expected_relations"],
        "relation_accuracy": 0,
        "status": "FAIL",
        "errors": []
    }

    try:
        # Format entity list for prompt
        entity_list_str = ", ".join(test_case['entities'])

        user_prompt_relation = USER_PROMPT_TEMPLATE_RELATION.format(
            entity_list=entity_list_str,
            text=test_case['text']
        )

        # Relation Extraction
        start = time.perf_counter()
        response_relation = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_RELATION},
                {"role": "user", "content": user_prompt_relation}
            ],
            options={
                "temperature": 0.1,
                "num_predict": 2000,
                "num_ctx": 16384
            },
            format="json"
        )
        results['extraction_time'] = time.perf_counter() - start
        raw_relation_response = response_relation["message"]["content"]

        # Parse response
        relation_data = parse_json_response(raw_relation_response)
        relations = relation_data.get('relations', [])

        # Filter out relations with null targets
        valid_relations = [r for r in relations if r.get('target') is not None]
        results['relations_found'] = len(valid_relations)

        # Calculate accuracy
        results['relation_accuracy'] = 100 * results['relations_found'] / test_case['expected_relations'] if test_case['expected_relations'] > 0 else 0
        results['status'] = "PASS" if results['relations_found'] > 0 else "FAIL"

        # Log Results
        log_content = f"""
{'='*80}
MODEL: {model} | TEST CASE {test_case['id']}: {test_case['name']}
{'='*80}

Expected Relations: {test_case['expected_relations']}
Found Relations: {results['relations_found']} (filtered {len(relations) - len(valid_relations)} null targets)
Extraction Time: {results['extraction_time']:.2f}s
Accuracy: {results['relation_accuracy']:.1f}%
Status: {results['status']}

{'='*80}
ENTITY LIST ({len(test_case['entities'])} entities):
{'='*80}
{', '.join(test_case['entities'])}

{'='*80}
RAW LLM RESPONSE:
{'='*80}
{raw_relation_response}

{'='*80}
PARSED RELATIONS ({len(valid_relations)} valid):
{'='*80}
{json.dumps(valid_relations, indent=2)}

"""
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_content)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()

        results['errors'].append(str(e))
        results['status'] = "ERROR"

        # Log error
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"""
{'='*80}
MODEL: {model} | TEST CASE {test_case['id']}: {test_case['name']} [ERROR]
{'='*80}
Error: {e}

Full Traceback:
{error_details}
{'='*80}
""")

    return results


def main():
    """Main benchmark execution."""
    print(f"""{'='*80}
     Relation Extraction Benchmark - All Models
{'='*80}

Setup:
  - NO entity extraction phase
  - Pre-defined entity lists for each test case
  - Tests {len(MODELS_TO_TEST)} models across {len(TEST_CASES)} test cases
  - Warmup before each model
  - Context Window: 16384 tokens
  - Enhanced prompts with 4 examples
    """)

    client = Client()

    # Create log directory
    log_dir = Path("logs/relation_extraction_benchmark")
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{timestamp}_relation_extraction_all_models.log"
    log_path = log_dir / log_filename

    # Write log header
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f"""{'='*80}
RELATION EXTRACTION BENCHMARK - ALL MODELS
{'='*80}

Models Tested: {len(MODELS_TO_TEST)}
Test Cases: {len(TEST_CASES)}
Context Window: 16384
Start Time: {datetime.now().isoformat()}

Models:
{chr(10).join(f'  - {m}' for m in MODELS_TO_TEST)}

{'='*80}

""")

    all_results = []

    for model_idx, model in enumerate(MODELS_TO_TEST, 1):
        model_short = model.split('/')[-1] if '/' in model else model

        print(f"\n{'='*80}")
        print(f"[{model_idx}/{len(MODELS_TO_TEST)}] MODEL: {model_short}")
        print(f"{'='*80}")

        # Warmup
        print("\n[WARMUP] Loading model (not measured)...", end=" ", flush=True)
        try:
            client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello"}
                ],
                options={"num_ctx": 16384}
            )
            print("OK")
        except Exception as e:
            print(f"WARNING: {e}")
            continue

        # Test all cases
        for test_case in TEST_CASES:
            print(f"\n  [{test_case['id']}/3] {test_case['name']}...", end=" ", flush=True)
            result = test_relation_extraction(model, test_case, client, log_path)
            all_results.append(result)

            print(f"\n    Relations: {result['relations_found']}/{result['relations_expected']} ({result['relation_accuracy']:.0f}%)")
            print(f"    Time: {result['extraction_time']:.1f}s")
            print(f"    Status: [{result['status']}]")

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print(f"\n{'='*80}")
    print("SUMMARY: RELATION EXTRACTION BENCHMARK")
    print(f"{'='*80}\n")

    print(f"{'Model':<40} {'Avg Accuracy':<15} {'Avg Time':<12} {'Status':<8}")
    print(f"{'-'*40} {'-'*15} {'-'*12} {'-'*8}")

    for model in MODELS_TO_TEST:
        model_results = [r for r in all_results if r['model'] == model]
        if not model_results:
            continue

        model_short = model.split('/')[-1] if '/' in model else model
        avg_accuracy = sum(r['relation_accuracy'] for r in model_results) / len(model_results)
        avg_time = sum(r['extraction_time'] for r in model_results) / len(model_results)
        success_rate = 100 * sum(1 for r in model_results if r['status'] in ['PASS']) / len(model_results)

        print(f"{model_short:<40} {avg_accuracy:>6.1f}%        {avg_time:>6.1f}s      {success_rate:>3.0f}%")

    # Save results
    output_file = Path("relation_extraction_benchmark_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*80}")
    print(f"[OK] Detailed results saved to: {output_file}")
    print(f"[OK] Detailed logs saved to: {log_dir}/")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
