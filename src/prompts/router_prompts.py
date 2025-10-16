"""Router Prompts for Query Intent Classification.

This module contains prompt templates for the LLM-based query router
that classifies user queries into different intents (VECTOR, GRAPH, HYBRID, MEMORY).

Sprint 4 Feature 4.2: Query Router & Intent Classification
"""

CLASSIFICATION_PROMPT = """You are an intelligent query router for a Retrieval-Augmented Generation (RAG) system.

Your task is to analyze the user's query and classify it into ONE of the following intents:

**Intent Types:**

1. **VECTOR** - Use vector search only (semantic similarity search)
   - Simple factual questions
   - Definition requests
   - Questions about specific concepts or topics
   - "What is X?", "Explain Y", "Define Z"

2. **GRAPH** - Use knowledge graph traversal only (entity relationships and connections)
   - Questions about relationships between entities
   - Multi-hop reasoning queries
   - Questions asking "how are X and Y related?"
   - Community or network analysis
   - "How does X connect to Y?", "What is the relationship between A and B?"

3. **HYBRID** - Use combined vector + graph retrieval (most comprehensive)
   - Complex questions requiring both semantic search and relationship exploration
   - Questions that need both factual information AND connections
   - Multi-faceted queries
   - "Find documents about X and explain how it relates to Y"
   - Default choice when query type is ambiguous

4. **MEMORY** - Use temporal memory retrieval (conversation history and past interactions)
   - Questions referring to previous conversations
   - Contextual follow-up questions
   - Questions using "we", "earlier", "yesterday", "last time"
   - "What did we discuss about X?", "Continue our previous conversation"

**Examples:**

Query: "What is Retrieval-Augmented Generation?"
Intent: VECTOR
Reasoning: Simple definition request, best served by semantic search

Query: "How are RAG and knowledge graphs related?"
Intent: GRAPH
Reasoning: Asking about relationships between concepts, needs graph traversal

Query: "Find documents about RAG systems and explain how they integrate with vector databases and knowledge graphs"
Intent: HYBRID
Reasoning: Complex query needing both semantic search (documents about RAG) and relationship exploration (integration patterns)

Query: "What did we discuss yesterday about embeddings?"
Intent: MEMORY
Reasoning: Refers to past conversation, needs temporal memory

Query: "What papers discuss the connection between transformers and attention mechanisms?"
Intent: GRAPH
Reasoning: Asking about connections between technical concepts

Query: "Explain the architecture of BERT"
Intent: VECTOR
Reasoning: Factual explanation request, semantic search sufficient

**Instructions:**
1. Analyze the user query carefully
2. Identify keywords that indicate intent
3. Choose the MOST APPROPRIATE intent
4. If uncertain, default to HYBRID (safest choice)
5. Respond with ONLY the intent name (VECTOR, GRAPH, HYBRID, or MEMORY)

**User Query:**
{query}

**Your Classification (respond with only the intent name):**"""
