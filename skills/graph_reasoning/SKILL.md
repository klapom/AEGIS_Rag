---
name: graph_reasoning
version: 1.0.0
description: Knowledge graph traversal and multi-hop entity reasoning via Neo4j and LightRAG
author: AegisRAG Team
triggers:
  - related to
  - connected to
  - relationship
  - entity
  - graph
  - associated with
dependencies:
  - neo4j
  - lightrag
permissions:
  - read_graph
  - invoke_llm
resources:
  prompts: prompts/
---

# Graph Reasoning Skill

## Overview

The Graph Reasoning Skill provides advanced knowledge graph traversal and multi-hop reasoning capabilities using Neo4j and LightRAG. It answers queries about entity relationships, connections, and complex reasoning chains that span multiple knowledge graph hops.

## Capabilities

- **Entity Lookup**: Find entities by name, type, or description in the knowledge graph
- **Relationship Traversal**: Follow typed relationships (RELATES_TO, PART_OF, USES, MENTIONS, CITES)
- **Multi-Hop Reasoning**: Traverse 1-3 hops to discover indirect connections
- **Community Detection**: Leverage graph communities for topic clustering (Sprint 92: 2,387 communities)
- **Comparison Queries**: Compare entities by their graph neighborhood and shared connections
- **Bilingual Entity Matching**: Match entities in DE/EN queries

## When to Activate

This skill is triggered when queries contain:
- Relationship indicators: "related to", "connected to", "associated with", "verbunden mit"
- Entity references: "entities", "relationships", "graph", "Entitaeten", "Beziehungen"
- Comparison patterns: "compare", "contrast", "difference", "versus", "Vergleich"
- Graph-specific intent classification (C-LARA GRAPH/HYBRID intents)

## Integration

- **Neo4j Backend**: Direct Cypher queries for entity/relation lookup
- **LightRAG**: Structured graph reasoning with entity extraction pipeline
- **Hybrid Search**: Combines with vector retrieval for augmented graph results
- **SmartEntityExpander**: Disabled by default (ADR-057) for performance, configurable per-query
