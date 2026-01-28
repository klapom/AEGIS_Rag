---
name: fact_check
version: 1.0.0
description: Fact verification and claim validation against trusted sources
author: AegisRAG Team
triggers:
  - verify
  - fact check
  - is it true
  - confirm
  - validate claim
dependencies: []
permissions:
  - read_documents
  - web_access
  - invoke_llm
resources:
  prompts: prompts/
---

# Fact Check Skill

## Overview

The Fact Check Skill provides claim verification capabilities by cross-referencing statements against trusted sources, knowledge graph entities, and retrieved documents. It decomposes complex claims into verifiable sub-claims and assigns confidence scores.

## Capabilities

- **Claim Decomposition**: Break complex statements into individually verifiable sub-claims
- **Source Verification**: Cross-reference claims against retrieved documents and knowledge graph
- **Confidence Scoring**: Assign verification scores (supported, refuted, insufficient evidence)
- **Evidence Linking**: Connect verification results to specific source passages
- **Bilingual Support**: Handle DE/EN verification queries ("stimmt das", "ist das korrekt")

## When to Activate

This skill is triggered when queries contain:
- Verification intent: "is it true", "verify", "fact check", "stimmt das"
- Claim keywords: "claims that", "according to", "supposedly"
- Contradiction detection: "but I read", "conflicting information"

## Integration

- **RAG Verification**: Uses retrieval skill to find supporting/contradicting evidence
- **Knowledge Graph**: Cross-references entities and relationships in Neo4j
- **LLM Reasoning**: Chain-of-thought verification with source attribution
- **Hallucination Monitor**: Works with hallucination_monitor skill for quality assurance

## Limitations

- Cannot verify claims about events after knowledge cutoff
- Confidence depends on coverage of the document corpus
- Nuanced claims may receive "insufficient evidence" rather than definitive verdicts
