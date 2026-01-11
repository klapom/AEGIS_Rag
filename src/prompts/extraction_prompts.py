"""Prompts for entity and relationship extraction.

Sprint 5: Feature 5.3 - Entity & Relationship Extraction
Sprint 13: Enhanced prompts for llama3.2:3b compatibility (TD-30 fix)
Sprint 45: Feature 45.8 - Generic extraction prompts for domain fallback
Sprint 83: Feature 83.3 - Gleaning multi-pass extraction prompts (TD-100)
"""

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
RELATIONSHIP_EXTRACTION_PROMPT = """Extract relationships between entities from the following text.

Few-shot examples:

Example 1:
Entities:
- John Smith (PERSON)
- Google (ORGANIZATION)
- machine learning (CONCEPT)

Text: "John Smith is a software engineer at Google, working on machine learning projects."

Relationships:
[
  {{"source": "John Smith", "target": "Google", "type": "WORKS_AT", "description": "John Smith is employed by Google as a software engineer"}},
  {{"source": "John Smith", "target": "machine learning", "type": "WORKS_ON", "description": "John Smith works on machine learning projects"}}
]

Example 2:
Entities:
- Python (TECHNOLOGY)
- Guido van Rossum (PERSON)

Text: "The Python programming language was created by Guido van Rossum in 1991."

Relationships:
[
  {{"source": "Guido van Rossum", "target": "Python", "type": "CREATED", "description": "Guido van Rossum created the Python programming language"}}
]

Now extract relationships from this text:

Entities found in this text:
{entities}

Text:
{text}

For each relationship, identify:
1. Source entity (must be from the list above)
2. Target entity (must be from the list above)
3. Relationship type (WORKS_AT, KNOWS, LOCATED_IN, USES, CREATES, PART_OF, MANAGES, etc.)
4. Description (1 sentence explaining the relationship based on text)

Return relationships as a JSON array. Use this exact format:
[
  {{"source": "Entity1", "target": "Entity2", "type": "RELATIONSHIP_TYPE", "description": "One sentence description"}},
  ...
]

Guidelines:
- Only extract relationships explicitly stated or strongly implied in the text
- Use standard relationship types (uppercase with underscores, e.g., WORKS_AT)
- Common types: WORKS_AT, KNOWS, LOCATED_IN, CREATED, USES, PART_OF, MANAGES, WORKS_ON
- Ensure source and target entities exist in the list above
- Return only valid JSON (no additional text)

Relationships:
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

GENERIC_RELATION_EXTRACTION_PROMPT = """Extract relationships between the given entities from the text.

Entities:
{entities}

Text:
{text}

Return subject-predicate-object triples where:
- subject and object MUST be from the entity list above
- predicate is a natural language description of the relationship

Output format (JSON array):
[{{"subject": "Entity1", "predicate": "relationship description", "object": "Entity2"}}]

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
