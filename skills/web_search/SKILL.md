---
name: web_search
version: 1.0.0
description: Web search and real-time information retrieval for current events and external knowledge
author: AegisRAG Team
triggers:
  - search web
  - google
  - internet
  - browse
  - latest news
  - current events
dependencies:
  - tavily
  - brave-search
permissions:
  - web_access
  - invoke_llm
resources:
  prompts: prompts/
---

# Web Search Skill

## Overview

The Web Search Skill provides real-time web search capabilities for queries requiring current information beyond the local knowledge base. It integrates with external search APIs to fetch, summarize, and cite web-based sources.

## Capabilities

- **Real-Time Web Search**: Query external search engines for up-to-date information
- **Source Summarization**: Extract and summarize relevant content from web pages
- **Citation Generation**: Provide proper source attribution with URLs
- **Query Reformulation**: Optimize user queries for web search APIs
- **Bilingual Support**: Handle DE/EN queries for web search

## When to Activate

This skill is triggered when queries contain:
- Recency indicators: "latest", "current", "recent", "today", "2026", "aktuell", "neueste"
- Web references: "google", "search web", "internet", "browse", "web suche"
- External knowledge needs beyond the local document corpus

## Integration

- **Search API**: Configurable backend (Tavily, Brave Search, SearXNG)
- **Result Processing**: LLM-powered summarization of search results
- **Hybrid Mode**: Can combine web results with local RAG retrieval for comprehensive answers

## Limitations

- Requires external API keys for search providers
- Rate-limited based on API plan
- Results depend on search provider quality and availability
