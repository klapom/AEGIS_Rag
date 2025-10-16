"""Prompts for entity and relationship extraction.

Sprint 5: Feature 5.3 - Entity & Relationship Extraction
"""

# Entity Extraction Prompt with Few-Shot Examples
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

Now extract entities from this text:

Text:
{text}

Return entities as a JSON array. Use this exact format:
[
  {{"name": "Entity Name", "type": "ENTITY_TYPE", "description": "One sentence description"}},
  ...
]

Guidelines:
- Extract ALL significant entities mentioned in the text
- Use standard entity types: PERSON, ORGANIZATION, LOCATION, CONCEPT, TECHNOLOGY, PRODUCT, EVENT
- Be comprehensive but avoid duplicates
- Keep descriptions concise (1 sentence)
- Return only valid JSON (no additional text)

Entities:
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
