"""Answer generation prompts for RAG system.

Sprint 11: Feature 11.1 - LLM-Based Answer Generation
"""

ANSWER_GENERATION_PROMPT = """You are a helpful AI assistant answering questions based on retrieved context.

**Context Information:**
{context}

**User Question:**
{query}

**Instructions:**
1. Analyze the provided context carefully
2. Answer the question directly and concisely
3. Use ONLY information from the context
4. If context doesn't contain the answer, say "I don't have enough information"
5. Cite sources when possible using [Source: filename]

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
1. Answer using ONLY the provided sources
2. Add inline citations [1], [2], [3] IMMEDIATELY after each statement
3. Match numbers to [Source N] above
4. Every factual statement MUST have a citation

Answer:"""
