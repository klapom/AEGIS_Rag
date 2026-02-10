"""Prompts for entity and relationship extraction.

Sprint 5: Feature 5.3 - Entity & Relationship Extraction
Sprint 13: Enhanced prompts for llama3.2:3b compatibility (TD-30 fix)
Sprint 45: Feature 45.8 - Generic extraction prompts for domain fallback
Sprint 83: Feature 83.3 - Gleaning multi-pass extraction prompts (TD-100)
Sprint 86: Feature 86.2 - DSPy MIPROv2 optimized prompts (A/B tested, 100% pipeline compatible)
Sprint 86: Feature 86.3 - DSPy prompts as default for all domains
"""

import os

# Sprint 86.3: DSPy-optimized prompts are now the DEFAULT for all domains
# The DSPy prompts showed +22% Entity F1, +30% Relation F1, -12% Latency improvement
# Set AEGIS_USE_LEGACY_PROMPTS=1 to revert to old generic prompts if needed
USE_DSPY_PROMPTS = os.environ.get("AEGIS_USE_LEGACY_PROMPTS", "0") != "1"


# Sprint 45 Feature 45.8: Generic Extraction Prompts for Domain Fallback
# These prompts are used when no domain-specific prompts are available

GENERIC_ENTITY_EXTRACTION_PROMPT = """Extract all named entities from the text. Return ONLY a valid JSON array.

Entity types (ADR-060): PERSON, ORGANIZATION, LOCATION, EVENT, DATE_TIME, CONCEPT, TECHNOLOGY, PRODUCT, METRIC, DOCUMENT, PROCESS, MATERIAL, REGULATION, QUANTITY, FIELD

Rules:
- Entity name: max 4 words, canonical form
- One entity per concept, no duplicates
- Confidence: 1.0 = explicit mention, 0.7 = implied, 0.4 = inferred

Text:
{text}

Output example:
[
  {{"name": "NVIDIA", "type": "ORGANIZATION", "description": "GPU manufacturer", "confidence": 1.0}},
  {{"name": "machine learning", "type": "CONCEPT", "description": "AI training methodology", "confidence": 0.7}}
]

Entities:"""

GENERIC_RELATION_EXTRACTION_PROMPT = """Extract ALL relationships between the given entities. Return ONLY a valid JSON array.

Relation types (ADR-060): PART_OF, CONTAINS, INSTANCE_OF, TYPE_OF, EMPLOYS, MANAGES, FOUNDED_BY, OWNS, LOCATED_IN, CAUSES, ENABLES, REQUIRES, LEADS_TO, PRECEDES, FOLLOWS, USES, CREATES, IMPLEMENTS, DEPENDS_ON, SIMILAR_TO, ASSOCIATED_WITH, RELATED_TO (last resort only)

Rules:
- Be exhaustive: at least 1 relationship per entity
- Decompose N-ary: "A and B founded C" → two triples
- Subject/object: max 4 words, must match entity name exactly
- Strength: 10 = explicit statement, 7 = strong implication, 4 = weak inference

Entities:
{entities}

Text:
{text}

Output example:
[
  {{"subject": "NVIDIA", "relation": "CREATES", "object": "DGX Spark", "description": "NVIDIA designed the DGX Spark", "strength": 10}},
  {{"subject": "DGX Spark", "relation": "CONTAINS", "object": "GB10 GPU", "description": "DGX Spark includes GB10 GPU", "strength": 9}}
]

Relations:"""

# Sprint 83 Feature 83.3: Gleaning Multi-Pass Extraction (TD-100)
# Based on Microsoft GraphRAG approach

COMPLETENESS_CHECK_PROMPT = """You have extracted the following entities from a document:

{extracted_entities}

Document text:
{document_text}

Are there any significant entities (people, organizations, locations, concepts, technologies, products, events) that were MISSED in this extraction?

Think carefully about:
- Named entities that appear in the text but are not in the list above
- Important concepts or terminology not captured
- Relationships or connections that imply missing entities

Answer with ONLY "YES" or "NO" (no explanation needed).

If you believe the extraction is complete and comprehensive, answer: NO
If you believe there are missing entities worth extracting, answer: YES

Answer:"""

CONTINUATION_EXTRACTION_PROMPT = """You previously extracted these entities from a document:

{extracted_entities}

The full document text is:
{document_text}

Please extract ONLY the entities that were MISSED in the previous extraction.
Do NOT repeat entities that were already extracted in the list above.

Focus on:
- Named entities (people, organizations, locations)
- Important concepts and topics not captured before
- Domain-specific terminology that was overlooked
- Products, technologies, or events mentioned but not extracted

For each missing entity use the 15 ADR-060 types: PERSON, ORGANIZATION, LOCATION, EVENT, DATE_TIME, CONCEPT, TECHNOLOGY, PRODUCT, METRIC, DOCUMENT, PROCESS, MATERIAL, REGULATION, QUANTITY, FIELD

Return ONLY a valid JSON array. No markdown, no explanatory text. If none missing, return [].

Output example:
[
  {{"name": "Entity Name", "type": "CONCEPT", "description": "One sentence description", "confidence": 0.7}}
]

Entities:"""


# Sprint 85 Feature 85.8: Relationship Gleaning Prompts
# Adds multi-pass extraction for relationships to improve ER ratio

RELATIONSHIP_COMPLETENESS_CHECK_PROMPT = """You have extracted the following relationships between entities:

{extracted_relationships}

From entities:
{entities}

Document text:
{document_text}

Are there any significant RELATIONSHIPS between the entities that were MISSED?

Think carefully about:
- Explicit relationships stated in the text (e.g., "X works at Y", "A created B")
- Implicit relationships strongly implied (e.g., "X and Y collaborated" implies COLLABORATES_WITH)
- Causal relationships (X causes Y, X leads to Y, X enables Y)
- Temporal relationships (X precedes Y, X follows Y)
- Spatial relationships (X is located in Y, X is part of Y)
- Hierarchical relationships (X manages Y, X owns Y, X contains Y)

Answer with ONLY "YES" or "NO" (no explanation needed).

If you believe the extraction is complete and comprehensive, answer: NO
If you believe there are missing relationships worth extracting, answer: YES

Answer:"""


RELATIONSHIP_CONTINUATION_PROMPT = """You previously extracted these relationships:

{extracted_relationships}

From entities:
{entities}

Full document text:
{document_text}

Please extract ONLY the relationships that were MISSED in the previous extraction.
Do NOT repeat relationships that were already extracted in the list above.

Focus on these ADR-060 relation types:
- Causal: CAUSES, LEADS_TO, ENABLES, REQUIRES
- Functional: USES, CREATES, IMPLEMENTS, DEPENDS_ON
- Organizational: MANAGES, OWNS, EMPLOYS, FOUNDED_BY, LOCATED_IN
- Structural: PART_OF, CONTAINS, INSTANCE_OF, TYPE_OF
- Temporal: PRECEDES, FOLLOWS
- Semantic: SIMILAR_TO, ASSOCIATED_WITH
- Fallback: RELATED_TO (only when nothing else fits)

Extract AT LEAST ONE relationship per entity pair that co-occurs in the text.
Return ONLY a valid JSON array. No markdown, no explanatory text. If none missing, return [].

Output example:
[
  {{"subject": "Entity1", "relation": "CAUSES", "object": "Entity2", "description": "Evidence from text", "strength": 7}}
]

Output (JSON array only):"""


# Sprint 86 Feature 86.2: DSPy MIPROv2 Optimized Prompts
# These prompts were optimized using DSPy MIPROv2 with 80% combined score
# Source: data/dspy_prompts/pipeline_gptoss/pipeline_extraction_20260113_060510.json

DSPY_OPTIMIZED_ENTITY_PROMPT = """Extract all named entities from the text. Return ONLY a valid JSON array.

Entity types:
- PERSON: Named individuals
- ORGANIZATION: Companies, agencies, institutions
- LOCATION: Places, regions, countries
- EVENT: Named events, milestones
- DATE_TIME: Dates, periods, timestamps
- CONCEPT: Abstract ideas, theories, methods
- TECHNOLOGY: Frameworks, platforms, tools, protocols
- PRODUCT: Software, hardware, consumer products
- METRIC: Measurements, KPIs, scores
- DOCUMENT: Standards, laws, papers, patents
- PROCESS: Procedures, workflows, algorithms
- MATERIAL: Physical substances, compounds
- REGULATION: Laws, policies, compliance rules
- QUANTITY: Numerical values with units
- FIELD: Academic disciplines, professional fields

Rules:
- Entity name: max 4 words, canonical form
- One entity per concept, no duplicates
- Confidence: 1.0 = explicit mention, 0.7 = implied, 0.4 = inferred

Text: {text}
Domain: {domain}

Output example:
[
  {{"name": "NVIDIA", "type": "ORGANIZATION", "description": "GPU manufacturer", "confidence": 1.0}},
  {{"name": "machine learning", "type": "CONCEPT", "description": "AI training methodology", "confidence": 0.7}}
]

Entities:"""

DSPY_OPTIMIZED_RELATION_PROMPT = """Extract ALL relationships between the given entities. Return ONLY a valid JSON array.

Relation types:
- PART_OF: Component → Whole
- CONTAINS: Whole → Component
- INSTANCE_OF: Instance → Type
- TYPE_OF: Subtype → Supertype
- EMPLOYS: Organization → Person
- MANAGES: Person → Entity
- FOUNDED_BY: Organization → Person
- OWNS: Entity → Entity
- LOCATED_IN: Entity → Location
- CAUSES: Cause → Effect
- ENABLES: Enabler → Enabled
- REQUIRES: Dependent → Dependency
- LEADS_TO: Antecedent → Consequent
- PRECEDES: Earlier → Later
- FOLLOWS: Later → Earlier
- USES: User → Tool/Resource
- CREATES: Creator → Creation
- IMPLEMENTS: Implementation → Specification
- DEPENDS_ON: Dependent → Dependency
- SIMILAR_TO: Entity → Entity
- ASSOCIATED_WITH: Entity → Entity
- RELATED_TO: Entity → Entity (ONLY as last resort)

Rules:
- Be exhaustive: extract ALL relationships, at least 1 per entity
- Decompose N-ary: "A and B founded C" → two triples
- Subject/object: max 4 words, must match entity name exactly
- Strength: 10 = explicit statement, 7 = strong implication, 4 = weak inference
- Use RELATED_TO ONLY when no specific type fits

Entities:
{entities}

Text: {text}

Output example:
[
  {{"subject": "NVIDIA", "relation": "CREATES", "object": "DGX Spark", "description": "NVIDIA designed the DGX Spark workstation", "strength": 10}},
  {{"subject": "DGX Spark", "relation": "CONTAINS", "object": "GB10 GPU", "description": "DGX Spark includes the GB10 Blackwell GPU", "strength": 9}}
]

Relations:"""


# Sprint 89 Feature 89.1: SpaCy-First Pipeline Prompts (TD-102 Iteration 1)
# These prompts are used in the 3-stage pipeline: SpaCy → LLM Enrichment → LLM Relations

ENTITY_ENRICHMENT_PROMPT = """You are enriching a SpaCy NER baseline with domain-specific entities.

---Context---
SpaCy has already extracted these entities: {spacy_entities}

SpaCy is good at: PERSON, ORGANIZATION, LOCATION, DATE_TIME
SpaCy MISSES: CONCEPT, TECHNOLOGY, PRODUCT, PROCESS, METRIC, DOCUMENT, MATERIAL, REGULATION, QUANTITY, FIELD

---Your Task---
Find ONLY entities that SpaCy MISSED. Do NOT repeat SpaCy entities.

---Text---
{text}

---Instructions---
1. Review SpaCy's entities - these are already captured
2. Find ADDITIONAL entities of types SpaCy cannot detect (use 15 universal types from ADR-060):
   - CONCEPT: Abstract ideas, theories, methods (e.g., "machine learning", "democracy")
   - TECHNOLOGY: Frameworks, platforms, tools, protocols (e.g., "Docker", "TCP/IP", "React")
   - PRODUCT: Software products, hardware, services (e.g., "ChatGPT", "iPhone", "AWS")
   - PROCESS: Procedures, workflows, algorithms (e.g., "gradient descent", "CI/CD")
   - METRIC: Measurements, KPIs, scores (e.g., "accuracy 95%", "GDP", "F1 score")
   - DOCUMENT: Standards, laws, papers, patents (e.g., "RFC 2616", "GDPR", "ISO 9001")
   - MATERIAL: Physical substances, compounds (e.g., "silicon", "H2O", "steel")
   - REGULATION: Laws, policies, compliance rules (e.g., "GDPR Article 17", "FDA approval")
   - QUANTITY: Numerical values with units (e.g., "5 GB", "100 meters", "3 days")
   - FIELD: Academic discipline, professional field (e.g., "neuroscience", "engineering")
3. Do NOT repeat any entity from SpaCy's list
4. Be thorough but precise - only include clear entities
5. IMPORTANT: Keep entity names SHORT (max 4 words, use canonical names)

---Output Format---
Return ONLY a valid JSON array of NEW entities (not already in SpaCy list):

Output example:
[
  {{"name": "gradient descent", "type": "PROCESS", "description": "Optimization algorithm for neural networks", "confidence": 1.0}},
  {{"name": "Docker", "type": "TECHNOLOGY", "description": "Container platform", "confidence": 0.7}}
]

If no additional entities found, return: []

Entities:"""


RELATION_EXTRACTION_FROM_ENTITIES_PROMPT = """Extract ALL relationships between the given entities.

---Role---
You are a Knowledge Graph Specialist. Your task is to find ALL relationships between entities.

---Entities---
{entities}

---Text---
{text}

---Goal---
Create a COMPLETE relationship graph. Every entity should have at least ONE relationship.

---Instructions---
1. Consider ALL entity pairs - check if any relationship exists
2. Decompose complex relationships: "A and B work at C" → A EMPLOYS John, B EMPLOYS Jane (inverse of WORKS_AT)
3. Include implicit relationships from context
4. Rate strength 1-10: 10=explicit, 7=implied, 4=inferred
5. Use ONLY the 22 universal relation types (ADR-060 Standard)
6. Keep entity names SHORT (max 4 words)
7. Relation types must be 1-3 words in UPPER_SNAKE_CASE

---22 Universal Relation Types (ADR-060 Standard)---
Use ONLY these types:

**Structural:** PART_OF, CONTAINS, INSTANCE_OF, TYPE_OF
**Organizational:** EMPLOYS, MANAGES, FOUNDED_BY, OWNS, LOCATED_IN
**Causal:** CAUSES, ENABLES, REQUIRES, LEADS_TO
**Temporal:** PRECEDES, FOLLOWS
**Functional:** USES, CREATES, IMPLEMENTS, DEPENDS_ON
**Semantic:** SIMILAR_TO, ASSOCIATED_WITH
**Fallback:** RELATED_TO (only if no specific type fits)

---Output Format---
Return ONLY a valid JSON array:
[
  {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "Evidence from text", "strength": 8}},
  ...
]

IMPORTANT: Every entity should have at least one relationship!

Relationships (JSON array only):"""


def get_active_extraction_prompts(domain: str = "technical") -> tuple[str, str]:
    """Get the active extraction prompts based on configuration.

    Sprint 86 Feature 86.3: DSPy MIPROv2 optimized prompts are now the DEFAULT.

    Returns DSPy-optimized prompts by default (proven +22% Entity F1, +30% Relation F1).
    Set AEGIS_USE_LEGACY_PROMPTS=1 to revert to old generic prompts if issues arise.

    Domain-specific prompt optimization happens during domain training, which uses
    these DSPy prompts as the starting point (base prompts).

    Args:
        domain: Document domain (technical, organizational, scientific)
                Currently unused - all domains use same optimized prompts.
                Domain-specific prompts are stored in domain training config.

    Returns:
        Tuple of (entity_prompt, relation_prompt)
    """
    if USE_DSPY_PROMPTS:
        # DEFAULT: Return DSPy optimized prompts (Sprint 86.3)
        # These are the MIPROv2-optimized prompts with step-by-step reasoning
        return (
            DSPY_OPTIMIZED_ENTITY_PROMPT,
            DSPY_OPTIMIZED_RELATION_PROMPT,
        )
    else:
        # LEGACY: Return old generic prompts (set AEGIS_USE_LEGACY_PROMPTS=1)
        return (
            GENERIC_ENTITY_EXTRACTION_PROMPT,
            GENERIC_RELATION_EXTRACTION_PROMPT,
        )


def get_domain_enriched_extraction_prompts(
    domain: str,
    entity_sub_types: list[str] | None = None,
    entity_sub_type_mapping: dict[str, str] | None = None,
    relation_hints: list[str] | None = None,
) -> tuple[str, str]:
    """Generate domain-specific extraction prompts from seed_domains.yaml metadata.

    Sprint 126: Bridges seed_domains.yaml metadata into extraction prompts.
    Sprint 128: Rewritten to produce compact, domain-specific prompts with
    domain types listed directly (no universal type table) and concrete JSON examples.

    Priority chain in extraction_service.get_extraction_prompts():
        1. DSPy-trained prompts from Neo4j (fully trained)
        2. THIS: Domain-specific prompts built from seed_domains.yaml
        3. Generic prompts (no domain enrichment)
        4. Legacy prompts

    Args:
        domain: Domain identifier (e.g., "medicine_health")
        entity_sub_types: List of Tier 2 entity types (e.g., ["DISEASE", "SYMPTOM"])
        entity_sub_type_mapping: Maps sub-types to universal types (e.g., {"DISEASE": "CONCEPT"})
        relation_hints: Domain-specific S-P-O patterns (e.g., ["TREATS → Medication → Disease"])

    Returns:
        Tuple of (enriched_entity_prompt, enriched_relation_prompt)
    """
    # If no domain-specific types available, fall back to generic prompts
    if not entity_sub_types and not relation_hints:
        return (DSPY_OPTIMIZED_ENTITY_PROMPT, DSPY_OPTIMIZED_RELATION_PROMPT)

    # ── Build domain-specific entity prompt ──────────────────────────────
    domain_label = domain.replace("_", " ").title()

    # Build entity type list from domain sub-types + universal types
    entity_type_lines = []
    if entity_sub_types and entity_sub_type_mapping:
        for sub_type in entity_sub_types:
            entity_type_lines.append(f"- {sub_type}")
        # Add essential universal types not covered by domain sub-types
        covered_universal = set(entity_sub_type_mapping.values())
        essential_universal = ["PERSON", "ORGANIZATION", "LOCATION", "EVENT", "DATE_TIME"]
        for u_type in essential_universal:
            if u_type not in covered_universal:
                entity_type_lines.append(f"- {u_type}")
    else:
        # No sub-types: use all 15 universal types
        entity_type_lines = [
            "- PERSON",
            "- ORGANIZATION",
            "- LOCATION",
            "- EVENT",
            "- DATE_TIME",
            "- CONCEPT",
            "- TECHNOLOGY",
            "- PRODUCT",
            "- METRIC",
            "- DOCUMENT",
            "- PROCESS",
            "- MATERIAL",
            "- REGULATION",
            "- QUANTITY",
            "- FIELD",
        ]

    entity_types_block = "\n".join(entity_type_lines)

    # Build entity example from first two sub-types (or generic)
    if entity_sub_types and len(entity_sub_types) >= 2:
        ex1_type = entity_sub_types[0]
        ex2_type = entity_sub_types[1]
        entity_example = (
            f'  {{"name": "example A", "type": "{ex1_type}", '
            f'"description": "Description of entity A", "confidence": 1.0}},\n'
            f'  {{"name": "example B", "type": "{ex2_type}", '
            f'"description": "Description of entity B", "confidence": 0.7}}'
        )
    else:
        entity_example = (
            '  {"name": "NVIDIA", "type": "ORGANIZATION", '
            '"description": "GPU manufacturer", "confidence": 1.0},\n'
            '  {"name": "machine learning", "type": "CONCEPT", '
            '"description": "AI training methodology", "confidence": 1.0}'
        )

    entity_prompt = f"""Extract all named entities from the text. Return ONLY a valid JSON array.

Entity types for {domain_label}:
{entity_types_block}

Rules:
- Entity name: max 4 words, canonical form
- One entity per concept, no duplicates
- Confidence: 1.0 = explicit mention, 0.7 = implied, 0.4 = inferred

Text: {{text}}
Domain: {{domain}}

Output example:
[
{entity_example}
]

Entities:"""

    # ── Build domain-specific relation prompt ────────────────────────────
    if relation_hints:
        relation_type_lines = []
        for hint in relation_hints:
            relation_type_lines.append(f"- {hint}")
        # Add essential universal relation types
        relation_type_lines.extend(
            [
                "- PART_OF → Component → Whole",
                "- CONTAINS → Whole → Component",
                "- LOCATED_IN → Entity → Location",
                "- USES → User → Tool/Resource",
                "- CREATES → Creator → Creation",
                "- RELATED_TO → Entity → Entity (ONLY as last resort)",
            ]
        )
        relation_types_block = "\n".join(relation_type_lines)

        # Build relation example from first hint
        first_hint_parts = relation_hints[0].split("→")
        if len(first_hint_parts) >= 3:
            ex_rel = first_hint_parts[0].strip()
            ex_subj_type = first_hint_parts[1].strip()
            ex_obj_type = first_hint_parts[2].strip()
            relation_example = (
                f'  {{"subject": "{ex_subj_type.lower()} A", "relation": "{ex_rel}", '
                f'"object": "{ex_obj_type.lower()} B", '
                f'"description": "{ex_subj_type} A {ex_rel.lower().replace("_", " ")} {ex_obj_type} B", '
                f'"strength": 10}}'
            )
        else:
            relation_example = (
                '  {"subject": "entity A", "relation": "USES", '
                '"object": "entity B", "description": "A uses B", "strength": 10}'
            )
    else:
        # No relation hints: use generic universal types
        relation_types_block = (
            "- PART_OF: Component → Whole\n"
            "- CONTAINS: Whole → Component\n"
            "- INSTANCE_OF: Instance → Type\n"
            "- TYPE_OF: Subtype → Supertype\n"
            "- EMPLOYS: Organization → Person\n"
            "- MANAGES: Person → Entity\n"
            "- FOUNDED_BY: Organization → Person\n"
            "- OWNS: Entity → Entity\n"
            "- LOCATED_IN: Entity → Location\n"
            "- CAUSES: Cause → Effect\n"
            "- ENABLES: Enabler → Enabled\n"
            "- REQUIRES: Dependent → Dependency\n"
            "- LEADS_TO: Antecedent → Consequent\n"
            "- PRECEDES: Earlier → Later\n"
            "- FOLLOWS: Later → Earlier\n"
            "- USES: User → Tool/Resource\n"
            "- CREATES: Creator → Creation\n"
            "- IMPLEMENTS: Implementation → Specification\n"
            "- DEPENDS_ON: Dependent → Dependency\n"
            "- SIMILAR_TO: Entity → Entity\n"
            "- ASSOCIATED_WITH: Entity → Entity\n"
            "- RELATED_TO: Entity → Entity (ONLY as last resort)"
        )
        relation_example = (
            '  {"subject": "NVIDIA", "relation": "CREATES", '
            '"object": "DGX Spark", "description": "NVIDIA designed the DGX Spark", "strength": 10}'
        )

    relation_prompt = f"""Extract ALL relationships between the given entities. Return ONLY a valid JSON array.

Relation types for {domain_label}:
{relation_types_block}

Rules:
- Be exhaustive: extract ALL relationships, at least 1 per entity
- Decompose N-ary: "A and B founded C" → two triples
- Subject/object: max 4 words, must match entity name exactly
- Strength: 10 = explicit statement, 7 = strong implication, 4 = weak inference
- Use RELATED_TO ONLY when no specific type fits

Entities:
{{entities}}

Text: {{text}}

Output example:
[
{relation_example}
]

Relations:"""

    return (entity_prompt, relation_prompt)
