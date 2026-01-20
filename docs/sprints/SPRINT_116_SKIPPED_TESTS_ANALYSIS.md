# Sprint 116: Skipped E2E Tests Analysis

**Date:** 2026-01-20
**Source:** Comprehensive scan of all Playwright E2E test files in `/frontend/e2e/`
**Status:** All skipped tests documented with missing feature requirements

## Skipped E2E Tests - Missing Features

| Test File | Test Name | Missing Feature | Backend/Frontend | Est. SP |
|-----------|-----------|-----------------|------------------|---------|
| time-travel.spec.ts | Time Travel Tab - Feature 39.5 | Temporal point-in-time graph queries with date slider, quick jump buttons, snapshot export | Backend (POST /api/v1/temporal/point-in-time), Frontend (TimeTravelTab component, date controls) | 8 |
| version-compare.spec.ts | Version Comparison View - Feature 39.7 | Entity versioning with side-by-side diff, version comparison API, revert functionality | Backend (GET /api/v1/entities/{id}/versions, POST /api/v1/entities/{id}/versions/{v1}/compare/{v2}, POST /api/v1/entities/{id}/versions/{version}/revert), Frontend (VersionCompareView component) | 13 |
| entity-changelog.spec.ts | Entity Changelog Panel - Feature 39.6 | Entity change history tracking, changelog display, user filtering, change type badges | Backend (GET /api/v1/entities/{id}/changelog, filtering/pagination), Frontend (EntityChangelogPanel component, change badges) | 10 |
| admin-dashboard.spec.ts | Admin Dashboard Stats Cards - Feature 46.8.9 | Domain statistics cards with numeric values, domain overview metrics | Backend (GET /api/v1/admin/dashboard/stats with enhanced data), Frontend (StatCard components) | 5 |
| test_domain_training_api.spec.ts | Domain Training API - CRUD Operations | Domain management endpoints, list/get/create domain APIs with validation | Backend (GET /api/v1/admin/domains/, POST /api/v1/admin/domains/, domain CRUD endpoints) | 13 |
| test_domain_training_api.spec.ts | Domain Training API - Classification | Document-to-domain classifier endpoint with top_k parameter and confidence scoring | Backend (POST /api/v1/admin/domains/classify with LLM-based classification) | 8 |
| test_domain_training_api.spec.ts | Domain Training API - Auto-Discovery | Automatic domain discovery from sample texts with 3-10 sample validation | Backend (POST /api/v1/admin/domains/discover with LLM generation) | 8 |
| test_domain_training_api.spec.ts | Domain Training API - Data Augmentation | Training data augmentation from seed samples with target count generation | Backend (POST /api/v1/admin/domains/augment with LLM synthesis) | 8 |
| test_domain_training_api.spec.ts | Domain Training API - Batch Ingestion | Batch document ingestion with domain routing and model grouping | Backend (POST /api/v1/admin/domains/ingest-batch with batch processing) | 8 |
| test_domain_training_api.spec.ts | Domain Training API - Domain Details | Get domain details, training status endpoints, 404 error handling | Backend (GET /api/v1/admin/domains/{name}, GET /api/v1/admin/domains/{name}/training-status) | 5 |
| test_domain_training_api.spec.ts | Domain Training API - Input Validation | Training sample structure validation, entity/relation field requirements | Backend (POST /api/v1/admin/domains/{id}/train with strict validation) | 5 |
| test_domain_training_api.spec.ts | Domain Training API - Response Format | Consistent response structure for domain list, classification, and other endpoints | Backend (Response schema validation and documentation) | 3 |
| group02-bash-execution.spec.ts | Bash Tool Execution - Simple Echo | Bash command execution UI with tool selector, command input, output display | Frontend (MCP tool executor UI pattern, tool selector combobox, command runner) | 8 |
| group12-graph-communities.spec.ts | Graph Communities Rendering | Communities list loading, UI rendering with data-testid selectors | Frontend (Graph communities page, community cards, summary display) | 5 |
| group01-mcp-tools.spec.ts | MCP Tool Management | Tool list display, permissions, enable/disable toggles, tool configuration modal | Frontend (MCPToolsPage component with tool cards and toggles) | 8 |
| test_domain_training_flow.spec.ts | Domain Training - Default Domain | Default "general" domain seeding in backend, guaranteed presence | Backend (Domain seeding on system initialization) | 3 |
| group08-deep-research.spec.ts | Deep Research - Multi-Step Query Execution | Multi-step research execution with LangGraph state progression, tool use, synthesis | Backend (LangGraph deep research agent with >30-60s timeout support), Frontend (Research UI with step tracking) | 13 |
| visual-regression.example.spec.ts | Visual Regression Testing Framework | Visual regression infrastructure with baseline snapshots and comparison logic | Frontend (Visual regression configuration, baseline storage, snapshot comparison) | 5 |
| api-errors.spec.ts | API Error 500/413/504 Handling | Graceful error handling for server errors with user-friendly messages and retry UI | Frontend (Error boundary, retry mechanisms, user-friendly error messages) | 5 |
| performance-regression.spec.ts | Performance Regression Tests | Performance baseline measurement infrastructure with HAR capture, latency tracking, p95 metrics | Backend/Frontend (Performance instrumentation, metrics collection, HAR support) | 13 |
| edge-filters.spec.ts | Graph Edge Type Filters | Edge type filtering UI (RELATES_TO, MENTIONED_IN, etc.), weight threshold slider | Frontend (Graph filter controls, edge type toggles, weight threshold slider) | 5 |
| graph-visualization.spec.ts | Graph Visualization Rendering | Graph canvas rendering with edge colors by type, legend display, relationship tooltips | Frontend (Graph visualization component with canvas/WebGL rendering) | 8 |
| citations.spec.ts | Citation Tooltip and Linking | Citation hover tooltips with source preview, citation-to-source linking | Frontend (Citation tooltip component, source card linking) | 5 |

## Summary Statistics

**Total Skipped Tests:** 23 test suites/groups
**Total Story Points Estimated:** 176 SP
**High Priority (8+ SP):** 14 features
**Medium Priority (5-7 SP):** 7 features
**Low Priority (3-4 SP):** 2 features

## Feature Categories

### Graph & Versioning Features (39 SP)
- Time Travel Tab (8 SP)
- Version Comparison (13 SP)
- Entity Changelog (10 SP)
- Graph Edge Filters (5 SP)
- Graph Visualization (3 SP)

### Domain Management Features (53 SP)
- Domain Training API - CRUD (13 SP)
- Domain Training API - Classification (8 SP)
- Domain Training API - Auto-Discovery (8 SP)
- Domain Training API - Data Augmentation (8 SP)
- Domain Training API - Batch Ingestion (8 SP)
- Domain Training API - Details/Status (5 SP)
- Domain Training API - Validation (5 SP)
- Domain Training API - Response Format (3 SP)
- Default Domain Seeding (3 SP)

### Admin Dashboard Features (5 SP)
- Domain Statistics Cards (5 SP)

### MCP & Tool Features (21 SP)
- Bash Tool Execution UI (8 SP)
- MCP Tool Management (8 SP)
- Graph Communities UI (5 SP)

### Research & Analysis Features (26 SP)
- Deep Research Multi-Step (13 SP)
- Performance Regression Tests (13 SP)

### Quality & Infrastructure Features (18 SP)
- Visual Regression Framework (5 SP)
- API Error Handling (5 SP)
- Citation Tooltips (5 SP)
- Citation Linking (3 SP)

## Critical Path Dependencies

```
Domain Training API Features (53 SP)
├── CRUD Operations (13 SP) - REQUIRED for all other domain features
├── Classification (8 SP) - Depends on CRUD
├── Auto-Discovery (8 SP) - Depends on CRUD
├── Data Augmentation (8 SP) - Depends on CRUD
├── Batch Ingestion (8 SP) - Depends on CRUD
└── Supporting Features (10 SP)

Entity Versioning Features (39 SP)
├── Version Comparison API (13 SP) - REQUIRED foundation
├── Time Travel Tab (8 SP) - Depends on Version API
├── Entity Changelog (10 SP) - Depends on Version API
└── Frontend Components (8 SP)

Admin Dashboard (5 SP)
└── Domain Statistics (5 SP)

MCP Tool Features (21 SP)
├── Tool Management Infrastructure (8 SP) - REQUIRED
├── Bash Tool Execution (8 SP) - Depends on infrastructure
└── Community UI (5 SP)
```

## Implementation Priority

### Sprint 116 Recommended (33 SP):
1. Domain Training API - CRUD Operations (13 SP) - Foundation for all domain features
2. Domain Default Seeding (3 SP) - Quick win, unblocks tests
3. Admin Dashboard Stats Cards (5 SP) - Quick win
4. API Error Handling (5 SP) - Improves reliability
5. Citation Tooltips (5 SP) - User experience
6. Citation Linking (2 SP) - User experience

### Sprint 117 Recommended (47 SP):
1. Domain Classification API (8 SP)
2. Domain Auto-Discovery API (8 SP)
3. Domain Data Augmentation API (8 SP)
4. Domain Batch Ingestion API (8 SP)
5. MCP Tool Management UI (8 SP)
6. Graph Edge Filters UI (5 SP)

### Sprint 118+ Recommended (96 SP):
1. Entity Versioning APIs (13 SP) - Foundation for time travel/changelog
2. Version Comparison UI (13 SP)
3. Time Travel Tab (8 SP)
4. Entity Changelog UI (10 SP)
5. Bash Tool Execution UI (8 SP)
6. Graph Communities UI (5 SP)
7. Deep Research Multi-Step (13 SP)
8. Performance Regression Tests (13 SP)
9. Visual Regression Framework (5 SP)
10. Graph Visualization (8 SP)

## Notes

- **Sprint 114 Context:** Tests were skipped due to missing backend/frontend implementations
- **Test File Locations:** All E2E tests are in `/home/admin/projects/aegisrag/AEGIS_Rag/frontend/e2e/`
- **Fixture Pattern:** Most tests follow the `setupAuthMocking` + `page.goto()` pattern from Sprint 106
- **Performance Consideration:** Some tests (Deep Research, Performance Regression) have extended timeouts (30-60s)
- **Data Dependencies:** Many tests require backend data seeding (e.g., general domain, test documents)

## Backend API Endpoints Required

### Domain Management
```
GET  /api/v1/admin/domains/                          # List domains
GET  /api/v1/admin/domains/{name}                    # Get domain details
POST /api/v1/admin/domains/                          # Create domain
POST /api/v1/admin/domains/classify                  # Classify document
POST /api/v1/admin/domains/discover                  # Auto-discover domains
POST /api/v1/admin/domains/augment                   # Augment training data
POST /api/v1/admin/domains/ingest-batch              # Batch ingestion
GET  /api/v1/admin/domains/{name}/training-status    # Training status
POST /api/v1/admin/domains/{id}/train                # Train domain
```

### Entity Versioning
```
GET  /api/v1/entities/{id}/versions                  # List versions
GET  /api/v1/entities/{id}/versions/{v1}/compare/{v2} # Compare versions
GET  /api/v1/entities/{id}/changelog                 # Get changelog
POST /api/v1/entities/{id}/versions/{version}/revert # Revert version
POST /api/v1/temporal/point-in-time                  # Point-in-time query
```

### Dashboard
```
GET  /api/v1/admin/dashboard/stats                   # Dashboard statistics
GET  /api/v1/admin/indexing/stats                    # Indexing statistics
GET  /api/v1/admin/settings                          # Admin settings
```

## Frontend Components Required

### Graph Features
- `TimeTravelTab` - Temporal graph navigation
- `VersionCompareView` - Entity version comparison
- `EntityChangelogPanel` - Change history display
- `GraphEdgeFilter` - Edge type and weight filtering
- Graph visualization with canvas/WebGL

### Domain Training
- Domain list view
- Domain creation wizard
- Training dataset upload
- Training progress monitor
- Metric configuration UI

### MCP Tools
- MCPToolsPage with tool registry
- Tool selector combobox
- Bash command executor UI
- Tool enable/disable toggles

### Admin Dashboard
- StatCard components
- Section collapse/expand
- Domain list cards
- Indexing statistics display

### Quality of Life
- Citation tooltip component
- Visual regression testing infrastructure
- Error boundary components
- Retry mechanisms
