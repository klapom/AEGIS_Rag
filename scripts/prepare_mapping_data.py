#!/usr/bin/env python3
"""Prepare relation type mapping data from benchmark logs.

Extracts all relation types (known + unknown) from benchmark v1 and v2 logs,
saves as JSON for the BGE-M3 mapper.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

# Combined unknown types from both benchmarks (extracted from logs)
# v1 (complete, 8 configs) + v2 (partial, 3 configs)
UNKNOWN_TYPES_FROM_LOGS = {
    # High frequency (>10 occurrences in v1)
    "HAS": 550,
    "FUNCTIONS_IN": 97,
    "INVOLVED_IN": 50,
    "EXPLAINS": 52,
    "OCCURS_IN": 27,
    "ENCODED_BY": 25,
    "INVOLVES": 23,
    "INHERITED_FROM": 23,
    "PRODUCES": 19,
    "EVOLVED_FROM": 15,
    "REPLICATES": 16,
    "INHERITS": 10,
    "ENCODING": 10,
    # Medium frequency (3-9)
    "TRANSMITTED_BY": 9,
    "ENCLOSED_BY": 7,
    "HAS_OWN_DNA": 6,
    "ESSENTIAL_FOR": 6,
    "SUGGESTED": 6,
    "PROPOSED": 3,
    "SEQUENCED": 5,
    "INHERITED_BY": 4,
    "FUNCTIONS_AS": 4,
    "SURROUNDED_BY": 3,
    "RESULTS_IN": 3,
    "REGULATED_BY": 3,
    "MAINTAINS": 3,
    "FOUND_IN": 3,
    "DYNAMIC": 3,
    "DIVIDES": 4,
    "CONVERTS": 3,
    "COMPOSED_OF": 3,
    "DESCRIBES": 1,
    "SHOWS": 2,
    "SPANS": 2,
    # Low frequency (1-2) but semantically interesting
    "STRUCTURED_BY": 2,
    "PRODUCED_BY": 2,
    "LOCALIZED_IN": 2,
    "IS_REGULATED_BY": 2,
    "INTERACTS_WITH": 2,
    "DRIVEN_BY": 2,
    "COORDINATED_WITH": 2,
    "COEXISTS_WITH": 2,
    "IS_A": 2,
    "USED_TO": 1,
    "USED_IN": 1,
    "REPLICATES_BY": 1,
    "ENGULFED": 1,
    "UNDERGOES": 1,
    "TRANSMITS": 1,
    "ORIGINATED_FROM": 1,
    "REQUIRED_FOR": 1,
    "PERFORMS": 1,
    "MODULATES": 1,
    "GENERATES": 1,
    "EXPRESSED_FROM": 1,
    "CONSISTS_OF": 1,
    "CATALYZE": 1,
    "ACTS_AS": 1,
    "ADAPTS_TO": 1,
    "INCLUDES": 1,
    "IMPORTED_FROM": 1,
    "INFLUENCED_BY": 1,
    "INDEPENDENT_OF": 1,
    "IS_COMPOSED_OF": 1,
    "IS_CLASSIFIED_AS": 1,
    "IS_CRITICAL_FOR": 1,
    "IS_ENABLED_BY": 1,
    "IS_FOUND_IN": 1,
    "IS_INVOLVED_IN": 1,
    "IS_ORIGIN_OF": 1,
    "POWER_SOURCE": 1,
    "SHARE_ORIGIN_WITH": 1,
}

# Known types that already map correctly (from extraction_service.py)
KNOWN_UNIVERSAL = {
    "RELATED_TO",
    "PART_OF",
    "CONTAINS",
    "INSTANCE_OF",
    "TYPE_OF",
    "EMPLOYS",
    "MANAGES",
    "FOUNDED_BY",
    "OWNS",
    "LOCATED_IN",
    "CAUSES",
    "ENABLES",
    "REQUIRES",
    "LEADS_TO",
    "PRECEDES",
    "FOLLOWS",
    "USES",
    "CREATES",
    "IMPLEMENTS",
    "DEPENDS_ON",
    "SIMILAR_TO",
    "ASSOCIATED_WITH",
}

KNOWN_ALIASES = {
    "RELATES_TO",
    "ASSOCIATED",
    "WORKS_AT",
    "FOUNDED",
    "BASED_IN",
    "HEADQUARTERED_IN",
    "OPERATES_IN",
    "DEVELOPED",
    "BUILT",
    "PRODUCED",
    "INVENTED",
    "BASED_ON",
    "EXTENDS",
    "DERIVED_FROM",
    "MODIFIES",
    "READS",
    "WRITES",
    "DELETES",
    "TREATS",
    "DIAGNOSED_BY",
    "CONTRAINDICATED_WITH",
    "INDICATES",
    "ADMINISTERED_VIA",
    "SIDE_EFFECT_OF",
    "ENCODES",
    "REGULATES",
    "INHABITS",
    "EVOLVES_FROM",
    "PARTICIPATES_IN",
    "PREYS_ON",
    "CONTROLS",
    "POWERED_BY",
    "MEETS_STANDARD",
    "TESTED_BY",
    "FAILS_DUE_TO",
    "TOLERATES",
    "RUNS_ON",
    "TRAINS_ON",
    "COMPILES_TO",
    "QUERIES",
    "AUTHENTICATES",
    "DEPLOYS_TO",
    "EXPLOITS",
}

# Build the data file for BGE-M3 mapper
output = {
    "source": "benchmark_v1_v2_combined_logs",
    "total_unknown_types": len(UNKNOWN_TYPES_FROM_LOGS),
    "total_unknown_occurrences": sum(UNKNOWN_TYPES_FROM_LOGS.values()),
    "unknown_types": UNKNOWN_TYPES_FROM_LOGS,
}

output_path = (
    Path("/app/data/evaluation/results/cross_sentence_raw_relations_v2.json")
    if "--container" in sys.argv
    else Path("data/evaluation/results/cross_sentence_raw_relations_v2.json")
)

# Create a format the mapper expects: config_key -> list of relation dicts
fake_raw = {}
all_rels = []
for rtype, count in UNKNOWN_TYPES_FROM_LOGS.items():
    for _ in range(count):
        all_rels.append(
            {
                "source": "entity_a",
                "target": "entity_b",
                "type": rtype,
                "description": "",
                "strength": 5,
            }
        )

# Also add the known types from v1 benchmark
v1_known_counts = {
    "RELATED_TO": 543,  # From v1 benchmark totals
    "PART_OF": 290,
    "CONTAINS": 99,
    "REQUIRES": 91,
    "CREATES": 54,
    "ASSOCIATED_WITH": 9,
    "CAUSES": 8,
    "SIMILAR_TO": 13,
    "DEPENDS_ON": 17,
    "LOCATED_IN": 16,
    "MANAGES": 3,
    "TYPE_OF": 1,
    "INSTANCE_OF": 1,
}
for rtype, count in v1_known_counts.items():
    for _ in range(count):
        all_rels.append(
            {
                "source": "entity_a",
                "target": "entity_b",
                "type": rtype,
                "description": "",
                "strength": 5,
            }
        )

fake_raw["combined_v1_v2"] = all_rels

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(fake_raw, indent=2))
print(
    f"Saved {len(all_rels)} relations ({len(UNKNOWN_TYPES_FROM_LOGS)} unknown types) to {output_path}"
)
