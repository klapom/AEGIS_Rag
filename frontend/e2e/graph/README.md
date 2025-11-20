# Graph Visualization E2E Tests

## Overview

Sprint 31 Feature 31.8: Comprehensive E2E test suite for knowledge graph visualization.

- Total Tests: 17 E2E tests
- Query Graph Mode: 6 tests (relational query graphs)
- Admin Graph Mode: 11 tests (admin analytics page)

## Test Files

### query-graph.spec.ts (6 tests)
- Display query graph for relational questions
- Show entities and relationships
- Support zoom and pan interactions
- Close modal via multiple methods
- Export graph data
- Handle missing/error data

### admin-graph.spec.ts (11 tests)
- Display full knowledge graph
- Show graph statistics (nodes/edges)
- Filter by entity type
- Zoom controls
- Reset view
- Select nodes and view details
- Export visualization
- Toggle layout algorithm
- Handle empty graph, timeouts, filter errors

## Prerequisites

1. Ollama running on http://localhost:11434
2. Neo4j running on http://localhost:7687
3. Backend API on http://localhost:8000
4. Frontend on http://localhost:5173
5. At least 1-2 documents ingested for admin tests

## Running Tests

All graph tests:
```
npm run test:e2e -- e2e/graph/
```

Query graph only:
```
npm run test:e2e -- e2e/graph/query-graph.spec.ts
```

Admin graph only:
```
npm run test:e2e -- e2e/graph/admin-graph.spec.ts
```

Visual debugging:
```
npm run test:e2e:ui -- e2e/graph/
```

## Test Coverage

Features:
- Graph visualization (modal and admin page)
- User interactions (zoom, pan, filter, export)
- Node/edge rendering
- Error handling (network, empty, timeout)
- Responsive design

UI Elements:
- show-graph-button
- graph-modal
- graph-canvas
- graph-node/edge
- zoom-in, reset-view, export-graph
- graph-filter, layout-toggle

## Performance Notes

Timeouts:
- Graph load: 15 seconds
- Modal open: 10 seconds
- Graph update: 2-5 seconds
- Animation: 300-500ms

## Known Limitations

1. Export file download can't be fully validated
2. Canvas interactions have limited testing capability
3. Admin tests need ingested documents
4. Query graph tests work with any response

## Related Features

- Sprint 29 Feature 29.1: GraphViewer
- Sprint 29 Feature 29.2: GraphModal
- Sprint 29 Feature 29.3: GraphAnalyticsPage
- Sprint 31 Feature 31.8: E2E Tests
