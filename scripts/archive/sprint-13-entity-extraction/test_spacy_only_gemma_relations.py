#!/usr/bin/env python3
"""Test pure spaCy NER + Semantic Deduplication + Gemma 3 4B for relation extraction.

Sprint 13 TD-31: Advanced 3-phase strategy:
  Phase 1: Entity extraction with spaCy Transformer NER ONLY (no LLM)
  Phase 2: Semantic entity deduplication with sentence-transformers
  Phase 3: Relation extraction with Gemma 3 4B Q4_K_M (with deduplicated entities)
  Phase 4: Post-process to LightRAG format
"""

import json
import time
from pathlib import Path
from datetime import datetime
from ollama import Client
from typing import List, Dict, Any, Tuple
import numpy as np

# Try to import spaCy
try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    print("ERROR: spaCy not available. Install with: pip install spacy")
    print("ERROR: Download model with: python -m spacy download en_core_web_trf")
    exit(1)

# Try to import sentence-transformers for semantic deduplication
try:
    from sentence_transformers import SentenceTransformer
    import torch

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("WARNING: sentence-transformers not available.")
    print("WARNING: Install with: pip install sentence-transformers")
    print("WARNING: Continuing without semantic deduplication.")

# ============================================================================
# LIGHTRAG DELIMITERS (for conversion)
# ============================================================================
TUPLE_DELIMITER = "<|#|>"
COMPLETION_DELIMITER = "<|COMPLETE|>"

# ============================================================================
# PHASE 2 - RELATION EXTRACTION PROMPT (with entity context)
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


# ============================================================================
# SEMANTIC DEDUPLICATION
# ============================================================================
class SemanticDeduplicator:
    """Deduplicate entities using semantic similarity (sentence-transformers)."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        threshold: float = 0.93,
        device: str = None,
    ):
        """Initialize semantic deduplicator.

        Args:
            model_name: Sentence transformer model name
            threshold: Cosine similarity threshold (0.90-0.95 recommended)
            device: 'cuda' or 'cpu' (auto-detect if None)
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers required for semantic deduplication")

        # Auto-detect device
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = SentenceTransformer(model_name, device=device)
        self.threshold = threshold
        self.device = device

        print(f"[INFO] Semantic deduplicator initialized on {device}")
        if device == "cuda":
            print(f"[INFO] GPU: {torch.cuda.get_device_name(0)}")
            print(f"[INFO] VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    def deduplicate(self, entities: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Deduplicate entities using semantic similarity.

        Strategy:
        1. Group entities by type (only compare same types)
        2. Compute embeddings for all entity names
        3. Find clusters with similarity > threshold
        4. Keep first entity from each cluster

        Args:
            entities: List of entity dicts with 'name', 'type', 'description'

        Returns:
            Deduplicated entity list
        """
        if not entities:
            return []

        # Group by type
        type_groups = {}
        for entity in entities:
            etype = entity.get("type", "OTHER")
            if etype not in type_groups:
                type_groups[etype] = []
            type_groups[etype].append(entity)

        deduplicated = []
        stats = {"total": len(entities), "removed": 0, "kept": 0}

        # Deduplicate within each type
        for etype, group in type_groups.items():
            if len(group) == 1:
                deduplicated.extend(group)
                stats["kept"] += 1
                continue

            # Extract names
            names = [e["name"] for e in group]

            # Compute embeddings (batched)
            embeddings = self.model.encode(names, batch_size=64, convert_to_tensor=True)

            # Compute pairwise cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity

            embeddings_np = embeddings.cpu().numpy()
            similarity_matrix = cosine_similarity(embeddings_np)

            # Find clusters (greedy clustering)
            used = set()
            for i in range(len(group)):
                if i in used:
                    continue

                # Find all similar entities
                similar = [i]
                for j in range(i + 1, len(group)):
                    if j not in used and similarity_matrix[i, j] >= self.threshold:
                        similar.append(j)
                        used.add(j)

                # Keep first entity, merge descriptions
                representative = group[i].copy()
                if len(similar) > 1:
                    # Merge descriptions from duplicates
                    descriptions = [group[idx]["description"] for idx in similar]
                    representative["description"] = (
                        f"{group[i]['description']} [Deduplicated from {len(similar)} mentions]"
                    )
                    stats["removed"] += len(similar) - 1

                deduplicated.append(representative)
                stats["kept"] += 1

        print(
            f"[DEDUP] Total: {stats['total']}, Kept: {stats['kept']}, Removed: {stats['removed']}"
        )
        return deduplicated


def extract_entities_spacy(text: str, nlp) -> List[Dict[str, str]]:
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
                "description": f"{ent.text} is a {ent.label_} entity.",
                "source": "spacy",
            }
        )

    return entities


def convert_json_to_lightrag(
    entities: List[Dict[str, str]], relations: List[Dict[str, str]]
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


def test_spacy_gemma(
    model: str, test_case: dict, client: Client, nlp, deduplicator, log_path: Path
) -> dict:
    """Test spaCy entity extraction + semantic deduplication + Gemma relation extraction."""

    results = {
        "model": model,
        "test_id": test_case["id"],
        "test_name": test_case["name"],
        "phase1_time": 0,
        "phase2_time": 0,
        "phase3_time": 0,
        "total_time": 0,
        "spacy_entities": 0,
        "deduplicated_entities": 0,
        "relations_found": 0,
        "entities_expected": test_case["expected_entities"],
        "relations_expected": test_case["expected_relations"],
        "entity_accuracy": 0,
        "relation_accuracy": 0,
        "dedup_reduction": 0,
        "status": "FAIL",
        "errors": [],
    }

    total_start = time.perf_counter()

    try:
        # ====================================================================
        # PHASE 1: spaCy NER Entity Extraction (NO LLM)
        # ====================================================================
        start = time.perf_counter()
        spacy_entities = extract_entities_spacy(test_case["text"], nlp)
        results["phase1_time"] = time.perf_counter() - start
        results["spacy_entities"] = len(spacy_entities)

        # ====================================================================
        # PHASE 2: Semantic Deduplication (sentence-transformers on GPU)
        # ====================================================================
        start = time.perf_counter()
        if deduplicator:
            deduplicated_entities = deduplicator.deduplicate(spacy_entities)
            results["deduplicated_entities"] = len(deduplicated_entities)
            results["dedup_reduction"] = (
                100 * (1 - len(deduplicated_entities) / len(spacy_entities))
                if len(spacy_entities) > 0
                else 0
            )
        else:
            deduplicated_entities = spacy_entities
            results["deduplicated_entities"] = len(spacy_entities)
            results["dedup_reduction"] = 0
        results["phase2_time"] = time.perf_counter() - start

        # ====================================================================
        # PHASE 3: Gemma 3 4B Relation Extraction (with Deduplicated Entities)
        # ====================================================================
        start = time.perf_counter()

        # Format entity list for prompt
        entity_names = [e["name"] for e in deduplicated_entities]
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

        results["phase3_time"] = time.perf_counter() - start

        relation_data = parse_json_response(response["message"]["content"])
        relations = relation_data.get("relations", [])
        results["relations_found"] = len(relations)

        # ====================================================================
        # PHASE 4: Post-process to LightRAG format
        # ====================================================================
        lightrag_format = convert_json_to_lightrag(deduplicated_entities, relations)

        results["total_time"] = time.perf_counter() - total_start
        results["entity_accuracy"] = (
            100 * results["deduplicated_entities"] / test_case["expected_entities"]
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
            if results["deduplicated_entities"] > 0 and results["relations_found"] > 0
            else "PARTIAL"
        )

        # ====================================================================
        # Log Results
        # ====================================================================
        log_content = f"""
{'='*80}
TEST CASE {test_case['id']}: {test_case['name']} [spaCy + Semantic Dedup + Gemma]
{'='*80}

Expected: {test_case['expected_entities']} entities, {test_case['expected_relations']} relations
Found: {results['deduplicated_entities']} entities (after dedup), {results['relations_found']} relations

Phase 1 (spaCy NER):          {results['phase1_time']:.2f}s → {results['spacy_entities']} entities (raw)
Phase 2 (Semantic Dedup):     {results['phase2_time']:.2f}s → {results['deduplicated_entities']} entities ({results['dedup_reduction']:.1f}% reduction)
Phase 3 (Gemma Relations):    {results['phase3_time']:.2f}s → {results['relations_found']} relations
Total Time:                   {results['total_time']:.2f}s

Accuracy: {results['entity_accuracy']:.1f}% entities, {results['relation_accuracy']:.1f}% relations

{'='*80}
PHASE 1 - spaCy RAW ENTITIES:
{'='*80}
{json.dumps(spacy_entities, indent=2)}

{'='*80}
PHASE 2 - DEDUPLICATED ENTITIES:
{'='*80}
{json.dumps(deduplicated_entities, indent=2)}

{'='*80}
PHASE 3 - GEMMA RELATIONS:
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
     spaCy NER + Semantic Dedup + Gemma 3 4B Relation Extraction
{'='*80}

Architecture:
  Phase 1: Entity Extraction -> spaCy Transformer NER ONLY (no LLM)
  Phase 2: Semantic Deduplication -> sentence-transformers (GPU-accelerated)
  Phase 3: Relation Extraction -> Gemma 3 4B Q4_K_M + Entity Context
  Phase 4: Post-Process -> LightRAG delimiter-separated format

Expected:
  - Very fast entity extraction (spaCy NER ~0.5s)
  - Fast deduplication (sentence-transformers ~0.5-1s on GPU)
  - High-quality relation extraction (Gemma 3 4B ~13s)
  - Total Time: ~14-15s per test case
    """
    )

    # Load spaCy model
    if not SPACY_AVAILABLE:
        print("\n[ERROR] spaCy not available. Exiting.")
        return

    try:
        print("\n[INFO] Loading spaCy transformer model (en_core_web_trf)...", end=" ", flush=True)
        nlp = spacy.load("en_core_web_trf")
        print("OK")
    except OSError:
        print("\n[ERROR] spaCy model 'en_core_web_trf' not found.")
        print("[ERROR] Download with: python -m spacy download en_core_web_trf")
        return

    # Load semantic deduplicator
    deduplicator = None
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        try:
            print(
                "\n[INFO] Loading sentence-transformers model (all-MiniLM-L6-v2)...",
                end=" ",
                flush=True,
            )
            deduplicator = SemanticDeduplicator(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                threshold=0.93,
                device=None,  # Auto-detect GPU
            )
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            print("[WARNING] Continuing without semantic deduplication")
    else:
        print("\n[WARNING] sentence-transformers not available. Skipping deduplication.")

    client = Client()

    # Use Gemma 3 4B Q4_K_M for relation extraction
    model = "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M"
    model_short = model.split("/")[-1] if "/" in model else model

    print(f"\n{'='*80}")
    print(f"RELATION MODEL: {model_short}")
    print(f"{'='*80}")

    # Warmup
    print("\n[WARMUP] Loading Gemma model (not measured)...", end=" ", flush=True)
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
    log_dir = Path("logs/spacy_semantic_gemma")
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dedup_suffix = "_with_dedup" if deduplicator else "_no_dedup"
    log_filename = f"{timestamp}_spacy_semantic_gemma{dedup_suffix}.log"
    log_path = log_dir / log_filename

    # Write log header
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(
            f"""{'='*80}
spaCy NER + SEMANTIC DEDUP + Gemma 3 4B TEST LOG
{'='*80}

Phase 1: spaCy en_core_web_trf (Transformer NER)
Phase 2: sentence-transformers all-MiniLM-L6-v2 (Semantic Deduplication, threshold=0.93)
Phase 3: {model} (Relation Extraction)
Strategy: Multi-phase extraction with semantic deduplication
Test Suite: All 3 LightRAG Original Examples
Context Window: 16384
GPU Enabled: {torch.cuda.is_available() if SENTENCE_TRANSFORMERS_AVAILABLE else 'N/A'}
Start Time: {datetime.now().isoformat()}

{'='*80}

"""
        )

    results = []

    for test_case in TEST_CASES:
        print(f"\n[{test_case['id']}/3] {test_case['name']}...", end=" ", flush=True)
        result = test_spacy_gemma(model, test_case, client, nlp, deduplicator, log_path)
        results.append(result)

        print(f"\n  Phase 1 (spaCy):  {result['spacy_entities']}E in {result['phase1_time']:.1f}s")
        print(
            f"  Phase 2 (Dedup):  {result['deduplicated_entities']}E in {result['phase2_time']:.1f}s ({result['dedup_reduction']:.1f}% removed)"
        )
        print(f"  Phase 3 (Gemma):  {result['relations_found']}R in {result['phase3_time']:.1f}s")
        print(
            f"  Total:            {result['total_time']:.1f}s | "
            f"{result['entity_accuracy']:.0f}% entities, {result['relation_accuracy']:.0f}% relations | "
            f"[{result['status']}]"
        )

    # ========================================================================
    # SUMMARY
    # ========================================================================
    print(f"\n{'='*80}")
    print("SUMMARY: spaCy + Semantic Dedup + Gemma Performance")
    print(f"{'='*80}\n")

    print(f"{'Test':<30} {'Raw->Dedup':<15} {'Relations':<12} {'Total Time':<12} {'Status':<8}")
    print(f"{'-'*30} {'-'*15} {'-'*12} {'-'*12} {'-'*8}")

    for r in results:
        entity_str = (
            f"{r['spacy_entities']}->{r['deduplicated_entities']} (-{r['dedup_reduction']:.0f}%)"
        )
        relation_str = f"{r['relations_found']}/{r['relations_expected']}"
        time_str = f"{r['total_time']:.1f}s"

        print(
            f"{r['test_name']:<30} {entity_str:<15} {relation_str:<12} {time_str:<12} {r['status']:<8}"
        )

    # Calculate averages
    print(f"\n{'='*80}")
    print("AVERAGE PERFORMANCE")
    print(f"{'='*80}\n")

    avg_time = sum(r["total_time"] for r in results) / len(results)
    avg_phase1 = sum(r["phase1_time"] for r in results) / len(results)
    avg_phase2 = sum(r["phase2_time"] for r in results) / len(results)
    avg_phase3 = sum(r["phase3_time"] for r in results) / len(results)
    avg_dedup_reduction = sum(r["dedup_reduction"] for r in results) / len(results)
    avg_entity_acc = sum(r["entity_accuracy"] for r in results) / len(results)
    avg_relation_acc = sum(r["relation_accuracy"] for r in results) / len(results)
    success_rate = (
        100 * sum(1 for r in results if r["status"] in ["PASS", "PARTIAL"]) / len(results)
    )

    print(f"spaCy + Semantic Dedup + Gemma:")
    print(f"  Average Phase 1 (spaCy NER):       {avg_phase1:.2f}s")
    print(f"  Average Phase 2 (Deduplication):   {avg_phase2:.2f}s")
    print(f"  Average Phase 3 (Gemma Relations): {avg_phase3:.2f}s")
    print(f"  Average Total Time:                {avg_time:.1f}s")
    print(f"  Average Dedup Reduction:           {avg_dedup_reduction:.1f}%")
    print(f"  Average Entity Accuracy:           {avg_entity_acc:.1f}%")
    print(f"  Average Relation Accuracy:         {avg_relation_acc:.1f}%")
    print(f"  Success Rate:                      {success_rate:.0f}%")
    print()

    # Save results
    output_file = Path("spacy_semantic_gemma_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"{'='*80}")
    print(f"[OK] Results saved to: {output_file}")
    print(f"[OK] Detailed logs: {log_dir}/")
    if deduplicator:
        print(f"[OK] Semantic deduplication: ENABLED (threshold={deduplicator.threshold})")
    else:
        print(f"[WARNING] Semantic deduplication: DISABLED")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
