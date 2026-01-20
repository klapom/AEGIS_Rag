# Skipped E2E Tests - Feature Requirements Table

**Generated:** 2026-01-20  
**Scope:** 23 skipped test suites across 16 E2E test files  
**Total Story Points:** 176 SP

## Skipped E2E Tests Summary

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

**Total: 176 Story Points across 23 skipped test suites**

---

For detailed analysis including dependencies, recommendations, and implementation priorities, see:
- **Detailed Analysis:** `/docs/sprints/SPRINT_116_SKIPPED_TESTS_ANALYSIS.md`
- **Sprint Planning:** `/docs/sprints/SPRINT_116_PLAN.md`
- **Quick Summary:** `/SKIPPED_TESTS_SUMMARY.md`
