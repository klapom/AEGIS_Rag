# Skipped E2E Tests Summary

**Generated:** 2026-01-20  
**Source:** Comprehensive scan of `/frontend/e2e/` directory  
**Total Test Suites:** 23  
**Total Story Points:** 176 SP  
**Documentation:** See `docs/sprints/SPRINT_116_SKIPPED_TESTS_ANALYSIS.md`

## Quick Reference Table

| Category | Count | SP | Priority |
|----------|-------|----|---------| 
| Domain Management | 8 features | 53 | HIGH |
| Graph & Versioning | 5 features | 39 | MEDIUM |
| Research & Performance | 2 features | 26 | MEDIUM |
| MCP & Tools | 3 features | 21 | MEDIUM |
| Quality & Infrastructure | 4 features | 18 | MEDIUM |
| Admin Dashboard | 1 feature | 5 | LOW |
| **TOTAL** | **23 features** | **176** | - |

## Skipped Tests by File

### Domain Training API Tests
File: `test_domain_training_api.spec.ts`  
Status: All 7 test suites skipped  
Reason: Endpoint /api/v1/admin/domains/ returns 404

| Test Suite | Est. SP |
|-----------|---------|
| CRUD Operations | 13 |
| Classification | 8 |
| Auto-Discovery | 8 |
| Data Augmentation | 8 |
| Batch Ingestion | 8 |
| Domain Details | 5 |
| Input Validation | 5 |
| Response Format | 3 |
| **Subtotal** | **58** |

### Graph Versioning Tests
| File | Test | SP |
|------|------|----| 
| time-travel.spec.ts | Time Travel Tab (39.5) | 8 |
| version-compare.spec.ts | Version Comparison (39.7) | 13 |
| entity-changelog.spec.ts | Entity Changelog (39.6) | 10 |
| edge-filters.spec.ts | Edge Filters | 5 |
| graph-visualization.spec.ts | Graph Visualization | 8 |
| **Subtotal** | | **44** |

### MCP & Tool Tests
| File | Test | SP |
|------|------|----| 
| group01-mcp-tools.spec.ts | Tool Management | 8 |
| group02-bash-execution.spec.ts | Bash Execution | 8 |
| group12-graph-communities.spec.ts | Graph Communities | 5 |
| **Subtotal** | | **21** |

### Research & Performance Tests
| File | Test | SP |
|------|------|----| 
| group08-deep-research.spec.ts | Deep Research Multi-Step | 13 |
| performance-regression.spec.ts | Performance Regression | 13 |
| **Subtotal** | | **26** |

### Quality & Infrastructure Tests
| File | Test | SP |
|------|------|----| 
| visual-regression.example.spec.ts | Visual Regression Framework | 5 |
| api-errors.spec.ts | API Error Handling | 5 |
| citations.spec.ts | Citation Features (Tooltips + Linking) | 5 |
| **Subtotal** | | **15** |

### Admin Dashboard Tests
| File | Test | SP |
|------|------|----| 
| admin-dashboard.spec.ts | Stats Cards (46.8.9) | 5 |
| test_domain_training_flow.spec.ts | Default Domain Seeding | 3 |
| **Subtotal** | | **8** |

## Backend API Endpoints Required (53 endpoints)

### Domain Management (12 endpoints)
```
GET    /api/v1/admin/domains/
GET    /api/v1/admin/domains/{name}
GET    /api/v1/admin/domains/available-models
POST   /api/v1/admin/domains/
POST   /api/v1/admin/domains/classify
POST   /api/v1/admin/domains/discover
POST   /api/v1/admin/domains/augment
POST   /api/v1/admin/domains/ingest-batch
GET    /api/v1/admin/domains/{name}/training-status
POST   /api/v1/admin/domains/{id}/train
```

### Entity Versioning (5 endpoints)
```
GET    /api/v1/entities/{id}/versions
GET    /api/v1/entities/{id}/versions/{v1}/compare/{v2}
GET    /api/v1/entities/{id}/changelog
POST   /api/v1/entities/{id}/versions/{version}/revert
POST   /api/v1/temporal/point-in-time
```

### Dashboard & Admin (3 endpoints)
```
GET    /api/v1/admin/dashboard/stats
GET    /api/v1/admin/indexing/stats
GET    /api/v1/admin/settings
```

### MCP Tools (Already exist, UI needed)
```
GET    /api/v1/mcp/servers
GET    /api/v1/mcp/tools
GET    /api/v1/mcp/tools/{tool_name}
POST   /api/v1/mcp/tools/{tool_name}/execute
```

## Frontend Components Required

### Domain Training
- Domain list view
- Domain creation wizard (steps)
- Training dataset upload & preview
- Metric configuration UI
- Training progress monitor

### Graph Features
- TimeTravelTab (date slider, quick buttons)
- VersionCompareView (side-by-side diff)
- EntityChangelogPanel (history display)
- GraphEdgeFilter (type toggles, weight slider)
- Graph visualization (canvas/WebGL)

### MCP Tools
- MCPToolsPage (tool registry)
- Tool selector (combobox)
- Bash executor (command input)
- Tool toggles (enable/disable)

### Quality
- Citation tooltip (hover preview)
- Citation linker (scroll to source)
- Error boundary (graceful handling)
- Retry UI (for failed requests)
- StatCard (for metrics)

## Dependencies & Implementation Order

### Critical Path (Must implement first)
1. Domain Training API CRUD (13 SP) - Foundation for all domain features
2. Entity Versioning API (13 SP) - Foundation for time travel/changelog
3. MCP Tool Infrastructure (8 SP) - Foundation for tool execution

### Build on Critical Path
4. Domain Classification (8 SP) - Depends on CRUD
5. Domain Discovery (8 SP) - Depends on CRUD
6. Version Compare (13 SP) - Depends on Versioning API
7. Entity Changelog (10 SP) - Depends on Versioning API

### Everything Else (Independent)
8. Domain Augmentation (8 SP)
9. Domain Batch Ingestion (8 SP)
10. Time Travel Tab (8 SP)
11. Bash Tool Execution (8 SP)
12. And 13 more features...

## Files & Locations

- **Analysis Document:** `/docs/sprints/SPRINT_116_SKIPPED_TESTS_ANALYSIS.md`
- **Sprint Plan:** `/docs/sprints/SPRINT_116_PLAN.md`
- **Test Files:** `/frontend/e2e/` (16 directories with skipped tests)
- **This Summary:** `/SKIPPED_TESTS_SUMMARY.md`

## Recommendations

### For Sprint 116 (33 SP - quick wins)
1. Domain CRUD API (13 SP)
2. Default domain seeding (3 SP)
3. Admin dashboard stats (5 SP)
4. API error handling (5 SP)
5. Citation features (7 SP)

### For Sprint 117+ (143 SP - major features)
Start with entity versioning and domain classification to unblock 30+ story points of features.

---

**Last Updated:** 2026-01-20  
**Scope:** All E2E test files in `/frontend/e2e/` directory  
**Test Pattern:** Playwright with TypeScript fixtures
