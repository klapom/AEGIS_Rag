"""Test Script: LLM Entity Validation (Option 4 - Hybrid Pipeline)

Sprint 20 Enhancement: Hybrid SpaCy→LLM Validation
- Phase 1: SpaCy extracts entities (fast, ~15s/doc)
- Phase 2: LLM validates and filters entities (quality gate)
- Phase 3: Only high-quality entities proceed to graph

This script:
1. Reads entities from ENTITIES_AND_RELATIONS_FOR_ANNOTATION.txt
2. Uses LLM to validate each entity (keep/discard decision)
3. Outputs filtered entity list with quality scores

Author: Claude Code
Date: 2025-11-07
"""

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

import structlog
from ollama import AsyncClient

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings

logger = structlog.get_logger(__name__)

# ============================================================================
# LLM VALIDATION PROMPT
# ============================================================================

ENTITY_VALIDATION_PROMPT = """---Role---
You are a quality control expert for entity extraction in technical documentation.

---Goal---
Evaluate whether an extracted entity is meaningful and relevant for a knowledge graph about IT systems, software, and technical concepts.

---Task---
Given an entity extracted by an NER system, decide if it should be KEPT or DISCARDED.

---Criteria for DISCARDING---
1. **Generic numbers without context** (1, 2, 3, 100, etc.)
2. **Measurements without entity status** (40%, << 1ms, 600=240.0)
3. **Common words misclassified as entities** (Seite, Tipps, one, two, three)
4. **Page numbers or layout artifacts**
5. **Overly generic concepts** (Solution, Beispiel, etc.)
6. **Fragments or incomplete names**

---Criteria for KEEPING---
1. **Organizations** (OMNINET, Microsoft, SAP)
2. **Products/Technologies** (OMNITRACKER, MSA, Oracle)
3. **Technical concepts** (Multi Server Architektur, Performance Tuning)
4. **Specific features or components**
5. **Named locations, persons, or events** (when relevant to technical context)

---Input Format---
Entity Name: {entity_name}
Entity Type: {entity_type}
Mentions: {mention_count}
Sample Contexts: {contexts}

---Output Format---
Return ONLY valid JSON with this exact structure:
{{
  "decision": "KEEP" or "DISCARD",
  "confidence": 0.0-1.0,
  "reason": "Brief explanation (1 sentence)",
  "suggested_type": "ORGANIZATION|PRODUCT|CONCEPT|TECHNOLOGY|..." (optional, if entity type should be corrected)
}}

---Examples---

Example 1:
Entity Name: Seite
Entity Type: PERSON
Mentions: 16
Sample Contexts: ["auf dieser Seite", "Seite 3"]

Output:
{{"decision": "DISCARD", "confidence": 0.95, "reason": "German word for 'page', not a person entity"}}

Example 2:
Entity Name: OMNINET
Entity Type: ORGANIZATION
Mentions: 46
Sample Contexts: ["OMNINET Multi Server Architektur", "OMNINET configuration"]

Output:
{{"decision": "KEEP", "confidence": 0.98, "reason": "Core product/organization name with high relevance", "suggested_type": "PRODUCT"}}

Example 3:
Entity Name: 100
Entity Type: CONCEPT
Mentions: 3
Sample Contexts: ["100 users", "performance at 100%"]

Output:
{{"decision": "DISCARD", "confidence": 0.92, "reason": "Generic number without entity status"}}

Example 4:
Entity Name: Multi Server Architektur
Entity Type: CONCEPT
Mentions: 13
Sample Contexts: ["OMNINET Multi Server Architektur", "MSA deployment"]

Output:
{{"decision": "KEEP", "confidence": 0.90, "reason": "Core technical concept with specific meaning in system architecture"}}

---Critical Instructions---
- Output ONLY valid JSON (no markdown, no code fences, no extra text)
- Be strict: when in doubt, DISCARD
- Focus on technical relevance for knowledge graph
- Consider mention count (high mentions = likely important)

Now evaluate this entity:

Entity Name: {entity_name}
Entity Type: {entity_type}
Mentions: {mention_count}

Decision (JSON only):
"""


class LLMEntityValidator:
    """Validates SpaCy-extracted entities using LLM quality gate."""

    def __init__(
        self,
        llm_model: str = "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M",
        ollama_base_url: str = "http://localhost:11434",
        temperature: float = 0.1,
    ):
        """Initialize LLM validator.

        Args:
            llm_model: Ollama model for validation
            ollama_base_url: Ollama server URL
            temperature: Low temp for consistent decisions
        """
        self.llm_model = llm_model
        self.client = AsyncClient(host=ollama_base_url)
        self.temperature = temperature

        logger.info(
            "llm_entity_validator_initialized",
            model=llm_model,
            temperature=temperature,
        )

    async def validate_entity(
        self,
        entity_name: str,
        entity_type: str,
        mention_count: int,
        contexts: list[str] = None,
    ) -> dict[str, Any]:
        """Validate a single entity using LLM.

        Args:
            entity_name: Entity name to validate
            entity_type: SpaCy-assigned entity type
            mention_count: Number of mentions in corpus
            contexts: Sample contexts (optional, for future enhancement)

        Returns:
            Validation result dict:
            {
                "decision": "KEEP"|"DISCARD",
                "confidence": float,
                "reason": str,
                "suggested_type": str (optional)
            }
        """
        # Format prompt
        prompt = ENTITY_VALIDATION_PROMPT.format(
            entity_name=entity_name,
            entity_type=entity_type,
            mention_count=mention_count,
            contexts=contexts or ["(no context available)"],
        )

        try:
            # Call LLM
            response = await self.client.generate(
                model=self.llm_model,
                prompt=prompt,
                options={
                    "temperature": self.temperature,
                    "num_predict": 200,  # Short response needed
                },
            )

            llm_response = response.get("response", "")

            # Parse JSON
            result = self._parse_json_response(llm_response)

            # Validate result structure
            if "decision" not in result or result["decision"] not in ["KEEP", "DISCARD"]:
                logger.warning(
                    "invalid_validation_response",
                    entity=entity_name,
                    response=llm_response[:200],
                )
                # Default: KEEP (conservative fallback)
                return {
                    "decision": "KEEP",
                    "confidence": 0.5,
                    "reason": "LLM response parsing failed, keeping entity conservatively",
                }

            logger.info(
                "entity_validated",
                entity=entity_name,
                decision=result["decision"],
                confidence=result.get("confidence", 0.0),
            )

            return result

        except Exception as e:
            logger.error(
                "entity_validation_failed",
                entity=entity_name,
                error=str(e),
            )
            # Conservative fallback: KEEP
            return {
                "decision": "KEEP",
                "confidence": 0.5,
                "reason": f"Validation error: {str(e)}",
            }

    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON from LLM response with fallbacks.

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON dict
        """
        cleaned = response.strip()

        # Remove markdown code fences
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        # Try direct parsing
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try regex extraction
            json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            logger.warning("validation_json_parse_failed", response_preview=cleaned[:200])
            return {"decision": "KEEP", "confidence": 0.5, "reason": "JSON parse failed"}


def parse_annotation_file(file_path: Path) -> list[dict[str, Any]]:
    """Parse ENTITIES_AND_RELATIONS_FOR_ANNOTATION.txt.

    Args:
        file_path: Path to annotation file

    Returns:
        List of entity dicts with name, type, mention_count
    """
    entities = {}  # Use dict to count mentions per entity

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_entity = None
    current_type = None

    for line in lines:
        # Parse entity name: "ENTITY: 'OMNINET'"
        entity_match = re.match(r"ENTITY: '(.+?)'", line)
        if entity_match:
            current_entity = entity_match.group(1)
            continue

        # Parse entity type: "  Type: ORGANIZATION"
        type_match = re.match(r"\s+Type: (.+)", line)
        if type_match and current_entity:
            current_type = type_match.group(1).strip()

            # Add or update entity
            if current_entity in entities:
                # Entity already exists, increment mention count
                entities[current_entity]["mentions"] += 1
            else:
                # New entity
                entities[current_entity] = {
                    "name": current_entity,
                    "type": current_type,
                    "mentions": 1,
                }

    # Convert dict to list
    entity_list = list(entities.values())

    logger.info("entities_parsed_from_file", count=len(entity_list))
    return entity_list


async def main():
    print("=" * 80)
    print("LLM ENTITY VALIDATION TEST (Option 4 - Hybrid Pipeline)")
    print("=" * 80)

    # Load annotation file
    annotation_file = project_root / "ENTITIES_AND_RELATIONS_FOR_ANNOTATION.txt"

    if not annotation_file.exists():
        print(f"\n[ERROR] Annotation file not found: {annotation_file}")
        return

    print(f"\n[1/4] Loading entities from {annotation_file.name}...")
    entities = parse_annotation_file(annotation_file)
    print(f"      Loaded {len(entities)} entities")

    # Initialize validator
    print(f"\n[2/4] Initializing LLM validator (gemma-3-4b Q4_K_M)...")
    validator = LLMEntityValidator(
        llm_model="hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M",  # Available in Docker Ollama
        temperature=0.1,  # Low for consistent decisions
    )

    # Validate entities
    print(f"\n[3/4] Validating entities with LLM...")
    print(f"      (This will take ~{len(entities) * 3}s for {len(entities)} entities)\n")

    results = []
    keep_count = 0
    discard_count = 0

    for i, entity in enumerate(entities, 1):
        # Validate
        validation = await validator.validate_entity(
            entity_name=entity["name"],
            entity_type=entity["type"],
            mention_count=entity["mentions"],
        )

        # Track results
        result = {
            "entity_name": entity["name"],
            "entity_type": entity["type"],
            "mentions": entity["mentions"],
            "decision": validation["decision"],
            "confidence": validation.get("confidence", 0.0),
            "reason": validation.get("reason", ""),
            "suggested_type": validation.get("suggested_type", None),
        }
        results.append(result)

        if validation["decision"] == "KEEP":
            keep_count += 1
            status = "[KEEP]"
        else:
            discard_count += 1
            status = "[DISCARD]"

        # Progress output
        print(
            f"   [{i:3d}/{len(entities)}] {status} - {entity['name']:30s} "
            f"({entity['type']:15s}) - {validation.get('reason', '')[:50]}"
        )

    # Output results
    print(f"\n[4/4] Writing results...")

    if len(entities) == 0:
        print("\n[ERROR] No entities found in annotation file!")
        return

    output_file = project_root / "ENTITY_VALIDATION_RESULTS.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# LLM Entity Validation Results\n")
        f.write("# Option 4: Hybrid SpaCy→LLM Validation Pipeline\n")
        f.write(f"# Generated: 2025-11-07\n\n")

        f.write("## Summary\n\n")
        f.write(f"- **Total Entities:** {len(entities)}\n")
        f.write(f"- **KEEP:** {keep_count} ({keep_count/len(entities)*100:.1f}%)\n")
        f.write(f"- **DISCARD:** {discard_count} ({discard_count/len(entities)*100:.1f}%)\n\n")

        f.write("## Kept Entities (High Quality)\n\n")
        for r in results:
            if r["decision"] == "KEEP":
                f.write(
                    f"- **{r['entity_name']}** ({r['entity_type']}) - "
                    f"{r['mentions']} mentions - "
                    f"Confidence: {r['confidence']:.2f}\n"
                    f"  Reason: {r['reason']}\n"
                )
                if r["suggested_type"]:
                    f.write(f"  Suggested Type: {r['suggested_type']}\n")
                f.write("\n")

        f.write("\n## Discarded Entities (Low Quality)\n\n")
        for r in results:
            if r["decision"] == "DISCARD":
                f.write(
                    f"- **{r['entity_name']}** ({r['entity_type']}) - "
                    f"{r['mentions']} mentions - "
                    f"Confidence: {r['confidence']:.2f}\n"
                    f"  Reason: {r['reason']}\n\n"
                )

    print(f"\n   [OK] Results written to {output_file.name}")

    # Statistics
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total Entities:    {len(entities)}")
    print(f"KEEP:              {keep_count} ({keep_count/len(entities)*100:.1f}%)")
    print(f"DISCARD:           {discard_count} ({discard_count/len(entities)*100:.1f}%)")
    print(f"Quality Improvement: -{discard_count} noise entities removed")
    print("=" * 80)

    # Top discarded entities
    print("\nTop Discarded Entities (likely noise):")
    discarded = [r for r in results if r["decision"] == "DISCARD"]
    discarded_sorted = sorted(discarded, key=lambda x: x["mentions"], reverse=True)[:10]

    for r in discarded_sorted:
        print(f"  - {r['entity_name']:20s} ({r['type']:15s}) - {r['mentions']:3d} mentions")

    print(f"\n[DONE] Full results in: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
