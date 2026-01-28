---
name: comparison
version: 1.0.0
description: Structured comparison and contrast analysis of entities, concepts, or documents
author: AegisRAG Team
triggers:
  - compare
  - versus
  - difference between
  - pros and cons
  - similarities
dependencies: []
permissions:
  - read_documents
  - invoke_llm
resources:
  prompts: prompts/
---

# Comparison Skill

## Overview

The Comparison Skill provides structured comparison capabilities for analyzing similarities and differences between entities, concepts, technologies, or documents. It generates comparison matrices, pros/cons analyses, and decision frameworks.

## Capabilities

- **Entity Comparison**: Compare two or more entities across defined dimensions
- **Feature Matrix**: Generate structured comparison tables with ratings
- **Pros/Cons Analysis**: Balanced analysis of advantages and disadvantages
- **Similarity Scoring**: Quantify similarity between compared items
- **Decision Support**: Weighted scoring for decision-making scenarios
- **Bilingual Support**: Handle DE/EN comparison queries ("vergleiche", "Unterschied")

## When to Activate

This skill is triggered when queries contain:
- Comparison keywords: "compare", "versus", "vs", "difference between", "vergleiche"
- Contrast intent: "pros and cons", "advantages", "better than", "Vor- und Nachteile"
- Decision queries: "which should I use", "what's the difference", "was ist besser"

## Integration

- **Retrieval Skill**: Fetches relevant information about compared entities
- **Knowledge Graph**: Uses entity relationships for structured comparison
- **LLM Reasoning**: Chain-of-thought analysis for nuanced comparisons

## Limitations

- Comparison quality depends on available information about each entity
- Subjective comparisons include disclaimer about perspective
- Maximum 5 entities in a single comparison for readability
