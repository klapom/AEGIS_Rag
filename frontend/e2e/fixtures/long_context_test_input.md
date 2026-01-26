# AegisRAG Long Context Test Fixture
## Comprehensive Technical Documentation (Sprints 90-92, 118-119)

This document compiles key technical information from Sprint planning and architecture documentation for testing long context handling in the AegisRAG system. It covers system design, implementation details, and feature specifications across multiple sprints.

---

## Sprint 90: Skill Registry Foundation

### Executive Summary

Sprint 90 establishes the foundational skill registry infrastructure for the AegisRAG multi-agent system. This sprint implements a local, configurable registry for Agent Skills that enables intelligent capability loading while maintaining context efficiency. The skill registry represents a significant architectural improvement to the agent coordination system.

### Skill Registry Architecture

The Skill Registry is a centralized, configurable system for managing agent capabilities in a local environment. Key characteristics include:

1. **Local-First Design**: All skills are stored and loaded locally without cloud dependencies. This ensures complete control over skill availability and reduces latency for skill lookups.

2. **YAML-Based Metadata**: Skills are defined with YAML metadata that includes name, description, parameters, and execution environment. This structured approach enables automated skill discovery and loading.

3. **Embedding-Based Intent Matching**: Skills are matched to queries using semantic embeddings, enabling the system to identify relevant capabilities without explicit routing rules.

4. **On-Demand Loading**: Skills are loaded dynamically based on query intent and available context budget. This reduces memory footprint and improves inference speed by keeping only active skills in the context window.

5. **Active Skill Instructions**: The system maintains a set of currently active skills and injects their instructions into the LLM context when relevant. This approach enables adaptive behavior based on the current task.

### Performance Implications

Early benchmark testing indicates that the Skill Registry approach provides approximately 30% token savings compared to traditional hardcoded capability definitions. This is achieved by:

- Loading only the subset of skills relevant to each query
- Using efficient embedding-based matching rather than full-text search
- Maintaining lean skill instruction sets (~200-500 tokens per skill)
- Avoiding redundant capability descriptions in system prompts

### Implementation Details

The Skill Registry implementation involves several key components:

1. **SkillRegistry Class**: Central registry that manages all available skills. Provides methods for skill discovery, loading, validation, and caching.

2. **Skill Loading Service**: Responsible for dynamically loading skills based on current context usage and query intent. Implements caching to avoid repeated I/O operations.

3. **Intent-Skill Mapping**: Maintains embeddings for all available skills and matches query intent to skill capabilities using semantic similarity.

4. **Resource Management**: Tracks skill resource requirements (tokens, execution time, dependencies) and makes loading decisions based on available context budget.

### Benefits for Agent System

The Skill Registry enables several important improvements to the multi-agent system:

1. **Scalability**: The system can support hundreds of skills without degrading performance or exceeding context limits.

2. **Flexibility**: New skills can be added without modifying the core agent code. Skills are discovered automatically on system startup.

3. **Efficiency**: By loading only necessary skills, the system reduces token consumption and improves inference latency significantly.

4. **Adaptability**: Skills can be updated independently without full system redeployment. Configuration changes take effect immediately.

### Integration Points

The Skill Registry integrates with several core systems:

1. **LangGraph Coordinator**: Queries the registry to determine available skills before routing to specialized agents.

2. **Memory System**: Uses Redis to cache frequently accessed skills, improving lookup performance.

3. **Embedding Service**: Leverages BGE-M3 embeddings for semantic skill matching.

4. **LLM Integration**: Injects active skill instructions into context when generating responses.

---

## Sprint 91: Recursive LLM Context & Intent Router

### Recursive LLM Context Implementation

Sprint 91 introduces the Recursive LLM Context framework (ADR-051), enabling the system to process documents significantly larger than the model's context window. This breakthrough feature allows handling of research papers, books, and large knowledge bases without truncation.

### The Problem: Context Window Limitations

Traditional RAG systems face a fundamental constraint: documents larger than the model's context window must be truncated, losing information. With Nemotron3 Nano's 4K token context window, documents larger than approximately 3000 tokens are incomplete. The Recursive LLM Context approach solves this by processing documents in hierarchical stages.

### Recursive Processing Strategy

The system implements a multi-level recursive approach:

**Level 0-1: Local Scoring**
- BGE-M3 Dense and Sparse vectors provide initial ranking
- Fast execution (~80ms typical)
- Identifies top-k most relevant segments

**Level 2: Adaptive Expansion**
- Multi-vector ColBERT scoring for fine-grained matching
- Processes full document context in segments
- Enables 10x larger document handling

**Level 3: Deep Dive Analysis**
- Recursive LLM scoring for complex queries
- Multiple passes over document structure
- Maintains hierarchical citation tracking

### Architecture

The Recursive LLM Context architecture follows a hierarchical design:

1. **Segmentation Phase**: Document is divided into logical segments based on structure (sections, subsections, paragraphs).

2. **Scoring Phase**: Each segment receives relevance scores from multiple models (BGE-M3, ColBERT).

3. **Selection Phase**: Most relevant segments are selected for inclusion in context based on query requirements and available budget.

4. **Aggregation Phase**: Selected segments are synthesized into a coherent response with proper citations.

### Performance Characteristics

The recursive approach enables processing of documents up to 10x larger than context window:

- **Input Capacity**: 14,000+ tokens vs 4,000 token context window (3.5x improvement on baseline)
- **Latency**: Average 1.2-1.5 seconds for complete processing including scoring and LLM inference
- **Accuracy**: Maintains high precision through multi-stage scoring

### Intent Router Implementation

Sprint 91 also introduces the C-LARA Intent Router, a specialized classifier that determines how queries should be processed:

**Intent Categories**:

1. **NAVIGATION (Simple Lookup)**: Direct factual questions requiring specific information
   - Example: "What is the model version?"
   - Strategy: Use fast BGE-M3 dense+sparse scoring

2. **PROCEDURAL (How-To)**: Questions about processes or step-by-step instructions
   - Example: "How does the skill registry work?"
   - Strategy: Use LLM-based semantic understanding with full document context

3. **COMPARATIVE (Compare/Contrast)**: Questions requiring multiple pieces of information
   - Example: "Compare Recursive LLM vs traditional truncation"
   - Strategy: Use multi-vector ColBERT scoring with segment selection

4. **EXPLANATORY (Why/Explain)**: Questions seeking deeper understanding
   - Example: "Why does the Skill Registry improve efficiency?"
   - Strategy: Use recursive LLM scoring with hierarchical analysis

### Classification Accuracy

The C-LARA classifier achieves 95.22% accuracy on a diverse test set of 500+ queries, enabling reliable intent-based routing. This accuracy enables the system to choose optimal processing strategies automatically.

---

## Sprint 92: Adaptive Scoring & Deep Research Features

### Adaptive Context Expansion

Sprint 92 implements adaptive context expansion, a mechanism that automatically adjusts how much and what type of context is provided based on query characteristics and available resources.

### Expansion Levels

The system implements a graduated expansion strategy:

**Level 1: Minimal Context (50-200 tokens)**
- Fast response (<100ms)
- Simple factual queries
- Uses only top-1 to top-3 most relevant segments

**Level 2: Standard Context (200-800 tokens)**
- Normal latency (100-500ms)
- Procedural and explanatory queries
- Includes 5-10 relevant segments with connecting information

**Level 3: Full Context (800-2000 tokens)**
- Extended latency (500-2000ms)
- Comparative and complex queries
- Includes complete relevant context with citations and references

### Adaptive Selection Algorithm

The system uses several signals to determine expansion level:

1. **Query Complexity**: Measured by query length, presence of logical operators, and semantic diversity
2. **Available Context Budget**: Remaining tokens in context window after system prompts and instructions
3. **Document Relevance**: If top segments have low relevance scores, expand to find better matches
4. **User Preferences**: Settings allow users to prefer speed or completeness

### Performance Optimization

The adaptive approach achieves significant performance improvements:

- **30% Faster**: Simple queries return in 100-200ms instead of 500ms
- **Memory Efficient**: Unnecessary context segments are excluded, reducing token consumption
- **Quality Maintained**: Complex queries still receive complete context for accurate answers

### Recursive LLM Scoring (ADR-052)

Sprint 92 implements ADR-052, which adds sophisticated recursive LLM-based scoring on top of the vector-based foundation:

**Scoring Method Progression**:

1. **Stage 1 - Vector Retrieval (80ms)**
   - BGE-M3 dense vectors with RRF fusion for multiple modalities
   - Retrieves top-20 candidate chunks

2. **Stage 2 - Fine-Grained Ranking (200-300ms)**
   - ColBERT multi-vector scoring on candidate chunks
   - Re-ranks based on semantic coherence

3. **Stage 3 - LLM Deep Dive (800-1200ms)**
   - LLM explicitly scores chunks for relevance to query
   - Considers context and interdependencies between chunks
   - Applies confidence weighting to final scores

### Citation Tracking

The system maintains hierarchical citation tracking throughout the recursive processing:

- **Source Chunk**: Original document location
- **Segment Path**: Position in document hierarchy (section → subsection → paragraph)
- **Relevance Score**: Confidence of relevance
- **Processing Stage**: Which stage generated the citation (vector, LLM, etc.)

This enables detailed explanations of where answers come from and how confident the system is in each piece of information.

### Community Detection & Graph Clustering

Sprint 92 also refines community detection algorithms using Neo4j Graph Data Science. The system now efficiently detects and clusters related entities:

**Algorithm Improvements**:
- Detects 2,387+ communities in large knowledge graphs
- Uses modularity optimization for meaningful clustering
- Enables community-focused search and summarization

### Graph Communities API

New API endpoints provide programmatic access to community information:

```
POST /api/v1/graph/communities/detect
GET  /api/v1/graph/communities/{id}/members
GET  /api/v1/graph/communities/{id}/summary
POST /api/v1/graph/communities/search
```

These enable building analytical interfaces for exploring community structure in knowledge graphs.

---

## System Architecture Overview

### High-Level Components

The AegisRAG system consists of several integrated components working together:

**Frontend Layer (React 19, TypeScript)**
- SearchResultsPage: Main interface for queries and results
- StreamingAnswer: Real-time response rendering with SSE
- Citation: Inline citation display with source tracking
- FollowUpQuestions: Context-aware follow-up suggestions
- Settings: User preferences and configuration

**API Layer (FastAPI)**
- Health API: System status and diagnostic information
- Retrieval API: Search and document retrieval operations
- Graph Visualization API: Knowledge graph rendering
- Admin API: System configuration and monitoring

**LangGraph Multi-Agent Orchestration**
- Router Agent: Intent classification and routing
- Vector Search Agent: Qdrant hybrid search execution
- Graph Query Agent: Neo4j entity and relationship queries
- Memory Agent: Temporal memory retrieval and consolidation
- Action Agent: Tool execution (bash, python, browser)

**Storage Layer**
- Redis (In-Memory Cache): Session state, follow-up questions, conversation history
- Qdrant (Vector Database): BGE-M3 dense and sparse vectors with RRF fusion
- Neo4j (Graph Database): Entity/relationship graph with temporal versioning
- Ollama (LLM Service): Nemotron3 Nano for local inference

### Data Flow

A typical query follows this flow:

1. User submits query through React frontend
2. Query sent to `/api/v1/chat` endpoint via HTTP POST with SSE stream
3. FastAPI coordinator routes to LangGraph
4. Router Agent classifies intent using C-LARA classifier
5. Specialized agents execute:
   - Vector Agent queries Qdrant using BGE-M3 embeddings
   - Graph Agent queries Neo4j for entity relationships
   - Memory Agent retrieves session context from Redis
6. Results aggregated and re-ranked using recursive LLM scoring
7. Response streamed to frontend as server-sent events
8. Frontend renders answer with citations and follow-up questions

### Performance Characteristics

Key performance metrics for the system:

- **Vector Search (BGE-M3)**: 80-150ms for top-k retrieval
- **Graph Query (N-hop)**: 200-600ms depending on hops
- **Hybrid Combination**: 300-800ms with reranking
- **LLM Generation**: 1500-3000ms for token generation
- **Total Latency**: 2000-4000ms P95 for complete response
- **Context Window**: 4096 tokens (Nemotron3) with adaptive compression

---

## Technical Debt & Future Work

### Identified Improvements

**Performance Optimization**:
- Parallel scoring stages to reduce sequential latency
- GPU-accelerated vector scoring for Qdrant operations
- Caching of embeddings for frequently accessed documents

**Scalability**:
- Horizontal scaling of agent workers
- Distributed Qdrant deployment for large vector collections
- Neo4j clustering for enterprise deployments

**Quality Enhancement**:
- Fine-tuning C-LARA classifier on domain-specific data
- Adding more sophisticated semantic reranking
- Improving entity extraction accuracy

**User Experience**:
- Progressive result streaming with incremental citations
- Explainability UI showing scoring breakdown
- Interactive debugging of agent decisions

---

## Sprint 118: Testing Infrastructure & Quality Assurance

Sprint 118 focuses on establishing comprehensive testing infrastructure to ensure code quality and prevent regressions.

### Visual Regression Testing

Visual regression testing detects unintended UI changes:

- Baseline snapshots of critical UI paths (chat, search, graph)
- Automated diff generation on every PR
- Integration with CI/CD for automatic failure detection
- Allows intentional changes with explicit approval

### Performance Regression Testing

Automated performance tracking prevents latency regressions:

- Baseline latency tracking (p50, p95, p99)
- HAR file recording for network analysis
- Resource utilization monitoring (GPU VRAM, CPU)
- Alerting on >10% degradation from baseline

### Test Coverage Goals

The infrastructure supports comprehensive testing:

- 15+ Visual regression tests covering critical paths
- 8+ Performance tests for latency measurement
- 5+ Graph communities UI tests
- >80% code coverage across all modules

---

## Sprint 119: E2E Test Analysis & Stabilization

Sprint 119 analyzes and fixes failing and skipped E2E tests to improve test reliability.

### Skipped Test Categories

**Graph Versioning (28 tests)**: Features 39.5-39.7 not yet implemented
- Time-travel query API
- Entity changelog viewer
- Version comparison UI

**Domain Training API (31 tests)**: Full API not exposed
- Basic CRUD operations for domains
- Domain classification endpoint
- Training data augmentation

**Performance Regression (15 tests)**: Some metrics endpoints missing
- GPU utilization tracking
- API latency monitoring
- Resource usage metrics

**Citations (7 tests)**: Citation rendering issues
- Some tests pass, others depend on response content
- Missing data-testid attributes fixed

### Bug Fixes Completed

Sprint 118-119 bug fixes improved test reliability:

1. **Follow-up Questions SSE Cache**: Check Redis cache before regenerating (3 SP)
2. **Graph Edge Filter Testids**: Convert underscores to hyphens in selectors (2 SP)
3. **Memory Consolidation Endpoint**: Correct endpoint path from `/consolidate/` to `/consolidation/` (3 SP)
4. **Environment Variable Consistency**: Use `VITE_API_BASE_URL` throughout (1 SP)
5. **Component Integration**: Add FollowUpQuestions to ConversationView (2 SP)
6. **Test Assertions**: Fix message count expectations (1 SP)
7. **Retry Timeouts**: Reduce excessive 60s timeout to 30s (1 SP)
8. **Multi-turn Cache**: Clear old follow-up questions on new query (2 SP)
9. **Page Reload Handling**: Add early exit for non-persistent conversations (2 SP)

### Test Results

After bug fixes:

- **followup.spec.ts**: 9/9 PASS (100%)
- **Citations**: 4/9 PASS (conditional skips based on response content)
- **Graph filters**: Filter visibility tests pass, interaction tests need data

---

## Knowledge Base Content Summary

This fixture file synthesizes technical documentation across multiple sprints covering:

- Skill Registry architecture and 30% token savings
- Recursive LLM Context enabling 10x document size handling
- Multi-level scoring strategy (vector → fine-grained → deep-dive)
- C-LARA Intent Classification at 95.22% accuracy
- Adaptive context expansion across three levels
- Community detection with 2,387+ communities in large graphs
- Testing infrastructure improvements and bug fixes
- Performance optimization and scaling strategies
- Multi-agent orchestration with LangGraph
- Complete storage layer with Redis/Qdrant/Neo4j

---

## Long Context Test Scenarios

This fixture supports testing several important long context scenarios:

1. **Large Document Processing**: Testing handling of 14,000+ token documents
2. **Recursive Scoring Efficiency**: Verifying multi-stage scoring completes in <2s
3. **Context Window Management**: Ensuring adaptive expansion selects appropriate levels
4. **Citation Accuracy**: Validating proper source tracking through deep processing
5. **Performance Under Load**: Confirming latency targets met with large documents
6. **Intent-Based Routing**: Testing correct selection of scoring strategy
7. **Multi-turn Conversation**: Verifying context maintenance across multiple queries
8. **Memory Efficiency**: Confirming token savings from skill registry approach

---

## Extended Technical Details & Implementation Guide

### LangGraph Orchestration in Detail

The LangGraph orchestration layer is responsible for coordinating multiple specialized agents to handle complex queries. The system implements a sophisticated routing mechanism that determines which agents should be invoked based on query intent and available resources.

**Agent Responsibilities**:

The Router Agent performs initial intent classification using the C-LARA classifier. It examines the query to determine which processing strategy will be most effective. For NAVIGATION queries, it routes directly to the Vector Search Agent. For PROCEDURAL queries, it may invoke both Vector and Graph agents. COMPARISON queries trigger special handling that retrieves diverse results from multiple sources. EXPLANATORY queries invoke the Memory Agent to gather conversation context before processing.

The Vector Search Agent handles semantic search operations using BGE-M3 embeddings. It maintains both dense and sparse vector indices for complementary retrieval. When a query arrives, it generates embeddings and performs RRF (Reciprocal Rank Fusion) on dense and sparse results. This approach combines the benefits of dense vector search (semantic understanding) with sparse search (exact term matching). The agent also handles query reformulation for ambiguous or complex queries.

The Graph Query Agent executes entity and relationship lookups in Neo4j. It implements multi-hop path traversal to discover relationships between entities. The agent can handle complex queries requiring 2-3 hops through the knowledge graph. For each hop, it applies relevance filters to avoid explosion of search space. Results are deduplicated and ranked by relevance before returning to the coordinator.

The Memory Agent retrieves session context from Redis and Graphiti. It implements a 3-layer memory system: Redis for recent conversation state, Qdrant vectors for semantic session memory, and Graphiti for longer-term persistent memory. The agent automatically consolidates old messages when conversation length exceeds thresholds. This prevents context window exhaustion while maintaining relevant conversation history.

The Action Agent executes tools like bash, python, and browser commands. It implements sandboxing for security and provides capability constraints to prevent dangerous operations. Tool execution is tracked for explainability and reproducibility.

### BGE-M3 Embedding System Details

The BGE-M3 (BAAI General Embedding, Multilingual, Multi-representation) system is the foundation for semantic search in AegisRAG. It generates three types of representations for each passage:

**Dense Representation**: A 1024-dimensional dense vector capturing semantic meaning. This enables fast approximate nearest neighbor search using vector indices in Qdrant. Dense vectors work well for topic-level matching and are computationally efficient.

**Sparse Representation**: Learned lexical weights for important terms in the passage. This captures exact term matching and rare entity names. Sparse representation enables keyword-based retrieval and handles OOV (out-of-vocabulary) terms better than pure dense methods.

**ColBERT Representation**: Multi-vector representation with one vector per token. This enables fine-grained matching where individual query tokens can match specific tokens in the passage. ColBERT scoring is more expensive computationally but provides superior precision for complex queries.

The system performs RRF (Reciprocal Rank Fusion) to combine rankings from dense and sparse retrieval:

```
RRF Score = 1 / (60 + rank_dense) + 1 / (60 + rank_sparse)
```

This formula gives equal weight to both rankings while giving top results much higher scores. The constant 60 is chosen to penalize tail results less severely.

### Neo4j Graph Operations

The Neo4j graph database stores a knowledge graph of entities and relationships extracted from ingested documents. Entity types include PERSON, ORGANIZATION, LOCATION, CONCEPT, and METHODOLOGY. Relationships include RELATED_TO, MENTIONED_IN, USES, OWNS, and DEPENDS_ON.

The graph extraction pipeline uses a 3-rank LLM cascade:

**Rank 1 - Primary LLM (Nemotron3)**: Attempts entity and relationship extraction using standard prompting. Success rate approximately 85%.

**Rank 2 - Fallback LLM (GPT-OSS via Ollama)**: Used when Nemotron3 fails. Provides higher quality extraction at cost of longer latency. Success rate approximately 95%.

**Rank 3 - Hybrid Approach**: Combines LLM results with SpaCy NER (Named Entity Recognition) for multi-language support (English, German, French, Spanish). Achieves 99%+ entity detection with lower hallucination.

The graph indexing includes several important indices for fast querying:

- Entity name index for fast lookup by name
- Entity type index for filtering by entity class
- Relationship type index for filtering by relationship class
- Community detection index for cluster-based analysis

Community detection runs periodically using Neo4j Graph Data Science algorithms. The modularity optimization algorithm discovers natural clusters of related entities. Current knowledge graphs typically contain 1,000-10,000 entities organized into 50-500 communities depending on document size and diversity.

### Context Window Management Strategy

The system manages the limited context window (4096 tokens for Nemotron3) through several strategies:

**Adaptive Compression**: When context exceeds budget, the system applies progressive compression:
1. Remove stop words and reduce to key terms
2. Summarize long passages to 2-3 sentence summaries
3. Remove lowest relevance results
4. Apply aggressive token truncation as last resort

**Skill Registry Optimization**: Skills are loaded on-demand rather than keeping all instructions in context. This alone saves 20-30% of context tokens.

**Conversation Summarization**: Old messages are automatically summarized and consolidated when conversation exceeds 50 exchanges. The consolidation process uses LLM to extract key facts, decisions, and follow-ups while discarding details.

**Result Ranking**: Only top-3 to top-5 results are included in context depending on availability. This is usually sufficient to answer the query while preserving context space.

The system implements an elaborate scoring system to select which results to include:

- **Relevance Score** (from vector/graph search): How well result matches query intent
- **Freshness Score**: How recently the source document was ingested
- **Authority Score**: How often the result appears in other retrieved results
- **Diversity Score**: Whether result covers unique aspects not in other results

Final selection combines these scores using learned weights from historical interaction data.

### Streaming Response Generation

Responses are generated using server-sent events (SSE) to provide real-time streaming to the frontend. This improves perceived latency and enables progressive rendering of results.

**Streaming Architecture**:

1. Coordinator generates query embedding and launches retrieval in background threads
2. As results arrive, they are immediately sent to client via SSE
3. Reranking happens progressively on each batch of results
4. LLM generation begins as soon as first set of results arrive
5. LLM output is streamed token-by-token to frontend
6. Follow-up questions generated asynchronously after answer completes

This approach achieves time-to-first-token (TTFT) around 300-500ms compared to 2-3 seconds if responses were computed end-to-end before transmission.

### Citation and Explainability System

The citation system tracks exactly where each statement in the answer comes from. Every piece of information includes:

- **Document Reference**: Original document name and location
- **Chunk ID**: Specific chunk within document
- **Relevance Confidence**: Score from 0.0 to 1.0
- **Extraction Method**: Vector search, graph, or hybrid
- **Processing Stage**: Which stage (Level 1-3) generated citation

The citation system supports several display modes:

- **Inline Citations**: [1], [2], [3] as superscripts in answer
- **Hover Details**: Full citation info appears on hover
- **Bibliography**: Complete list of sources at end of answer
- **Citation Map**: Visual diagram showing relationships between citations

For long context processing, the system maintains hierarchical citations showing which document section, subsection, and paragraph each citation comes from. This enables drilling down to exact source location.

### Performance Tuning and Optimization

The system includes several optimization techniques for performance:

**Query Planning**: Complex queries are analyzed and decomposed into sub-queries that can be answered in parallel. For example, "Compare features X and Y across products A and B" becomes four separate queries that run in parallel.

**Result Caching**: Frequently accessed documents are cached at multiple levels:
- Redis cache for recent queries and results (5 minute TTL)
- Qdrant vector index cache in GPU memory
- OS file system cache for frequently accessed documents

**Lazy Loading**: Component rendering is deferred until actually needed. Off-screen results aren't fully processed until user scrolls to view them.

**Token Budgeting**: The system pre-computes token requirements for system prompt, instruction, examples, and results. It allocates remaining context budget to document chunks in priority order.

---

## Comprehensive Test Scenario Documentation

### Scenario 1: Large Research Paper Processing

Test Input: 45,000 token research paper on "Efficient Large Language Model Inference"

**Execution Path**:
1. Document ingested via Docling CUDA parser
2. Section-aware chunking creates 52 chunks (800-1800 tokens each)
3. Chunks embedded using BGE-M3
4. Entities extracted using 3-rank cascade
5. Relationships discovered between entities
6. Communities detected in entity graph

**Test Assertions**:
- All 52 chunks successfully embedded
- Entity extraction achieves >95% coverage
- Community detection completes in <30 seconds
- Storage in all three databases (Qdrant, Neo4j, Redis) successful

### Scenario 2: Multi-Turn Research Conversation

Test Input: 5 consecutive queries about retrieved research paper

**Execution Path**:
1. Query 1: "What is the main contribution?" - Level 1 scoring, top-3 results
2. Query 2: "Explain the methodology" - Level 2 expansion, top-8 results
3. Query 3: "Compare with related work" - Level 2-3 hybrid, 12 results
4. Query 4: "What are limitations?" - Level 1 focused, top-5 results
5. Query 5: "Summarize key findings" - Level 2 summary, top-6 results

**Test Assertions**:
- Follow-up questions generated for each response
- Context window never exceeds budget
- Conversation maintained across 5 turns
- Memory consolidation not triggered (<50 exchanges)
- Latency <2s P95 for each query

### Scenario 3: Complex Hybrid Query

Test Input: "In the context of recent research on efficient inference, how does the skill registry approach compare to dynamic prompt optimization, and what are the trade-offs in token efficiency?"

**Execution Path**:
1. Intent Classification: COMPARISON with high complexity
2. Query Decomposition: 3 sub-queries generated
3. Vector Search: BGE-M3 retrieval with sparse + dense RRF
4. Graph Search: 2-hop entity relationship lookups
5. Reranking: ColBERT multi-vector scoring
6. LLM Synthesis: Recursive LLM scoring for final ranking
7. Response Generation: Stream LLM output with citations

**Test Assertions**:
- Query decomposition successful
- Parallel sub-queries complete
- Reranking produces expected result ordering
- All sources properly cited
- Response includes comparison table
- Total latency <3 seconds

### Scenario 4: Error Handling and Recovery

Test Input: Query triggering various error conditions

**Execution Path**:
1. Query timeout during graph lookup - graceful fallback to vector results
2. Embedding service unavailable - switch to cached embeddings
3. LLM output truncation - partial response with truncation indicator
4. Memory exhaustion - aggressive compression applied

**Test Assertions**:
- Timeouts handled gracefully with fallback
- Service unavailability doesn't crash system
- Responses still generated despite errors
- User informed of degraded performance

---

## Advanced Architecture Patterns

### Multi-Agent Communication Protocol

The agents communicate through a message queue system implemented in Redis. Each agent registers handlers for specific message types, enabling loose coupling between components. Message types include QueryRequest, RetrievalResult, RerankingRequest, GenerationRequest, and ResponseStream.

Messages flow through the coordinator agent, which maintains a state machine tracking the current phase of query processing. The state machine implements transitions between phases: Classification → Retrieval → Reranking → Generation → Response. Timeouts at each phase trigger fallback behaviors or graceful degradation.

The coordinator maintains a priority queue for handling multiple concurrent queries. It allocates resources (embedding budget, graph query budget, LLM tokens) fairly across queries while prioritizing recently active queries. This prevents one heavy query from starving other users.

### Vector Index Optimization

Qdrant maintains multiple vector indices for different use cases. The dense vector index uses hierarchical navigable small world (HNSW) algorithm for fast approximate nearest neighbor search. The sparse index uses inverted posting lists for exact term matching.

Periodic index optimization rebuilds indices to compact memory usage and improve query performance. The system tracks query patterns and reorders vectors in the index to improve cache locality. Popular documents and entities are pinned in GPU memory for sub-millisecond lookup.

Index partitioning by document source enables faster filtering. For example, queries restricted to recent documents only search the "recent" partition. Vector dimensionality reduction using principal component analysis compresses 1024-dimensional vectors to 256-dimensional representations for faster computation while maintaining 95%+ recall.

### Graph Traversal Optimization

Graph queries implement bidirectional search to reduce exploration space. Starting from both query entities and target entities, the algorithm explores inward until paths meet. This reduces the branching factor significantly compared to unidirectional traversal.

The system pre-computes shortest paths between frequently accessed entity pairs and caches them. For example, paths between industry leaders in a domain are cached and updated daily. This enables O(1) lookup for common queries instead of O(n) traversal.

Community boundaries are used to constrain graph traversal. Queries exploring beyond entity community boundaries are either blocked or require explicit permission. This prevents combinatorial explosion in large graphs.

### LLM Prompt Optimization

Prompts are dynamically constructed based on query intent, available context, and conversation history. The system maintains prompt templates for different intent categories. For NAVIGATION queries, prompts are concise with focus on direct factual statements. For EXPLANATORY queries, prompts encourage deeper reasoning.

Few-shot examples in prompts are selected dynamically from similar historical queries. The system uses embedding similarity to find examples most similar to the current query, then includes 1-3 examples in the prompt.

Chain-of-thought prompting is used for complex queries requiring reasoning over multiple documents. The LLM is prompted to generate intermediate reasoning steps before final answer. This improves answer quality and provides explainability.

### Evaluation Metrics and Monitoring

The system continuously measures RAGAS metrics on a sample of conversations:

- **Context Precision**: Fraction of retrieved context that is relevant to answer
- **Context Recall**: Fraction of necessary context that was retrieved
- **Faithfulness**: Fraction of answer supported by retrieved context
- **Answer Relevance**: How directly answer addresses query

These metrics are tracked per intent category, per domain, and per time window. Degradation in metrics triggers alerts for monitoring. A moving average of metrics is displayed in dashboard.

Performance metrics are also tracked: retrieval latency, reranking latency, LLM generation latency, total latency. Percentile latencies (p50, p95, p99) are reported separately.

Resource utilization metrics include GPU memory (peak and average), GPU compute utilization, CPU utilization, Redis memory, and Qdrant memory. These trigger alerts if utilization exceeds thresholds.

---

## Integration Testing Strategy

### Test Data Preparation

Test data consists of diverse documents representing different domains:

- **Technical Papers** (10 documents, ~50K tokens total): Research on ML, NLP, systems
- **News Articles** (50 documents, ~100K tokens): Covering diverse topics and news sources
- **Product Documentation** (5 documents, ~30K tokens): Software and hardware documentation
- **Books and Long-Form Content** (3 documents, ~100K tokens): Complete chapters from public domain books

Each document is ingested through the full pipeline: parsing, chunking, embedding, entity extraction, graph building. This creates realistic test corpus representing actual usage.

### Test Query Sets

The test query sets include different patterns:

- **Simple Factual Queries** (100 queries): "What is X?", "When did Y happen?", "Where is Z?"
- **Procedural Queries** (100 queries): "How do I do X?", "Steps to achieve Y", "Explain Z"
- **Comparative Queries** (50 queries): "Compare X and Y", "Contrast A versus B"
- **Complex Multi-hop Queries** (50 queries): "In context of X, how does Y relate to Z?"
- **Conversational Multi-turn** (20 sets of 5 queries): Follow-up questions maintaining context

### Expected Outcomes

For each query, expected outcomes include:

- **Relevant Documents** (manual annotation): Which documents should be retrieved
- **Expected Answer Structure**: Outline of answer points
- **Citation Count**: Number of expected citations
- **Processing Strategy**: Which agent(s) should be involved

Test results are compared against expected outcomes using automatic metrics and manual review.

### Continuous Integration

The E2E test suite runs on every commit in CI/CD pipeline:

1. **Unit Tests** (5 minutes): Core function tests with mocks
2. **Integration Tests** (15 minutes): Real database tests, mocked LLM
3. **E2E Tests** (30 minutes): Full pipeline with real LLM (subset of queries)
4. **Performance Tests** (20 minutes): Latency and resource utilization baselines
5. **Visual Regression** (10 minutes): Screenshot comparison with baselines

CI fails if any test fails or performance degrades >10%. All commits must pass full test suite before merging.

---

## Deployment and Scaling Considerations

### Container Orchestration

The system is deployed using Docker Compose on single machine (DGX Spark) for development. For production multi-machine deployments, Kubernetes orchestration enables:

- Horizontal scaling of API servers and workers
- Automated service discovery and load balancing
- Rolling deployments with zero downtime
- Resource requests and limits enforcement
- Persistent volume management for databases

Each component runs in its own container with defined CPU and memory limits:

- API Server: 4 CPU, 8GB memory
- Vector Worker: 8 CPU, 16GB memory (GPU required)
- Graph Worker: 4 CPU, 8GB memory
- Embedding Service: 8 CPU, 32GB memory (GPU required)
- Cache Service (Redis): 2 CPU, 4GB memory

### High Availability Architecture

Production deployments implement high availability with:

- **API Server Redundancy**: 3+ instances behind load balancer
- **Vector DB Replication**: Qdrant cluster with 3+ nodes
- **Graph DB Replication**: Neo4j cluster with 3+ nodes
- **Cache Replication**: Redis Sentinel with automatic failover
- **Monitoring**: Prometheus metrics, Grafana dashboards, PagerDuty alerts

---

## Implementation Details for Each Sprint Feature

### Sprint 90 Deep Dive: Skill Registry

The Skill Registry is a cornerstone feature enabling the agent system to scale to hundreds of capabilities without context window explosion. Each skill is defined by a YAML configuration file specifying metadata, parameters, and execution requirements.

The YAML schema includes:

```yaml
name: "Document_Search"
description: "Search through document corpus using semantic similarity"
version: "1.0"
category: "retrieval"
tags: [search, vector, semantic]
parameters:
  - name: query
    type: string
    description: "Search query"
    required: true
  - name: top_k
    type: integer
    default: 5
    description: "Number of results to return"
resources:
  tokens: 50  # Average tokens needed
  latency_ms: 200  # Expected latency
  dependencies: [embedding_service, qdrant]
examples:
  - input: "What is hybrid search?"
    output: "3 relevant documents with citations"
```

The skill discovery mechanism scans the skills directory at startup and loads all available skills. Each skill is indexed by name and category for quick lookup. Skills are assigned embedding vectors representing their capability profile.

When a query arrives, the Router Agent generates an embedding for the query intent. It then performs semantic similarity search against skill embeddings, returning the top-5 most relevant skills. These skills are the candidates for inclusion in the context window.

The context budgeting algorithm then selects which skills to load based on:
1. Relevance score (how well skill matches query)
2. Priority score (how frequently skill is used)
3. Token cost (how many tokens skill requires)
4. Dependency requirements (other skills this depends on)

The algorithm uses dynamic programming to find the optimal set of skills that maximizes relevance while staying within token budget. This is essentially a variant of the 0/1 knapsack problem.

### Sprint 91 Deep Dive: Recursive LLM Context

The Recursive LLM Context implementation addresses a fundamental limitation: documents larger than the model's context window cannot be processed without truncation and information loss. The recursive approach processes documents hierarchically, discovering relevant information across the entire document regardless of size.

The recursion works by applying increasingly sophisticated scoring at each level:

**Level 0: Simple Embedding-Based Ranking**
- All chunks embedded using BGE-M3 dense vectors
- Top-20 chunks selected by cosine similarity
- Execution time: ~80ms
- Suitable for simple factual queries

**Level 1: Dense-Sparse Hybrid Ranking**
- Combines BGE-M3 dense and sparse vectors
- Applies RRF to combine two rankings
- Improves recall for keyword-heavy queries
- Execution time: ~100ms
- Suitable for procedural queries with specific terms

**Level 2: Fine-Grained Multi-Vector Ranking**
- Applies ColBERT multi-vector scoring
- Scores interactions between query tokens and chunk tokens
- Top-8 chunks selected
- Execution time: ~300ms
- Suitable for questions requiring specific detail

**Level 3: Deep LLM-Based Ranking**
- LLM explicitly scores each candidate chunk
- LLM considers interdependencies between chunks
- Generates confidence scores for each chunk
- Top-5 highest confidence chunks selected
- Execution time: ~1200ms
- Suitable for complex comparative questions

The routing decision uses several signals:

1. **Query Complexity**: Number of entities, operators, modifiers
2. **Available Time Budget**: User's tolerance for latency
3. **Baseline Results Quality**: Confidence in top-1 result from Level 1
4. **Query Type**: Intent classification (NAVIGATION → Level 1, EXPLANATORY → Level 3)

For queries requesting "top N results", the system includes N+2 results and lets the LLM rank them, ensuring full utilization of context window.

### Sprint 92 Deep Dive: Adaptive Scoring

The adaptive scoring system (ADR-052) implements a principled approach to selecting which scoring method to apply based on query and context characteristics. Rather than always using the most sophisticated scoring, it chooses the minimal sufficient scoring level.

The adaptation logic measures several factors:

**Query Factors**:
- Word count (queries >100 words get higher levels)
- Entity mentions (multiple entities need higher levels)
- Temporal references ("recent", "latest" need freshness signals)
- Numerical queries (comparisons, ranges, statistics)
- Negations ("not", "without" need broader context)

**Context Factors**:
- Document relevance variance (high variance = need higher scoring)
- Retrieved chunk density (if many chunks near top, can use lower level)
- Time-sensitive information (recent documents ranked higher)
- Domain specificity (specialized domains may need higher levels)

**User Factors**:
- User expertise (experts prefer concise results, lower levels)
- Conversation length (long conversations → lower levels to avoid exhaustion)
- Historical preferences (some users prefer breadth, others depth)

The system combines these factors using a decision tree learned from historical interaction data. The tree outputs recommended scoring level and alternative levels if time permits.

---

## Practical Application Examples

### Example 1: Skill Registry in Action

User Query: "What are the main risks of LLM inference?"

1. Router Agent classifies intent: NAVIGATION + EXPLANATORY hybrid
2. Query embedding generated: [0.45, 0.32, ..., 0.78] (1024-dim)
3. Skill Registry similarity search:
   - Document_Search: 0.92 (very relevant)
   - Entity_Extraction: 0.34 (somewhat relevant)
   - Code_Execution: 0.12 (not relevant)
   - LLM_Synthesis: 0.78 (relevant)
4. Token budget: 3500 tokens available (after system prompt, instructions, history)
5. Skill selection:
   - Document_Search: 50 tokens cost, 0.92 relevance → SELECT
   - LLM_Synthesis: 30 tokens cost, 0.78 relevance → SELECT
   - Remaining budget: 3420 tokens for context/results
6. Document_Search skill loads and executes
7. LLM_Synthesis skill loads and executes
8. Results: "The main risks of LLM inference are [citations]. These are addressed by [methods]."

Tokens saved: 500 tokens (by not loading Entity_Extraction, Code_Execution, others)

### Example 2: Recursive LLM Scoring Decision

User Query: "In the context of the research paper on efficient inference, what specific techniques are mentioned for reducing memory consumption during the attention computation phase?"

1. C-LARA Classification: EXPLANATORY (requires deep understanding)
2. Document Size: 45,000 tokens (11x larger than context window)
3. Query Specificity: HIGH (asking for "specific techniques")
4. Time Budget: 5 seconds available (user not in rush)

Routing Decision: Level 3 (Deep LLM-Based Ranking)

Execution:
1. Initial retrieval: 20 chunks selected via Level 1 (80ms)
2. Fine-grained ranking: Top-8 candidates selected via Level 2 (300ms)
3. Deep LLM ranking: LLM scores each of 8 candidates (1200ms)
   - "Efficient attention mechanisms" → 0.95 confidence
   - "Memory-optimized hardware design" → 0.87 confidence
   - "Approximation techniques for attention" → 0.92 confidence
   - Others: <0.70 confidence
4. Final selection: Top-3 highest confidence chunks
5. Generation: LLM generates answer using selected chunks (1500ms)
6. Total latency: 3080ms (within 5s budget)

### Example 3: Adaptive Expansion Decision

User Query: "What is the difference between dense and sparse embeddings?"

Query Factors: Low complexity (simple factual question), no temporal references
Context Factors: High relevance document corpus (low variance in results)
User Factors: Regular user who prefers concise responses

Decision Tree Output: LEVEL 1 (Dense-Sparse Hybrid)

Execution:
1. BGE-M3 dense + sparse embedding retrieval (100ms)
2. RRF ranking of combined results (10ms)
3. Top-3 results selected: ~400 tokens context
4. LLM generation (1200ms)
5. Total latency: 1310ms (very fast, better UX)

User feedback triggers next query or follow-up, showing the adaptive system is responding appropriately to user's interaction style.

---

## Metrics and Measurements

### Performance Baseline Metrics

Current measured performance characteristics on DGX Spark (NVIDIA Blackwell, sm_121):

**Vector Operations**:
- BGE-M3 embedding generation: 150-200 ms per query
- Dense vector search (top-20): 45-60 ms
- Sparse vector search: 30-45 ms
- RRF combination: 2-3 ms
- ColBERT ranking (8 chunks): 150-250 ms

**Graph Operations**:
- Single-hop entity lookup: 10-20 ms
- 2-hop path traversal: 50-100 ms
- Community membership query: 20-30 ms
- Full community detection: 15-30 seconds

**LLM Operations**:
- Token generation (first 100 tokens): 1000-1500 ms
- Throughput (after warmup): 30-50 tokens/sec
- Context window processing: ~200ms overhead

**End-to-End Query Latency**:
- Simple factual (Level 1): 1.2-1.5 seconds
- Procedural (Level 2): 1.5-2.0 seconds
- Complex comparative (Level 3): 2.5-4.0 seconds
- P95 latency: <3 seconds for 95% of queries

**Quality Metrics (RAGAS)**:
- Context Precision: 0.72 average
- Context Recall: 0.68 average
- Faithfulness: 0.81 average
- Answer Relevance: 0.76 average

### Resource Utilization Baseline

**GPU Memory** (NVIDIA GB10 with 128GB unified):
- Model weights (Nemotron3): 12GB
- BGE-M3 embeddings: 8GB
- Qdrant vector index (pinned): 20GB
- KV cache for LLM: 4GB (per sequence)
- Available for other operations: ~85GB

**CPU Memory**:
- Neo4j graph cache: 16GB
- Redis cache: 8GB
- Application buffers: 4GB
- OS and other: 4GB

**GPU Compute**:
- Typical sustained: 40-60% utilization
- Peak (during embedding generation): 85-95%
- Idle (waiting for I/O): <5%

**Network**:
- Vector search query: ~100 bytes
- Vector search result (top-20): ~50KB
- Graph query: ~100 bytes
- Graph result: ~10-100KB
- Total bandwidth: typically <1 Mbps average

---

## Future Enhancements and Roadmap

### Planned Improvements

**Batch Processing Optimization** (Sprint 120+):
- Implement query batching to amortize embedding costs
- Multiple queries evaluated in parallel within single batch
- Expected 40% improvement in throughput for batch workloads

**Fine-Tuned Intent Classification** (Sprint 121+):
- Train C-LARA on domain-specific data
- Improve accuracy from 95.22% to 98%+
- Faster inference through model distillation

**Streaming Chunks** (Sprint 122+):
- Stream chunks as they're retrieved rather than waiting for all
- Reduces TTFT from 500ms to 150-200ms
- Progressive result refinement

**Hierarchical Retrieval** (Sprint 123+):
- First retrieve book chapters or sections
- Then retrieve specific paragraphs within selected sections
- Reduces search space while maintaining quality

**Knowledge Graph Expansion** (Sprint 124+):
- Add temporal versioning to all entities
- Enable time-travel queries ("state of the art in 2023 vs 2024")
- Support for entity evolution tracking

---

## Comprehensive Testing Strategies

### Unit Test Coverage

The AegisRAG system maintains >80% unit test coverage across all modules. Each component has dedicated unit tests validating isolated functionality with mocked dependencies.

**Vector Search Tests** (50+ tests):
- BGE-M3 embedding generation with various input types
- Dense vector index operations (insert, delete, update)
- Sparse vector index operations
- RRF combination and ranking accuracy
- Edge cases (empty queries, duplicate vectors, overflow)

**Graph Operation Tests** (40+ tests):
- Entity CRUD operations
- Relationship creation and traversal
- Multi-hop path finding
- Community detection algorithm
- Graph statistics computation

**Agent Orchestration Tests** (60+ tests):
- Router intent classification accuracy
- Vector Agent retrieval execution
- Graph Agent query composition
- Memory Agent consolidation logic
- Action Agent sandboxing and execution

**LLM Integration Tests** (30+ tests):
- Prompt template rendering
- Token counting accuracy
- Context compression simulation
- Response parsing and validation
- Error handling for truncated outputs

### Integration Test Scenarios

Integration tests verify component interactions with real or near-real services. These tests use testcontainers to spin up isolated database instances.

**Retrieval Pipeline Integration** (15 tests):
- Document ingestion through chunking
- Chunk embedding and indexing
- Vector search accuracy validation
- Graph structure verification
- Cache invalidation logic

**Query Orchestration Integration** (10 tests):
- End-to-end query processing
- Multi-agent coordination
- Result aggregation and ranking
- Response generation and streaming
- Session state management

**Conversation Management Integration** (8 tests):
- Multi-turn conversation context
- Follow-up question generation
- Memory consolidation triggering
- Session persistence
- Cache consistency

### E2E Test Execution Strategy

The Playwright E2E test suite covers critical user journeys end-to-end. Tests execute in headless Chrome against a real backend.

**Login and Session Management** (5 tests):
- User authentication flow
- Session initialization
- Token management
- Logout and cleanup

**Search and Retrieval** (15 tests):
- Simple text queries
- Complex multi-clause queries
- Filter application
- Result sorting and pagination
- Citation display accuracy

**Conversation Features** (12 tests):
- Message sending and receiving
- Follow-up question suggestions
- Conversation history
- Conversation sharing
- Conversation search

**Admin Features** (8 tests):
- Document upload
- Indexing status monitoring
- Configuration management
- Metrics dashboard
- System health monitoring

---

## Performance Optimization Techniques

### Embedding Computation Optimization

The BGE-M3 embedding computation is the most expensive operation in the retrieval pipeline. Several optimizations reduce latency:

**Batch Processing**: Multiple queries are batched together when possible, reducing per-query overhead. A batch of 32 queries processes nearly 32x faster than sequential processing.

**GPU Caching**: Frequently computed embeddings are cached in GPU memory. Popular queries and entities have their embeddings pinned, reducing recomputation.

**Model Quantization**: BGE-M3 model weights are quantized from float32 to float16 (or int8 for older hardware), reducing memory footprint and improving compute speed by 2-4x with minimal accuracy loss.

**Distributed Embedding**: The embedding service can be horizontally scaled. Multiple GPU devices compute embeddings in parallel, enabling higher throughput during peak load.

**Progressive Embedding**: When embedding a long document, chunks are embedded lazily as needed rather than eagerly. This amortizes cost across multiple queries to the same document.

### Vector Index Optimization

Qdrant maintains several optimization techniques for efficient vector search:

**HNSW Tuning**: The navigable small world graph parameters (M, ef_construct, ef_search) are tuned to balance memory usage and search accuracy. Current settings: M=16, ef_construct=200, ef_search=100.

**Vector Quantization**: 1024-dimensional vectors are quantized to lower dimensions using PCA (Principal Component Analysis) for faster distance computation. Current: 256 dimensions, 98% variance retained.

**Index Sharding**: Large index collections are partitioned by document source or date, enabling faster filtering and faster index rebuilds.

**Caching Strategy**: Popular vectors are cached in GPU memory (pinned memory), reducing PCIe transfers for hot data. LRU cache eviction manages the pinned memory pool.

### Graph Query Optimization

Neo4j graph queries are optimized through several techniques:

**Query Compilation**: Frequently executed query patterns are pre-compiled to execution plans, avoiding compilation overhead on each execution.

**Index Creation**: Entity name, type, and relationship type indices enable fast filtering. Composite indices on (entity_type, name) enable multi-criteria lookups.

**Statistics-Based Planning**: Query optimizer uses entity and relationship statistics to choose optimal execution plans, using index seeks when beneficial.

**Result Caching**: Frequently executed queries cache their results, with LRU eviction based on query hash and timestamp.

**Connection Pooling**: Neo4j connections are pooled and reused, avoiding connection establishment overhead.

### Response Streaming Optimization

The system streams responses to clients incrementally, improving perceived latency:

**SSE Streaming**: Server-sent events enable progressive result delivery without page reloads. Results are sent as soon as available.

**Progressive LLM Tokens**: LLM output is streamed token-by-token, enabling users to see answers starting within 300-500ms rather than waiting 2-3s for complete generation.

**Progressive Result Refinement**: Initial results are sent with lower relevance scores, then refined as better scoring completes. Users see results immediately but refinement happens progressively.

**Parallel Aggregation**: Results from different agents (vector, graph, memory) are aggregated in parallel rather than sequentially, reducing total latency.

### LLM Context Optimization

The LLM context window is carefully managed:

**Compression on Admission**: When context exceeds budget, aggressive compression is applied: stopword removal, summarization, truncation. Context quality degrades gracefully rather than crashing.

**Smart Truncation**: If context must be truncated, the system truncates from the middle (least important section), keeping beginning (problem statement) and end (conclusion) intact.

**Deduplication**: Redundant information in context is removed before sending to LLM, maximizing utilization of limited tokens.

**Quantization**: Key information is conveyed using fewer tokens through abbreviations, symbols, and structured formats (tables instead of prose).

---

## Debugging and Monitoring Infrastructure

### Logging and Tracing

The system implements comprehensive logging at multiple levels:

**Request Logging**: Every API request logs method, path, parameters, response status, and latency. This enables identifying slow endpoints.

**Component Logging**: Each agent and service logs its operations with millisecond-precision timing. This enables identifying bottlenecks.

**Database Logging**: Vector and graph database operations log queries and latencies. This identifies slow queries and missing indices.

**LLM Logging**: LLM prompts, completions, and generation times are logged for debugging and optimization.

**Error Logging**: All errors include stack traces, context, and reproduction information for debugging.

### Distributed Tracing

The system uses OpenTelemetry and Jaeger for distributed tracing:

- Each request receives a unique trace ID
- Components propagate trace ID in headers
- Service calls are recorded with timing and status
- Traces are visualized in Jaeger UI showing request waterfall

This enables quickly identifying which components are slow for specific requests.

### Metrics Collection

Prometheus metrics are collected for all components:

- **Latency histograms**: p50, p95, p99 latencies for each operation
- **Error counters**: Number of errors by type and component
- **Resource gauges**: Current GPU memory, CPU load, network bandwidth
- **Business metrics**: Queries per second, success rate, average satisfaction

Metrics are visualized in Grafana dashboards with alerts for anomalies.

### Health Checks

The system implements health checks at multiple levels:

- **Service Health**: Each service exposes `/health` endpoint with status
- **Dependency Health**: Health checks verify database connectivity
- **Resource Health**: Alerts trigger if GPU memory or CPU exceeds thresholds
- **Functional Health**: Periodic test queries verify correct behavior

Failed health checks trigger automatic alerts and potential failover to backup components.

---

## Documentation and Knowledge Transfer

### API Documentation

FastAPI generates OpenAPI/Swagger documentation automatically. The documentation includes:

- All endpoint paths and methods
- Request and response schemas
- Parameter descriptions and examples
- Error codes and explanations
- Rate limiting information

The documentation is accessible at `/api/docs` for interactive exploration.

### Architecture Documentation

The system maintains comprehensive architecture documentation including:

- **System Diagram**: High-level component relationships
- **Data Flow Diagram**: Request flow through components
- **Agent Diagram**: Agent responsibilities and interactions
- **Storage Schema**: Database schema and indices
- **API Reference**: Complete API endpoint documentation

### Decision Records

Architecture Decision Records (ADRs) document major technical decisions:

- **ADR-051**: Recursive LLM Context for handling large documents
- **ADR-052**: Adaptive Scoring for query-aware ranking
- **ADR-033**: AegisLLMProxy for multi-cloud LLM routing
- **ADR-039**: Section-Aware Chunking for document processing
- **ADR-027**: Docling CUDA for GPU-accelerated OCR

Each ADR includes decision context, alternatives considered, and consequences.

### Code Examples

The codebase includes numerous examples demonstrating common patterns:

```python
# Example: Using the Retrieval API
from aegisrag.api.client import AegisRAGClient

client = AegisRAGClient(base_url="http://localhost:8000")

# Simple search
results = client.retrieval.search(
    query="What is hybrid search?",
    top_k=5,
    mode="hybrid"
)

# Iterate through results
for result in results:
    print(f"Source: {result.document}")
    print(f"Content: {result.content}")
    print(f"Score: {result.score:.2f}")
```

### Training Materials

Training materials help new developers onboard:

- **Getting Started Guide**: Environment setup and first query
- **Architecture Overview**: System design and components
- **Development Guide**: Adding new features and agents
- **Debugging Guide**: Identifying and fixing common issues
- **Performance Tuning**: Optimizing system performance

---

## Conclusion: Complete System Implementation

This comprehensive fixture document covers the complete AegisRAG system from Sprints 90-119, including:

1. **Skill Registry Foundation** (Sprint 90): Local-first skill management with 30% token savings
2. **Recursive LLM Context** (Sprint 91): Processing documents 10x larger than context window
3. **Adaptive Scoring** (Sprint 92): Query-aware selection of scoring strategy
4. **Multi-Agent Architecture**: Orchestration of specialized agents
5. **Storage Systems**: Vector, graph, and memory databases
6. **Testing Infrastructure**: Unit, integration, and E2E testing
7. **Performance Optimization**: Multiple techniques for speed and efficiency
8. **Monitoring and Debugging**: Comprehensive logging, tracing, and health checks
9. **Deployment Strategies**: Containerization and high availability
10. **Future Roadmap**: Planned improvements through Sprint 124+

The system is production-ready for enterprise deployments with comprehensive documentation, extensive testing, and robust error handling.

---

## Reference Information

**Total Content**: This fixture provides 15,000+ tokens of technical documentation suitable for comprehensive long context testing scenarios.

**Source Material**:
- Sprint 90 Planning: Skill Registry Foundation
- Sprint 91 Planning: Recursive LLM Context & Intent Router
- Sprint 92 Planning: Adaptive Scoring & Deep Research
- Sprint 118 Planning: Testing Infrastructure & Quality Assurance
- Sprint 119 Planning: E2E Test Analysis & Stabilization
- CLAUDE.md: Project Overview
- ARCHITECTURE.md: System Design
- TECH_STACK.md: Technology Specifications

**Documentation Sections**: 15 major sections covering architecture, implementation, performance, testing, and advanced scenarios

**Estimated Tokens**: 15,000+ (approximately 11,500 words × 1.3 token-to-word ratio)

**Last Updated**: 2026-01-25
**Status**: Production Test Fixture
**Compatibility**: Playwright E2E tests, long context scenarios, multi-turn conversations
