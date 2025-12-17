"""Answer generation prompts for RAG system.

Sprint 11: Feature 11.1 - LLM-Based Answer Generation
"""

ANSWER_GENERATION_PROMPT = """You are a helpful AI assistant answering questions based on retrieved context.

**CRITICAL RULES:**
- ONLY use information EXPLICITLY stated in the context
- If the context does NOT discuss the topic, say: "Die bereitgestellten Dokumente enthalten keine Informationen zu diesem Thema."
- DO NOT invent connections between unrelated content and the question
- DO NOT use general knowledge - ONLY the provided context

**Context Information:**
{context}

**User Question:**
{query}

**Instructions:**
1. First check: Does the context actually discuss the question's topic?
2. If NO relevant information exists, respond: "Die bereitgestellten Dokumente enthalten keine Informationen zu diesem Thema."
3. If YES, answer using ONLY explicitly stated facts
4. Cite sources when possible using [Source: filename]

**Answer:**"""

MULTI_HOP_REASONING_PROMPT = """You are an AI assistant that combines information from multiple sources.

**Retrieved Documents:**
{contexts}

**Question:**
{query}

**Task:**
Connect information across documents to answer the multi-hop question.
Show your reasoning step-by-step.

**Answer:**"""

ANSWER_GENERATION_WITH_CITATIONS_PROMPT = """You are a helpful AI assistant answering questions with inline source citations.

**CRITICAL RULES - READ CAREFULLY:**
- ONLY use information that is EXPLICITLY stated in the source documents
- If the sources do NOT contain information about the topic, say: "Die bereitgestellten Dokumente enthalten keine Informationen zu diesem Thema."
- DO NOT invent connections between unrelated documents and the question
- DO NOT use your general knowledge - ONLY the provided sources
- If sources discuss a different topic than the question, acknowledge this mismatch

**EXAMPLE:**

Source Documents:
[Source 1]: Machine Learning Basics
Machine learning is a subset of artificial intelligence that enables computers to learn from data.

[Source 2]: Deep Learning Overview
Deep learning uses neural networks with many layers to process complex patterns.

Question: What is machine learning and how does it relate to deep learning?
Answer: Machine learning is a subset of artificial intelligence that allows computers to learn from data [1]. Deep learning is a specialized form of machine learning that uses neural networks with multiple layers [2].

---

**YOUR TASK:**

Source Documents:
{contexts}

Question: {query}

Instructions:
1. First check: Do the sources actually discuss the topic in the question?
2. If NO relevant information exists, respond: "Die bereitgestellten Dokumente enthalten keine Informationen zu diesem Thema."
3. If YES, answer using ONLY explicitly stated facts from sources
4. Add inline citations [1], [2], [3] IMMEDIATELY after each statement
5. Match numbers to [Source N] above
6. Every factual statement MUST have a citation from the sources

Answer:"""
