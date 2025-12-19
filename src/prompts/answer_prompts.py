"""Answer generation prompts for RAG system.

Sprint 11: Feature 11.1 - LLM-Based Answer Generation
Sprint 52: Simplified German prompts for better Nemotron compatibility
"""

# Sprint 52: Simplified German prompt for better model compatibility
ANSWER_GENERATION_PROMPT = """Du bist ein hilfreicher KI-Assistent. Beantworte die Frage basierend auf den bereitgestellten Dokumenten.

**Dokumente:**
{context}

**Frage:** {query}

**Antwort:**"""

MULTI_HOP_REASONING_PROMPT = """Du bist ein KI-Assistent, der Informationen aus mehreren Quellen kombiniert.

**Dokumente:**
{contexts}

**Frage:** {query}

Verbinde Informationen aus den Dokumenten, um die Frage zu beantworten.

**Antwort:**"""

# Sprint 52: Simplified German prompt with inline citations
# Removed complex multi-step instructions that confused Nemotron models
ANSWER_GENERATION_WITH_CITATIONS_PROMPT = """Du bist ein hilfreicher KI-Assistent. Beantworte die Frage basierend auf den Quellen und füge Quellenverweise [1], [2], [3] hinzu.

**Quellen:**
{contexts}

**Frage:** {query}

Beantworte die Frage und füge nach jeder Aussage die Quellennummer in eckigen Klammern hinzu, z.B. [1].

**Antwort:**"""
