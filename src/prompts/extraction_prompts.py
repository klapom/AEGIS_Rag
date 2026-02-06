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

# Entity Extraction Prompt with Few-Shot Examples
# Sprint 13: Optimized for llama3.2:3b model to ensure reliable JSON output
ENTITY_EXTRACTION_PROMPT = """Extract entities from the following text. For each entity, identify:
1. Entity name (exact string from text)
2. Entity type (PERSON, ORGANIZATION, LOCATION, CONCEPT, TECHNOLOGY, PRODUCT, EVENT, or other)
3. Short description (1 sentence, based on context in text)

Few-shot examples:

Example 1:
Text: "John Smith is a software engineer at Google, working on machine learning projects."
Entities:
[
  {{"name": "John Smith", "type": "PERSON", "description": "Software engineer at Google"}},
  {{"name": "Google", "type": "ORGANIZATION", "description": "Technology company"}},
  {{"name": "machine learning", "type": "CONCEPT", "description": "Field of artificial intelligence"}}
]

Example 2:
Text: "The Python programming language was created by Guido van Rossum in 1991."
Entities:
[
  {{"name": "Python", "type": "TECHNOLOGY", "description": "Programming language"}},
  {{"name": "Guido van Rossum", "type": "PERSON", "description": "Creator of Python"}},
  {{"name": "1991", "type": "EVENT", "description": "Year Python was created"}}
]

Example 3:
Text: "Microsoft was founded by Bill Gates and Paul Allen in 1975 in Albuquerque."
Entities:
[
  {{"name": "Microsoft", "type": "ORGANIZATION", "description": "Technology company founded in 1975"}},
  {{"name": "Bill Gates", "type": "PERSON", "description": "Co-founder of Microsoft"}},
  {{"name": "Paul Allen", "type": "PERSON", "description": "Co-founder of Microsoft"}},
  {{"name": "1975", "type": "EVENT", "description": "Year Microsoft was founded"}},
  {{"name": "Albuquerque", "type": "LOCATION", "description": "City where Microsoft was founded"}}
]

Now extract entities from this text:

Text:
{text}

CRITICAL OUTPUT INSTRUCTIONS:
- You MUST return ONLY a valid JSON array
- Do NOT include any explanatory text before the JSON array
- Do NOT include any explanatory text after the JSON array
- Do NOT use markdown code fences (no ``` or ```json)
- Do NOT say "Here are the entities" or similar phrases
- Just output the raw JSON array starting with [ and ending with ]
- Extract at least 3-5 entities if the text contains them

Required JSON format (copy this structure exactly):
[
  {{"name": "Entity Name", "type": "ENTITY_TYPE", "description": "One sentence description"}},
  ...
]

Additional guidelines:
- Extract ALL significant entities mentioned in the text
- Use standard entity types: PERSON, ORGANIZATION, LOCATION, CONCEPT, TECHNOLOGY, PRODUCT, EVENT
- Be comprehensive but avoid duplicates
- Keep descriptions concise (1 sentence)

Output (JSON array only):
"""

# Relationship Extraction Prompt with Few-Shot Examples
# Sprint 85: Enhanced with GraphRAG/LightRAG best practices
RELATIONSHIP_EXTRACTION_PROMPT = """---Role---
You are a Knowledge Graph Specialist extracting ALL relationships between entities.

---Goal---
Identify ALL relationships among the identified entities. Be EXHAUSTIVE.
A good knowledge graph has at least 1 relationship per entity.

---Few-shot Examples---

Example 1:
Entities: John Smith (PERSON), Google (ORGANIZATION), machine learning (CONCEPT)
Text: "John Smith is a software engineer at Google, working on machine learning projects."

Relationships:
[
  {{"source": "John Smith", "target": "Google", "type": "WORKS_AT", "description": "John Smith is employed by Google as a software engineer", "strength": 9}},
  {{"source": "John Smith", "target": "machine learning", "type": "WORKS_ON", "description": "John Smith works on machine learning projects", "strength": 8}},
  {{"source": "Google", "target": "machine learning", "type": "USES", "description": "Google uses machine learning in its projects", "strength": 6}}
]

Example 2:
Entities: Python (TECHNOLOGY), Guido van Rossum (PERSON), 1991 (EVENT)
Text: "The Python programming language was created by Guido van Rossum in 1991."

Relationships:
[
  {{"source": "Guido van Rossum", "target": "Python", "type": "CREATED", "description": "Guido van Rossum created the Python programming language", "strength": 10}},
  {{"source": "Python", "target": "1991", "type": "CREATED_IN", "description": "Python was created in 1991", "strength": 9}}
]

---Task---
Extract ALL relationships from this text:

Entities found:
{entities}

Text:
{text}

---Instructions---
1. Extract ALL relationships - be exhaustive, not conservative
2. Decompose N-ary relationships: "A and B founded C" → A FOUNDED C, B FOUNDED C
3. Include implicit relationships (co-occurrence in same sentence often implies relation)
4. Rate strength 1-10: 10=explicit statement, 7=strong implication, 4=weak inference

---Output Format---
[
  {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "Why related", "strength": 8}},
  ...
]

Common types: WORKS_AT, CREATED, FOUNDED, DIRECTED, PRODUCED, STARS_IN, LOCATED_IN,
PART_OF, MANAGES, USES, COLLABORATES_WITH, BASED_ON, CONTAINS, LEADS_TO, ASSOCIATED_WITH

Output (JSON array only):
"""

# Sprint 45 Feature 45.8: Generic Extraction Prompts for Domain Fallback
# These prompts are used when no domain-specific prompts are available

GENERIC_ENTITY_EXTRACTION_PROMPT = """Extract all significant entities from the following text.

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

GENERIC_RELATION_EXTRACTION_PROMPT = """Extract ALL relationships between the given entities from the text.

---Role---
You are a Knowledge Graph Specialist extracting relationships from text.

---Goal---
Identify ALL relationships among the provided entities. Be EXHAUSTIVE.
A good knowledge graph has at least 1 relationship per entity.

---Entities---
{entities}

---Text---
{text}

---Instructions---
1. For EVERY pair of entities that interact or relate, extract a relationship
2. Decompose complex N-ary relationships into multiple binary pairs
   Example: "John and Mary founded Company" → John FOUNDED Company, Mary FOUNDED Company
3. Include both explicit relationships (stated in text) and implicit ones (strongly implied)
4. Rate relationship strength from 1-10 (10 = explicitly stated, 5 = implied, 1 = weak inference)

---Output Format---
Return a JSON array with this structure:
[
  {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "Why they are related", "strength": 8}},
  ...
]

Common relationship types: WORKS_AT, CREATED, FOUNDED, LOCATED_IN, PART_OF, MANAGES, USES,
COLLABORATES_WITH, DIRECTED, PRODUCED, STARS_IN, BASED_ON, CONTAINS, LEADS_TO

Output (JSON array only):
"""

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

For each missing entity, identify:
1. Entity name (exact string from text)
2. Entity type (PERSON, ORGANIZATION, LOCATION, CONCEPT, TECHNOLOGY, PRODUCT, EVENT, or other)
3. Short description (1 sentence, based on context in text)

CRITICAL OUTPUT INSTRUCTIONS:
- You MUST return ONLY a valid JSON array
- Do NOT include any explanatory text before the JSON array
- Do NOT include any explanatory text after the JSON array
- Do NOT use markdown code fences (no ``` or ```json)
- Do NOT say "Here are the missing entities" or similar phrases
- Just output the raw JSON array starting with [ and ending with ]
- If there are NO missing entities, return an empty array: []

Required JSON format (copy this structure exactly):
[
  {{"name": "Entity Name", "type": "ENTITY_TYPE", "description": "One sentence description"}},
  ...
]

Output (JSON array only):"""


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

Focus on extracting:
- CAUSAL relationships: CAUSES, LEADS_TO, ENABLES, RESULTS_IN, TRIGGERS
- FUNCTIONAL relationships: USES, IMPLEMENTS, EXTENDS, INTEGRATES_WITH
- ORGANIZATIONAL relationships: MANAGES, OWNS, CONTROLS, CONTAINS, PART_OF
- KNOWLEDGE relationships: KNOWS, CREATED, DEVELOPED, DISCOVERED, INVENTED
- TEMPORAL relationships: PRECEDES, FOLLOWS, CONCURRENT_WITH
- SEMANTIC relationships: RELATES_TO, SIMILAR_TO, CONTRASTS_WITH, DEPENDS_ON

CRITICAL: For each pair of related entities, try to find AT LEAST ONE relationship.
If two entities appear in the same sentence or context, they likely have a relationship.

For each missing relationship, identify:
1. Source entity (must be from the entity list)
2. Target entity (must be from the entity list)
3. Relationship type (use UPPERCASE_WITH_UNDERSCORES)
4. Description (1 sentence explaining the relationship)

CRITICAL OUTPUT INSTRUCTIONS:
- You MUST return ONLY a valid JSON array
- Do NOT include any explanatory text before or after the JSON array
- Do NOT use markdown code fences (no ``` or ```json)
- If there are NO missing relationships, return an empty array: []

Required JSON format:
[
  {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "One sentence description"}},
  ...
]

Output (JSON array only):"""


# Sprint 86 Feature 86.2: DSPy MIPROv2 Optimized Prompts
# These prompts were optimized using DSPy MIPROv2 with 80% combined score
# Source: data/dspy_prompts/pipeline_gptoss/pipeline_extraction_20260113_060510.json

DSPY_OPTIMIZED_ENTITY_PROMPT = """You are a data annotator working with a structured knowledge‑extraction pipeline.
Given a **Document Text** and a **Domain** label, your job is to identify all relevant named entities, classify each one with a type from the controlled list below, and give a brief description.

**Procedure**

1. **Read** the entire text and the domain (`technical`, `scientific`, or `organizational`).
2. **Think step by step**: For every entity you plan to list, write a short justification that explains *why* it belongs in the output.
3. **Output** exactly two sections, in this order:
   - `Reasoning:` – a single line that starts with `Reasoning:` followed by your step‑by‑step reasoning.
   - `Entities:` – a single line that starts with `Entities:` followed by a **valid JSON array** of objects.
     Each object must contain the keys:
     * `name`   – the canonical entity string as it appears in the text (MAX 4 WORDS, use shortest common name).
     * `type`   – one of the 15 universal type tags (see below).
     * `description` – a concise, one‑sentence explanation of the entity's role in the text.

**15 Universal Entity Types (ADR-060 Standard)**

| Tag | Typical meaning | Examples |
|-----|-----------------|----------|
| `PERSON` | Individual person | "John Smith", "Einstein" |
| `ORGANIZATION` | Company, lab, institute, agency | "NVIDIA", "WHO", "MIT" |
| `LOCATION` | City, country, address, region | "Berlin", "Europe", "GPS coordinates" |
| `EVENT` | Conference, meeting, occurrence | "WWII", "NeurIPS 2025" |
| `DATE_TIME` | Calendar year, month, day, period | "2025", "Q1 2026" |
| `CONCEPT` | Abstract idea, theory, method | "machine learning", "democracy" |
| `TECHNOLOGY` | Software, framework, platform, protocol | "Docker", "TCP/IP", "React" |
| `PRODUCT` | Physical or digital product, service | "iPhone", "ChatGPT", "AWS" |
| `METRIC` | Measurements, KPIs, scores | "accuracy 95%", "GDP", "F1 score" |
| `DOCUMENT` | Standards, laws, papers, patents | "RFC 2616", "GDPR", "ISO 9001" |
| `PROCESS` | Procedures, workflows, algorithms | "gradient descent", "CI/CD" |
| `MATERIAL` | Physical substances, compounds | "silicon", "H2O", "steel" |
| `REGULATION` | Laws, policies, compliance rules | "GDPR Article 17", "FDA approval" |
| `QUANTITY` | Numerical values with units | "5 GB", "100 meters", "3 days" |
| `FIELD` | Academic discipline, professional field | "neuroscience", "engineering" |

**IMPORTANT Entity Naming Rules**
- **MAX 4 WORDS**: Use concise names (e.g., "NVIDIA" not "NVIDIA Corporation headquartered in Santa Clara")
- **Canonical names**: Use most common name (e.g., "Einstein" not "Albert Einstein, German physicist")
- If entity name in text is > 4 words, shorten it to canonical form

If no entities match the domain or the text, output an empty JSON array: `[]`.

**Formatting rules**

- Do **not** wrap the entire answer in markdown or code fences.
- The JSON array must be syntactically correct; no trailing commas.
- Do not add any extra keys, comments, or explanatory text beyond the two required sections.

---

Text: {text}
Domain: {domain}

Reasoning: Let's think step by step in order to identify all named entities.
Entities:"""

DSPY_OPTIMIZED_RELATION_PROMPT = """Extract ALL relationships between entities from the text as Subject-Predicate-Object triples.

---Role---
You are a Knowledge Graph Specialist extracting structured S-P-O triples for a graph database.

---Goal---
Identify ALL relationships among the provided entities. Be EXHAUSTIVE.
A good knowledge graph has at least 1 relationship per entity.

---Entities---
{entities}

---Text---
{text}

---Instructions---
1. Extract ALL relationships - be exhaustive, not conservative
2. Decompose N-ary relationships: "A and B founded C" → A FOUNDED C, B FOUNDED C
3. Include implicit relationships (co-occurrence in same sentence often implies relation)
4. Rate strength 1-10: 10=explicit statement, 7=strong implication, 4=weak inference
5. CRITICAL: Use a SPECIFIC relationship type from the 22 universal types below
6. Keep entity names concise (MAX 4 WORDS). Use the most common/canonical name
7. Relationship type must be 1-3 words in UPPER_SNAKE_CASE
8. Use "RELATED_TO" ONLY as fallback when no specific type fits

---22 Universal Relation Types (ADR-060 Standard)---
Use ONLY these types (pick the closest match):

**Structural Relations:**
- PART_OF: Component is part of whole (e.g., "GPU is PART_OF DGX Spark")
- CONTAINS: Whole contains component (e.g., "DGX Spark CONTAINS GPU")
- INSTANCE_OF: Specific instance of a type (e.g., "Fido INSTANCE_OF Dog")
- TYPE_OF: Subtype relationship (e.g., "Dog TYPE_OF Animal")

**Organizational Relations:**
- EMPLOYS: Organization employs person (e.g., "NVIDIA EMPLOYS John")
- MANAGES: Person manages entity (e.g., "John MANAGES team")
- FOUNDED_BY: Organization founded by person (e.g., "Microsoft FOUNDED_BY Bill Gates")
- OWNS: Entity owns another entity (e.g., "Google OWNS YouTube")
- LOCATED_IN: Entity located in location (e.g., "Office LOCATED_IN Berlin")

**Causal Relations:**
- CAUSES: X causes Y (e.g., "Fire CAUSES smoke")
- ENABLES: X enables Y (e.g., "API ENABLES integration")
- REQUIRES: X requires Y (e.g., "Python REQUIRES interpreter")
- LEADS_TO: X leads to Y (e.g., "Training LEADS_TO model")

**Temporal Relations:**
- PRECEDES: X happens before Y (e.g., "Testing PRECEDES deployment")
- FOLLOWS: X happens after Y (e.g., "Q2 FOLLOWS Q1")

**Functional Relations:**
- USES: X uses Y (e.g., "Application USES database")
- CREATES: X creates Y (e.g., "Model CREATES predictions")
- IMPLEMENTS: X implements Y (e.g., "Code IMPLEMENTS algorithm")
- DEPENDS_ON: X depends on Y (e.g., "Service DEPENDS_ON API")

**Semantic Relations:**
- SIMILAR_TO: X is similar to Y (e.g., "BERT SIMILAR_TO GPT")
- ASSOCIATED_WITH: X is associated with Y (e.g., "Research ASSOCIATED_WITH paper")

**Fallback (use ONLY when no specific type fits):**
- RELATED_TO: Generic relationship (e.g., "Topic RELATED_TO concept")

---S-P-O Triple Output Format---
Return ONLY a valid JSON array with this structure:
[
  {{
    "subject": "Entity1",
    "subject_type": "ORGANIZATION",
    "relation": "DEVELOPED",
    "object": "Entity2",
    "object_type": "PRODUCT",
    "description": "Entity1 developed Entity2 to solve problem X",
    "strength": 9
  }},
  ...
]

**IMPORTANT:**
- "subject" = source entity (short name, max 4 words)
- "subject_type" = one of the 15 universal entity types
- "relation" = one of the 21 universal relation types (1-3 words, UPPER_SNAKE_CASE)
- "object" = target entity (short name, max 4 words)
- "object_type" = one of the 15 universal entity types
- "description" = evidence from text explaining the relationship (1 sentence)
- "strength" = confidence score 1-10

Output (JSON array only):
"""


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
[
  {{"name": "Entity Name", "type": "ENTITY_TYPE", "description": "Brief description"}},
  ...
]

If no additional entities found, return: []

Entities (JSON array only):"""


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


# Enhanced relationship extraction prompt for better ER ratio (Sprint 85)
ENHANCED_RELATIONSHIP_EXTRACTION_PROMPT = """Extract ALL relationships between entities from the following text.

IMPORTANT: Be thorough! For a knowledge graph to be useful, we need MANY relationships.
A good knowledge graph has at least 1 relationship per entity.

Entities found in this text:
{entities}

Text:
{text}

For EVERY pair of entities that interact or relate in the text, extract a relationship.

Relationship types to consider:
- FUNCTIONAL: USES, CREATES, IMPLEMENTS, PROCESSES, GENERATES, TRANSFORMS
- CAUSAL: CAUSES, ENABLES, LEADS_TO, RESULTS_IN, INFLUENCES, TRIGGERS
- HIERARCHICAL: CONTAINS, PART_OF, MANAGES, OWNS, CONTROLS, BELONGS_TO
- TEMPORAL: PRECEDES, FOLLOWS, DURING, CONCURRENT_WITH
- KNOWLEDGE: KNOWS, CREATED_BY, DEVELOPED_BY, DISCOVERED_BY, INVENTED_BY
- LOCATION: LOCATED_IN, BASED_IN, OPERATES_IN, HEADQUARTERED_IN
- ASSOCIATION: WORKS_AT, WORKS_WITH, COLLABORATES_WITH, ASSOCIATED_WITH
- SEMANTIC: RELATES_TO, SIMILAR_TO, CONTRASTS_WITH, DEPENDS_ON, EXTENDS

For each relationship, provide:
1. source: The entity that is the subject of the relationship
2. target: The entity that is the object of the relationship
3. type: Relationship type from the list above (UPPERCASE_WITH_UNDERSCORES)
4. description: One sentence explaining the relationship based on text

CRITICAL OUTPUT INSTRUCTIONS:
- Return ONLY a valid JSON array
- Do NOT include any explanatory text
- Do NOT use markdown code fences
- Extract ALL possible relationships (aim for at least {min_relations} relationships)

Output format:
[
  {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "Explanation"}},
  ...
]

Output (JSON array only):
"""


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
