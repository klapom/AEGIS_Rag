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
