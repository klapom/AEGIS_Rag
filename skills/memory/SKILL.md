---
name: memory
version: 1.0.0
description: Conversational memory retrieval and context management via Graphiti 3-layer temporal memory
author: AegisRAG Team
triggers:
  - remember
  - recall
  - previous
  - earlier
  - last time
  - you said
dependencies:
  - redis
  - graphiti
permissions:
  - read_memory
  - write_memory
resources:
  prompts: prompts/
---

# Memory Skill

## Overview

The Memory Skill provides conversational memory capabilities using the Graphiti 3-layer temporal memory system backed by Redis. It enables the agent to recall previous conversations, maintain context across sessions, and provide personalized responses based on interaction history.

## Capabilities

- **Short-Term Memory**: Current conversation context and recent messages
- **Episodic Memory**: Past conversation episodes and interaction history
- **Semantic Memory**: Learned facts, preferences, and user-specific knowledge
- **Temporal Queries**: Recall by timeframe ("last week", "yesterday", "letzte Woche")
- **Context Summarization**: Summarize conversation history for prompt efficiency
- **Bilingual Memory**: Store and retrieve memories in DE/EN

## When to Activate

This skill is triggered when queries contain:
- Memory indicators: "remember", "recall", "previous", "earlier", "erinnere", "frueher"
- Temporal references: "last time", "you said", "we discussed", "du sagtest", "letzte mal"
- Context needs: The C-LARA MEMORY intent classification

## Integration

- **Redis Backend**: Fast key-value storage for short-term memory
- **Graphiti**: 3-layer temporal memory (episodic, semantic, procedural)
- **Conversation History**: Maintains sliding window of recent messages
- **Memory Consolidation**: Periodic summarization of old episodes

## Memory Layers

| Layer | Storage | TTL | Purpose |
|-------|---------|-----|---------|
| Short-Term | Redis | Session | Current conversation context |
| Episodic | Graphiti | 30 days | Past conversation episodes |
| Semantic | Graphiti | Permanent | Learned facts and preferences |
