#!/usr/bin/env python3
"""BGE-M3 Semantic Relation Type Mapper.

Sprint 128: Maps LLM-generated relation types to ADR-060 Universal Taxonomy
using BGE-M3 dense embeddings (1024-dim) and cosine similarity.

Reads raw relations from cross_sentence_raw_relations_v2.json and:
1. Collects all unique LLM-generated relation types
2. Embeds both LLM types and ADR-060 types with BGE-M3
3. Computes cosine similarity matrix
4. Suggests best mapping for each unknown type
5. Evaluates impact: how many RELATED_TO can be recovered?

Usage (run inside API container):
    docker exec aegis-api python /app/scripts/bge_m3_relation_mapper.py
"""

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, "/app")


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def cosine_similarity_matrix(matrix_a: np.ndarray, matrix_b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity matrix between two sets of vectors.

    Args:
        matrix_a: (N, D) — query vectors
        matrix_b: (M, D) — reference vectors

    Returns:
        (N, M) similarity matrix
    """
    # Normalize
    norms_a = np.linalg.norm(matrix_a, axis=1, keepdims=True)
    norms_b = np.linalg.norm(matrix_b, axis=1, keepdims=True)
    norms_a[norms_a == 0] = 1.0
    norms_b[norms_b == 0] = 1.0
    normed_a = matrix_a / norms_a
    normed_b = matrix_b / norms_b
    return normed_a @ normed_b.T


async def main():
    """Run BGE-M3 semantic relation type mapping."""
    print("=" * 80)
    print("BGE-M3 Semantic Relation Type Mapper")
    print("=" * 80)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Step 1: Load raw relations from benchmark v2
    raw_path = Path("/app/data/evaluation/results/cross_sentence_raw_relations_v2.json")
    if not raw_path.exists():
        # Fallback: try v1 benchmark
        raw_path_v1 = Path("/app/data/evaluation/results/cross_sentence_benchmark.json")
        if raw_path_v1.exists():
            print("WARNING: v2 raw relations not found, using v1 benchmark data")
            print("Run benchmark_cross_sentence_v2.py first for full raw relations")
            # Extract relation types from v1 data
            v1_data = json.loads(raw_path_v1.read_text())
            all_types = Counter()
            for bench in v1_data.get("window_benchmarks", []):
                for rtype, count in bench.get("top_relation_types", {}).items():
                    all_types[rtype] += count
            raw_relations = None
        else:
            print("ERROR: No benchmark data found. Run benchmark_cross_sentence_v2.py first.")
            return
    else:
        raw_data = json.loads(raw_path.read_text())
        raw_relations = raw_data

    # Step 2: Collect unique LLM-generated relation types
    print("--- Step 1: Collecting LLM-generated relation types ---")

    # ADR-060 Universal Relation Types (21 types)
    UNIVERSAL_TYPES = [
        # Structural (4)
        "PART_OF",
        "CONTAINS",
        "INSTANCE_OF",
        "TYPE_OF",
        # Organizational (5)
        "EMPLOYS",
        "MANAGES",
        "FOUNDED_BY",
        "OWNS",
        "LOCATED_IN",
        # Causal (4)
        "CAUSES",
        "ENABLES",
        "REQUIRES",
        "LEADS_TO",
        # Temporal (2)
        "PRECEDES",
        "FOLLOWS",
        # Functional (4)
        "USES",
        "CREATES",
        "IMPLEMENTS",
        "DEPENDS_ON",
        # Semantic (2)
        "SIMILAR_TO",
        "ASSOCIATED_WITH",
        # Fallback (1)
        "RELATED_TO",
    ]

    # Existing hardcoded aliases (from extraction_service.py)
    EXISTING_ALIASES = {
        "RELATES_TO": "RELATED_TO",
        "ASSOCIATED": "ASSOCIATED_WITH",
        "WORKS_AT": "EMPLOYS",
        "FOUNDED": "FOUNDED_BY",
        "BASED_IN": "LOCATED_IN",
        "HEADQUARTERED_IN": "LOCATED_IN",
        "OPERATES_IN": "LOCATED_IN",
        "DEVELOPED": "CREATES",
        "BUILT": "CREATES",
        "PRODUCED": "CREATES",
        "INVENTED": "CREATES",
        "BASED_ON": "DEPENDS_ON",
        "EXTENDS": "TYPE_OF",
        "DERIVED_FROM": "TYPE_OF",
        "MODIFIES": "USES",
        "READS": "USES",
        "WRITES": "CREATES",
        "DELETES": "USES",
        # Domain aliases (Sprint 126)
        "TREATS": "USES",
        "DIAGNOSED_BY": "USES",
        "CONTRAINDICATED_WITH": "ASSOCIATED_WITH",
        "INDICATES": "ASSOCIATED_WITH",
        "ADMINISTERED_VIA": "USES",
        "SIDE_EFFECT_OF": "CAUSES",
        "ENCODES": "CREATES",
        "REGULATES": "MANAGES",
        "INHABITS": "LOCATED_IN",
        "EVOLVES_FROM": "TYPE_OF",
        "PARTICIPATES_IN": "PART_OF",
        "PREYS_ON": "USES",
        "CONTROLS": "MANAGES",
        "POWERED_BY": "DEPENDS_ON",
        "MEETS_STANDARD": "IMPLEMENTS",
        "TESTED_BY": "USES",
        "FAILS_DUE_TO": "CAUSES",
        "TOLERATES": "ASSOCIATED_WITH",
        "RUNS_ON": "DEPENDS_ON",
        "TRAINS_ON": "USES",
        "COMPILES_TO": "CREATES",
        "QUERIES": "USES",
        "AUTHENTICATES": "USES",
        "DEPLOYS_TO": "USES",
        "EXPLOITS": "USES",
    }

    # Collect all unique LLM types from raw relations
    llm_type_counts = Counter()
    if raw_relations:
        for config_key, rels in raw_relations.items():
            for rel in rels:
                rtype = rel.get("type", "RELATED_TO").upper().strip()
                llm_type_counts[rtype] += 1
    elif all_types:
        llm_type_counts = all_types

    total_relations = sum(llm_type_counts.values())
    print(f"Total relations across all configs: {total_relations}")
    print(f"Unique relation types: {len(llm_type_counts)}")
    print()

    # Categorize types
    known_universal = {}
    known_alias = {}
    unknown_types = {}

    for rtype, count in llm_type_counts.most_common():
        if rtype in set(UNIVERSAL_TYPES):
            known_universal[rtype] = count
        elif rtype in EXISTING_ALIASES:
            known_alias[rtype] = count
        else:
            unknown_types[rtype] = count

    print(f"  Known universal types: {len(known_universal)} ({sum(known_universal.values())} rels)")
    for t, c in sorted(known_universal.items(), key=lambda x: -x[1]):
        print(f"    {t}: {c}")

    print(
        f"\n  Known aliases (already mapped): {len(known_alias)} ({sum(known_alias.values())} rels)"
    )
    for t, c in sorted(known_alias.items(), key=lambda x: -x[1]):
        print(f"    {t} → {EXISTING_ALIASES[t]}: {c}")

    print(
        f"\n  UNKNOWN types (need BGE-M3 mapping): {len(unknown_types)} ({sum(unknown_types.values())} rels)"
    )
    for t, c in sorted(unknown_types.items(), key=lambda x: -x[1]):
        print(f"    {t}: {c}")

    if not unknown_types:
        print("\nNo unknown types to map! All relation types are already covered.")
        return

    # Step 3: BGE-M3 Embeddings
    print("\n--- Step 2: Computing BGE-M3 embeddings ---")
    print("Loading FlagEmbeddingService...")

    from src.components.shared.flag_embedding_service import FlagEmbeddingService

    embedding_service = FlagEmbeddingService()

    # Prepare text representations for embedding
    # For relation types, we expand the underscore-separated name into natural language
    def relation_type_to_text(rtype: str) -> str:
        """Convert relation type to natural language for embedding.

        Examples:
            PART_OF → "part of (structural relationship: X is part of Y)"
            CAUSES → "causes (causal relationship: X causes Y)"
            OCCURS_IN → "occurs in (X occurs in Y)"
        """
        words = rtype.lower().replace("_", " ")
        return f"{words} (relationship type: X {words} Y)"

    def embed_batch_sync(texts: list[str]) -> list[list[float]]:
        """Embed batch using sync _embed_single_sync to avoid async issues."""
        results = []
        for text in texts:
            result = embedding_service._embed_single_sync(text)
            results.append(result["dense"])
        return results

    # Embed universal types
    universal_texts = [relation_type_to_text(t) for t in UNIVERSAL_TYPES]
    print(f"  Embedding {len(universal_texts)} universal types...")
    t0 = time.time()
    universal_embeddings = embed_batch_sync(universal_texts)
    universal_matrix = np.array(universal_embeddings)
    print(f"  Done in {time.time() - t0:.2f}s (shape: {universal_matrix.shape})")

    # Embed unknown types
    unknown_list = list(unknown_types.keys())
    unknown_texts = [relation_type_to_text(t) for t in unknown_list]
    print(f"  Embedding {len(unknown_texts)} unknown types...")
    t0 = time.time()
    unknown_embeddings = embed_batch_sync(unknown_texts)
    unknown_matrix = np.array(unknown_embeddings)
    print(f"  Done in {time.time() - t0:.2f}s (shape: {unknown_matrix.shape})")

    # Step 4: Compute similarity matrix
    print("\n--- Step 3: Computing cosine similarity ---")
    sim_matrix = cosine_similarity_matrix(unknown_matrix, universal_matrix)
    print(f"  Similarity matrix shape: {sim_matrix.shape}")

    # Step 5: Find best mapping for each unknown type
    print("\n--- Step 4: BGE-M3 Suggested Mappings ---")
    print(
        f"{'Unknown Type':<30} {'Best Match':<20} {'Sim':>6} {'2nd Best':<20} {'Sim':>6} {'Count':>6}"
    )
    print("-" * 110)

    suggested_mappings = {}
    recoverable_relations = 0

    for i, unknown_type in enumerate(unknown_list):
        # Get top-2 matches (excluding RELATED_TO as a match target)
        sims = sim_matrix[i]
        # Sort indices by similarity (descending)
        sorted_indices = np.argsort(sims)[::-1]

        # Best match
        best_idx = sorted_indices[0]
        best_type = UNIVERSAL_TYPES[best_idx]
        best_sim = sims[best_idx]

        # Second best
        second_idx = sorted_indices[1]
        second_type = UNIVERSAL_TYPES[second_idx]
        second_sim = sims[second_idx]

        # Skip if best match is RELATED_TO (no improvement)
        if best_type == "RELATED_TO":
            best_idx = sorted_indices[1]
            best_type = UNIVERSAL_TYPES[best_idx]
            best_sim = sims[best_idx]
            second_idx = sorted_indices[2]
            second_type = UNIVERSAL_TYPES[second_idx]
            second_sim = sims[second_idx]

        count = unknown_types[unknown_type]
        marker = (
            "***"
            if best_sim >= 0.7
            else "**"
            if best_sim >= 0.5
            else "*"
            if best_sim >= 0.3
            else ""
        )

        print(
            f"{unknown_type:<30} {best_type:<20} {best_sim:>5.3f} "
            f"{second_type:<20} {second_sim:>5.3f} {count:>6} {marker}"
        )

        suggested_mappings[unknown_type] = {
            "suggested_universal_type": best_type,
            "similarity": round(float(best_sim), 4),
            "second_best": second_type,
            "second_similarity": round(float(second_sim), 4),
            "count_in_benchmark": count,
            "confidence": "high" if best_sim >= 0.7 else "medium" if best_sim >= 0.5 else "low",
        }

        if best_sim >= 0.5:  # Medium or high confidence
            recoverable_relations += count

    print("-" * 110)
    print(f"\n*** = high confidence (>=0.7), ** = medium (>=0.5), * = low (>=0.3)")

    # Step 6: Impact analysis
    print("\n--- Step 5: Impact Analysis ---")
    total_generic = sum(
        c for t, c in llm_type_counts.items() if t in ("RELATED_TO", "RELATES_TO", "UNKNOWN")
    )
    total_specific = total_relations - total_generic
    total_unknown = sum(unknown_types.values())

    print(f"  Total relations: {total_relations}")
    print(
        f"  Currently specific: {total_specific} ({total_specific / max(total_relations, 1) * 100:.1f}%)"
    )
    print(
        f"  Currently generic (RELATED_TO): {total_generic} ({total_generic / max(total_relations, 1) * 100:.1f}%)"
    )
    print(f"  Unknown types (unmapped): {total_unknown}")
    print(f"  Recoverable with BGE-M3 mapping (sim>=0.5): {recoverable_relations}")
    print(
        f"  New specificity if mapped: {(total_specific + recoverable_relations) / max(total_relations, 1) * 100:.1f}%"
    )

    # Step 7: Generate proposed alias additions
    print("\n--- Step 6: Proposed RELATION_TYPE_ALIASES additions ---")
    print(
        "# Copy these to extraction_service.py RELATION_TYPE_ALIASES or DOMAIN_RELATION_TYPE_ALIASES:"
    )
    print()

    high_conf = {}
    medium_conf = {}
    low_conf = {}

    for unknown_type, mapping in sorted(suggested_mappings.items()):
        line = f'    "{unknown_type}": "{mapping["suggested_universal_type"]}",  # BGE-M3 sim={mapping["similarity"]:.3f}, count={mapping["count_in_benchmark"]}'
        if mapping["confidence"] == "high":
            high_conf[unknown_type] = line
        elif mapping["confidence"] == "medium":
            medium_conf[unknown_type] = line
        else:
            low_conf[unknown_type] = line

    if high_conf:
        print("# HIGH confidence (sim >= 0.7) — safe to add automatically:")
        for line in high_conf.values():
            print(line)
        print()

    if medium_conf:
        print("# MEDIUM confidence (sim 0.5-0.7) — review recommended:")
        for line in medium_conf.values():
            print(line)
        print()

    if low_conf:
        print("# LOW confidence (sim < 0.5) — manual review required:")
        for line in low_conf.values():
            print(line)
        print()

    # Save results
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_relations": total_relations,
        "unique_types": len(llm_type_counts),
        "known_universal": {k: v for k, v in known_universal.items()},
        "known_aliases": {
            k: {"mapped_to": EXISTING_ALIASES[k], "count": v} for k, v in known_alias.items()
        },
        "unknown_types": dict(unknown_types),
        "suggested_mappings": suggested_mappings,
        "impact": {
            "current_specific_count": total_specific,
            "current_generic_count": total_generic,
            "current_specificity_pct": round(total_specific / max(total_relations, 1) * 100, 1),
            "recoverable_with_bge_m3": recoverable_relations,
            "projected_specificity_pct": round(
                (total_specific + recoverable_relations) / max(total_relations, 1) * 100, 1
            ),
        },
    }

    output_path = Path("/app/data/evaluation/results/bge_m3_relation_mapping.json")
    output_path.write_text(json.dumps(output, indent=2))
    print(f"\nResults saved to: {output_path}")

    # Also save the full similarity matrix for analysis
    sim_output = {
        "unknown_types": unknown_list,
        "universal_types": UNIVERSAL_TYPES,
        "similarity_matrix": sim_matrix.tolist(),
    }
    sim_path = Path("/app/data/evaluation/results/bge_m3_similarity_matrix.json")
    sim_path.write_text(json.dumps(sim_output, indent=2))
    print(f"Similarity matrix saved to: {sim_path}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
