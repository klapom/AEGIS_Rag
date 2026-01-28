---
name: academic
version: 1.0.0
description: Academic paper search and scholarly research across scientific databases
author: AegisRAG Team
triggers:
  - paper
  - academic
  - scholarly
  - research paper
  - journal
  - citation
  - doi
dependencies:
  - semantic-scholar
  - arxiv
permissions:
  - web_access
  - invoke_llm
resources:
  prompts: prompts/
---

# Academic Skill

## Overview

The Academic Skill provides scholarly research capabilities for queries requiring academic papers, scientific publications, and citation-based knowledge retrieval. It integrates with academic databases to search, summarize, and cite peer-reviewed sources.

## Capabilities

- **Academic Paper Search**: Query Semantic Scholar, arXiv, and CrossRef for scholarly publications
- **Citation Analysis**: Trace citation chains and identify influential papers
- **Abstract Summarization**: Extract and summarize key findings from research papers
- **DOI Resolution**: Resolve DOIs to full paper metadata and abstracts
- **Bilingual Support**: Handle DE/EN academic queries ("Forschungsarbeit", "Publikation")

## When to Activate

This skill is triggered when queries contain:
- Academic keywords: "paper", "study", "research", "journal", "publication", "Forschung"
- Citation references: DOIs, arXiv IDs, author names in academic context
- Scholarly intent: "peer-reviewed", "scientific evidence", "according to studies"

## Integration

- **Search APIs**: Semantic Scholar API, arXiv API, CrossRef
- **Citation Graph**: Build citation networks for related paper discovery
- **RAG Fusion**: Combine academic search results with local document retrieval

## Limitations

- Requires external API access for academic databases
- Full-text access depends on open access availability
- Citation data may have ingestion delays (1-7 days for new publications)
