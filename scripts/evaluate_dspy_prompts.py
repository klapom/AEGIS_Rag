#!/usr/bin/env python3
"""A/B Test: Generic Prompts vs DSPy-Optimized Prompts.

Sprint 86: Feature 86.2 - DSPy Prompt Evaluation

This script compares extraction quality between:
- Baseline: Current generic prompts from extraction_prompts.py
- Optimized: DSPy MIPROv2 optimized prompts

All requests and responses are logged for debugging and analysis.
Pipeline compatibility is validated for every response.

Usage:
    poetry run python scripts/evaluate_dspy_prompts.py --help
    poetry run python scripts/evaluate_dspy_prompts.py --test-data data/dspy_training/test.jsonl
    poetry run python scripts/evaluate_dspy_prompts.py --quick-test
"""

import argparse
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False
    print("WARNING: DSPy not installed. Run: pip install dspy-ai")

from pydantic import ValidationError

# ============================================================================
# Logging Configuration
# ============================================================================

LOG_DIR = Path("logs/dspy_ab_test")
LOG_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class RequestLog:
    """Log entry for a single LLM request."""

    timestamp: str
    test_id: str
    prompt_type: str  # "baseline" or "optimized"
    model: str
    prompt: str
    raw_response: str
    parsed_entities: list[dict] | None
    parsed_relations: list[dict] | None
    parse_success: bool
    pipeline_compatible: bool
    validation_errors: list[str]
    latency_ms: float


@dataclass
class TestResult:
    """Results for a single test case."""

    test_id: str
    text: str
    domain: str
    gold_entities: list[dict]
    gold_relations: list[dict]
    baseline_result: dict | None = None
    optimized_result: dict | None = None
    baseline_log: RequestLog | None = None
    optimized_log: RequestLog | None = None


# ============================================================================
# Pipeline Compatibility Validation
# ============================================================================


def validate_entity_for_pipeline(entity: dict) -> tuple[bool, list[str]]:
    """
    Validate that an entity can be processed by the extraction pipeline.

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Required fields
    if "name" not in entity or not entity.get("name"):
        errors.append("Missing or empty 'name' field")

    if "type" not in entity or not entity.get("type"):
        errors.append("Missing or empty 'type' field")

    # Optional but expected fields
    if "description" not in entity:
        errors.append("Missing 'description' field (will use empty string)")

    # Type validation
    if not isinstance(entity.get("name", ""), str):
        errors.append(f"'name' must be string, got {type(entity.get('name'))}")

    if not isinstance(entity.get("type", ""), str):
        errors.append(f"'type' must be string, got {type(entity.get('type'))}")

    return len([e for e in errors if "Missing or empty" in e]) == 0, errors


def validate_relation_for_pipeline(relation: dict) -> tuple[bool, list[str]]:
    """
    Validate that a relation can be processed by the extraction pipeline.

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Required fields
    if "source" not in relation or not relation.get("source"):
        errors.append("Missing or empty 'source' field")

    if "target" not in relation or not relation.get("target"):
        errors.append("Missing or empty 'target' field")

    if "type" not in relation or not relation.get("type"):
        errors.append("Missing or empty 'type' field")

    # Optional but expected fields
    if "description" not in relation:
        errors.append("Missing 'description' field (will use empty string)")

    if "strength" not in relation:
        errors.append("Missing 'strength' field (will use default)")
    elif not isinstance(relation.get("strength"), (int, float)):
        errors.append(f"'strength' must be numeric, got {type(relation.get('strength'))}")

    # Type validation
    if not isinstance(relation.get("source", ""), str):
        errors.append(f"'source' must be string, got {type(relation.get('source'))}")

    if not isinstance(relation.get("target", ""), str):
        errors.append(f"'target' must be string, got {type(relation.get('target'))}")

    if not isinstance(relation.get("type", ""), str):
        errors.append(f"'type' must be string, got {type(relation.get('type'))}")

    return len([e for e in errors if "Missing or empty" in e]) == 0, errors


def validate_extraction_output(
    entities: list[dict],
    relations: list[dict]
) -> tuple[bool, list[str]]:
    """
    Validate complete extraction output for pipeline compatibility.

    Returns:
        Tuple of (all_compatible, list_of_all_errors)
    """
    all_errors = []
    all_valid = True

    # Validate entities
    for i, entity in enumerate(entities):
        is_valid, errors = validate_entity_for_pipeline(entity)
        if not is_valid:
            all_valid = False
        for error in errors:
            all_errors.append(f"Entity[{i}] ({entity.get('name', 'unknown')}): {error}")

    # Validate relations
    for i, relation in enumerate(relations):
        is_valid, errors = validate_relation_for_pipeline(relation)
        if not is_valid:
            all_valid = False
        for error in errors:
            all_errors.append(f"Relation[{i}] ({relation.get('source', '?')} -> {relation.get('target', '?')}): {error}")

    return all_valid, all_errors


# ============================================================================
# JSON Parsing Utilities
# ============================================================================


def repair_json_string(json_str: str) -> str:
    """Apply common repairs to malformed JSON from LLM responses."""
    import re

    # Remove markdown code fences
    json_str = re.sub(r"```json\s*", "", json_str)
    json_str = re.sub(r"```\s*", "", json_str)

    # Remove common prefixes
    json_str = re.sub(r"^(Entities|Relations|Output|Here are).*?:", "", json_str, flags=re.IGNORECASE)

    # Fix trailing commas
    json_str = re.sub(r",\s*]", "]", json_str)
    json_str = re.sub(r",\s*}", "}", json_str)

    # Fix Python literals
    json_str = json_str.replace("None", "null")
    json_str = json_str.replace("True", "true")
    json_str = json_str.replace("False", "false")

    return json_str.strip()


def parse_json_output(raw_response: str) -> list[dict] | None:
    """Parse JSON array from LLM response, with repair attempts."""
    import re

    def ensure_list_of_dicts(data) -> list[dict] | None:
        """Ensure the result is a list of dicts."""
        if not isinstance(data, list):
            return None
        result = []
        for item in data:
            if isinstance(item, dict):
                result.append(item)
            elif isinstance(item, str):
                # Try to parse string as JSON
                try:
                    parsed = json.loads(item)
                    if isinstance(parsed, dict):
                        result.append(parsed)
                except json.JSONDecodeError:
                    pass
        return result if result else None

    # Try direct parse first
    try:
        result = json.loads(raw_response)
        if isinstance(result, list):
            return ensure_list_of_dicts(result)
        elif isinstance(result, dict) and "entities" in result:
            return ensure_list_of_dicts(result["entities"])
        elif isinstance(result, dict) and "relations" in result:
            return ensure_list_of_dicts(result["relations"])
    except json.JSONDecodeError:
        pass

    # Try repair
    repaired = repair_json_string(raw_response)

    # Find JSON array in response
    array_match = re.search(r"\[[\s\S]*\]", repaired)
    if array_match:
        try:
            parsed = json.loads(array_match.group())
            return ensure_list_of_dicts(parsed)
        except json.JSONDecodeError:
            pass

    return None


# ============================================================================
# Prompt Definitions
# ============================================================================

# Baseline prompts (from extraction_prompts.py)
BASELINE_ENTITY_PROMPT = """Extract all significant entities from the following text.

An entity is any named thing: person, organization, place, concept, technology, product, event, etc.
Do NOT limit yourself to predefined types - extract whatever is meaningful in the context.

Text:
{text}

Return a JSON array of entities. Each entity should have:
- name: The exact name as it appears in text
- type: Your best categorization (use natural language, e.g., "Software Framework")
- description: Brief description based on context (1 sentence)

Output (JSON array only):
"""

BASELINE_RELATION_PROMPT = """Extract ALL relationships between the given entities from the text.

---Entities---
{entities}

---Text---
{text}

---Instructions---
1. For EVERY pair of entities that interact or relate, extract a relationship
2. Include both explicit relationships (stated in text) and implicit ones (strongly implied)
3. Rate relationship strength from 1-10 (10 = explicitly stated, 5 = implied)

---Output Format---
Return a JSON array with this structure:
[
  {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "Why they are related", "strength": 8}},
  ...
]

Output (JSON array only):
"""


# ============================================================================
# LLM Extraction Functions
# ============================================================================


class ExtractionRunner:
    """Runs extraction with either baseline or optimized prompts."""

    def __init__(self, model: str = "gpt-oss:20b", ollama_base: str = "http://localhost:11434"):
        self.model = model
        self.ollama_base = ollama_base
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = LOG_DIR / f"ab_test_{self.session_id}.jsonl"

        # Configure DSPy
        if DSPY_AVAILABLE:
            lm = dspy.LM(
                f"ollama_chat/{model}",
                api_base=ollama_base,
                temperature=0.1,
                max_tokens=4096,
            )
            dspy.configure(lm=lm)

        print(f"ExtractionRunner initialized with model: {model}")
        print(f"Log file: {self.log_file}")

    def _call_ollama(self, prompt: str) -> tuple[str, float]:
        """Call Ollama API directly and return response + latency."""
        import time
        import requests

        start = time.time()

        response = requests.post(
            f"{self.ollama_base}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 4096,
                }
            },
            timeout=120
        )

        latency_ms = (time.time() - start) * 1000

        if response.status_code == 200:
            return response.json().get("response", ""), latency_ms
        else:
            return f"ERROR: {response.status_code} - {response.text}", latency_ms

    def _log_request(self, log: RequestLog):
        """Append request log to JSONL file."""
        with open(self.log_file, "a") as f:
            log_dict = {
                "timestamp": log.timestamp,
                "test_id": log.test_id,
                "prompt_type": log.prompt_type,
                "model": log.model,
                "prompt": log.prompt[:500] + "..." if len(log.prompt) > 500 else log.prompt,
                "raw_response": log.raw_response,
                "parsed_entities_count": len(log.parsed_entities) if log.parsed_entities else 0,
                "parsed_relations_count": len(log.parsed_relations) if log.parsed_relations else 0,
                "parse_success": log.parse_success,
                "pipeline_compatible": log.pipeline_compatible,
                "validation_errors": log.validation_errors,
                "latency_ms": log.latency_ms,
            }
            f.write(json.dumps(log_dict) + "\n")

    def run_baseline(self, text: str, domain: str, test_id: str) -> tuple[list[dict], list[dict], RequestLog]:
        """Run baseline extraction (generic prompts)."""
        timestamp = datetime.now().isoformat()
        all_errors = []

        # Entity extraction
        entity_prompt = BASELINE_ENTITY_PROMPT.format(text=text)
        entity_response, entity_latency = self._call_ollama(entity_prompt)

        entities = parse_json_output(entity_response)
        if entities is None:
            entities = []
            all_errors.append("Failed to parse entity JSON")

        # Relation extraction
        entity_summary = json.dumps([{"name": e.get("name"), "type": e.get("type")} for e in entities])
        relation_prompt = BASELINE_RELATION_PROMPT.format(text=text, entities=entity_summary)
        relation_response, relation_latency = self._call_ollama(relation_prompt)

        relations = parse_json_output(relation_response)
        if relations is None:
            relations = []
            all_errors.append("Failed to parse relation JSON")

        # Validate pipeline compatibility
        pipeline_compatible, validation_errors = validate_extraction_output(entities, relations)
        all_errors.extend(validation_errors)

        log = RequestLog(
            timestamp=timestamp,
            test_id=test_id,
            prompt_type="baseline",
            model=self.model,
            prompt=f"[ENTITY]\n{entity_prompt}\n\n[RELATION]\n{relation_prompt}",
            raw_response=f"[ENTITIES]\n{entity_response}\n\n[RELATIONS]\n{relation_response}",
            parsed_entities=entities,
            parsed_relations=relations,
            parse_success=len(entities) > 0,
            pipeline_compatible=pipeline_compatible,
            validation_errors=all_errors,
            latency_ms=entity_latency + relation_latency,
        )

        self._log_request(log)

        return entities, relations, log

    def run_optimized(
        self,
        text: str,
        domain: str,
        test_id: str,
        pipeline_path: str = "data/dspy_prompts/pipeline_gptoss/pipeline_extraction_20260113_060510.json"
    ) -> tuple[list[dict], list[dict], RequestLog]:
        """Run optimized extraction (DSPy pipeline)."""
        timestamp = datetime.now().isoformat()
        all_errors = []

        # Load optimized pipeline
        pipeline_file = Path(pipeline_path)
        if not pipeline_file.exists():
            # Fallback to any pipeline file
            pipeline_dir = Path("data/dspy_prompts/pipeline_gptoss")
            if pipeline_dir.exists():
                pipeline_files = list(pipeline_dir.glob("*.json"))
                if pipeline_files:
                    pipeline_file = pipeline_files[0]

        if not pipeline_file.exists():
            all_errors.append(f"Pipeline file not found: {pipeline_path}")
            log = RequestLog(
                timestamp=timestamp,
                test_id=test_id,
                prompt_type="optimized",
                model=self.model,
                prompt="ERROR: Pipeline not found",
                raw_response="",
                parsed_entities=None,
                parsed_relations=None,
                parse_success=False,
                pipeline_compatible=False,
                validation_errors=all_errors,
                latency_ms=0,
            )
            self._log_request(log)
            return [], [], log

        # Load pipeline state
        with open(pipeline_file) as f:
            pipeline_config = json.load(f)

        # Extract instruction and demos from pipeline
        state = pipeline_config.get("state", {})

        # Get entity extractor config - note the correct key format
        entity_predictor = state.get("entity_extractor.predict", {})
        entity_instruction = entity_predictor.get("signature", {}).get("instructions", "Extract named entities from document text.")
        entity_demos = entity_predictor.get("demos", [])

        # Get relation extractor config
        relation_predictor = state.get("relation_extractor.predict", {})
        relation_instruction = relation_predictor.get("signature", {}).get("instructions", "Extract relationships between entities.")
        relation_demos = relation_predictor.get("demos", [])

        # Build optimized entity prompt with DSPy signature format
        entity_prompt = f"{entity_instruction}\n\n---\n\n"

        # Add few-shot examples
        if entity_demos:
            for demo in entity_demos[:3]:  # Max 3 demos
                demo_text = demo.get("text", "")[:300]
                demo_domain = demo.get("domain", "technical")
                demo_entities = demo.get("entities", [])

                # Parse entities if they're a string
                if isinstance(demo_entities, str):
                    try:
                        demo_entities = json.loads(demo_entities)
                    except json.JSONDecodeError:
                        demo_entities = []

                if demo_text and demo_entities:
                    entity_prompt += f"Text: {demo_text}...\n"
                    entity_prompt += f"Domain: {demo_domain}\n"
                    if demo.get("reasoning"):
                        entity_prompt += f"Reasoning: {demo['reasoning'][:200]}...\n"
                    entity_prompt += f"Entities: {json.dumps(demo_entities[:4], ensure_ascii=False)}\n\n---\n\n"

        # Add the actual query
        entity_prompt += f"Text: {text}\n"
        entity_prompt += f"Domain: {domain}\n"
        entity_prompt += "Reasoning: Let's think step by step in order to identify all named entities.\n"
        entity_prompt += "Entities:"

        # Call LLM for entities
        entity_response, entity_latency = self._call_ollama(entity_prompt)

        # Parse entity response - handle DSPy "Entities: [...]" format
        entities = self._parse_dspy_output(entity_response, "entities")
        if entities is None:
            entities = []
            all_errors.append("Failed to parse entity JSON from optimized prompt")

        # Build optimized relation prompt with DSPy format
        entity_names_json = json.dumps([{"name": e.get("name"), "type": e.get("type")} for e in entities], ensure_ascii=False)

        relation_prompt = f"{relation_instruction}\n\n---\n\n"

        # Add few-shot examples for relations
        if relation_demos:
            for demo in relation_demos[:2]:  # Max 2 demos
                demo_text = demo.get("text", "")[:200]
                demo_entities = demo.get("entities", "[]")
                demo_relations = demo.get("relations", [])

                # Parse relations if they're a string
                if isinstance(demo_relations, str):
                    try:
                        demo_relations = json.loads(demo_relations)
                    except json.JSONDecodeError:
                        demo_relations = []

                if demo_text and demo_relations:
                    relation_prompt += f"Text: {demo_text}...\n"
                    relation_prompt += f"Entities: {demo_entities[:300]}...\n"
                    relation_prompt += f"Relations: {json.dumps(demo_relations[:3], ensure_ascii=False)}\n\n---\n\n"

        # Add the actual query
        relation_prompt += f"Text: {text}\n"
        relation_prompt += f"Entities: {entity_names_json}\n"
        relation_prompt += "Reasoning: Let's think step by step to find relationships between entities.\n"
        relation_prompt += "Relations:"

        # Call LLM for relations
        relation_response, relation_latency = self._call_ollama(relation_prompt)

        # Parse relations - handle both formats
        relations = self._parse_dspy_output(relation_response, "relations")
        if relations is None:
            relations = []
            all_errors.append("Failed to parse relation JSON from optimized prompt")

        # Normalize relation format (subject/predicate/object -> source/target/type)
        relations = self._normalize_relations(relations)

        # Validate pipeline compatibility
        pipeline_compatible, validation_errors = validate_extraction_output(entities, relations)
        all_errors.extend(validation_errors)

        log = RequestLog(
            timestamp=timestamp,
            test_id=test_id,
            prompt_type="optimized",
            model=self.model,
            prompt=f"[ENTITY]\n{entity_prompt}\n\n[RELATION]\n{relation_prompt}",
            raw_response=f"[ENTITIES]\n{entity_response}\n\n[RELATIONS]\n{relation_response}",
            parsed_entities=entities,
            parsed_relations=relations,
            parse_success=len(entities) > 0,
            pipeline_compatible=pipeline_compatible,
            validation_errors=all_errors,
            latency_ms=entity_latency + relation_latency,
        )

        self._log_request(log)

        return entities, relations, log

    def _parse_dspy_output(self, response: str, output_type: str) -> list[dict] | None:
        """Parse DSPy-style output with Reasoning: and Entities:/Relations: format."""
        import re

        # First try the standard JSON parser
        result = parse_json_output(response)
        if result:
            return result

        # Look for the specific output section
        if output_type == "entities":
            pattern = r"Entities:\s*(\[[\s\S]*?\])"
        else:
            pattern = r"Relations:\s*(\[[\s\S]*?\])"

        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if isinstance(parsed, list):
                    # Handle list of strings (entity names only)
                    result = []
                    for item in parsed:
                        if isinstance(item, dict):
                            result.append(item)
                        elif isinstance(item, str):
                            # Convert string to entity dict
                            result.append({"name": item, "type": "UNKNOWN", "description": ""})
                    return result if result else None
            except json.JSONDecodeError:
                pass

        # Try to find any JSON array in the response
        array_match = re.search(r"\[[\s\S]*\]", response)
        if array_match:
            try:
                parsed = json.loads(array_match.group())
                if isinstance(parsed, list):
                    result = []
                    for item in parsed:
                        if isinstance(item, dict):
                            result.append(item)
                        elif isinstance(item, str):
                            result.append({"name": item, "type": "UNKNOWN", "description": ""})
                    return result if result else None
            except json.JSONDecodeError:
                pass

        return None

    def _normalize_relations(self, relations: list[dict]) -> list[dict]:
        """Normalize relation format from subject/predicate/object to source/target/type."""
        normalized = []
        for rel in relations:
            norm_rel = {}

            # Map source field
            if "source" in rel:
                norm_rel["source"] = rel["source"]
            elif "subject" in rel:
                norm_rel["source"] = rel["subject"]
            else:
                norm_rel["source"] = ""

            # Map target field
            if "target" in rel:
                norm_rel["target"] = rel["target"]
            elif "object" in rel:
                norm_rel["target"] = rel["object"]
            else:
                norm_rel["target"] = ""

            # Map type field
            if "type" in rel:
                norm_rel["type"] = rel["type"]
            elif "predicate" in rel:
                norm_rel["type"] = rel["predicate"].upper().replace(" ", "_")
            else:
                norm_rel["type"] = "RELATES_TO"

            # Copy optional fields
            norm_rel["description"] = rel.get("description", "")
            norm_rel["strength"] = rel.get("strength", 5)

            normalized.append(norm_rel)

        return normalized


# ============================================================================
# Metrics Computation
# ============================================================================


def compute_f1(predicted: list[dict], gold: list[dict], key: str = "name") -> dict:
    """Compute precision, recall, F1 for extraction."""
    pred_set = {item.get(key, "").lower() for item in predicted if item.get(key)}
    gold_set = {item.get(key, "").lower() for item in gold if item.get(key)}

    if not pred_set and not gold_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    if not pred_set:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    if not gold_set:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    tp = len(pred_set & gold_set)
    precision = tp / len(pred_set) if pred_set else 0.0
    recall = tp / len(gold_set) if gold_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}


def compute_relation_f1(predicted: list[dict], gold: list[dict]) -> dict:
    """Compute F1 for relations (source-type-target tuples)."""
    def relation_key(r):
        return (r.get("source", "").lower(), r.get("type", "").upper(), r.get("target", "").lower())

    pred_set = {relation_key(r) for r in predicted}
    gold_set = {relation_key(r) for r in gold}

    if not pred_set and not gold_set:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    if not pred_set or not gold_set:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    tp = len(pred_set & gold_set)
    precision = tp / len(pred_set) if pred_set else 0.0
    recall = tp / len(gold_set) if gold_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1}


# ============================================================================
# Test Data Loading
# ============================================================================


def load_test_data(path: str) -> list[dict]:
    """Load test data from JSONL file."""
    data = []
    with open(path) as f:
        for line in f:
            data.append(json.loads(line))
    return data


def create_sample_test_data() -> list[dict]:
    """Create sample test data for quick testing."""
    return [
        {
            "text": "TensorFlow is an open-source machine learning framework developed by Google Brain team. It was released in November 2015 and supports both Python and C++ programming languages.",
            "domain": "technical",
            "entities": [
                {"name": "TensorFlow", "type": "SOFTWARE", "description": "Open-source ML framework"},
                {"name": "Google Brain", "type": "ORGANIZATION", "description": "AI research team at Google"},
                {"name": "November 2015", "type": "DATE", "description": "TensorFlow release date"},
                {"name": "Python", "type": "LANGUAGE", "description": "Programming language"},
                {"name": "C++", "type": "LANGUAGE", "description": "Programming language"},
            ],
            "relations": [
                {"source": "Google Brain", "target": "TensorFlow", "type": "DEVELOPED", "strength": 10},
                {"source": "TensorFlow", "target": "November 2015", "type": "RELEASED_ON", "strength": 10},
                {"source": "TensorFlow", "target": "Python", "type": "SUPPORTS", "strength": 9},
                {"source": "TensorFlow", "target": "C++", "type": "SUPPORTS", "strength": 9},
            ],
        },
        {
            "text": "Microsoft was founded by Bill Gates and Paul Allen in 1975 in Albuquerque, New Mexico. The company later moved its headquarters to Redmond, Washington.",
            "domain": "organizational",
            "entities": [
                {"name": "Microsoft", "type": "ORGANIZATION", "description": "Technology company"},
                {"name": "Bill Gates", "type": "PERSON", "description": "Co-founder of Microsoft"},
                {"name": "Paul Allen", "type": "PERSON", "description": "Co-founder of Microsoft"},
                {"name": "1975", "type": "DATE", "description": "Year Microsoft was founded"},
                {"name": "Albuquerque", "type": "LOCATION", "description": "City in New Mexico"},
                {"name": "Redmond", "type": "LOCATION", "description": "Microsoft headquarters location"},
            ],
            "relations": [
                {"source": "Bill Gates", "target": "Microsoft", "type": "FOUNDED", "strength": 10},
                {"source": "Paul Allen", "target": "Microsoft", "type": "FOUNDED", "strength": 10},
                {"source": "Microsoft", "target": "1975", "type": "FOUNDED_IN", "strength": 10},
                {"source": "Microsoft", "target": "Albuquerque", "type": "FOUNDED_IN", "strength": 9},
                {"source": "Microsoft", "target": "Redmond", "type": "HEADQUARTERED_IN", "strength": 9},
            ],
        },
    ]


# ============================================================================
# Main A/B Test Runner
# ============================================================================


def run_ab_test(
    test_data: list[dict],
    model: str = "gpt-oss:20b",
    pipeline_path: str | None = None,
) -> dict:
    """Run A/B test comparing baseline vs optimized prompts."""

    print("\n" + "=" * 70)
    print("A/B TEST: Baseline vs DSPy-Optimized Prompts")
    print("=" * 70)
    print(f"Model: {model}")
    print(f"Test samples: {len(test_data)}")
    print("=" * 70)

    runner = ExtractionRunner(model=model)

    results = []
    baseline_metrics = {"entity_f1": [], "relation_f1": [], "pipeline_compatible": [], "latency_ms": []}
    optimized_metrics = {"entity_f1": [], "relation_f1": [], "pipeline_compatible": [], "latency_ms": []}

    for i, sample in enumerate(test_data):
        test_id = f"test_{i+1:03d}"
        text = sample["text"]
        domain = sample.get("domain", "technical")
        gold_entities = sample.get("entities", [])
        gold_relations = sample.get("relations", [])

        print(f"\n--- Test {i+1}/{len(test_data)}: {test_id} ---")
        print(f"Text: {text[:100]}...")
        print(f"Gold entities: {len(gold_entities)}, Gold relations: {len(gold_relations)}")

        # Run baseline
        print("\n[BASELINE] Running...")
        baseline_entities, baseline_relations, baseline_log = runner.run_baseline(text, domain, test_id)

        print(f"  Entities: {len(baseline_entities)}, Relations: {len(baseline_relations)}")
        print(f"  Pipeline compatible: {baseline_log.pipeline_compatible}")
        print(f"  Latency: {baseline_log.latency_ms:.0f}ms")
        if baseline_log.validation_errors:
            print(f"  Errors: {baseline_log.validation_errors[:3]}")

        # Compute baseline metrics
        b_entity_f1 = compute_f1(baseline_entities, gold_entities)
        b_relation_f1 = compute_relation_f1(baseline_relations, gold_relations)
        baseline_metrics["entity_f1"].append(b_entity_f1["f1"])
        baseline_metrics["relation_f1"].append(b_relation_f1["f1"])
        baseline_metrics["pipeline_compatible"].append(baseline_log.pipeline_compatible)
        baseline_metrics["latency_ms"].append(baseline_log.latency_ms)

        print(f"  Entity F1: {b_entity_f1['f1']:.2f}, Relation F1: {b_relation_f1['f1']:.2f}")

        # Run optimized
        print("\n[OPTIMIZED] Running...")
        opt_entities, opt_relations, opt_log = runner.run_optimized(
            text, domain, test_id,
            pipeline_path or "data/dspy_prompts/pipeline_gptoss/pipeline_extraction_20260113_060510.json"
        )

        print(f"  Entities: {len(opt_entities)}, Relations: {len(opt_relations)}")
        print(f"  Pipeline compatible: {opt_log.pipeline_compatible}")
        print(f"  Latency: {opt_log.latency_ms:.0f}ms")
        if opt_log.validation_errors:
            print(f"  Errors: {opt_log.validation_errors[:3]}")

        # Compute optimized metrics
        o_entity_f1 = compute_f1(opt_entities, gold_entities)
        o_relation_f1 = compute_relation_f1(opt_relations, gold_relations)
        optimized_metrics["entity_f1"].append(o_entity_f1["f1"])
        optimized_metrics["relation_f1"].append(o_relation_f1["f1"])
        optimized_metrics["pipeline_compatible"].append(opt_log.pipeline_compatible)
        optimized_metrics["latency_ms"].append(opt_log.latency_ms)

        print(f"  Entity F1: {o_entity_f1['f1']:.2f}, Relation F1: {o_relation_f1['f1']:.2f}")

        # Store result
        results.append(TestResult(
            test_id=test_id,
            text=text,
            domain=domain,
            gold_entities=gold_entities,
            gold_relations=gold_relations,
            baseline_result={"entities": baseline_entities, "relations": baseline_relations},
            optimized_result={"entities": opt_entities, "relations": opt_relations},
            baseline_log=baseline_log,
            optimized_log=opt_log,
        ))

    # Compute aggregate metrics
    def avg(lst): return sum(lst) / len(lst) if lst else 0.0
    def pct(lst): return sum(lst) / len(lst) * 100 if lst else 0.0

    print("\n" + "=" * 70)
    print("AGGREGATE RESULTS")
    print("=" * 70)

    print("\n| Metric | Baseline | Optimized | Delta |")
    print("|--------|----------|-----------|-------|")

    b_ef1 = avg(baseline_metrics["entity_f1"])
    o_ef1 = avg(optimized_metrics["entity_f1"])
    print(f"| Entity F1 | {b_ef1:.2f} | {o_ef1:.2f} | {(o_ef1 - b_ef1):+.2f} |")

    b_rf1 = avg(baseline_metrics["relation_f1"])
    o_rf1 = avg(optimized_metrics["relation_f1"])
    print(f"| Relation F1 | {b_rf1:.2f} | {o_rf1:.2f} | {(o_rf1 - b_rf1):+.2f} |")

    b_pc = pct(baseline_metrics["pipeline_compatible"])
    o_pc = pct(optimized_metrics["pipeline_compatible"])
    print(f"| Pipeline Compat | {b_pc:.0f}% | {o_pc:.0f}% | {(o_pc - b_pc):+.0f}% |")

    b_lat = avg(baseline_metrics["latency_ms"])
    o_lat = avg(optimized_metrics["latency_ms"])
    print(f"| Latency (ms) | {b_lat:.0f} | {o_lat:.0f} | {(o_lat - b_lat):+.0f} |")

    print("\n" + "=" * 70)
    print(f"Log file: {runner.log_file}")
    print("=" * 70)

    return {
        "baseline": baseline_metrics,
        "optimized": optimized_metrics,
        "results": results,
        "log_file": str(runner.log_file),
    }


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="A/B Test: Generic Prompts vs DSPy-Optimized Prompts"
    )
    parser.add_argument(
        "--test-data",
        type=str,
        help="Path to test data JSONL file",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-oss:20b",
        help="Ollama model to use",
    )
    parser.add_argument(
        "--pipeline",
        type=str,
        default=None,
        help="Path to optimized pipeline JSON",
    )
    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Run quick test with sample data",
    )

    args = parser.parse_args()

    # Load test data
    if args.quick_test:
        print("Running quick test with sample data...")
        test_data = create_sample_test_data()
    elif args.test_data:
        print(f"Loading test data from: {args.test_data}")
        test_data = load_test_data(args.test_data)
    else:
        # Try to load from default locations
        for path in ["data/dspy_training/test.jsonl", "data/dspy_training/all.jsonl"]:
            if Path(path).exists():
                print(f"Loading test data from: {path}")
                test_data = load_test_data(path)
                break
        else:
            print("No test data found. Using sample data.")
            test_data = create_sample_test_data()

    # Run A/B test
    results = run_ab_test(test_data, model=args.model, pipeline_path=args.pipeline)

    print("\n\nTest complete!")


if __name__ == "__main__":
    main()
