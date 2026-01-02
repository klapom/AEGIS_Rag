# AegisRAG LLM Prompts Documentation

**Last Updated:** 2026-01-02 (Sprint 71)
**Total Prompts:** 20+
**Languages:** English (extraction/routing), German (answer generation)

---

## Table of Contents

1. [Answer Generation Prompts](#1-answer-generation-prompts)
2. [Query Routing & Classification](#2-query-routing--classification)
3. [Entity & Relationship Extraction](#3-entity--relationship-extraction)
4. [Graph RAG Prompts](#4-graph-rag-prompts)
5. [Query Processing](#5-query-processing)
6. [Domain Training](#6-domain-training)
7. [Tool Use & Actions](#7-tool-use--actions)
8. [Follow-up Generation](#8-follow-up-generation)
9. [Prompt Design Principles](#9-prompt-design-principles)

---

## 1. Answer Generation Prompts

**File:** `src/prompts/answer_prompts.py`

### 1.1 ANSWER_GENERATION_PROMPT

**Purpose:** Standard answer generation from retrieved contexts
**Language:** German
**Sprint:** 11 (Feature 11.1), 52 (Nemotron optimization), 71 (Anti-hallucination)

**Used By:**
- `src/agents/answer_generator.py` → `generate_answer()` (mode="simple")

**Key Features:**
- Anti-hallucination constraints (Sprint 71 - TD-080)
- Explicit knowledge base restriction
- German language for Nemotron compatibility

**Template Variables:**
- `{context}` - Retrieved document contexts (formatted)
- `{query}` - User question

**Prompt Structure:**
```
Du bist ein hilfreicher KI-Assistent für eine Wissensdatenbank.

**WICHTIGE REGELN:**
- Antworte NUR basierend auf den bereitgestellten Dokumenten
- Nutze KEIN externes Wissen aus deinem Training
- Wenn die Dokumente die Frage nicht beantworten können, antworte:
  "Diese Information ist nicht in der Wissensdatenbank verfügbar."
- Erfinde KEINE Informationen

**Dokumente:**
{context}

**Frage:** {query}

**Antwort:**
```

---

### 1.2 MULTI_HOP_REASONING_PROMPT

**Purpose:** Multi-hop reasoning across multiple contexts
**Language:** German
**Sprint:** 11, 52, 71

**Used By:**
- `src/agents/answer_generator.py` → `generate_answer()` (mode="multi_hop")

**Key Features:**
- Combines information from multiple sources
- Anti-hallucination constraints (Sprint 71)
- Complex reasoning support

**Template Variables:**
- `{contexts}` - Multiple retrieved contexts
- `{query}` - User question

---

### 1.3 ANSWER_GENERATION_WITH_CITATIONS_PROMPT

**Purpose:** Answer generation with inline source citations [1], [2], [3]
**Language:** German
**Sprint:** 52, 71

**Used By:**
- `src/agents/answer_generator.py` → `generate_answer_with_citations()`

**Key Features:**
- Inline citation markers ([1], [2], [3])
- Anti-hallucination constraints (Sprint 71)
- Source attribution

**Template Variables:**
- `{contexts}` - Numbered source contexts
- `{query}` - User question

**Citation Format:**
```
Aussage basierend auf Quelle A [1].
Weitere Information aus Quelle B [2].
```

---

## 2. Query Routing & Classification

### 2.1 CLASSIFICATION_PROMPT (Query Router)

**File:** `src/prompts/router_prompts.py`
**Purpose:** Route queries to appropriate retrieval mode (VECTOR, GRAPH, HYBRID, MEMORY)
**Language:** English
**Sprint:** 4 (Feature 4.2)

**Used By:**
- `src/components/routing/query_router.py` → `route_query()`

**Intent Types:**
1. **VECTOR** - Semantic similarity search (factual questions, definitions)
2. **GRAPH** - Knowledge graph traversal (relationships, entity connections)
3. **HYBRID** - Combined vector + graph (complex multi-faceted queries)
4. **MEMORY** - Temporal memory retrieval (conversation history)

**Examples in Prompt:**
- "What is RAG?" → VECTOR
- "How are RAG and knowledge graphs related?" → GRAPH
- "What did we discuss yesterday?" → MEMORY

**Template Variables:**
- `{query}` - User query to classify

**Output Format:** Single intent name (VECTOR/GRAPH/HYBRID/MEMORY)

---

### 2.2 INTENT_CLASSIFICATION_PROMPT (4-Way Hybrid RRF)

**File:** `src/components/retrieval/intent_classifier.py`
**Purpose:** Classify query intent for RRF weight tuning (factual, keyword, exploratory, summary)
**Language:** English
**Sprint:** 42 (TD-057), 52 (Embedding-based), 67 (C-LARA SetFit)

**Used By:**
- `src/components/retrieval/intent_classifier.py` → `_classify_with_llm()` (fallback only)
- **NOTE:** Primary classification now uses SetFit model (Sprint 67), LLM is fallback

**Intent Types:**
1. **factual** - Specific fact lookups (Who, What, When, Where)
2. **keyword** - Keyword searches (codes, identifiers, technical terms)
3. **exploratory** - Exploration queries (How, Why, explain, relationships)
4. **summary** - Overview requests (summarize, main points, high-level)

**RRF Weight Profiles:**
```python
FACTUAL:     vector=0.3, bm25=0.3, local=0.4, global=0.0
KEYWORD:     vector=0.1, bm25=0.6, local=0.3, global=0.0
EXPLORATORY: vector=0.2, bm25=0.1, local=0.2, global=0.5
SUMMARY:     vector=0.1, bm25=0.0, local=0.1, global=0.8
```

**Output Format:** Single intent word (factual/keyword/exploratory/summary)

**Classification Methods:**
1. **SetFit (Primary):** C-LARA trained model (~30ms, 85-92% accuracy)
2. **Embedding (Fallback):** BGE-M3 zero-shot (~30ms, 60% accuracy)
3. **LLM (Legacy):** This prompt (~2-10s, highest accuracy)
4. **Rule-based (Final Fallback):** Regex patterns (~0ms)

---

## 3. Entity & Relationship Extraction

**File:** `src/prompts/extraction_prompts.py`

### 3.1 ENTITY_EXTRACTION_PROMPT

**Purpose:** Extract named entities with types and descriptions
**Language:** English
**Sprint:** 5 (Feature 5.3), 13 (llama3.2 optimization)

**Used By:**
- `src/components/graph_rag/entity_extractor.py`
- **DEPRECATED:** Replaced by domain-specific prompts in Sprint 45+

**Entity Types:**
- PERSON, ORGANIZATION, LOCATION, CONCEPT, TECHNOLOGY, PRODUCT, EVENT

**Few-Shot Examples:** 3 examples included (John Smith, Python, Microsoft)

**Output Format:** JSON array
```json
[
  {"name": "Entity Name", "type": "ENTITY_TYPE", "description": "One sentence"}
]
```

**Template Variables:**
- `{text}` - Text chunk to extract entities from

**Critical Instructions:**
- Return ONLY valid JSON array
- No markdown code fences
- No explanatory text
- Extract 3-5 entities minimum

---

### 3.2 RELATIONSHIP_EXTRACTION_PROMPT

**Purpose:** Extract relationships between pre-identified entities
**Language:** English
**Sprint:** 5, 13

**Used By:**
- `src/components/graph_rag/relation_extractor.py`
- **DEPRECATED:** Replaced by domain-specific prompts

**Relationship Types:**
- WORKS_AT, KNOWS, LOCATED_IN, CREATED, USES, PART_OF, MANAGES, WORKS_ON

**Few-Shot Examples:** 2 examples (John Smith → Google, Guido van Rossum → Python)

**Output Format:** JSON array
```json
[
  {"source": "Entity1", "target": "Entity2", "type": "REL_TYPE", "description": "..."}
]
```

**Template Variables:**
- `{text}` - Text chunk
- `{entities}` - Previously extracted entities (list)

---

### 3.3 GENERIC_ENTITY_EXTRACTION_PROMPT

**Purpose:** Fallback entity extraction for unknown domains
**Language:** English
**Sprint:** 45 (Feature 45.8)

**Used By:**
- `src/components/graph_rag/entity_extractor.py` (when no domain-specific prompt available)

**Key Differences from 3.1:**
- No predefined entity types (flexible categorization)
- Uses natural language types (e.g., "Software Framework" instead of TECHNOLOGY)
- Simplified output format

**Template Variables:**
- `{text}` - Text chunk to extract from

---

### 3.4 GENERIC_RELATION_EXTRACTION_PROMPT

**Purpose:** Fallback relationship extraction for unknown domains
**Language:** English
**Sprint:** 45 (Feature 45.8)

**Used By:**
- `src/components/graph_rag/relation_extractor.py` (fallback)

**Output Format:** Subject-Predicate-Object triples
```json
[{"subject": "Entity1", "predicate": "relationship description", "object": "Entity2"}]
```

**Template Variables:**
- `{text}` - Text chunk
- `{entities}` - Previously extracted entities

---

## 4. Graph RAG Prompts

### 4.1 SYSTEM_PROMPT_RELATION & USER_PROMPT_TEMPLATE_RELATION

**File:** `src/components/graph_rag/relation_extractor.py`
**Purpose:** LightRAG-style relationship extraction
**Language:** English
**Sprint:** 13+

**Used By:**
- `src/components/graph_rag/relation_extractor.py` → `extract_relations()`

**System Prompt:**
```
---Role---
You are a helpful assistant that extracts up to {max_gleanings} relationships
from text to build a knowledge graph.
```

**User Prompt Template:**
```
---Task---
Given a text, extract relationships between entities.
Return valid JSON array with source, target, type, description.
```

**Template Variables:**
- `{max_gleanings}` - Maximum number of relationships to extract
- `{text}` - Text chunk
- `{entity_types}` - List of entity types to focus on

**Output Format:** JSON array of relationships

---

### 4.2 ENTITY_PROMPT & RELATION_PROMPT (Parallel Extractor)

**File:** `src/components/graph_rag/parallel_extractor.py`
**Purpose:** Parallel entity and relation extraction (performance optimization)
**Language:** English
**Sprint:** 13+

**Used By:**
- `src/components/graph_rag/parallel_extractor.py` → `extract_parallel()`

**ENTITY_PROMPT:**
```
Extract all named entities from the following text. Return ONLY a valid JSON array.

Format: [{"name": "...", "type": "...", "description": "..."}]
```

**RELATION_PROMPT:**
```
Extract relationships between entities from the text. Return ONLY a valid JSON array.

Format: [{"source": "...", "target": "...", "type": "...", "description": "..."}]
```

**Template Variables:**
- `{text}` - Text chunk to process

**Key Feature:** Both prompts run in parallel via `asyncio.gather()` for speed

---

### 4.3 DEFAULT_SUMMARY_PROMPT (Community Summarizer)

**File:** `src/components/graph_rag/community_summarizer.py`
**Purpose:** Generate summaries of entity communities in knowledge graph
**Language:** English
**Sprint:** 52 (TD-058)

**Used By:**
- `src/components/graph_rag/community_summarizer.py` → `summarize_community()`

**Prompt Structure:**
```
You are analyzing a community of related entities in a knowledge graph.

Entities:
{entities}

Relationships:
{relationships}

Generate a concise summary (2-3 sentences) describing:
1. Main theme/topic of this community
2. Key entities and their roles
3. Significance/connections
```

**Template Variables:**
- `{entities}` - List of entities in community
- `{relationships}` - List of relationships in community

**Output Format:** Free-form text summary (2-3 sentences)

---

### 4.4 UNIFIED_EXTRACTION_PROMPT (Benchmark)

**File:** `src/components/graph_rag/extraction_benchmark.py`
**Purpose:** Benchmark prompt for combined entity + relation extraction
**Language:** English
**Sprint:** 13+ (benchmarking only)

**Used By:**
- Benchmarking scripts only (not in production)

**Prompt Structure:**
```
---Role---
You are a knowledge graph builder extracting entities and relationships.

---Goal---
Extract entities and relationships to build a comprehensive knowledge graph.
```

**Output Format:** JSON with both entities and relationships
```json
{
  "entities": [...],
  "relationships": [...]
}
```

---

## 5. Query Processing

### 5.1 CLASSIFICATION_PROMPT (Query Decomposition)

**File:** `src/components/retrieval/query_decomposition.py`
**Purpose:** Classify queries as SIMPLE or COMPLEX for decomposition
**Language:** English
**Sprint:** Unknown (early)

**Used By:**
- `src/components/retrieval/query_decomposition.py` → `decompose_query()`

**Query Types:**
1. **SIMPLE** - Single-facet questions (no decomposition needed)
2. **COMPLEX** - Multi-facet questions (decompose into sub-queries)

**Template Variables:**
- `{query}` - User query to classify

**Output Format:** Single word (SIMPLE/COMPLEX)

---

### 5.2 DECOMPOSITION_PROMPT (Query Decomposition)

**File:** `src/components/retrieval/query_decomposition.py`
**Purpose:** Break down complex queries into simpler sub-queries
**Language:** English
**Sprint:** Unknown (early)

**Used By:**
- `src/components/retrieval/query_decomposition.py` → `decompose_query()`

**Prompt Structure:**
```
Break down this complex query into simpler sub-queries.

Original: {query}

Output ONLY a JSON array of sub-query strings:
["sub-query 1", "sub-query 2", ...]
```

**Template Variables:**
- `{query}` - Complex query to decompose

**Output Format:** JSON array of strings
```json
["What is RAG?", "How does RAG integrate with vector databases?"]
```

---

### 5.3 GRAPH_INTENT_PROMPT (Query Rewriter V2)

**File:** `src/components/retrieval/query_rewriter_v2.py`
**Purpose:** Extract graph reasoning intents and rewrite query for graph search
**Language:** English
**Sprint:** 67+ (Query Rewriter V2)

**Used By:**
- `src/components/retrieval/query_rewriter_v2.py` → `rewrite_for_graph()`

**Prompt Structure:**
```
Analyze the query and extract graph reasoning intents.

Query: {query}

Identify:
1. Target entities to search for
2. Relationship types to explore
3. Graph traversal patterns needed
```

**Template Variables:**
- `{query}` - Original user query

**Output Format:** Structured JSON with entities, relationships, patterns

**Integration:** Part of Sprint 67 Adaptation Framework (Feature 67.7)

---

### 5.4 Query Expansion Prompt (Adaptation)

**File:** `src/adaptation/query_rewriter.py` (inline)
**Purpose:** Expand short queries with synonyms and related terms for better retrieval
**Language:** English
**Sprint:** 67 (Adaptation Framework - Feature 67.7)

**Used By:**
- `src/adaptation/query_rewriter.py` → `expand_query()`

**Prompt Structure:**
```
You are a query expansion assistant for hybrid retrieval systems.

Original query: "{query}"
{intent_hint}

Task: Expand this short query with:
- Synonyms and related terms
- Domain-specific keywords
- Common variations

Requirements:
- Keep the expansion concise (max 15 words)
- Focus on retrieval-relevant terms
- Maintain semantic coherence
- Do NOT add punctuation or formatting

Expanded query:
```

**Template Variables:**
- `{query}` - Original short query
- `{intent_hint}` - Optional intent context (e.g., "Intent: factual")

**Output Format:** Expanded query string (15 words max)

**Example:**
- Input: "RAG"
- Output: "RAG retrieval augmented generation vector search knowledge graph"

**Use Case:** Improve retrieval for short/ambiguous queries

---

### 5.5 Query Refinement Prompt (Adaptation)

**File:** `src/adaptation/query_rewriter.py` (inline)
**Purpose:** Refine vague queries to be more specific and actionable
**Language:** English
**Sprint:** 67 (Adaptation Framework - Feature 67.7)

**Used By:**
- `src/adaptation/query_rewriter.py` → `refine_query()`

**Prompt Structure:**
```
You are a query refinement assistant for hybrid retrieval systems.

Original query: "{query}"
{intent_hint}

Task: Refine this vague query to be more specific and actionable:
- Clarify ambiguous terms
- Add context where needed
- Make the intent explicit
- Expand acronyms if relevant

Requirements:
- Keep the refinement concise (max 20 words)
- Maintain the original question type
- Do NOT add punctuation or formatting beyond the question
- Focus on retrieval clarity

Refined query:
```

**Template Variables:**
- `{query}` - Original vague query
- `{intent_hint}` - Optional intent context

**Output Format:** Refined query string (20 words max)

**Example:**
- Input: "how does it work?"
- Output: "How does retrieval augmented generation work in RAG systems?"

**Use Case:** Clarify ambiguous or context-dependent queries

---

## 6. Domain Training

### 6.1 DISCOVERY_PROMPT (Domain Discovery)

**File:** `src/components/domain_training/domain_discovery.py`
**Purpose:** Analyze sample documents and suggest domain name/description
**Language:** English
**Sprint:** 46 (Feature 46.1)

**Used By:**
- `src/components/domain_training/domain_discovery.py` → `discover_domain()`

**Prompt Structure:**
```
Analyze the following sample documents and suggest a domain name and description.

Documents:
{documents}

Suggest:
1. Domain name (1-3 words, technical)
2. Domain description (1 sentence)
3. Key characteristics
```

**Template Variables:**
- `{documents}` - Sample document texts

**Output Format:** JSON
```json
{
  "domain_name": "Healthcare Compliance",
  "description": "Documents about healthcare regulations and HIPAA compliance",
  "characteristics": ["medical terminology", "regulatory language"]
}
```

**Used In:** File-based domain auto-discovery (Sprint 46)

---

### 6.2 AUGMENTATION_PROMPT (Data Augmentation)

**File:** `src/components/domain_training/data_augmentation.py`
**Purpose:** Generate synthetic training data for domain-specific extraction
**Language:** English
**Sprint:** 45+ (DSPy domain training)

**Used By:**
- `src/components/domain_training/data_augmentation.py` → `augment_training_data()`

**Prompt Structure:**
```
You are generating training data for an entity/relation extraction system.

Domain: {domain_name}
Sample Text: {sample_text}

Generate 5 similar examples with entities and relationships annotated.
```

**Template Variables:**
- `{domain_name}` - Target domain (e.g., "Medical Records")
- `{sample_text}` - Example document from domain

**Output Format:** JSON array of training examples
```json
[
  {"text": "...", "entities": [...], "relationships": [...]}
]
```

**Used In:** DSPy-based domain training (Sprint 45 Feature 45.1)

---

## 7. Tool Use & Actions

### 7.1 Tool Detection Prompt (LLM-based Strategy)

**File:** `src/agents/tools/tool_integration.py`
**Purpose:** Decide if external tools are needed based on assistant's response
**Language:** English
**Sprint:** 70 (Feature 70.11)

**Used By:**
- `src/agents/tools/tool_integration.py` → `_should_use_tools_llm()`

**Prompt Structure:**
```python
ChatPromptTemplate.from_messages([
    ("system", """You are a tool usage classifier.

    Tools should be used when:
    - Real-time data is needed (weather, stock prices, current events)
    - Web search would provide better information
    - External APIs need to be called
    - File operations are required
    - The answer indicates uncertainty that external data could resolve

    Tools should NOT be used when:
    - The answer can be given from existing context
    - The question is conversational or opinion-based
    - The information is general knowledge
    - The assistant is providing a complete answer

    Be conservative - only use tools when truly necessary."""),

    ("user", """Question: {question}

    Assistant's Response: {answer}

    Does this response require external tool use? Provide your decision.""")
])
```

**Template Variables:**
- `{question}` - Original user question
- `{answer}` - Assistant's generated answer

**Output Format:** Structured Pydantic model
```python
class ToolDecision(BaseModel):
    use_tools: bool
    reasoning: str
    tool_type: str | None  # "search", "fetch", "compute", etc.
    query: str | None
```

**Detection Strategies (Sprint 70):**
1. **markers** - Fast marker-based (~0ms) - checks for [TOOL:], [SEARCH:], [FETCH:]
2. **llm** - This prompt (~50-200ms) - intelligent decision
3. **hybrid** - Markers first, LLM fallback (0-200ms)

**Configuration:** Admin UI (`/admin/tools/config`) - see TD-080

---

## 8. Follow-up Generation

### 8.1 Follow-up Questions Prompt

**File:** `src/agents/followup_generator.py` (inline)
**Purpose:** Generate 3-5 insightful follow-up questions based on Q&A exchange
**Language:** English
**Sprint:** 35 (Feature 35.8), 52 (Async improvement)

**Used By:**
- `src/agents/followup_generator.py` → `generate_followup_questions()`

**Prompt Structure:**
```
Based on this Q&A exchange, suggest 3-5 insightful follow-up questions.

Original Question: {query_short}

Answer: {answer_short}

Available Context:
{source_context}

Generate questions that:
1. Explore related topics mentioned in the answer
2. Request clarification on complex points
3. Go deeper into specific details
4. Connect to broader context

Output ONLY a JSON array of question strings (no other text):
["question1", "question2", "question3"]
```

**Template Variables:**
- `{query_short}` - Original query (truncated to 200 chars)
- `{answer_short}` - Generated answer (truncated to 500 chars)
- `{source_context}` - Retrieved sources (optional, first 300 chars)

**Output Format:** JSON array of strings
```json
["What are the main challenges in implementing RAG?",
 "How does RAG compare to traditional search systems?",
 "Can you explain the role of vector databases in more detail?"]
```

**LLM Configuration:**
- Uses `LLMTask` with `QualityRequirement.MEDIUM`
- `Complexity.LOW` (simple task)
- Max tokens: 512

---

## 9. Research & Multi-Turn Prompts

### 9.1 Research Planning Prompt

**File:** `src/agents/research/planner.py` (inline)
**Purpose:** Generate 3-5 research queries to answer complex questions
**Language:** English
**Sprint:** 70 (Deep Research)

**Used By:**
- `src/agents/research/planner.py` → `create_plan()`

**Prompt Structure:**
```
Create a research plan to answer this question: "{query}"

Generate 3-5 specific search queries that will help find information to answer this question.
Each query should focus on a different aspect or approach.

Format your response as a numbered list:
1. [First search query]
2. [Second search query]
3. [Third search query]
etc.

Research plan:
```

**Template Variables:**
- `{query}` - User's research question

**Output Format:** Numbered list of search queries

**Example:**
- Input: "What are the latest developments in RAG?"
- Output:
  ```
  1. Recent RAG research papers 2024
  2. RAG performance improvements vector search
  3. RAG integration with knowledge graphs
  4. RAG production deployment best practices
  ```

**Integration:** Part of multi-step research workflow (Sprint 70)

---

### 9.2 Query Enhancement Prompt (Multi-Turn)

**File:** `src/agents/multi_turn/nodes.py` (inline)
**Purpose:** Enhance queries with conversation context for follow-ups
**Language:** English
**Sprint:** Multi-turn conversation support

**Used By:**
- `src/agents/multi_turn/nodes.py` → `prepare_context_node()`

**Prompt Structure:**
```
You are a helpful assistant that enhances user queries with conversation context.

Given the following conversation history and current query, generate an enhanced query that:
1. Incorporates relevant context from previous turns
2. Makes implicit references explicit
3. Preserves the user's intent
4. Is standalone and doesn't require conversation history to understand

Conversation History:
{conversation_context}

Current Query: {current_query}

Enhanced Query (single line, no explanation):
```

**Template Variables:**
- `{conversation_context}` - Previous Q&A turns
- `{current_query}` - Current follow-up query

**Output Format:** Single-line enhanced query

**Example:**
- History: "Q: What is RAG? A: RAG combines retrieval and generation..."
- Current: "How does it work?"
- Enhanced: "How does retrieval augmented generation work in practice?"

---

### 9.3 Contradiction Detection Prompt

**File:** `src/agents/multi_turn/nodes.py` (inline)
**Purpose:** Detect contradictions between current and previous information
**Language:** English
**Sprint:** Multi-turn conversation support

**Used By:**
- `src/agents/multi_turn/nodes.py` → `detect_contradictions()`

**Prompt Structure:**
```
You are an expert at detecting contradictions in information.

Compare the current information with previous answers and identify any contradictions.

Current Information:
{current_info}

Previous Answers:
{previous_answers}

If there are contradictions, list them in this format:
- Contradiction 1: [description]
- Contradiction 2: [description]

If no contradictions, respond with: "No contradictions found."
```

**Template Variables:**
- `{current_info}` - Current retrieval results/answer
- `{previous_answers}` - Previous conversation answers

**Output Format:** List of contradictions or "No contradictions found."

**Use Case:** Maintain consistency across multi-turn conversations

---

## 10. Utility & Supporting Prompts

### 10.1 Title Generation Prompt

**File:** `src/api/v1/title_generator.py` (inline)
**Purpose:** Generate concise 3-5 word conversation titles
**Language:** English
**Sprint:** 35 (Feature 35.4)

**Used By:**
- `src/api/v1/title_generator.py` → `generate_conversation_title()`

**Prompt Structure:**
```
Generate a concise title ({max_length} words max) for this conversation.
The title should capture the main topic being discussed.
Do NOT use quotes around the title.
Do NOT include phrases like "Discussion about" or "Question regarding".
Just output the title, nothing else.

User Question: {query_short}
Assistant Answer: {answer_short}

Title:
```

**Template Variables:**
- `{max_length}` - Maximum words (default: 5)
- `{query_short}` - First question (truncated to 200 chars)
- `{answer_short}` - First answer (truncated to 300 chars)

**Output Format:** Short title string (3-5 words)

**Examples:**
- "Retrieval Augmented Generation Explained"
- "Vector Database Comparison Guide"
- "Neo4j Knowledge Graph Setup"

**LLM Configuration:**
- Model: nemotron-3-nano (Sprint 51)
- Complexity: LOW
- Quality: LOW
- Max tokens: 20
- Temperature: 0.3

---

### 10.2 Community Labeling Prompt

**File:** `src/components/graph_rag/community_labeler.py` (inline)
**Purpose:** Generate concise labels for entity communities in knowledge graph
**Language:** English
**Sprint:** 6 (Feature 6.3), 25 (AegisLLMProxy migration)

**Used By:**
- `src/components/graph_rag/community_labeler.py` → `generate_label()`

**Prompt Structure:**
```
You are labeling a community of related entities in a knowledge graph.

Community members ({num_entities} total, showing first {num_shown}):
{entity_list}

Generate a concise label (2-5 words) that captures the main theme or topic.
Examples: "Machine Learning Research", "European Politics", "Software Engineering"

Return ONLY the label, nothing else. No explanation, no quotes, just the label.

Label:
```

**Template Variables:**
- `{num_entities}` - Total entities in community
- `{num_shown}` - Number shown in prompt
- `{entity_list}` - Formatted list of entity names and types

**Output Format:** Short label string (2-5 words)

**Examples:**
- "Python Programming Ecosystem"
- "Cloud Infrastructure Tools"
- "Healthcare Data Standards"

**LLM Configuration:**
- Task type: SUMMARIZATION
- Uses AegisLLMProxy for multi-cloud routing

---

### 10.3 VLM Image Description Prompt

**File:** `src/components/ingestion/image_processor.py` (inline)
**Purpose:** Generate descriptions for images/diagrams in documents using Vision-Language Model
**Language:** English
**Sprint:** 23 (VLM Integration)

**Used By:**
- `src/components/ingestion/image_processor.py` → `generate_description_cloud_vlm()`

**Default Prompt:**
```
Describe this image from a document in detail, including any text,
diagrams, charts, or important visual elements.
```

**Template Variables:**
- Custom prompt can be provided via `prompt_template` parameter

**Output Format:** Free-form descriptive text

**VLM Model:**
- Primary: qwen3-vl-30b-a3b-instruct (DashScope)
- Fallback: qwen3-vl-30b-a3b-thinking (on 403 errors)

**Use Case:** Extract textual descriptions from images during document ingestion

**Best Practices (Sprint 23):**
- Keep prompts simple and direct for Qwen3-VL
- Low-resolution mode (2,560 tokens) sufficient for most documents
- Default prompt works well for technical documents

---

### 10.4 Graph RAG Answer Generation Prompt

**File:** `src/components/retrieval/graph_rag_retriever.py` (inline)
**Purpose:** Generate answers using context from graph retrieval (entities + relationships + documents)
**Language:** English
**Sprint:** Graph RAG Integration

**Used By:**
- `src/components/retrieval/graph_rag_retriever.py` → `query_with_answer()`

**Prompt Structure:**
```
Answer the following question using the provided context.

Question: {query}

Context:
{context_str}

Instructions:
- Answer the question directly and concisely
- Use information from entities, relationships, and documents
- If the context doesn't contain enough information, say so
- Cite sources when possible

Answer:
```

**Template Variables:**
- `{query}` - User question
- `{context_str}` - Formatted context from graph (entities, relations, docs)

**Output Format:** Concise answer with optional source citations

**LLM Configuration:**
- Task type: ANSWER_GENERATION
- Quality: MEDIUM
- Complexity: MEDIUM
- Max tokens: 512
- Temperature: 0.3

**Integration:** Part of dual-level graph retrieval (local + global search)

---

## 11. Prompt Design Principles

### 11.1 Language Strategy

| Use Case | Language | Reason |
|----------|----------|--------|
| Answer Generation | **German** | Nemotron-3 optimization (Sprint 52) |
| Extraction | **English** | Better JSON reliability, domain-agnostic |
| Routing/Classification | **English** | Technical domain, model training bias |
| Follow-ups | **English** | JSON output reliability |

**Bilingual Considerations:**
- Intent Classifier descriptions include German phrases (Sprint 52)
- Answer prompts use German for Nemotron compatibility (Sprint 52)
- Extraction stays English for structured output reliability (Sprint 13)

---

### 9.2 Anti-Hallucination Strategies

**Sprint 71 (TD-080):** All answer generation prompts now include:

1. **Explicit Constraints:**
   - "Antworte NUR basierend auf den bereitgestellten Dokumenten"
   - "Nutze KEIN externes Wissen aus deinem Training"

2. **Rejection Instruction:**
   - "Wenn die Dokumente die Frage nicht beantworten können, antworte: 'Diese Information ist nicht in der Wissensdatenbank verfügbar.'"

3. **Prohibition:**
   - "Erfinde KEINE Informationen"

**Effectiveness:** ~60-70% reduction in hallucinations (estimated)

**Future Work (TD-080):**
- Phase 2: Evaluation (Sprint 72)
- Phase 3: Embedding-based relevance check or LLM guard (Sprint 73+)

---

### 9.3 JSON Output Reliability

**Problem:** LLMs often add explanatory text or markdown around JSON

**Solution Patterns:**

1. **Explicit Instructions (Extraction Prompts):**
```
CRITICAL OUTPUT INSTRUCTIONS:
- You MUST return ONLY a valid JSON array
- Do NOT include any explanatory text before the JSON array
- Do NOT include any explanatory text after the JSON array
- Do NOT use markdown code fences (no ``` or ```json)
- Do NOT say "Here are the entities" or similar phrases
- Just output the raw JSON array starting with [ and ending with ]
```

2. **Few-Shot Examples (Sprint 13):**
   - Show exact JSON format in 2-3 examples
   - Use double braces `{{}}` in f-strings to prevent Python interpolation

3. **JSON Parsing Fallback:**
   - Strip markdown code fences in parsing logic
   - Use regex to extract JSON from mixed text
   - Log warnings when cleanup is needed

**Success Rate:** ~95% with extraction prompts (Sprint 13 optimization)

---

### 9.4 Model-Specific Optimizations

#### Nemotron-3 Nano (Sprint 52)

**Optimizations:**
- Simplified German prompts (removed complex multi-step instructions)
- Shorter constraint lists (4-5 bullets max)
- Concrete examples over abstract rules
- Inline instructions vs. separate sections

**Files Affected:**
- `src/prompts/answer_prompts.py` - All 3 prompts

#### llama3.2:3b (Sprint 13)

**Optimizations:**
- Added "CRITICAL OUTPUT INSTRUCTIONS" section (all-caps emphasis)
- Increased few-shot examples from 1 to 3
- Explicit JSON format template
- "Extract at least 3-5 entities" threshold

**Files Affected:**
- `src/prompts/extraction_prompts.py` - ENTITY_EXTRACTION_PROMPT

---

### 9.5 Prompt Versioning Strategy

**Sprint Tracking:**
- Each prompt includes docstring with Sprint number
- Major changes increment version comment
- Example: "Sprint 11 (Feature 11.1), 52 (Nemotron), 71 (Anti-hallucination)"

**Migration Path:**
1. Old prompt deprecated but kept as `*_PROMPT_V1`
2. New prompt becomes `*_PROMPT` (default)
3. Feature flag controls which version is used
4. After 2 sprints, old version removed if stable

**Example (Query Rewriter):**
- `GRAPH_INTENT_PROMPT_V1` (Sprint 42) - Removed in Sprint 67
- `GRAPH_INTENT_PROMPT` (Sprint 67) - Current version with adaptation support

---

### 9.6 Template Variable Naming

**Conventions:**
- `{query}` - User's original question (never `{question}` or `{user_query}`)
- `{text}` - Document text to process (extraction prompts)
- `{context}` - Retrieved contexts (singular, formatted)
- `{contexts}` - Multiple contexts (plural, for multi-hop)
- `{entities}` - Previously extracted entities (list format)

**Rationale:** Consistency across all prompts for easier maintenance

---

### 9.7 Few-Shot Learning Patterns

**When to Use:**
- **Structured Output:** Always use 2-3 examples (entities, relations, JSON)
- **Classification:** Optional (intent types have descriptions instead)
- **Free-form Generation:** Rarely (constrains creativity)

**Example Structure:**
```
Few-shot examples:

Example 1:
Input: [concrete example]
Output: [exact expected format]

Example 2:
Input: [different scenario]
Output: [exact expected format]

Now process this input:
Input: {variable}
Output:
```

**Files Using Few-Shot:**
- `extraction_prompts.py` - ENTITY_EXTRACTION_PROMPT (3 examples)
- `extraction_prompts.py` - RELATIONSHIP_EXTRACTION_PROMPT (2 examples)
- `router_prompts.py` - CLASSIFICATION_PROMPT (5 examples)

---

## 12. Prompt Usage Map

### Answer Generation Flow

```
User Query
    ↓
Intent Classifier (SetFit/Embedding/LLM)
    ↓
4-Way Hybrid RRF Retrieval
    ↓
Context Ranking & Fusion
    ↓
Answer Generator
    ├→ ANSWER_GENERATION_PROMPT (simple)
    ├→ MULTI_HOP_REASONING_PROMPT (complex)
    └→ ANSWER_GENERATION_WITH_CITATIONS_PROMPT (with sources)
    ↓
Follow-up Generator
    └→ Follow-up Questions Prompt
```

---

### Extraction Flow

```
Document Upload
    ↓
Docling Parser (CUDA)
    ↓
Section-Aware Chunker
    ↓
Domain Detection
    ├→ DISCOVERY_PROMPT (if new domain)
    └→ Load domain-specific prompts
    ↓
Entity Extraction
    ├→ Domain-specific prompt (if available)
    └→ GENERIC_ENTITY_EXTRACTION_PROMPT (fallback)
    ↓
Relation Extraction
    ├→ Domain-specific prompt (if available)
    └→ GENERIC_RELATION_EXTRACTION_PROMPT (fallback)
    ↓
Graph Storage (Neo4j)
```

---

### Tool Use Flow (Sprint 70)

```
User Query
    ↓
Answer Generator → Initial Answer
    ↓
Tool Detection Router (should_use_tools)
    ├→ Markers Strategy (~0ms)
    │   └→ Check for [TOOL:], [SEARCH:], [FETCH:]
    ├→ LLM Strategy (~50-200ms)
    │   └→ Tool Detection Prompt → ToolDecision
    └→ Hybrid Strategy (0-200ms)
        ├→ Fast Path: Check markers first
        └→ Slow Path: Check action hints → LLM
    ↓
If tools needed:
    └→ tools_node → ActionAgent → MCP Tool Execution
        ↓
    Re-generate answer with tool results
```

---

## 13. Performance Benchmarks

| Prompt Type | Model | Latency (P95) | Success Rate | Notes |
|-------------|-------|---------------|--------------|-------|
| Answer Generation | Nemotron-3 Nano | ~800ms | 95% | Sprint 52 optimization |
| Entity Extraction | llama3.2:3b | ~1.2s | 95% | Sprint 13 JSON fixes |
| Intent Classification (LLM) | Nemotron-3 Nano | ~400ms | 78% | **Deprecated** (SetFit is primary) |
| Intent Classification (SetFit) | SetFit BGE | ~30ms | 89.5% | Sprint 67 C-LARA |
| Follow-up Generation | Nemotron-3 Nano | ~500ms | 92% | Sprint 52 |
| Tool Detection (Markers) | N/A | <1ms | ~70% | Sprint 70 |
| Tool Detection (LLM) | Nemotron-3 Nano | ~150ms | ~90% | Sprint 70 |

**Key Insights:**
- SetFit replaced LLM for intent (26x faster, 89.5% accuracy)
- Marker-based tool detection is fastest but less reliable
- German prompts perform better with Nemotron-3 (Sprint 52 finding)

---

## 14. Prompt Maintenance Checklist

When adding/modifying a prompt:

- [ ] Add Sprint number and feature ID to docstring
- [ ] Include template variable documentation
- [ ] Provide 2-3 few-shot examples (if structured output)
- [ ] Add to this documentation under appropriate section
- [ ] Update usage map if new flow
- [ ] Test with target LLM model (llama3.2, Nemotron-3, etc.)
- [ ] Measure latency and success rate
- [ ] Add unit tests in `tests/unit/prompts/`
- [ ] Consider anti-hallucination constraints (TD-080)
- [ ] Document language choice (English vs. German)

---

## 15. Future Improvements

### TD-080: Context Relevance Guard

**Status:** Phase 1 Complete (Prompt Hardening)
**Next:** Phase 2 Evaluation (Sprint 72)

**Potential Additions:**
1. **Pre-check Prompt:** Validate if contexts can answer query
2. **Confidence Scoring:** LLM returns confidence in addition to answer
3. **Hybrid Strategy:** Embedding score + prompt constraints

---

### Prompt Optimization Opportunities

1. **Compression:** Use prompt compression techniques for long contexts (Sprint 72+)
2. **Chain-of-Thought:** Add CoT for complex reasoning queries (research mode)
3. **Self-Consistency:** Generate multiple answers and vote (accuracy improvement)
4. **Dynamic Examples:** Select few-shot examples based on query similarity
5. **Multilingual Support:** Extend German prompts to support French, Spanish

---

## 16. Related Documentation

- **Architecture:** [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- **Tech Stack:** [docs/TECH_STACK.md](TECH_STACK.md)
- **Conventions:** [docs/CONVENTIONS.md](CONVENTIONS.md)
- **TD-080:** [docs/technical-debt/TD-080_CONTEXT_RELEVANCE_GUARD.md](technical-debt/TD-080_CONTEXT_RELEVANCE_GUARD.md)
- **ADR-033:** AegisLLMProxy Multi-Cloud Routing
- **ADR-039:** Section-Aware Chunking Strategy

---

**Document Maintained By:** Claude Code (claude-sonnet-4-5)
**Last Review:** 2026-01-02 (Sprint 71)
