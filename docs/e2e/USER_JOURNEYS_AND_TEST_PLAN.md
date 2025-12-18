# AEGIS RAG - Complete User Journeys & E2E Test Plan

**Status:** Comprehensive Mapping
**Created:** 2025-12-17
**Last Updated:** 2025-12-18 (Sprint 52 Features Added)
**Purpose:** Map all user journeys and design complete E2E test coverage

## Recent Updates (Sprints 48-52)

### Sprint 52 Features
- **Community Summaries:** LLM-generated summaries for graph communities with delta-tracking
- **Admin LLM Config:** Model selector for community summary generation
- **Domain Management:** Stats view, Re-index, Validate, Health Status
- **Async Follow-ups:** Non-blocking follow-up question generation
- **CI/CD Optimization:** Auto-mocking for integration tests

### Sprint 51 Features
- **Phase Display Fixes:** Real-time phase updates during streaming
- **Admin Navigation:** Improved layout with consolidated pages
- **Maximum Hybrid Search:** 4-Signal retrieval (Vector + BM25 + Graph Local + Graph Global)
- **111 E2E Tests:** Comprehensive test coverage

### Sprint 49-50 Features
- **Dynamic LLM Selection:** Auto-discover Ollama models
- **Graph Relationship Filtering:** Multi-select filter for edge types
- **Provenance Tracking:** source_chunk_id on relationships
- **BGE-M3 Consolidation:** Unified embedding model

### Sprint 48 Features
- **Real-Time Phase Events:** SSE streaming for processing status
- **Reranking via Ollama:** Cross-encoder reranking
- **Request Timeout & Cancel:** Abort long-running queries

---

## 📋 Table of Contents

1. [Frontend Routes Overview](#frontend-routes-overview)
2. [Complete User Journeys](#complete-user-journeys)
3. [Existing E2E Tests](#existing-e2e-tests)
4. [Missing E2E Tests](#missing-e2e-tests)
5. [E2E Test Implementation Plan](#e2e-test-implementation-plan)

---

## 🗺️ Frontend Routes Overview

### Public Routes
```
/login                     → LoginPage (JWT Authentication)
/share/:shareToken         → SharedConversationPage (Public Conversation Sharing)
```

### Protected Routes (Require Authentication)

#### Main Application
```
/                          → HomePage (Chat Interface)
/search                    → SearchResultsPage (Search Results Display)
/settings                  → Settings (User Settings, Theme Toggle)
```

#### Admin Routes
```
/admin                     → AdminDashboard (Consolidated Admin Overview)
/admin/legacy              → AdminPage (Legacy Admin Page)
/admin/indexing            → AdminIndexingPage (Document Indexing Management)
/admin/graph               → GraphAnalyticsPage (Knowledge Graph Visualization)
/admin/costs               → CostDashboardPage (LLM Cost Tracking)
/admin/llm-config          → AdminLLMConfigPage (LLM Configuration)
/admin/domain-training     → DomainTrainingPage (DSPy Domain Training)
/admin/upload              → UploadPage (Document Upload with Domain Classification)
```

#### Health & Monitoring
```
/health                    → HealthDashboard (System Health Monitoring)
/dashboard/costs           → CostDashboardPage (Duplicate route)
```

---

## 🚶 Complete User Journeys

### **Journey 1: Admin Setup & Domain Creation**
**User Goal:** Set up a new domain with DSPy training for specialized query understanding

#### Steps:
1. **Login** (`/login`)
   - User enters credentials
   - JWT token received and stored
   - Redirected to homepage

2. **Navigate to Domain Training** (`/admin/domain-training`)
   - Click "Admin" in navigation
   - Click "Domain Training" link
   - See list of existing domains

3. **Create New Domain**
   - Click "+ New Domain" button
   - **Step 1: Domain Configuration** (NewDomainWizard)
     - Enter domain name (e.g., "legal", "medical", "omnitracker")
     - Enter description
     - Select LLM model (default: qwen3:32b)
     - Click "Next"

   - **Step 2: Dataset Upload** (DatasetUploadStep)
     - Upload training dataset (JSON/JSONL with query-answer pairs)
     - Preview uploaded samples
     - Click "Start Training"

   - **Step 3: Training Progress** (TrainingProgressStep with SSE)
     - Watch live training logs via SSE streaming
     - See metrics (bootstrap samples, training loss, validation score)
     - Optional: Export JSONL log file
     - Training completion notification
     - Close wizard

4. **Verify Domain Created**
   - See new domain in DomainList
   - Verify status shows "ready" or training metrics

#### Test Coverage:
- ✅ Existing: None (NEW TEST NEEDED)
- 🆕 Required: `test_e2e_domain_creation_workflow.py`

---

### **Journey 2: Document Upload & Ingestion**
**User Goal:** Upload documents with automatic domain classification and indexing

#### Steps:
1. **Navigate to Upload Page** (`/admin/upload`)
   - Click "Admin" → "Upload" or direct URL
   - See upload dropzone

2. **Upload Documents**
   - Drag & drop files OR click to select
   - Files are automatically classified via DSPy
   - See domain suggestions with confidence scores
   - See alternative domain recommendations

3. **Review & Adjust Domain Assignment**
   - Review AI-suggested domains for each file
   - Override domain selection if needed using DomainSelector
   - Verify confidence badges (High/Medium/Low)

4. **Start Upload & Ingestion**
   - Click "Upload" button
   - Monitor upload progress (optional: SSE events)
   - Wait for processing completion

5. **Validate Ingestion Results** (Backend Systems)
   - **Qdrant:** Check documents indexed with BGE-M3 embeddings
   - **Neo4j:** Verify entities and relations extracted
   - **BM25:** Confirm corpus updated
   - **Provenance:** Verify source_chunk_id on relationships (Sprint 49.5)

#### Test Coverage:
- ✅ Existing: `test_e2e_document_ingestion_workflow.py` (partial)
- 🆕 Required: `test_e2e_upload_page_domain_classification.py`

---

### **Journey 3: Hybrid Search & Query (Maximum Hybrid Search)**
**User Goal:** Search uploaded documents using 4-signal hybrid retrieval
**Feature Status:** ✅ Fully Implemented (Sprint 51 Maximum Hybrid Search)

#### Steps:
1. **Navigate to Chat** (`/`)
   - Click "New Chat" or go to homepage
   - See welcome screen with quick prompts

2. **Enter Search Query**
   - Type query in chat input (e.g., "What is machine learning?")
   - Select search mode (Hybrid/Vector/BM25/Graph) - default: Maximum Hybrid
   - Optional: Select namespaces/domains
   - Press Enter or click Send

3. **Watch Real-Time Phase Progress** (Sprint 48)
   - See phase progress indicators with live timing:
     - 🔍 Intent Classification (query analysis)
     - 📊 Vector Search (BGE-M3 similarity)
     - 📝 BM25 Search (keyword matching)
     - 🕸️ Graph Local (entity relationships)
     - 🌐 Graph Global (community summaries - Sprint 52)
     - ⚖️ RRF Fusion (Reciprocal Rank Fusion)
     - 🔄 Reranking (cross-encoder via Ollama - Sprint 48)
     - 💬 LLM Generation (answer synthesis)
   - See real-time execution times per phase
   - Phase count shows actual phases executed (not hardcoded)

4. **Watch Streaming Answer**
   - See answer tokens appearing in real-time
   - See source cards appearing as retrieved
   - Answer quality reflects 4-signal fusion

5. **Review Results**
   - Read complete answer with inline citations
   - Click citations to see source chunks with provenance (Sprint 49)
   - Verify sources from uploaded documents
   - See source_chunk_id tracing back to origin

6. **View Async Follow-up Questions** (Sprint 52)
   - After answer completes, see loading skeleton
   - Follow-up questions appear asynchronously (1-3 seconds)
   - Questions generated in background (non-blocking)
   - Click follow-up to pre-fill chat input

7. **Interact with Results**
   - Click citation to open source panel
   - Verify citation references correct document
   - Ask follow-up question
   - Share conversation (optional)
   - Cancel long-running request (Sprint 48)

#### Test Coverage:
- ✅ Existing:
  - `test_e2e_hybrid_search_quality.py` (BM25, Vector, Hybrid quality)
  - `test_e2e_document_ingestion_workflow.py` (query with citations)
  - `test_e2e_historical_phase_events.py` (phase tracking - Sprint 51)
- 🆕 Required: `test_e2e_async_followup_questions.py` (Sprint 52)

---

### **Journey 4: Knowledge Graph Exploration**
**User Goal:** Visualize and explore the knowledge graph from uploaded documents
**Feature Status:** ✅ Enhanced (Sprint 49 + Sprint 52)

#### Steps:
1. **Navigate to Graph Analytics** (`/admin/graph`)
   - Click "Admin" → "Graph Analytics"
   - Wait for graph to load
   - See enhanced Graph Analytics Page (Sprint 52)

2. **View Graph Statistics** (Sprint 52 Enhanced)
   - See summary cards:
     - Total Entities (nodes)
     - Total Relationships (edges)
     - Total Communities
     - Total Documents indexed
   - See entity type distribution chart
   - See relationship type distribution
   - See graph health metrics:
     - Orphaned nodes count
     - Disconnected components
     - Average node degree

3. **Apply Filters** (Sprint 49 Enhanced)
   - **Entity Type Filter:** Multi-select entity types (PERSON, ORG, LOCATION, etc.)
   - **Relationship Type Filter:** Multi-select edge types (Sprint 49.2)
     - RELATES_TO (semantic)
     - WORKED_AT, FOUNDED, LOCATED_IN, etc.
   - **Min Node Degree:** Filter low-connectivity nodes
   - **Max Nodes:** Limit render for performance
   - **Min Edge Weight:** Filter weak connections

4. **Explore Graph Visually**
   - Pan and zoom the graph
   - Click nodes to see details in NodeDetailsPanel:
     - Entity name, type, aliases
     - Connected entities with relationship types
     - Source documents with provenance
   - Click edges to see relationship details:
     - Relationship type (deduplicated via BGE-M3 - Sprint 49.7)
     - Weight/confidence
     - **source_chunk_id** (Sprint 49.5 provenance tracking)
     - Link to source document

5. **Explore Communities** (Sprint 52 Enhanced)
   - See TopCommunities list in sidebar
   - Click community to highlight in graph
   - **View Community Summary** (Sprint 52):
     - LLM-generated description of community theme
     - Key entities and relationships
     - Domain context
   - See community documents
   - Verify semantic clustering via BGE-M3

6. **Export Graph**
   - Click "Export" button
   - Select format (GraphML, Cypher, JSON)
   - Download graph data

7. **Refresh Data**
   - Click "Refresh" button
   - Graph reloads with latest data
   - See loading indicator during refresh

#### Test Coverage:
- ✅ Existing:
  - `test_e2e_graph_analytics.py` (Sprint 52 - page load, stats, refresh)
  - `test_e2e_graph_relationship_filtering.py` (Sprint 51)
- 🆕 Required: `test_e2e_graph_exploration_full_workflow.py`

---

### **Journey 5: Community Detection & Analysis**
**User Goal:** Find and analyze semantic communities in the knowledge graph
**Feature Status:** ✅ Enhanced with LLM Summaries (Sprint 52)

#### Steps:
1. **Navigate to Graph Analytics** (`/admin/graph`)
   - Load graph visualization
   - See community statistics
   - See community summary status (generated/pending)

2. **View Community List**
   - See TopCommunities component
   - See communities ranked by:
     - Node count
     - Density
     - Semantic coherence
   - See **Community Summary Preview** (Sprint 52):
     - First 100 chars of LLM-generated summary
     - "View Details" link

3. **Select Community**
   - Click community in list
   - Graph highlights community nodes
   - See community documents in CommunityDocuments panel

4. **View Community Summary** (Sprint 52 NEW)
   - **LLM-Generated Summary:**
     - Main topic/theme description
     - Key relationships between entities
     - Domain context (research, business, technology)
   - Summary generated via delta-tracking (only affected communities)
   - ~90% cost savings vs full regeneration

5. **Analyze Community**
   - See key entities in community
   - See dominant entity types
   - See inter-community connections
   - See source documents with provenance

6. **Configure Summary Model** (Sprint 52 Admin)
   - Navigate to `/admin/llm-config`
   - Select "Graph Community Summary Model"
   - Choose from available Ollama models
   - Save configuration (persisted in Redis)

7. **Export Community Data**
   - Export community subgraph
   - Export community document list
   - Export community summary

#### Test Coverage:
- ✅ Existing:
  - `test_e2e_graph_analytics.py` (community counts - Sprint 52)
- 🆕 Required: `test_e2e_community_summaries.py` (Sprint 52)

---

### **Journey 6: Graph Time Travel (Optional Feature)**
**User Goal:** View historical versions of the knowledge graph and entity changelog

#### Steps:
1. **Navigate to Graph Analytics** (`/admin/graph`)
   - Load graph viewer
   - Click "Time Travel" tab

2. **Select Time Range**
   - Use TimeTravelTab controls
   - Select start and end dates
   - See graph state at selected time

3. **View Entity Changelog**
   - Click entity to see EntityChangelog
   - See historical changes:
     - Entity creation
     - Property updates
     - Relationship additions/removals

4. **Compare Versions**
   - Use VersionCompare component
   - Select two time points
   - See diff visualization

#### Test Coverage:
- ✅ Existing: None (OPTIONAL FEATURE)
- 🆕 Required: `test_e2e_graph_time_travel.py` (if feature is active)

---

### **Journey 7: Session Management & History**
**User Goal:** Manage chat sessions, search history, and continue previous conversations

#### Steps:
1. **View Session History**
   - Click sidebar toggle to open SessionSidebar
   - See list of previous conversations grouped by date
   - See session titles (auto-generated or user-edited)

2. **Continue Previous Session**
   - Click session in sidebar
   - Previous conversation loads
   - Continue asking questions in same session

3. **Edit Session Title**
   - Click edit icon on session
   - Enter new title
   - Title saved

4. **Archive Session**
   - Click archive button on session
   - Session moved to archived list
   - Can still access via "Show Archived"

5. **Share Session**
   - Click share button on session
   - Generate share link
   - Copy link
   - Share link opens in `/share/:shareToken` (public route)

6. **Delete Session**
   - Click delete on session
   - Confirm deletion
   - Session removed from history

#### Test Coverage:
- ✅ Existing: None (NEW TEST NEEDED)
- 🆕 Required: `test_e2e_session_management.py`

---

### **Journey 8: Cost Monitoring & LLM Configuration**
**User Goal:** Monitor LLM API costs and configure LLM providers
**Feature Status:** ✅ Enhanced (Sprint 49 Dynamic Models + Sprint 52 Summary Config)

#### Steps:
1. **Navigate to Cost Dashboard** (`/admin/costs`)
   - Click "Admin" → "Cost Dashboard"
   - See cost overview

2. **View Cost Metrics**
   - See total costs by provider (Ollama, Alibaba Cloud, OpenAI)
   - See cost breakdown by:
     - Model (llama3.2:8b, qwen3:32b, etc.)
     - Operation type (generation, embedding, classification, **summarization**)
     - Time period (daily, weekly, monthly)
   - See budget alerts if approaching limits
   - **Community Summary Costs** (Sprint 52):
     - Track costs for LLM summary generation
     - Delta-tracking saves ~90% costs

3. **Configure LLM Settings** (`/admin/llm-config`)
   - Navigate to LLM Config page
   - **Dynamic Model Discovery** (Sprint 49.1):
     - Models auto-populated from Ollama API
     - Embedding models (bge-m3, nomic) filtered out
     - Vision models tagged separately
   - Select primary LLM provider
   - Configure fallback providers
   - Set API keys
   - Test LLM connectivity

4. **Configure Summary Model** (Sprint 52 NEW)
   - See "Graph Community Summary Model" section
   - Select model for community summaries (dropdown)
   - Save configuration (persisted in Redis)
   - Model used when generating/regenerating summaries

5. **Monitor Real-time Costs**
   - See live cost updates during operations
   - Verify cost tracking accuracy
   - Track summarization costs separately

#### Test Coverage:
- ✅ Existing:
  - `test_e2e_dynamic_llm_configuration.py` (Sprint 51 - model discovery)
- 🆕 Required: `test_e2e_summary_model_config.py` (Sprint 52)

---

### **Journey 9: System Health & Monitoring**
**User Goal:** Monitor system health, check service status, view error logs

#### Steps:
1. **Navigate to Health Dashboard** (`/health`)
   - Click "System Status" or navigate directly
   - See health overview

2. **View Service Status**
   - Qdrant (Vector DB)
   - Neo4j (Graph DB)
   - Redis (Memory/Cache)
   - Ollama (LLM Server)
   - Backend API

3. **Check Resource Metrics**
   - CPU usage
   - Memory usage
   - Disk usage
   - Network traffic

4. **View Error Logs**
   - See recent errors
   - Filter by severity (Error, Warning, Info)
   - Click error for details
   - Export error logs

5. **Test Service Connectivity**
   - Click "Test Connection" for each service
   - Verify connectivity status

#### Test Coverage:
- ✅ Existing: None (NEW TEST NEEDED)
- 🆕 Required: `test_e2e_health_monitoring.py`

---

### **Journey 10: Indexing Management**
**User Goal:** Monitor and manage document indexing pipeline

#### Steps:
1. **Navigate to Indexing Page** (`/admin/indexing`)
   - Click "Admin" → "Full Indexing Page"
   - See indexing overview

2. **View Indexing Status**
   - See pipeline stages:
     - Document loading
     - Text extraction (Docling)
     - Chunking (section-aware, 800-1800 tokens)
     - Embedding (BGE-M3)
     - Entity extraction (LLM)
     - Relation extraction (LLM)
     - Graph construction
   - See progress bars for each stage

3. **Monitor Live Indexing** (SSE)
   - Watch live log stream
   - See documents processed
   - See errors/warnings
   - View worker pool status

4. **Configure Indexing Pipeline**
   - Adjust worker pool size
   - Configure chunking parameters
   - Set batch sizes

5. **Trigger Re-indexing**
   - Click "Index Directory" button
   - Select directory
   - Start indexing process

6. **View Indexing Results**
   - See total documents indexed
   - See chunks created
   - See entities extracted
   - See relations created

#### Test Coverage:
- ✅ Existing: `test_e2e_document_ingestion_workflow.py` (partial)
- 🆕 Required: `test_e2e_indexing_pipeline_monitoring.py`

---

### **Journey 11: Sprint 49 Feature Validation**
**User Goal:** Validate all Sprint 49 features (Provenance, Deduplication, BGE-M3)

#### Steps:
1. **Index Consistency Validation** (Feature 49.6)
   - Upload test documents
   - Verify Qdrant ↔ Neo4j ↔ BM25 consistency
   - Check chunk counts match across systems
   - Validate entity IDs consistent

2. **Relation Deduplication** (Feature 49.7 & 49.8)
   - Upload document with duplicate relation types
   - Verify semantic deduplication with BGE-M3
   - Check manual synonym overrides work
   - Validate hierarchical clustering

3. **Provenance Tracking** (Feature 49.5)
   - Check relationships have `source_chunk_id` property
   - Verify chunk ID traces back to source document
   - Validate citation links work

4. **BGE-M3 Consolidation** (Feature 49.9)
   - Verify all embeddings use BGE-M3 (1024-dim)
   - Check entity deduplication works
   - Validate semantic similarity

#### Test Coverage:
- ✅ Existing: `test_e2e_sprint49_features.py` (comprehensive)
- 🆕 Required: None (COMPLETE)

---

### **Journey 12: Graph Time Travel (Bi-Temporal Queries)**
**User Goal:** View historical graph states and track entity evolution over time
**Feature Status:** ✅ Fully Implemented (Sprint 39) - Needs E2E Test
**Reference:** ADR-042, Sprint 51.1

#### Steps:
1. **Enable Temporal Queries**
   - Navigate to /admin/graph
   - Click "Settings" or Feature Toggle
   - Enable "Temporal Queries" feature flag
   - Verify indexes created (composite temporal indexes)

2. **Upload Documents and Create Versions**
   - Upload document about "Python 3.11"
   - Wait for entity extraction
   - Update document with new information (Python 3.12 release)
   - Upload again → creates new version
   - Repeat to create version history (3+ versions)

3. **Access Time Travel Interface**
   - Navigate to /admin/graph
   - Click "Time Travel" tab
   - See date picker for historical queries

4. **Query Historical State**
   - Select date (e.g., 1 week ago)
   - View graph as it existed on that date
   - Verify entities match historical state
   - Check relationships reflect historical connections

5. **View Entity Version History**
   - Click entity node (e.g., "Python 3.11")
   - See version history panel
   - View all versions with timestamps
   - See "changed_by" user for each version

6. **Compare Versions**
   - Select two versions for comparison
   - View side-by-side diff
   - Highlight changes (properties, relationships)

7. **View Audit Trail**
   - See complete change log
   - Filter by date range
   - Filter by user
   - Export audit report

8. **Rollback Entity** (Optional)
   - Select entity version
   - Click "Rollback to this version"
   - Confirm action
   - Verify entity restored in current graph

#### Test Coverage:
- ⚠️ Existing: Feature implemented, NO E2E test
- 🆕 Required: `test_e2e_graph_time_travel_workflow.py` (Sprint 51.1 - 13 SP)

**API Endpoints to Test:**
- `GET /api/v1/graph/temporal/entities?as_of=2024-01-15`
- `GET /api/v1/graph/temporal/entity/{id}/history`
- `POST /api/v1/graph/temporal/query`
- `GET /api/v1/graph/temporal/entity/{id}/versions`
- `POST /api/v1/graph/temporal/entity/{id}/rollback`
- `GET /api/v1/graph/temporal/changes?from=...&to=...`

---

### **Journey 13: Secure Code Analysis with Shell Sandbox**
**User Goal:** Analyze code repositories safely using sandboxed shell execution
**Feature Status:** ✅ Fully Implemented (Sprint 40) - Needs E2E Test
**Reference:** ADR-043, Sprint 51.2

#### Steps:
1. **Navigate to Code Analysis**
   - Navigate to /admin/code-analysis (new page)
   - See repository selector

2. **Select Repository**
   - Choose from uploaded repositories
   - Or provide path to analyze
   - Click "Analyze"

3. **Monitor Sandbox Execution**
   - Watch real-time log stream (SSE)
   - See commands executed in sandbox:
     - `find . -name "*.py" | wc -l` (count files)
     - `grep -r "import" . | head -20` (dependencies)
     - `git log --oneline | head -10` (history)
   - Verify commands complete successfully

4. **View Analysis Results**
   - See extracted entities (functions, classes, modules)
   - View dependency graph
   - Check git metadata (contributors, timeline)

5. **Verify Sandbox Security**
   - Audit log shows all commands
   - Network isolation enforced (no curl/wget)
   - Filesystem isolation enforced
   - Dangerous commands blocked

6. **Test Sandbox Boundaries**
   - Try network command → should fail
   - Try write outside workspace → should fail
   - Try reading /etc/passwd → should fail
   - Verify all blocked with proper error messages

#### Test Coverage:
- ⚠️ Existing: Feature implemented, NO E2E test
- 🆕 Required: `test_e2e_secure_shell_sandbox.py` (Sprint 51.2 - 8 SP)

**Sandbox Features to Test:**
- Bubblewrap isolation (network, filesystem, process)
- Command validation and blocklist
- Timeout enforcement (30s default)
- Output sanitization (32KB limit)
- Audit logging
- Performance overhead (<200ms per ADR-043)

---

### **Journey 14: Dynamic LLM Model Discovery**
**User Goal:** Discover and configure available LLM models automatically
**Feature Status:** ✅ Fully Implemented (Sprint 49.1) - Needs E2E Test
**Reference:** Sprint 51.3

#### Steps:
1. **Navigate to LLM Configuration**
   - Navigate to /admin/llm-config
   - See LLM configuration page loading

2. **View Available Models**
   - See model dropdown populated dynamically
   - Verify models fetched from Ollama API
   - Check embedding models filtered out (bge-m3, nomic-embed)

3. **Inspect Model Details**
   - See model size displayed
   - Check vision models tagged correctly
   - Verify local vs cloud models distinguished

4. **Select New Model**
   - Choose different model from dropdown
   - Save configuration
   - Verify settings persisted

5. **Test Model Connection**
   - Click "Test Connection" button
   - Verify model responds
   - See connection status (success/failure)

6. **Pull New Model** (Optional)
   - Use Ollama CLI to pull new model: `ollama pull llama3.3:70b`
   - Refresh LLM config page
   - Verify new model appears automatically in dropdown

#### Test Coverage:
- ⚠️ Existing: Feature implemented, NO E2E test
- 🆕 Required: `test_e2e_dynamic_llm_configuration.py` (Sprint 51.3 - 5 SP)

**API to Test:**
- `GET /api/v1/admin/ollama/models`

---

### **Journey 15: Graph Relationship Type Filtering**
**User Goal:** Filter graph visualization by relationship types
**Feature Status:** ✅ Fully Implemented (Sprint 49.2) - Needs E2E Test
**Reference:** Sprint 51.4

#### Steps:
1. **Navigate to Graph Analytics**
   - Navigate to /admin/graph
   - See full graph with all relationships

2. **Open Relationship Filter**
   - Locate relationship type multiselect
   - See all available relationship types listed

3. **Apply Filter - Single Type**
   - Select only "WORKED_AT" relationships
   - Verify graph updates immediately
   - Only WORKED_AT edges visible
   - Nodes with no WORKED_AT connections hidden

4. **Apply Filter - Multiple Types**
   - Add "FOUNDED" to filter
   - Verify graph shows WORKED_AT + FOUNDED
   - Other edge types hidden

5. **Clear Filter**
   - Deselect all relationship types
   - Verify graph shows all relationships again

6. **Test Filter Persistence**
   - Apply filter
   - Refresh page
   - Verify filter still applied

7. **Combine with Entity Search**
   - Apply relationship filter
   - Search for entity
   - Verify filter persists during search

#### Test Coverage:
- ⚠️ Existing: Feature implemented, NO E2E test
- 🆕 Required: `test_e2e_graph_relationship_filtering.py` (Sprint 51.4 - 5 SP)

---

### **Journey 16: Historical Phase Events Display**
**User Goal:** View complete phase event history for chat messages
**Feature Status:** ✅ Fully Implemented (Sprint 49.3) - Needs E2E Test
**Reference:** Sprint 51.5

#### Steps:
1. **Start Chat Session**
   - Navigate to chat (/)
   - See chat interface ready

2. **Submit Query and Watch Phases**
   - Enter query: "Explain machine learning"
   - Submit query
   - Watch phase indicators during streaming:
     - "Query Analysis" phase
     - "Retrieval" phase
     - "Response Generation" phase
   - See phase progress in real-time

3. **View Phase Timing**
   - See phase durations displayed
   - Verify timestamps accurate
   - Check phase transitions smooth

4. **Expand Phase History**
   - After response completes
   - Click "Show Phase History" or expand accordion
   - See complete list of all phase events
   - Verify all phases recorded with timestamps

5. **Multiple Messages**
   - Submit second query
   - Verify new message has own phase tracking
   - Verify first message's phase history preserved
   - Check phase histories independent

6. **Phase Event Details**
   - Click on individual phase event
   - See detailed information:
     - Phase name
     - Start/end timestamps
     - Duration
     - Status (success/failure)
     - Optional: Phase-specific metadata

#### Test Coverage:
- ⚠️ Existing: Feature implemented, NO E2E test
- 🆕 Required: `test_e2e_historical_phase_events.py` (Sprint 51.5 - 3 SP)

**Component to Test:**
- `PhaseEventHistory` component in ConversationView
- SSE-based phase tracking
- Phase timing accuracy

---

### **Journey 17: Index Consistency Validation UI**
**User Goal:** Validate consistency across Qdrant, Neo4j, and BM25 indexes
**Feature Status:** ⚠️ Backend Implemented (Sprint 49.6), Frontend Missing
**Reference:** Sprint 51.6

#### Steps:
1. **Navigate to Indexing Management**
   - Navigate to /admin/indexing
   - See indexing management page
   - Locate "Index Consistency" section (NEW)

2. **Trigger Consistency Check**
   - Click "Check Consistency" button
   - Watch validation progress (SSE stream)
   - See checks running:
     - Qdrant chunk count
     - Neo4j entity/relation count
     - BM25 document count
     - Cross-index consistency

3. **View Results Dashboard**
   - See summary statistics:
     - Total documents indexed
     - Qdrant chunks: X
     - Neo4j entities: Y
     - Neo4j relations: Z
     - BM25 documents: W
   - Consistency status: ✅ Consistent or ⚠️ Inconsistencies Found

4. **Inspect Inconsistencies**
   - If inconsistencies found:
     - See detailed report
     - List of missing/orphaned chunks
     - List of entities without chunks
     - Recommendations for fixes

5. **Trigger Re-indexing**
   - Select inconsistent documents
   - Click "Re-index Selected"
   - Monitor re-indexing progress
   - Verify consistency after re-indexing

6. **Schedule Automatic Checks**
   - Configure automatic consistency checks
   - Set schedule (daily, weekly)
   - Enable email alerts for inconsistencies

#### Test Coverage:
- ⚠️ Existing: Backend API exists, NO frontend UI, NO E2E test
- 🆕 Required: `test_e2e_index_consistency_validation.py` (Sprint 51.6 - 5 SP)

**API to Test:**
- `GET /api/v1/admin/index/consistency`
- `POST /api/v1/admin/index/consistency/check`

---

### **Journey 18: User Preference Learning with Mem0 (OPTIONAL)**
**User Goal:** Let system learn user preferences automatically from conversations
**Feature Status:** ⚠️ Designed (ADR-025), NOT Implemented
**Reference:** Sprint 51.7 (OPTIONAL Stretch Goal)

#### Steps (If Implemented):
1. **Enable Mem0**
   - Navigate to user profile or settings
   - See "Preference Learning" toggle
   - Enable Mem0 feature

2. **Have Conversations**
   - Use chat interface normally
   - System learns preferences in background:
     - Communication style (concise vs detailed)
     - Technical level (beginner vs expert)
     - Language preferences
     - Topic affinities

3. **View Learned Preferences**
   - Navigate to /profile or /settings
   - See "Learned Preferences" section
   - View extracted facts:
     - "User prefers technical explanations"
     - "User works with Python and TypeScript"
     - "User frequently asks about RAG systems"

4. **Manage Preferences**
   - Delete individual preferences
   - Edit preferences manually
   - Disable preference learning temporarily

5. **Experience Personalization**
   - Chat responses tailored to preferences
   - Relevant context prioritized
   - Communication style adapted

6. **Privacy Controls**
   - View all stored preferences
   - Export preferences (JSON)
   - Delete all preferences (GDPR compliance)

#### Test Coverage:
- ⚠️ Existing: Feature NOT implemented
- 🆕 Required: `test_e2e_mem0_user_preferences.py` (Sprint 51.7 - 13 SP, OPTIONAL)

**Note:** Only implement if Sprint 51 ahead of schedule (5+ SP buffer).

---

### **Journey 19: Domain Management & Health Monitoring** (Sprint 52 NEW)
**User Goal:** Monitor domain health, view statistics, and perform bulk operations
**Feature Status:** ✅ Fully Implemented (Sprint 52)

#### Steps:
1. **Navigate to Domain Training** (`/admin/domain-training`)
   - Click "Admin" → "Domain Training"
   - See list of existing domains with status badges

2. **Open Domain Detail View**
   - Click on a domain row or "Details" button
   - DomainDetailDialog opens with statistics

3. **View Domain Statistics** (Sprint 52)
   - **Document Statistics:**
     - Total documents in domain
     - Total chunks (from Qdrant)
     - Total entities (from Neo4j)
     - Total relationships (from Neo4j)
   - **Health Status Badge:**
     - 🟢 Healthy: All systems consistent
     - 🟡 Degraded: Minor inconsistencies
     - 🔴 Error: Indexing failed or data missing
     - 🔵 Indexing: Currently processing
   - **Indexing Progress:**
     - Progress bar (0-100%)
     - Last indexed timestamp

4. **Perform Bulk Operations** (Sprint 52)
   - **Re-index Domain:**
     - Click "Re-index" button
     - Confirmation dialog
     - All documents re-processed
     - Watch progress via SSE
   - **Validate Domain:**
     - Click "Validate" button
     - Runs consistency checks:
       - Domain configuration complete?
       - Training prompts available?
       - Orphaned entities detected?
       - Chunks without references?
     - See validation results:
       - ✅ Passed checks
       - ⚠️ Warnings
       - ❌ Errors with recommendations

5. **View Validation Results**
   - Errors list with severity
   - Recommendations for fixing issues
   - Links to affected documents/entities

6. **Close Dialog**
   - Click "Close" or outside dialog
   - Return to domain list with updated status

#### API Endpoints:
- `GET /admin/domains/{domain_name}/stats` - Get domain statistics
- `POST /admin/domains/{domain_name}/reindex` - Trigger re-indexing
- `POST /admin/domains/{domain_name}/validate` - Run validation

#### Test Coverage:
- ✅ Existing:
  - `test_e2e_domain_management_enhancement.py` (Sprint 52)
    - Statistics display
    - Bulk operations visibility
    - Validate operation
    - Re-index operation
    - Health status display

---

### **Journey 20: Async Follow-up Questions** (Sprint 52 NEW)
**User Goal:** Receive contextual follow-up question suggestions without delay
**Feature Status:** ✅ Fully Implemented (Sprint 52)

#### Steps:
1. **Submit Query** (see Journey 3)
   - Enter question in chat
   - Submit and watch streaming answer

2. **Answer Completes**
   - Full answer displayed with citations
   - Loading skeleton appears below answer

3. **Follow-up Questions Load Asynchronously**
   - **Background Process:**
     - Conversation context stored in Redis (30min TTL)
     - LLM generates 3-5 contextual follow-up questions
     - Runs in background (non-blocking)
   - **Frontend Polling:**
     - Polls every 1 second for up to 10 attempts
     - Loading skeleton shows during wait
   - **Questions Appear:**
     - 3-5 clickable question cards
     - Questions contextual to conversation
     - Typically 1-3 seconds after answer

4. **Interact with Follow-ups**
   - Click a follow-up question
   - Question pre-fills chat input
   - Submit to continue conversation

5. **Session Context Persistence**
   - Context cached for 30 minutes
   - Multiple queries in session use accumulated context
   - Better follow-up relevance over time

#### Key Requirement:
**Follow-up questions NEVER delay the answer display.** Generation happens asynchronously after answer is complete.

#### Test Coverage:
- ✅ Existing:
  - `tests/unit/agents/test_followup_generator.py` (9 tests - Sprint 52)
- 🆕 Required: `test_e2e_async_followup_questions.py`

---

## ✅ Existing E2E Tests

**Total E2E Tests:** 111+ tests (as of Sprint 52)

### Core Workflow Tests

#### 1. `test_e2e_document_ingestion_workflow.py` (495 lines)
**Status:** ✅ Implemented
**Coverage:**
- Document upload via UI
- Chunking and indexing in Qdrant
- Entity extraction to Neo4j
- Relation extraction with source_chunk_id
- BM25 corpus updates
- Query with citations
- Answer quality validation

---

#### 2. `test_e2e_hybrid_search_quality.py` (457 lines)
**Status:** ✅ Implemented
**Coverage:**
- BM25 exact keyword matching
- Vector semantic search
- Hybrid RRF fusion
- Ranking quality
- Result diversity
- Performance benchmarks

---

#### 3. `test_e2e_sprint49_features.py` (409 lines)
**Status:** ✅ Implemented
**Coverage:**
- Feature 49.5: Provenance tracking validation
- Feature 49.6: Index consistency validation
- Feature 49.7 & 49.8: Relation deduplication & synonyms
- Feature 49.9: BGE-M3 entity deduplication

---

### Sprint 51 E2E Tests (NEW)

#### 4. `test_e2e_bi_temporal_queries.py`
**Status:** ✅ Implemented (Sprint 51.1)
**Coverage:**
- Historical graph state queries
- Entity version history
- Temporal range filtering

---

#### 5. `test_e2e_secure_shell_sandbox.py`
**Status:** ✅ Implemented (Sprint 51.2)
**Coverage:**
- Sandboxed command execution
- Network isolation verification
- Filesystem isolation verification
- Command blocklist enforcement

---

#### 6. `test_e2e_dynamic_llm_configuration.py`
**Status:** ✅ Implemented (Sprint 51.3)
**Coverage:**
- Dynamic model discovery from Ollama
- Embedding model filtering
- Model selection and persistence

---

#### 7. `test_e2e_graph_relationship_filtering.py`
**Status:** ✅ Implemented (Sprint 51.4)
**Coverage:**
- Multi-select relationship type filter
- Graph updates on filter change
- Filter persistence

---

#### 8. `test_e2e_historical_phase_events.py`
**Status:** ✅ Implemented (Sprint 51.5)
**Coverage:**
- Phase event display during streaming
- Phase timing accuracy
- Phase history after message complete

---

#### 9. `test_e2e_index_consistency_validation.py`
**Status:** ✅ Implemented (Sprint 51.6)
**Coverage:**
- Qdrant ↔ Neo4j ↔ BM25 consistency
- Consistency check UI
- Inconsistency reporting

---

### Sprint 52 E2E Tests (NEW)

#### 10. `test_e2e_graph_analytics.py`
**Status:** ✅ Implemented (Sprint 52)
**Coverage:**
- Graph analytics page load
- Summary cards display (entities, relationships, communities)
- Chart visualization
- Graph health banner
- Refresh functionality

---

#### 11. `test_e2e_domain_management_enhancement.py`
**Status:** ✅ Implemented (Sprint 52)
**Coverage:**
- Domain statistics display
- Health status badges
- Re-index bulk operation
- Validate bulk operation
- Dialog close functionality

---

#### 12. `test_e2e_health_monitoring.py`
**Status:** ✅ Implemented (Sprint 51)
**Coverage:**
- Service status indicators
- Health check API
- Error log display

---

## 🆕 Missing E2E Tests

### High Priority (User-Facing Features)

#### 1. **`test_e2e_domain_creation_workflow.py`**
**Journey:** Admin Setup & Domain Creation
**Priority:** 🔴 HIGH
**Complexity:** Medium

**Test Scenario:**
```python
class TestDomainCreationWorkflow:
    """Test complete domain creation workflow with DSPy training."""

    async def test_complete_domain_creation_workflow(
        self,
        page: Page,
        sample_training_dataset: Path
    ):
        """
        Test creating a new domain with DSPy training end-to-end.

        Steps:
        1. Navigate to /admin/domain-training
        2. Click "New Domain" button
        3. Fill domain config (name, description, LLM model)
        4. Upload training dataset
        5. Start training
        6. Monitor SSE training logs
        7. Wait for completion
        8. Verify domain appears in list with "ready" status
        """
        # 1. Navigate to domain training page
        await page.goto("http://localhost:5179/admin/domain-training")
        await page.wait_for_load_state("networkidle")

        # 2. Click "New Domain" button
        new_domain_btn = page.locator('[data-testid="new-domain-button"]')
        await new_domain_btn.click()

        # 3. Wait for wizard to appear
        wizard = page.locator('[data-testid="new-domain-wizard"]')
        await wizard.wait_for(state="visible")

        # Step 1: Domain Config
        await page.locator('input[name="name"]').fill("test-legal-domain")
        await page.locator('input[name="description"]').fill("Legal document analysis")
        await page.locator('select[name="llm_model"]').select_option("qwen3:32b")
        await page.locator('button:has-text("Next")').click()

        # Step 2: Dataset Upload
        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files(str(sample_training_dataset))

        # Wait for preview
        await page.wait_for_selector('[data-testid="dataset-preview"]', timeout=5000)

        # Start training
        await page.locator('button:has-text("Start Training")').click()

        # Step 3: Monitor training progress
        progress_step = page.locator('[data-testid="training-progress-step"]')
        await progress_step.wait_for(state="visible")

        # Wait for training completion (SSE stream)
        # Look for completion message or success indicator
        await page.wait_for_selector('text=/training.*complete/i', timeout=120000)

        # Close wizard
        await page.locator('button:has-text("Close"), button:has-text("Done")').first.click()

        # Verify domain in list
        domain_list = page.locator('[data-testid="domain-list"]')
        await domain_list.wait_for(state="visible")

        # Check domain appears with "ready" status
        new_domain_item = domain_list.locator('text="test-legal-domain"')
        assert await new_domain_item.count() > 0, "New domain should appear in list"

        # Verify status badge shows "ready"
        status_badge = new_domain_item.locator('..').locator('[data-testid="domain-status"]')
        status_text = await status_badge.inner_text()
        assert "ready" in status_text.lower(), "Domain should be in ready state"
```

**Fixtures Needed:**
```python
@pytest.fixture
async def sample_training_dataset(tmp_path_factory) -> Path:
    """Create sample training dataset for domain creation."""
    dataset = [
        {
            "query": "What is a contract breach?",
            "answer": "A contract breach occurs when one party fails to fulfill their obligations..."
        },
        {
            "query": "Define force majeure clause",
            "answer": "A force majeure clause excuses performance when extraordinary events..."
        },
        # ... 10-20 samples total
    ]

    dataset_path = tmp_path_factory.mktemp("training") / "legal_dataset.json"
    dataset_path.write_text(json.dumps(dataset, indent=2))
    return dataset_path
```

**Validation Points:**
- Domain creation successful
- Training completes without errors
- Live SSE logs display
- Domain appears in list
- Status shows "ready" after training

---

#### 2. **`test_e2e_upload_page_domain_classification.py`**
**Journey:** Document Upload with AI Domain Classification
**Priority:** 🔴 HIGH
**Complexity:** Medium

**Test Scenario:**
```python
class TestUploadPageDomainClassification:
    """Test document upload with automatic domain classification."""

    async def test_document_upload_with_domain_classification(
        self,
        page: Page,
        sample_documents_various_domains: list[Path]
    ):
        """
        Test uploading documents with AI domain classification.

        Steps:
        1. Navigate to /admin/upload
        2. Upload multiple documents (different domains)
        3. Wait for AI classification
        4. Verify domain suggestions with confidence scores
        5. Override one domain manually
        6. Submit upload
        7. Validate documents indexed with correct domains
        """
        # 1. Navigate to upload page
        await page.goto("http://localhost:5179/admin/upload")
        await page.wait_for_load_state("networkidle")

        # 2. Upload multiple documents
        file_input = page.locator('[data-testid="file-input"]')
        await file_input.set_input_files([str(p) for p in sample_documents_various_domains])

        # 3. Wait for classification
        await asyncio.sleep(3)  # Give time for DSPy classification

        # 4. Verify domain suggestions appear
        file_list = page.locator('[data-testid="uploaded-files-list"]')
        await file_list.wait_for(state="visible")

        # Check first file has domain suggestion
        first_file = file_list.locator('[data-testid^="file-item-"]').first
        domain_badge = first_file.locator('[data-testid="domain-suggestion"]')
        await domain_badge.wait_for(state="visible")

        # Verify confidence badge present
        confidence_badge = first_file.locator('[data-testid="confidence-badge"]')
        await confidence_badge.wait_for(state="visible")
        confidence_text = await confidence_badge.inner_text()
        assert any(level in confidence_text for level in ["High", "Medium", "Low"]), \
            "Confidence badge should show level"

        # 5. Override domain for second file
        second_file = file_list.locator('[data-testid^="file-item-"]').nth(1)
        domain_selector = second_file.locator('[data-testid="domain-selector"]')
        await domain_selector.click()

        # Select different domain
        await page.locator('[data-testid="domain-option-general"]').click()

        # 6. Submit upload
        upload_button = page.locator('button:has-text("Upload"), button[type="submit"]')
        await upload_button.click()

        # Wait for upload completion
        await page.wait_for_selector('text=/upload.*complete/i, text=/success/i', timeout=60000)

        # 7. Validate documents indexed (check via API or database)
        # This would require API calls to verify correct domain assignment
```

**Fixtures Needed:**
```python
@pytest.fixture
async def sample_documents_various_domains(tmp_path_factory) -> list[Path]:
    """Create sample documents for different domains."""
    docs_dir = tmp_path_factory.mktemp("upload_docs")

    # Legal document
    legal_doc = docs_dir / "contract_review.txt"
    legal_doc.write_text("""
    CONTRACT REVIEW AGREEMENT

    This contract review agreement establishes the terms for legal analysis
    of business contracts. The reviewer shall examine force majeure clauses,
    indemnification provisions, and dispute resolution mechanisms.
    """)

    # Medical document
    medical_doc = docs_dir / "patient_care.txt"
    medical_doc.write_text("""
    PATIENT CARE PROTOCOL

    This protocol outlines treatment procedures for cardiovascular conditions.
    Includes guidelines for medication administration, vital sign monitoring,
    and emergency response procedures.
    """)

    # Technical document
    tech_doc = docs_dir / "api_documentation.txt"
    tech_doc.write_text("""
    REST API DOCUMENTATION

    This API provides endpoints for data retrieval and manipulation.
    Supports JSON and XML formats. Authentication via OAuth 2.0.
    Rate limiting: 1000 requests per hour.
    """)

    return [legal_doc, medical_doc, tech_doc]
```

---

#### 3. **`test_e2e_graph_exploration_workflow.py`**
**Journey:** Knowledge Graph Exploration
**Priority:** 🔴 HIGH
**Complexity:** High

**Test Scenario:**
```python
class TestGraphExplorationWorkflow:
    """Test complete graph exploration workflow."""

    @pytest.fixture(scope="class")
    async def indexed_graph_documents(self, tmp_path_factory) -> list[Path]:
        """Create and index documents that form an interesting graph."""
        docs_dir = tmp_path_factory.mktemp("graph_docs")

        # Document 1: Stanford AI Lab
        doc1 = docs_dir / "stanford_ai.txt"
        doc1.write_text("""
        Stanford Artificial Intelligence Laboratory

        The Stanford AI Lab was founded by John McCarthy in 1962.
        Andrew Ng worked at Stanford and co-founded Coursera.
        Fei-Fei Li is a Stanford professor who created ImageNet.
        """)

        # Document 2: Google Brain
        doc2 = docs_dir / "google_brain.txt"
        doc2.write_text("""
        Google Brain Research

        Google Brain was co-founded by Andrew Ng and Jeff Dean.
        The team developed TensorFlow, an open-source ML framework.
        Ray Kurzweil joined Google as Director of Engineering.
        """)

        # Document 3: Deep Learning Pioneers
        doc3 = docs_dir / "deep_learning.txt"
        doc3.write_text("""
        Deep Learning Pioneers

        Geoffrey Hinton is considered a father of deep learning.
        Yann LeCun developed convolutional neural networks at NYU.
        Yoshua Bengio founded Mila, the Quebec AI Institute.
        All three won the Turing Award in 2018.
        """)

        return [doc1, doc2, doc3]

    async def test_complete_graph_exploration_workflow(
        self,
        page: Page,
        indexed_graph_documents: list[Path],
        qdrant_client,
        neo4j_driver
    ):
        """
        Test exploring the knowledge graph end-to-end.

        Steps:
        1. Upload documents to create graph
        2. Navigate to /admin/graph
        3. View graph statistics
        4. Apply filters
        5. Explore nodes and edges
        6. View communities
        7. Export graph
        """
        # 1. Upload documents first (reuse upload logic)
        await page.goto("http://localhost:5179/admin/upload")
        await page.wait_for_load_state("networkidle")

        file_input = page.locator('input[type="file"]')
        await file_input.set_input_files([str(p) for p in indexed_graph_documents])

        # Wait and submit upload
        await asyncio.sleep(2)
        upload_btn = page.locator('button:has-text("Upload")').first
        await upload_btn.click(force=True)

        # Wait for indexing to complete (60 seconds max)
        await asyncio.sleep(30)  # Allow time for graph construction

        # 2. Navigate to graph analytics
        await page.goto("http://localhost:5179/admin/graph")
        await page.wait_for_load_state("networkidle")

        # Wait for graph to render
        graph_viewer = page.locator('[data-testid="graph-viewer"]')
        await graph_viewer.wait_for(state="visible", timeout=10000)

        # 3. View graph statistics
        stats_section = page.locator('[data-testid="graph-statistics"]')
        await stats_section.wait_for(state="visible")

        # Validate statistics present
        node_count = page.locator('[data-testid="stat-nodes"]')
        assert await node_count.is_visible(), "Node count should be visible"

        edge_count = page.locator('[data-testid="stat-edges"]')
        assert await edge_count.is_visible(), "Edge count should be visible"

        community_count = page.locator('[data-testid="stat-communities"]')
        assert await community_count.is_visible(), "Community count should be visible"

        # Get actual counts
        node_count_text = await node_count.inner_text()
        print(f"Graph has {node_count_text} nodes")

        # 4. Apply filters
        # Select specific entity types
        filters_section = page.locator('[data-testid="graph-filters"]')
        await filters_section.wait_for(state="visible")

        # Select only PERSON and ORGANIZATION
        person_checkbox = page.locator('input[type="checkbox"][value="PERSON"]')
        if not await person_checkbox.is_checked():
            await person_checkbox.click()

        org_checkbox = page.locator('input[type="checkbox"][value="ORGANIZATION"]')
        if not await org_checkbox.is_checked():
            await org_checkbox.click()

        # Uncheck others
        location_checkbox = page.locator('input[type="checkbox"][value="LOCATION"]')
        if await location_checkbox.is_checked():
            await location_checkbox.click()

        # Apply filter button
        apply_filters_btn = page.locator('button:has-text("Apply Filters")')
        if await apply_filters_btn.is_visible():
            await apply_filters_btn.click()
            await asyncio.sleep(2)  # Wait for re-render

        # 5. Explore nodes
        # Click on a node (Andrew Ng should be present)
        # Use canvas interaction or search for entity
        search_input = page.locator('[data-testid="graph-search-input"]')
        if await search_input.is_visible():
            await search_input.fill("Andrew Ng")
            await page.keyboard.press("Enter")
            await asyncio.sleep(1)

            # Node details panel should appear
            details_panel = page.locator('[data-testid="node-details-panel"]')
            await details_panel.wait_for(state="visible", timeout=5000)

            # Verify entity name
            entity_name = details_panel.locator('[data-testid="entity-name"]')
            name_text = await entity_name.inner_text()
            assert "Andrew Ng" in name_text, "Should show Andrew Ng entity"

            # Verify connected entities shown
            connections = details_panel.locator('[data-testid="connected-entities"]')
            await connections.wait_for(state="visible")

            # Should show connections to Stanford, Google Brain, Coursera
            connection_list = await connections.inner_text()
            assert any(org in connection_list for org in ["Stanford", "Google", "Coursera"]), \
                "Should show organizational connections"

        # 6. View communities
        communities_section = page.locator('[data-testid="community-highlight"]')
        if await communities_section.is_visible():
            # Click first community
            first_community = communities_section.locator('[data-testid^="community-"]').first
            await first_community.click()

            # Graph should highlight community
            await asyncio.sleep(1)

            # Community documents should show
            community_docs = page.locator('[data-testid="community-documents"]')
            if await community_docs.is_visible():
                docs_text = await community_docs.inner_text()
                assert len(docs_text) > 0, "Should show community documents"

        # 7. Export graph
        export_button = page.locator('[data-testid="export-graph-button"]')
        if await export_button.is_visible():
            # Click export
            await export_button.click()

            # Select format (GraphML)
            format_selector = page.locator('select[name="export-format"], [data-testid="export-format-select"]')
            if await format_selector.is_visible():
                await format_selector.select_option("graphml")

            # Start download (this may trigger file download)
            async with page.expect_download() as download_info:
                download_btn = page.locator('button:has-text("Download"), button:has-text("Export")')
                await download_btn.click()

            download = await download_info.value
            assert download.suggested_filename.endswith('.graphml'), \
                "Should download GraphML file"

            print(f"✓ Graph exported: {download.suggested_filename}")
```

**Validation Points:**
- Graph renders without errors
- Statistics show correct counts
- Filters apply successfully
- Node details panel shows entity info
- Communities detected and highlightable
- Export functionality works

---

#### 4. **`test_e2e_community_detection_workflow.py`**
**Journey:** Community Detection & Analysis
**Priority:** 🟡 MEDIUM
**Complexity:** Medium

**Test Scenario:**
```python
class TestCommunityDetectionWorkflow:
    """Test community detection and analysis workflow."""

    async def test_community_detection_and_analysis(
        self,
        page: Page,
        neo4j_driver
    ):
        """
        Test finding and analyzing semantic communities.

        Steps:
        1. Navigate to graph analytics
        2. View community list
        3. Select community
        4. Analyze community composition
        5. View community documents
        6. Validate semantic coherence
        """
        # Prerequisite: Graph must have communities detected
        # Check via Neo4j
        async with neo4j_driver.session() as session:
            result = await session.run("""
                MATCH (n)
                WHERE n.community IS NOT NULL
                RETURN count(DISTINCT n.community) as community_count
            """)
            record = await result.single()
            community_count = record["community_count"]

            assert community_count > 0, "Graph must have communities detected"
            print(f"✓ Found {community_count} communities in graph")

        # Navigate to graph
        await page.goto("http://localhost:5179/admin/graph")
        await page.wait_for_load_state("networkidle")

        # Wait for communities to load
        communities_list = page.locator('[data-testid="top-communities"]')
        await communities_list.wait_for(state="visible", timeout=10000)

        # Get community count from UI
        community_items = page.locator('[data-testid^="community-item-"]')
        ui_community_count = await community_items.count()

        assert ui_community_count > 0, "Should display communities in UI"
        print(f"✓ UI shows {ui_community_count} communities")

        # Select first community
        first_community = community_items.first
        community_name = await first_community.locator('[data-testid="community-name"]').inner_text()
        await first_community.click()

        print(f"✓ Selected community: {community_name}")

        # Verify graph highlights community
        await asyncio.sleep(1)

        # Community documents panel should appear
        community_docs_panel = page.locator('[data-testid="community-documents"]')
        if await community_docs_panel.is_visible():
            # Count documents in community
            doc_items = community_docs_panel.locator('[data-testid^="doc-"]')
            doc_count = await doc_items.count()

            assert doc_count > 0, "Community should have associated documents"
            print(f"✓ Community has {doc_count} documents")

            # Verify document titles shown
            first_doc = doc_items.first
            doc_title = await first_doc.locator('[data-testid="doc-title"]').inner_text()
            assert len(doc_title) > 0, "Document should have title"

        # Get community statistics from details panel
        stats_panel = page.locator('[data-testid="community-stats"]')
        if await stats_panel.is_visible():
            # Node count
            node_count_elem = stats_panel.locator('[data-testid="community-node-count"]')
            if await node_count_elem.is_visible():
                node_count_text = await node_count_elem.inner_text()
                print(f"✓ Community node count: {node_count_text}")

            # Density
            density_elem = stats_panel.locator('[data-testid="community-density"]')
            if await density_elem.is_visible():
                density_text = await density_elem.inner_text()
                print(f"✓ Community density: {density_text}")

        # Validate semantic coherence (via Neo4j)
        async with neo4j_driver.session() as session:
            # Get entities in the selected community
            result = await session.run("""
                MATCH (n)
                WHERE n.community = $community_id
                RETURN n.name as name, labels(n) as types
                LIMIT 10
            """, community_id=community_name)

            entities = [record async for record in result]

            assert len(entities) > 0, "Community should have entities"
            print(f"✓ Community entities: {[e['name'] for e in entities]}")

            # Check entity types - should have some coherence
            entity_types = [e['types'][0] for e in entities if e['types']]
            print(f"✓ Entity types in community: {set(entity_types)}")
```

---

#### 5. **`test_e2e_chat_streaming_and_citations.py`**
**Journey:** Chat with Streaming & Citations
**Priority:** 🔴 HIGH
**Complexity:** High

**Test Scenario:**
```python
class TestChatStreamingAndCitations:
    """Test chat interface with streaming responses and citations."""

    async def test_chat_with_streaming_and_citations(
        self,
        page: Page,
        indexed_documents: list[Path]
    ):
        """
        Test complete chat workflow with streaming and citations.

        Steps:
        1. Navigate to homepage (chat)
        2. Enter query
        3. Watch streaming response
        4. Verify phase indicators
        5. Check citations appear
        6. Click citation to view source
        7. Ask follow-up question
        8. Test session persistence
        """
        # Navigate to chat
        await page.goto("http://localhost:5179/")
        await page.wait_for_load_state("networkidle")

        # Verify welcome screen
        welcome = page.locator('[data-testid="welcome-screen"]')
        if await welcome.is_visible():
            print("✓ Welcome screen displayed")

        # Enter query
        chat_input = page.locator('textarea[placeholder*="question"], textarea[placeholder*="message"], input[type="text"]')
        await chat_input.fill("What is machine learning and who are its pioneers?")

        # Submit query
        send_button = page.locator('button[type="submit"], button:has-text("Send")')
        await send_button.click()

        print("✓ Query submitted")

        # Watch for phase indicators (Sprint 48)
        retrieval_phase = page.locator('text=/retrieval/i, [data-phase="retrieval"]')
        if await retrieval_phase.is_visible(timeout=5000):
            print("✓ Retrieval phase indicator shown")

        reasoning_phase = page.locator('text=/reasoning/i, [data-phase="reasoning"]')
        # Don't wait long as it might not appear

        generation_phase = page.locator('text=/generat/i, [data-phase="generation"]')
        # Optional check

        # Wait for streaming to start
        # Look for assistant message container
        assistant_message = page.locator('[data-role="assistant"], .message-assistant').last
        await assistant_message.wait_for(state="visible", timeout=30000)

        print("✓ Streaming response started")

        # Wait for streaming to complete
        # Look for completion indicator or wait for text to stop changing
        await asyncio.sleep(10)  # Allow streaming to complete

        # Get final response text
        response_text = await assistant_message.inner_text()

        assert len(response_text) > 100, "Response should have substantial content"
        assert any(keyword in response_text.lower() for keyword in ["machine learning", "ml", "artificial intelligence"]), \
            "Response should mention machine learning"

        print(f"✓ Received response ({len(response_text)} chars)")

        # Check for citations
        citations = page.locator('[data-citation], .citation, [data-testid="source-card"]')
        citation_count = await citations.count()

        assert citation_count > 0, "Response should have citations"
        print(f"✓ Found {citation_count} citations")

        # Click first citation
        first_citation = citations.first
        await first_citation.click()

        # Citation panel should appear
        citation_panel = page.locator('[role="dialog"], [data-testid="citation-panel"], [data-testid="source-panel"]')
        if await citation_panel.is_visible(timeout=5000):
            # Verify citation content
            citation_text = await citation_panel.inner_text()
            assert len(citation_text) > 20, "Citation should show source text"
            print("✓ Citation panel opened with source text")

            # Close panel
            close_button = citation_panel.locator('button[aria-label="Close"], button:has-text("×")')
            if await close_button.is_visible():
                await close_button.click()

        # Check for follow-up questions
        followup_questions = page.locator('[data-testid="follow-up-questions"]')
        if await followup_questions.is_visible():
            questions = followup_questions.locator('button, a')
            question_count = await questions.count()

            if question_count > 0:
                print(f"✓ {question_count} follow-up questions suggested")

                # Click first follow-up
                first_followup = questions.first
                followup_text = await first_followup.inner_text()
                await first_followup.click()

                print(f"✓ Clicked follow-up: {followup_text}")

                # Wait for new response
                await asyncio.sleep(5)

        # Verify session persistence
        # Refresh page
        await page.reload()
        await page.wait_for_load_state("networkidle")

        # Check if conversation history persists
        messages = page.locator('[data-role="assistant"], .message-assistant')
        persisted_count = await messages.count()

        if persisted_count > 0:
            print(f"✓ Session persisted ({persisted_count} messages)")
        else:
            print("⚠ Session not persisted (may be expected behavior)")
```

---

#### 6. **`test_e2e_session_management.py`**
**Journey:** Session Management & History
**Priority:** 🟡 MEDIUM
**Complexity:** Medium

**Test Scenario:**
```python
class TestSessionManagement:
    """Test session management and history features."""

    async def test_session_management_workflow(self, page: Page):
        """
        Test complete session management workflow.

        Steps:
        1. Create new chat session
        2. Have conversation
        3. View session in sidebar
        4. Rename session
        5. Create second session
        6. Switch between sessions
        7. Archive session
        8. Share session
        9. Delete session
        """
        # 1. Create new chat
        await page.goto("http://localhost:5179/")
        await page.wait_for_load_state("networkidle")

        # Submit first query
        chat_input = page.locator('textarea, input[type="text"]')
        await chat_input.fill("What is Python?")
        await page.keyboard.press("Enter")

        # Wait for response
        await asyncio.sleep(10)

        # 2. Open session sidebar
        sidebar_toggle = page.locator('[aria-label="Toggle sidebar"], button:has-text("History")')
        if await sidebar_toggle.is_visible():
            await sidebar_toggle.click()

            # Sidebar should appear
            sidebar = page.locator('[data-testid="session-sidebar"]')
            await sidebar.wait_for(state="visible")

            # Session should be listed
            sessions = sidebar.locator('[data-testid^="session-"]')
            session_count = await sessions.count()

            assert session_count >= 1, "Should have at least one session"
            print(f"✓ Found {session_count} session(s) in sidebar")

            # 3. Rename session
            first_session = sessions.first

            # Click edit button
            edit_button = first_session.locator('button[aria-label*="Edit"], [data-testid="edit-session"]')
            if await edit_button.is_visible():
                await edit_button.click()

                # Enter new title
                title_input = page.locator('input[data-testid="session-title-input"]')
                await title_input.fill("Python Discussion")
                await page.keyboard.press("Enter")

                # Verify title changed
                await asyncio.sleep(1)
                session_title = await first_session.locator('[data-testid="session-title"]').inner_text()
                assert "Python Discussion" in session_title, "Session title should update"
                print("✓ Session renamed successfully")

            # 4. Create second session
            new_chat_btn = page.locator('button:has-text("New Chat"), button:has-text("Neu")')
            await new_chat_btn.click()

            # Enter new query
            await chat_input.fill("Explain machine learning")
            await page.keyboard.press("Enter")
            await asyncio.sleep(10)

            # 5. Verify two sessions exist
            sessions_after = sidebar.locator('[data-testid^="session-"]')
            new_session_count = await sessions_after.count()

            assert new_session_count >= 2, "Should have two sessions now"
            print(f"✓ Now have {new_session_count} sessions")

            # 6. Switch to first session
            first_session = sessions_after.first
            await first_session.click()

            # Verify conversation loaded
            await asyncio.sleep(2)
            messages = page.locator('[data-role="user"], .message-user')
            user_messages = [await msg.inner_text() for msg in await messages.all()]

            assert any("Python" in msg for msg in user_messages), \
                "Should load first session about Python"
            print("✓ Switched to first session successfully")

            # 7. Archive session
            second_session = sessions_after.nth(1)
            archive_btn = second_session.locator('button[aria-label*="Archive"], [data-testid="archive-session"]')

            if await archive_btn.is_visible():
                await archive_btn.click()

                # Confirm if needed
                confirm_btn = page.locator('button:has-text("Archive"), button:has-text("Confirm")')
                if await confirm_btn.is_visible():
                    await confirm_btn.click()

                await asyncio.sleep(1)

                # Session should be archived (may disappear or show archived status)
                print("✓ Session archived")

            # 8. Share session
            share_btn = first_session.locator('button[aria-label*="Share"], [data-testid="share-session"]')

            if await share_btn.is_visible():
                await share_btn.click()

                # Share modal should appear
                share_modal = page.locator('[data-testid="share-modal"], [role="dialog"]')
                await share_modal.wait_for(state="visible", timeout=5000)

                # Generate link
                generate_btn = share_modal.locator('button:has-text("Generate"), button:has-text("Create Link")')
                if await generate_btn.is_visible():
                    await generate_btn.click()
                    await asyncio.sleep(1)

                    # Share link should appear
                    share_link_input = share_modal.locator('input[value*="/share/"], [data-testid="share-link"]')
                    if await share_link_input.is_visible():
                        share_link = await share_link_input.input_value()
                        assert "/share/" in share_link, "Should generate share link"
                        print(f"✓ Share link generated: {share_link}")

                        # Close modal
                        close_btn = share_modal.locator('button:has-text("Close"), button[aria-label="Close"]')
                        if await close_btn.is_visible():
                            await close_btn.click()

            # 9. Delete session (use second session)
            # Refresh session list
            await asyncio.sleep(1)
            sessions_final = sidebar.locator('[data-testid^="session-"]')

            if await sessions_final.count() > 1:
                last_session = sessions_final.last
                delete_btn = last_session.locator('button[aria-label*="Delete"], [data-testid="delete-session"]')

                if await delete_btn.is_visible():
                    await delete_btn.click()

                    # Confirm deletion
                    confirm_delete = page.locator('button:has-text("Delete"), button:has-text("Confirm")')
                    if await confirm_delete.is_visible():
                        await confirm_delete.click()
                        await asyncio.sleep(1)

                        # Session should be removed
                        sessions_after_delete = await sidebar.locator('[data-testid^="session-"]').count()
                        print(f"✓ Session deleted (remaining: {sessions_after_delete})")
```

---

#### 7. **`test_e2e_cost_monitoring_workflow.py`**
**Journey:** Cost Monitoring & LLM Configuration
**Priority:** 🟡 MEDIUM
**Complexity:** Low

**Test Scenario:**
```python
class TestCostMonitoringWorkflow:
    """Test cost monitoring and LLM configuration."""

    async def test_cost_dashboard_display(self, page: Page):
        """Test cost dashboard displays correctly."""
        # Navigate to cost dashboard
        await page.goto("http://localhost:5179/admin/costs")
        await page.wait_for_load_state("networkidle")

        # Check dashboard elements
        dashboard = page.locator('[data-testid="cost-dashboard"]')
        await dashboard.wait_for(state="visible")

        # Total cost display
        total_cost = page.locator('[data-testid="total-cost"]')
        if await total_cost.is_visible():
            cost_text = await total_cost.inner_text()
            print(f"✓ Total cost: {cost_text}")

        # Cost by provider
        providers = ["Ollama", "Alibaba", "OpenAI"]
        for provider in providers:
            provider_cost = page.locator(f'[data-testid="cost-{provider.lower()}"]')
            if await provider_cost.is_visible():
                provider_cost_text = await provider_cost.inner_text()
                print(f"✓ {provider} cost: {provider_cost_text}")

        # Budget alerts
        budget_alert = page.locator('[data-testid="budget-alert"]')
        if await budget_alert.is_visible():
            alert_text = await budget_alert.inner_text()
            print(f"⚠ Budget alert: {alert_text}")

    async def test_llm_configuration(self, page: Page):
        """Test LLM configuration page."""
        await page.goto("http://localhost:5179/admin/llm-config")
        await page.wait_for_load_state("networkidle")

        # Check config form
        config_form = page.locator('[data-testid="llm-config-form"]')
        await config_form.wait_for(state="visible")

        # Primary provider selection
        primary_provider = page.locator('select[name="primary_provider"]')
        if await primary_provider.is_visible():
            await primary_provider.select_option("ollama")
            print("✓ Selected Ollama as primary provider")

        # Test connection button
        test_conn_btn = page.locator('button:has-text("Test Connection")')
        if await test_conn_btn.is_visible():
            await test_conn_btn.click()

            # Wait for result
            await asyncio.sleep(2)

            # Check for success message
            success_msg = page.locator('text=/connected/i, text=/success/i')
            if await success_msg.is_visible():
                print("✓ LLM connection test successful")
```

---

#### 8. **`test_e2e_health_monitoring.py`**
**Journey:** System Health & Monitoring
**Priority:** 🟡 MEDIUM
**Complexity:** Low

**Test Scenario:**
```python
class TestHealthMonitoring:
    """Test system health monitoring."""

    async def test_health_dashboard(self, page: Page):
        """Test health dashboard displays service status."""
        await page.goto("http://localhost:5179/health")
        await page.wait_for_load_state("networkidle")

        # Check service status indicators
        services = ["Qdrant", "Neo4j", "Redis", "Ollama", "API"]

        for service in services:
            service_status = page.locator(f'[data-testid="service-{service.lower()}"]')
            if await service_status.is_visible():
                status_text = await service_status.inner_text()
                print(f"✓ {service} status: {status_text}")

                # Check status indicator color
                status_icon = service_status.locator('[data-testid="status-icon"]')
                if await status_icon.is_visible():
                    # Green = healthy, Red = error, Yellow = warning
                    icon_class = await status_icon.get_attribute("class")
                    assert "bg-green" in icon_class or "bg-red" in icon_class or "bg-yellow" in icon_class

        # Test service connection
        qdrant_test = page.locator('button[data-testid="test-qdrant"]')
        if await qdrant_test.is_visible():
            await qdrant_test.click()
            await asyncio.sleep(1)

            # Check result
            test_result = page.locator('[data-testid="qdrant-test-result"]')
            if await test_result.is_visible():
                result_text = await test_result.inner_text()
                print(f"✓ Qdrant test result: {result_text}")
```

---

#### 9. **`test_e2e_indexing_pipeline_monitoring.py`**
**Journey:** Indexing Pipeline Monitoring
**Priority:** 🟡 MEDIUM
**Complexity:** Medium

**Test Scenario:**
```python
class TestIndexingPipelineMonitoring:
    """Test indexing pipeline monitoring."""

    async def test_indexing_pipeline_workflow(self, page: Page, sample_pdf: Path):
        """Test complete indexing pipeline with monitoring."""
        # Navigate to indexing page
        await page.goto("http://localhost:5179/admin/indexing")
        await page.wait_for_load_state("networkidle")

        # Check pipeline stages display
        stages = [
            "document_loading",
            "text_extraction",
            "chunking",
            "embedding",
            "entity_extraction",
            "relation_extraction",
            "graph_construction"
        ]

        for stage in stages:
            stage_elem = page.locator(f'[data-testid="stage-{stage}"]')
            if await stage_elem.is_visible():
                print(f"✓ Stage '{stage}' visible")

        # Trigger indexing
        index_btn = page.locator('button:has-text("Index Directory"), button:has-text("Start Indexing")')
        if await index_btn.is_visible():
            # May need to select directory first
            dir_input = page.locator('input[type="text"][name="directory"]')
            if await dir_input.is_visible():
                await dir_input.fill("/tmp/test_docs")

            await index_btn.click()
            print("✓ Started indexing")

            # Monitor progress via SSE
            # Watch for progress updates
            await asyncio.sleep(5)

            # Check live logs
            log_stream = page.locator('[data-testid="indexing-logs"]')
            if await log_stream.is_visible():
                logs_text = await log_stream.inner_text()
                assert len(logs_text) > 0, "Should show indexing logs"
                print(f"✓ Live logs displaying ({len(logs_text)} chars)")

            # Check worker pool status
            worker_pool = page.locator('[data-testid="worker-pool-display"]')
            if await worker_pool.is_visible():
                worker_text = await worker_pool.inner_text()
                print(f"✓ Worker pool: {worker_text}")

        # Check completion
        # Wait for indexing to complete or timeout
        completion_msg = page.locator('text=/indexing.*complete/i, text=/finished/i')
        try:
            await completion_msg.wait_for(state="visible", timeout=60000)
            print("✓ Indexing completed")
        except:
            print("⚠ Indexing timeout (may be expected for large datasets)")
```

---

### Medium Priority (Admin Features)

#### 10. **`test_e2e_graph_time_travel.py`** (Optional)
**Journey:** Graph Time Travel
**Priority:** 🟢 LOW
**Complexity:** High

*Only if time travel feature is implemented*

---

## 📊 E2E Test Implementation Plan

### Phase 1: High Priority User-Facing Features (Week 1)
**Goal:** Cover main user workflows

1. ✅ **Domain Creation** (`test_e2e_domain_creation_workflow.py`)
   - Effort: 1 day
   - Dependencies: DSPy training API, SSE streaming
   - Complexity: Medium

2. ✅ **Upload Page Classification** (`test_e2e_upload_page_domain_classification.py`)
   - Effort: 0.5 days
   - Dependencies: Document classification API
   - Complexity: Low-Medium

3. ✅ **Graph Exploration** (`test_e2e_graph_exploration_workflow.py`)
   - Effort: 2 days
   - Dependencies: Graph API, GraphViewer component
   - Complexity: High

4. ✅ **Chat Streaming** (`test_e2e_chat_streaming_and_citations.py`)
   - Effort: 1 day
   - Dependencies: Chat SSE API, Citations
   - Complexity: High

**Total:** ~4.5 days

---

### Phase 2: Admin & Session Management (Week 2)
**Goal:** Admin features and session handling

5. ✅ **Session Management** (`test_e2e_session_management.py`)
   - Effort: 1 day
   - Dependencies: Session API, Share API
   - Complexity: Medium

6. ✅ **Community Detection** (`test_e2e_community_detection_workflow.py`)
   - Effort: 1 day
   - Dependencies: Community detection, Neo4j
   - Complexity: Medium

7. ✅ **Indexing Monitoring** (`test_e2e_indexing_pipeline_monitoring.py`)
   - Effort: 0.5 days
   - Dependencies: Indexing SSE API
   - Complexity: Medium

**Total:** ~2.5 days

---

### Phase 3: Cost & Health Monitoring (Week 3)
**Goal:** System monitoring and configuration

8. ✅ **Cost Monitoring** (`test_e2e_cost_monitoring_workflow.py`)
   - Effort: 0.5 days
   - Dependencies: Cost tracking API
   - Complexity: Low

9. ✅ **Health Monitoring** (`test_e2e_health_monitoring.py`)
   - Effort: 0.5 days
   - Dependencies: Health check API
   - Complexity: Low

**Total:** ~1 day

---

### Total Effort Estimate: ~8 days (2 weeks)

---

## 🎯 Test Execution Strategy

### Local Execution
```bash
# Run all E2E tests
pytest tests/e2e/ -v -s

# Run specific journey
pytest tests/e2e/test_e2e_domain_creation_workflow.py -v -s

# Run in debug mode with visible browser
HEADED=1 pytest tests/e2e/ -v -s

# Run with slow motion for debugging
HEADED=1 SLOWMO=500 pytest tests/e2e/ -v -s
```

### CI/CD Integration
```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest

    services:
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333

      neo4j:
        image: neo4j:5.24-community
        ports:
          - 7687:7687
          - 7474:7474
        env:
          NEO4J_AUTH: neo4j/testpassword

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

      ollama:
        image: ollama/ollama:latest
        ports:
          - 11434:11434

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          poetry install --with dev,reranking
          poetry run playwright install chromium

      - name: Start backend
        run: |
          poetry run uvicorn src.api.main:app --port 8000 &
          sleep 10

      - name: Start frontend
        run: |
          cd frontend
          npm install
          npm run dev &
          sleep 10

      - name: Run E2E tests
        run: poetry run pytest tests/e2e/ -v --tb=short

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-screenshots
          path: tests/e2e/screenshots/
```

---

## 📝 Test Data Management

### Fixtures Organization
```
tests/e2e/
├── conftest.py                 # Shared fixtures
├── fixtures/
│   ├── documents.py            # Document fixtures
│   ├── datasets.py             # Training dataset fixtures
│   ├── graph_data.py           # Graph test data
│   └── sessions.py             # Session fixtures
```

### Shared Fixtures
```python
# tests/e2e/conftest.py

@pytest.fixture
async def qdrant_client():
    """Qdrant client for validation."""
    from qdrant_client import AsyncQdrantClient
    client = AsyncQdrantClient(url="http://localhost:6333")
    yield client
    await client.close()

@pytest.fixture
async def neo4j_driver():
    """Neo4j driver for validation."""
    from neo4j import AsyncGraphDatabase
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "testpassword")
    )
    yield driver
    await driver.close()

@pytest.fixture
async def redis_client():
    """Redis client for validation."""
    from redis.asyncio import Redis
    client = await Redis.from_url("redis://localhost:6379")
    yield client
    await client.aclose()
```

---

## 🔍 Quality Metrics

### Test Coverage Goals
- **User Journeys:** 100% (all critical paths)
- **Admin Features:** 90%
- **Error Scenarios:** 80%
- **Edge Cases:** 70%

### Performance Targets
- **Page Load:** < 3 seconds
- **Graph Render:** < 5 seconds
- **Search Response:** < 2 seconds (streaming start)
- **Upload Processing:** < 30 seconds per document

### Success Criteria
- ✅ All critical user journeys pass
- ✅ No console errors during normal operation
- ✅ Data consistency validated across systems
- ✅ Performance targets met
- ✅ Tests run reliably in CI/CD

---

## 🚀 Next Steps

1. **Review & Approve Plan** - Stakeholder sign-off
2. **Set Up Test Infrastructure** - CI/CD pipeline
3. **Implement Phase 1 Tests** - High priority user journeys
4. **Implement Phase 2 Tests** - Admin & session management
5. **Implement Phase 3 Tests** - Monitoring & configuration
6. **Integration & Refinement** - Fix flaky tests, optimize execution
7. **Documentation** - Update README with running instructions
8. **Continuous Maintenance** - Update tests with new features

---

**END OF USER JOURNEYS & E2E TEST PLAN**
