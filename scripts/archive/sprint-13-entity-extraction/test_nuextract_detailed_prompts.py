#!/usr/bin/env python3
"""Test NuExtract models with detailed LightRAG-style prompts in JSON format.

Sprint 13 TD-31: Compare simple vs detailed prompts for NuExtract models.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from ollama import Client

# ============================================================================
# LIGHTRAG DELIMITERS (for conversion)
# ============================================================================
TUPLE_DELIMITER = "<|#|>"
COMPLETION_DELIMITER = "<|COMPLETE|>"

# ============================================================================
# SIMPLE JSON PROMPT (current baseline)
# ============================================================================
SYSTEM_PROMPT_SIMPLE = """---Role---
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
     - `description`: Concise explanation of the relationship
     - `strength`: Relationship strength score (1-10)

---Output Requirements---
Output valid JSON with two arrays: "entities" and "relations".
No markdown formatting, no code blocks, just pure JSON."""

USER_PROMPT_TEMPLATE_SIMPLE = """---Task---
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
    {{"source": "SourceEntity", "target": "TargetEntity", "description": "Relationship description", "strength": 8}},
    ...
  ]
}}

Output only valid JSON, no markdown, no code blocks."""

# ============================================================================
# DETAILED JSON PROMPT (adapted from LightRAG original)
# ============================================================================
SYSTEM_PROMPT_DETAILED = """---Role---
You are an intelligent assistant that helps analyze entities and relationships presented in a text document.

---Goal---
Given a text document, identify all entities and all relationships among the identified entities.

---Steps---
1. Identify all entities. For each identified entity, extract the following information:
   - name: Name of the entity, capitalized
   - type: One of the following types: ORGANIZATION, PERSON, LOCATION, TECHNOLOGY, CONCEPT, EVENT, DATE, PRODUCT, OTHER
   - description: Comprehensive description of the entity's attributes and activities

2. From the entities identified in step 1, identify all pairs of (source, target) that are *clearly related* to each other.
   For each pair of related entities, extract the following information:
   - source: name of the source entity, as identified in step 1
   - target: name of the target entity, as identified in step 1
   - description: Explanation as to why you think the source entity and the target entity are related to each other
   - strength: A numeric score (1-10) indicating strength of the relationship between the source entity and target entity

3. Return output as valid JSON with two arrays: "entities" and "relations".

---Output Requirements---
Output valid JSON only. No markdown formatting, no code blocks, just pure JSON."""

USER_PROMPT_TEMPLATE_DETAILED = """---Task---
Extract entities and relationships from the input text following the detailed steps above.

######################
-Examples-
######################
Example 1 - Character Dynamics:

Input text:
"while Alex clenched his jaw, the buzz of frustration dull against the backdrop of Taylor's authoritarian certainty. It was this competitive undercurrent that kept him alert, the sense that his and Jordan's shared commitment to discovery was an unspoken rebellion against Cruz's narrowing vision of control and order. Then Taylor did something unexpected. They paused beside Jordan and, for a moment, observed the device with something akin to reverence."

Expected output:
{{
  "entities": [
    {{"name": "Alex", "type": "PERSON", "description": "Alex is a character who experiences frustration and is observant of the dynamics among other characters."}},
    {{"name": "Taylor", "type": "PERSON", "description": "Taylor is portrayed with authoritarian certainty and shows a moment of reverence towards a device, indicating a change in perspective."}},
    {{"name": "Jordan", "type": "PERSON", "description": "Jordan shares a commitment to discovery and has a significant interaction with Taylor regarding a device."}},
    {{"name": "Cruz", "type": "PERSON", "description": "Cruz is associated with a vision of control and order, influencing the dynamics among other characters."}},
    {{"name": "The Device", "type": "TECHNOLOGY", "description": "The Device is central to the story, with potential game-changing implications, and is revered by Taylor."}}
  ],
  "relations": [
    {{"source": "Alex", "target": "Taylor",  "description": "Alex observes Taylor's authoritarian behavior and notes changes in Taylor's attitude toward the device.", "strength": 7}},
    {{"source": "Alex", "target": "Jordan", "description": "Alex and Jordan share a commitment to discovery, which contrasts with Cruz's vision.", "strength": 8}},
    {{"source": "Taylor", "target": "Jordan",  "description": "Taylor and Jordan interact directly regarding the device, leading to a moment of mutual respect and an uneasy truce.", "strength": 6}},
    {{"source": "Jordan", "target": "Cruz",  "description": "Jordan's commitment to discovery is in rebellion against Cruz's vision of control and order.", "strength": 7}},
    {{"source": "Taylor", "target": "The Device", "description": "Taylor shows reverence towards the device, indicating its importance and potential impact.", "strength": 8}}
  ]
}}

Example 2 - Financial Markets:

Input text:
"Stock markets faced a sharp downturn today as tech giants saw significant declines, with the global tech index dropping by 3.4% in midday trading. Analysts attribute the selloff to investor concerns over rising interest rates and regulatory uncertainty. Among the hardest hit, Nexon Technologies saw its stock plummet by 7.8% after reporting lower-than-expected quarterly earnings."

Expected output:
{{
  "entities": [
    {{"name": "Global Tech Index", "type": "CONCEPT", "description": "The Global Tech Index tracks the performance of major technology stocks and experienced a 3.4% decline today."}},
    {{"name": "Nexon Technologies", "type": "ORGANIZATION", "description": "Nexon Technologies is a tech company that saw its stock decline by 7.8% after disappointing earnings."}},
    {{"name": "Market Selloff", "type": "EVENT", "description": "Market selloff refers to the significant decline in stock values due to investor concerns over interest rates and regulations."}}
  ],
  "relations": [
    {{"source": "Global Tech Index", "target": "Market Selloff",  "description": "The decline in the Global Tech Index is part of the broader market selloff driven by investor concerns.", "strength": 9}},
    {{"source": "Nexon Technologies", "target": "Global Tech Index",  "description": "Nexon Technologies' stock decline contributed to the overall drop in the Global Tech Index.", "strength": 8}},
    {{"source": "Nexon Technologies", "target": "Market Selloff",  "description": "Nexon Technologies was among the hardest hit in the market selloff with a 7.8% decline.", "strength": 9}}
  ]
}}

Example 3 - Sports Achievement:

Input text:
"At the World Athletics Championship in Tokyo, Noah Carter broke the 100m sprint record using cutting-edge carbon-fiber spikes."

Expected output:
{{
  "entities": [
    {{"name": "World Athletics Championship", "type": "EVENT", "description": "The World Athletics Championship is a global sports competition featuring top athletes in track and field."}},
    {{"name": "Tokyo", "type": "LOCATION", "description": "Tokyo is the host city of the World Athletics Championship."}},
    {{"name": "Noah Carter", "type": "PERSON", "description": "Noah Carter is a sprinter who set a new record in the 100m sprint at the World Athletics Championship."}},
    {{"name": "100m Sprint Record", "type": "CONCEPT", "description": "The 100m sprint record is a benchmark in athletics, recently broken by Noah Carter."}},
    {{"name": "Carbon-Fiber Spikes", "type": "TECHNOLOGY", "description": "Carbon-fiber spikes are advanced sprinting shoes that provide enhanced speed and traction."}}
  ],
  "relations": [
    {{"source": "World Athletics Championship", "target": "Tokyo",  "description": "The World Athletics Championship is being hosted in Tokyo.", "strength": 9}},
    {{"source": "Noah Carter", "target": "100m Sprint Record",  "description": "Noah Carter set a new 100m sprint record at the championship.", "strength": 10}},
    {{"source": "Noah Carter", "target": "Carbon-Fiber Spikes",  "description": "Noah Carter used carbon-fiber spikes to enhance performance during the race.", "strength": 7}},
    {{"source": "Noah Carter", "target": "World Athletics Championship",  "description": "Noah Carter is competing at the World Athletics Championship.", "strength": 9}}
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
# ENHANCED PROMPT (Focus on Completeness and Implicit Entities)
# ============================================================================
SYSTEM_PROMPT_ENHANCED = """---Role---
You are an intelligent assistant that extracts entities and relationships from a text document
for knowledge graph construction.

---Goal---
Identify all entities (people, organizations, technologies, events, locations, and abstract concepts)
and all meaningful relationships between these entities.

---Instructions---
1. **Entity Extraction**
   - Extract **every explicit and implicit entity** relevant to the text context.
   - Include entities even if they are only **indirectly implied** (e.g., event locations, referenced companies).
   - For each entity, extract:
     - `name`: Name of the entity (capitalized)
     - `type`: PERSON, ORGANIZATION, LOCATION, TECHNOLOGY, CONCEPT, EVENT, DATE, PRODUCT, OTHER
     - `description`: Brief but informative summary

2. **Relationship Extraction**
   - Identify **both explicit and implicit relationships** between extracted entities.
   - Include inferred relationships when the text provides contextual clues (e.g., co-workers, located in, created by).
   - For each relationship, extract:
     - `source`: Source entity name
     - `target`: Target entity name
     - `description`: Clear explanation of the relationship
     - `strength`: Relationship strength score (1-10)

3. **Completeness Rules**
   - Always include LOCATION, EVENT, CONCEPT and ORGANIZATION entities if mentioned or inferable.
   - Include multiple relations if an entity participates in several interactions.
   - Avoid repeating identical relations.

---Output---
Return valid JSON with the following format:
{{
  "entities": [...],
  "relations": [...]
}}
No markdown or commentary. Output pure JSON only."""

USER_PROMPT_TEMPLATE_ENHANCED = """---Task---
Extract all entities and relationships from the input text following the detailed rules above.

######################
-Examples-
######################
Example 1 - Character Dynamics:

Input text:
"while Alex clenched his jaw, the buzz of frustration dull against the backdrop of Taylor's authoritarian certainty. It was this competitive undercurrent that kept him alert, the sense that his and Jordan's shared commitment to discovery was an unspoken rebellion against Cruz's narrowing vision of control and order. Then Taylor did something unexpected. They paused beside Jordan and, for a moment, observed the device with something akin to reverence."

Expected output:
{{
  "entities": [
    {{"name": "Alex", "type": "PERSON", "description": "Alex is a character who experiences frustration and is observant of the dynamics among other characters."}},
    {{"name": "Taylor", "type": "PERSON", "description": "Taylor is portrayed with authoritarian certainty and shows a moment of reverence towards a device, indicating a change in perspective."}},
    {{"name": "Jordan", "type": "PERSON", "description": "Jordan shares a commitment to discovery and has a significant interaction with Taylor regarding a device."}},
    {{"name": "Cruz", "type": "PERSON", "description": "Cruz is associated with a vision of control and order, influencing the dynamics among other characters."}},
    {{"name": "The Device", "type": "TECHNOLOGY", "description": "The Device is central to the story, with potential game-changing implications, and is revered by Taylor."}}
  ],
  "relations": [
    {{"source": "Alex", "target": "Taylor",  "description": "Alex observes Taylor's authoritarian behavior and notes changes in Taylor's attitude toward the device.", "strength": 7}},
    {{"source": "Alex", "target": "Jordan",  "description": "Alex and Jordan share a commitment to discovery, which contrasts with Cruz's vision.", "strength": 8}},
    {{"source": "Taylor", "target": "Jordan",  "description": "Taylor and Jordan interact directly regarding the device, leading to a moment of mutual respect and an uneasy truce.", "strength": 6}},
    {{"source": "Jordan", "target": "Cruz",  "description": "Jordan's commitment to discovery is in rebellion against Cruz's vision of control and order.", "strength": 7}},
    {{"source": "Taylor", "target": "The Device",  "description": "Taylor shows reverence towards the device, indicating its importance and potential impact.", "strength": 8}}
  ]
}}

Example 2 - Financial Markets:

Input text:
"Stock markets faced a sharp downturn today as tech giants saw significant declines, with the global tech index dropping by 3.4% in midday trading. Analysts attribute the selloff to investor concerns over rising interest rates and regulatory uncertainty. Among the hardest hit, Nexon Technologies saw its stock plummet by 7.8% after reporting lower-than-expected quarterly earnings."

Expected output:
{{
  "entities": [
    {{"name": "Global Tech Index", "type": "CONCEPT", "description": "The Global Tech Index tracks the performance of major technology stocks and experienced a 3.4% decline today."}},
    {{"name": "Nexon Technologies", "type": "ORGANIZATION", "description": "Nexon Technologies is a tech company that saw its stock decline by 7.8% after disappointing earnings."}},
    {{"name": "Market Selloff", "type": "EVENT", "description": "Market selloff refers to the significant decline in stock values due to investor concerns over interest rates and regulations."}}
  ],
  "relations": [
    {{"source": "Global Tech Index", "target": "Market Selloff",  "description": "The decline in the Global Tech Index is part of the broader market selloff driven by investor concerns.", "strength": 9}},
    {{"source": "Nexon Technologies", "target": "Global Tech Index", "description": "Nexon Technologies' stock decline contributed to the overall drop in the Global Tech Index.", "strength": 8}},
    {{"source": "Nexon Technologies", "target": "Market Selloff",  "description": "Nexon Technologies was among the hardest hit in the market selloff with a 7.8% decline.", "strength": 9}}
  ]
}}

Example 3 - Sports Achievement:

Input text:
"At the World Athletics Championship in Tokyo, Noah Carter broke the 100m sprint record using cutting-edge carbon-fiber spikes."

Expected output:
{{
  "entities": [
    {{"name": "World Athletics Championship", "type": "EVENT", "description": "The World Athletics Championship is a global sports competition featuring top athletes in track and field."}},
    {{"name": "Tokyo", "type": "LOCATION", "description": "Tokyo is the host city of the World Athletics Championship."}},
    {{"name": "Noah Carter", "type": "PERSON", "description": "Noah Carter is a sprinter who set a new record in the 100m sprint at the World Athletics Championship."}},
    {{"name": "100m Sprint Record", "type": "CONCEPT", "description": "The 100m sprint record is a benchmark in athletics, recently broken by Noah Carter."}},
    {{"name": "Carbon-Fiber Spikes", "type": "TECHNOLOGY", "description": "Carbon-fiber spikes are advanced sprinting shoes that provide enhanced speed and traction."}}
  ],
  "relations": [
    {{"source": "World Athletics Championship", "target": "Tokyo",  "description": "The World Athletics Championship is being hosted in Tokyo.", "strength": 9}},
    {{"source": "Noah Carter", "target": "100m Sprint Record", "description": "Noah Carter set a new 100m sprint record at the championship.", "strength": 10}},
    {{"source": "Noah Carter", "target": "Carbon-Fiber Spikes",  "description": "Noah Carter used carbon-fiber spikes to enhance performance during the race.", "strength": 7}},
    {{"source": "Noah Carter", "target": "World Athletics Championship",  "description": "Noah Carter is competing at the World Athletics Championship.", "strength": 9}}
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
# TEST CASES - Same as before
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


def convert_json_to_lightrag(json_data: dict) -> str:
    """Convert JSON format to LightRAG delimiter-separated format."""
    lines = []

    # Convert entities
    for entity in json_data.get("entities", []):
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
    for relation in json_data.get("relations", []):
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


def validate_json_and_convert(response: str) -> dict:
    """Validate JSON response and convert to LightRAG format."""
    result = {
        "json_valid": False,
        "json_data": None,
        "lightrag_format": "",
        "entity_count": 0,
        "relation_count": 0,
        "errors": [],
    }

    try:
        # Remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        json_data = json.loads(cleaned)
        result["json_valid"] = True
        result["json_data"] = json_data

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
    prompt_type: str,
):
    """Append test execution to model's log file."""
    log_content = f"""
{'='*80}
TEST CASE {test_case['id']}: {test_case['name']} [{prompt_type.upper()} PROMPT]
{'='*80}

Start Time: {start_time.isoformat()}
End Time: {end_time.isoformat()}
Duration: {duration:.2f}s
Expected: {test_case['expected_entities']} entities, {test_case['expected_relations']} relations
Found: {validation['entity_count']} entities, {validation['relation_count']} relations
Accuracy: {validation['entity_count']}/{test_case['expected_entities']} entities ({100*validation['entity_count']/test_case['expected_entities']:.1f}%), {validation['relation_count']}/{test_case['expected_relations']} relations ({100*validation['relation_count']/test_case['expected_relations']:.1f}%)

{'='*80}
SYSTEM PROMPT:
{'='*80}
{system_prompt[:500]}...

{'='*80}
USER PROMPT:
{'='*80}
{user_prompt[:500]}...

{'='*80}
RAW JSON RESPONSE FROM LLM:
{'='*80}
{raw_response}

{'='*80}
VALIDATION RESULTS:
{'='*80}
JSON Valid: {validation['json_valid']}
Entities Found: {validation['entity_count']} (expected: {test_case['expected_entities']})
Relations Found: {validation['relation_count']} (expected: {test_case['expected_relations']})
Errors: {validation['errors']}

{'='*80}
CONVERTED LIGHTRAG FORMAT:
{'='*80}
{validation['lightrag_format']}

"""

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_content)


def test_model(
    model: str,
    test_case: dict,
    client: Client,
    log_path: Path,
    system_prompt: str,
    user_prompt_template: str,
    prompt_type: str,
    use_think_false: bool = False,
) -> dict:
    """Test a model with specified prompts."""
    mode = "think=False" if use_think_false else "default"

    user_prompt = user_prompt_template.format(text=test_case["text"])

    start_time = datetime.now()
    start = time.perf_counter()

    try:
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": 0.1, "num_predict": 2000, "num_ctx": 16384},
            "format": "json",
        }

        if use_think_false:
            kwargs["think"] = False

        response = client.chat(**kwargs)
        elapsed = time.perf_counter() - start
        end_time = datetime.now()

        content = response["message"]["content"]
        validation = validate_json_and_convert(content)

        append_to_log(
            log_path=log_path,
            test_case=test_case,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=content,
            validation=validation,
            start_time=start_time,
            end_time=end_time,
            duration=elapsed,
            prompt_type=prompt_type,
        )

        return {
            "model": model,
            "prompt_type": prompt_type,
            "mode": mode,
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "time": elapsed,
            "json_valid": validation["json_valid"],
            "entities_found": validation["entity_count"],
            "relations_found": validation["relation_count"],
            "entities_expected": test_case["expected_entities"],
            "relations_expected": test_case["expected_relations"],
            "entity_accuracy": (
                100 * validation["entity_count"] / test_case["expected_entities"]
                if test_case["expected_entities"] > 0
                else 0
            ),
            "relation_accuracy": (
                100 * validation["relation_count"] / test_case["expected_relations"]
                if test_case["expected_relations"] > 0
                else 0
            ),
            "errors": validation["errors"],
            "status": (
                "PASS" if validation["json_valid"] and validation["entity_count"] > 0 else "FAIL"
            ),
        }

    except Exception as e:
        elapsed = time.perf_counter() - start
        end_time = datetime.now()

        error_msg = f"Exception during test: {e}"

        append_to_log(
            log_path=log_path,
            test_case=test_case,
            system_prompt=system_prompt,
            user_prompt=user_prompt_template.format(text=test_case["text"]),
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
            prompt_type=prompt_type,
        )

        return {
            "model": model,
            "prompt_type": prompt_type,
            "mode": mode,
            "test_id": test_case["id"],
            "test_name": test_case["name"],
            "time": elapsed,
            "json_valid": False,
            "entities_found": 0,
            "relations_found": 0,
            "entities_expected": test_case["expected_entities"],
            "relations_expected": test_case["expected_relations"],
            "entity_accuracy": 0,
            "relation_accuracy": 0,
            "errors": [error_msg],
            "status": "ERROR",
        }


def main():
    """Main test execution."""
    print(
        f"""{'='*80}
     NuExtract: Prompt Strategy Comparison
{'='*80}

Comparing three prompt strategies:
1. SIMPLE: Basic JSON extraction prompt (no examples)
2. DETAILED: LightRAG-style prompt with 3 examples from original LightRAG
3. ENHANCED: Completeness-focused prompt (implicit entities, locations, events)

All output JSON format, converted to LightRAG delimiter-separated format.
Context Window: 16384 (LightRAG default)
    """
    )

    client = Client()

    # Test only NuExtract Q4_K_M (best performer)
    models_to_test = [
        ("hf.co/mradermacher/NuExtract-2.0-4B-i1-GGUF:Q4_K_M", True),
    ]

    results = []
    log_dir = Path("logs/nuextract_prompt_comparison")
    log_dir.mkdir(parents=True, exist_ok=True)

    for model, supports_think in models_to_test:
        model_short = model.split("/")[-1] if "/" in model else model

        print(f"\n{'='*80}")
        print(f"MODEL: {model_short}")
        print(f"{'='*80}")

        # Warmup
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

        # Test all three prompt types
        for prompt_type, sys_prompt, user_template in [
            ("simple", SYSTEM_PROMPT_SIMPLE, USER_PROMPT_TEMPLATE_SIMPLE),
            ("detailed", SYSTEM_PROMPT_DETAILED, USER_PROMPT_TEMPLATE_DETAILED),
            ("enhanced", SYSTEM_PROMPT_ENHANCED, USER_PROMPT_TEMPLATE_ENHANCED),
        ]:
            print(f"\n  --- Testing {prompt_type.upper()} prompts ---")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{timestamp}_{model_short.replace(':', '_')}_{prompt_type}.log"
            log_path = log_dir / log_filename

            # Write log header
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(
                    f"""{'='*80}
NuExtract PROMPT COMPARISON TEST LOG
{'='*80}

Model: {model}
Prompt Type: {prompt_type.upper()}
Test Suite: All 3 LightRAG Original Examples
Context Window: 16384
Start Time: {datetime.now().isoformat()}

{'='*80}

"""
                )

            for test_case in TEST_CASES:
                print(f"  [{test_case['id']}/3] {test_case['name']}...", end=" ", flush=True)
                result = test_model(
                    model,
                    test_case,
                    client,
                    log_path,
                    sys_prompt,
                    user_template,
                    prompt_type,
                    use_think_false=False,
                )
                results.append(result)

                status = "OK" if result["status"] == "PASS" else "FAIL"
                print(
                    f"{result['entities_found']}E/{result['relations_found']}R "
                    f"({result['entity_accuracy']:.0f}%/{result['relation_accuracy']:.0f}%) "
                    f"in {result['time']:.1f}s [{status}]"
                )

    # ========================================================================
    # SUMMARY & COMPARISON
    # ========================================================================
    print(f"\n{'='*80}")
    print("SUMMARY: PROMPT COMPARISON")
    print(f"{'='*80}\n")

    print(
        f"{'Prompt':<10} {'Test':<30} {'JSON':<8} {'Entities':<15} {'Relations':<15} {'Time':<8} {'Status':<8}"
    )
    print(f"{'-'*10} {'-'*30} {'-'*8} {'-'*15} {'-'*15} {'-'*8} {'-'*8}")

    for r in results:
        json_status = "VALID" if r["json_valid"] else "INVALID"
        entity_str = f"{r['entities_found']}/{r['entities_expected']} ({r['entity_accuracy']:.0f}%)"
        relation_str = (
            f"{r['relations_found']}/{r['relations_expected']} ({r['relation_accuracy']:.0f}%)"
        )
        time_str = f"{r['time']:.1f}s"

        print(
            f"{r['prompt_type']:<10} {r['test_name']:<30} {json_status:<8} {entity_str:<15} {relation_str:<15} {time_str:<8} {r['status']:<8}"
        )

    # Calculate averages
    print(f"\n{'='*80}")
    print("AVERAGE PERFORMANCE")
    print(f"{'='*80}\n")

    for prompt_type in ["simple", "detailed", "enhanced"]:
        prompt_results = [r for r in results if r["prompt_type"] == prompt_type]
        if prompt_results:
            avg_time = sum(r["time"] for r in prompt_results) / len(prompt_results)
            avg_entity_acc = sum(r["entity_accuracy"] for r in prompt_results) / len(prompt_results)
            avg_relation_acc = sum(r["relation_accuracy"] for r in prompt_results) / len(
                prompt_results
            )
            success_rate = (
                100 * sum(1 for r in prompt_results if r["status"] == "PASS") / len(prompt_results)
            )

            print(f"{prompt_type.upper()} PROMPT:")
            print(f"  Average Time: {avg_time:.1f}s")
            print(f"  Average Entity Accuracy: {avg_entity_acc:.1f}%")
            print(f"  Average Relation Accuracy: {avg_relation_acc:.1f}%")
            print(f"  Success Rate: {success_rate:.0f}%")
            print()

    # Save results
    output_file = Path("nuextract_prompt_comparison.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"{'='*80}")
    print(f"[OK] Detailed results saved to: {output_file}")
    print(f"[OK] Detailed logs saved to: {log_dir}/")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
